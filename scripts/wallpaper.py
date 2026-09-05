"""Shared installation, KConfig migration and wallpaper synchronization."""

import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent.parent
PLUGIN_ID = json.loads((ROOT / "metadata.json").read_text())["KPlugin"]["Id"]
OLD_ID = "com.user.csswallpaper"
IDS = (PLUGIN_ID, OLD_ID)
SDDM = Path("/usr/share/sddm/themes/css-wallpaper")


class Config:
    """Edit selected KConfig keys while retaining unrelated lines and comments."""

    def __init__(self, path):
        self.path = Path(path)
        self.lines = self.path.read_text().splitlines(keepends=True) if self.path.exists() else []

    def rows(self):
        group = ""
        for index, line in enumerate(self.lines):
            stripped = line.strip()
            if stripped.startswith("[") and stripped.endswith("]"):
                group = stripped
            elif "=" in line and not stripped.startswith(("#", ";")):
                key, value = line.rstrip("\r\n").split("=", 1)
                yield index, group, key.strip(), value.strip()

    def values(self, group):
        return {key: value for _, section, key, value in self.rows() if section == group}

    def set(self, group, key, value):
        matches = [i for i, section, name, _ in self.rows() if section == group and name == key]
        if matches:
            self.lines[matches[-1]] = f"{key}={value}\n"
            for index in reversed(matches[:-1]):
                del self.lines[index]
            return
        headers = [i for i, line in enumerate(self.lines) if line.strip() == group]
        if headers:
            if not self.lines[headers[-1]].endswith("\n"):
                self.lines[headers[-1]] += "\n"
            self.lines.insert(headers[-1] + 1, f"{key}={value}\n")
        else:
            if self.lines and not self.lines[-1].endswith("\n"):
                self.lines[-1] += "\n"
            self.lines.extend([f"\n{group}\n", f"{key}={value}\n"])

    def remove_tree(self, prefix):
        keep = []
        remove = False
        for line in self.lines:
            section = line.strip()
            if section.startswith("[") and section.endswith("]"):
                remove = section == prefix or section.startswith(prefix + "[")
            if not remove:
                keep.append(line)
        self.lines = keep

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(prefix=f".{self.path.name}.", dir=self.path.parent)
        try:
            with os.fdopen(fd, "w") as stream:
                stream.writelines(self.lines)
                stream.flush()
                os.fsync(stream.fileno())
            if self.path.exists():
                shutil.copymode(self.path, temporary)
            os.replace(temporary, self.path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)


def defaults():
    tree = ET.parse(ROOT / "contents/config/main.xml")
    ns = {"k": "http://www.kde.org/standards/kcfg/1.0"}
    return {entry.attrib["name"]: entry.findtext("k:default", namespaces=ns)
            for entry in tree.findall(".//k:entry", ns)}


def user_paths():
    config = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    data = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local/share")
    if not config.is_absolute() or not data.is_absolute():
        raise ValueError("XDG_CONFIG_HOME and XDG_DATA_HOME must be absolute paths.")
    return config, data


def lock_group(plugin):
    return f"[Greeter][Wallpaper][{plugin}][General]"


def animation_path(settings, directories):
    # KConfig uses backslash escapes, including escaped spaces in file names.
    name = re.sub(r"\\([sntr\\])", lambda m: {"s": " ", "n": "\n", "t": "\t",
                  "r": "\r", "\\": "\\"}[m[1]], settings["HtmlFile"])
    if (not name or Path(name).name != name or name in (".", "..") or "\\" in name
            or any(ord(char) < 32 for char in name)):
        raise ValueError("HtmlFile must name an animation inside contents/html.")
    for directory in directories:
        path = directory / name
        if path.is_file():
            return path
    raise ValueError(f"Animation does not exist: {name}")


def validate(settings, directories):
    for key, low, high in (("RenderScale", 10, 100), ("FrameRate", 1, 360)):
        value = settings[key]
        if not re.fullmatch(r"[0-9]+", value) or not low <= int(value) <= high:
            raise ValueError(f"Invalid {key}: {value!r}; expected {low}..{high}.")
    if settings["Freeze"].lower() not in ("true", "false", "1", "0"):
        raise ValueError(f"Invalid Freeze: {settings['Freeze']!r}.")
    return animation_path(settings, directories)


def backup_lock(config):
    backup = config.path.with_name(config.path.name + ".css-wallpaper.bak")
    backup.parent.mkdir(parents=True, exist_ok=True)
    try:
        with backup.open("x") as stream:
            os.chmod(backup, 0o600)
            stream.writelines(config.lines)
    except FileExistsError:
        pass


def write_lock(config, settings):
    backup_lock(config)
    for key, value in settings.items():
        config.set(lock_group(PLUGIN_ID), key, value)
    config.set("[Greeter]", "WallpaperPlugin", PLUGIN_ID)
    config.save()
    # The replacement must be safely on disk before retiring the old group.
    config.remove_tree(f"[Greeter][Wallpaper][{OLD_ID}]")
    config.save()


def active_desktops(config):
    found = {}
    for _, group, key, value in config.rows():
        match = re.fullmatch(r"\[Containments\]\[([0-9]+)\]", group)
        if match and key == "wallpaperplugin":
            found[match[1]] = value
    return {key: value for key, value in found.items() if value in IDS}


def install(config_dir, data_dir):
    base = data_dir / "plasma/wallpapers"
    target = base / PLUGIN_ID
    lock = Config(config_dir / "kscreenlockerrc")
    settings = defaults()
    settings.update({k: v for k, v in lock.values(lock_group(OLD_ID)).items() if k in settings})
    settings.update({k: v for k, v in lock.values(lock_group(PLUGIN_ID)).items() if k in settings})
    validate(settings, [target / "contents/html", base / OLD_ID / "contents/html", ROOT / "contents/html"])
    target.mkdir(parents=True, exist_ok=True)
    old_html = base / OLD_ID / "contents/html"
    if old_html.is_dir():
        copy_missing(old_html, target / "contents/html")
    # Update code, but preserve all existing animations, even bundled-name edits.
    shutil.copy2(ROOT / "metadata.json", target / "metadata.json")
    for source in (ROOT / "contents").iterdir():
        destination = target / "contents" / source.name
        if source.name == "html":
            copy_missing(source, destination)
        elif source.is_dir():
            shutil.copytree(source, destination, dirs_exist_ok=True)
        else:
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
    write_lock(lock, settings)
    print(f"Installed {PLUGIN_ID} and configured the lock screen.\nAnimations: {target / 'contents/html'}")
    print("Select CSS Wallpaper in desktop settings. SDDM installation remains separate.")


def copy_missing(source, destination):
    destination.mkdir(parents=True, exist_ok=True)
    for item in source.iterdir():
        target = destination / item.name
        if item.is_dir():
            copy_missing(item, target)
        elif not target.exists():
            shutil.copy2(item, target)


def uninstall(config_dir, data_dir):
    lock = Config(config_dir / "kscreenlockerrc")
    changed = any(section.startswith(f"[Greeter][Wallpaper][{plugin}]")
                  for _, section, _, _ in lock.rows() for plugin in IDS)
    selected = lock.values("[Greeter]").get("WallpaperPlugin") in IDS
    if changed or selected:
        backup_lock(lock)
        if selected:
            lock.set("[Greeter]", "WallpaperPlugin", "org.kde.image")
        for plugin in IDS:
            lock.remove_tree(f"[Greeter][Wallpaper][{plugin}]")
        lock.save()
    installed = [data_dir / "plasma/wallpapers" / plugin for plugin in IDS]
    installed = [path for path in installed if path.exists()]
    if installed:
        backup_root = data_dir / "plasma/css-wallpaper-backups"
        backup_root.mkdir(parents=True, exist_ok=True)
        backup = Path(tempfile.mkdtemp(prefix=datetime.now().strftime("%Y%m%d-%H%M%S-"), dir=backup_root))
        for path in installed:
            shutil.copytree(path, backup / path.name, symlinks=True)
        # Delete only after every installed tree has a recoverable copy.
        for path in installed:
            shutil.rmtree(path)
        print(f"Wallpaper files backed up to {backup}")
    print("CSS Wallpaper removed. SDDM is managed separately.")
    if active_desktops(Config(config_dir / "plasma-org.kde.plasma.desktop-appletsrc")):
        print("A desktop still selects CSS Wallpaper: choose another wallpaper in desktop settings.")


def sync(config_dir, data_dir, containment, lock_only):
    desktops = Config(config_dir / "plasma-org.kde.plasma.desktop-appletsrc")
    active = active_desktops(desktops)
    if containment is None:
        if not active:
            raise ValueError("No desktop currently uses CSS Wallpaper.")
        containment = min(active, key=int)
    if containment not in active:
        raise ValueError(f"Containment {containment} does not exist or does not use CSS Wallpaper.")
    plugin = active[containment]
    settings = defaults()
    settings.update({k: v for k, v in desktops.values(
        f"[Containments][{containment}][Wallpaper][{plugin}][General]").items() if k in settings})
    target = data_dir / "plasma/wallpapers" / PLUGIN_ID
    if not (target / "metadata.json").is_file():
        raise ValueError("Install the current plugin with install.sh before synchronizing.")
    animation = validate(settings, [target / "contents/html"])
    write_lock(Config(config_dir / "kscreenlockerrc"), settings)
    print(f"Updated lock screen from containment {containment}, including Freeze.")
    if not lock_only and SDDM.is_dir():
        # One privileged invocation; the editor changes only these four keys.
        with tempfile.TemporaryDirectory(prefix="css-wallpaper-sync-") as temporary:
            override = Config(SDDM / "theme.conf.user")
            for key, value in {"type": "web", "webBackground": "html/" + animation.name,
                               "webFps": settings["FrameRate"], "webScale": settings["RenderScale"]}.items():
                override.set("[General]", key, value)
            staged = Path(temporary) / "theme.conf.user"
            override.path = staged
            override.save()
            subprocess.run(["pkexec", "bash", "-euc",
                            'mkdir -p -- "$1/html"; cp -a -- "$2/." "$1/html/"; '
                            'install -m 644 -- "$3" "$1/theme.conf.user"',
                            "css-wallpaper-sync", str(SDDM), str(target / "contents/html"), str(staged)], check=True)
        print(f"Updated SDDM animation settings: {SDDM / 'theme.conf.user'}")
    elif not lock_only:
        print("SDDM theme is not installed; run install-sddm-theme.sh separately if needed.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("install")
    commands.add_parser("uninstall")
    syncing = commands.add_parser("sync")
    syncing.add_argument("--lock-only", action="store_true", help="do not update SDDM")
    syncing.add_argument("containment", nargs="?")
    args = parser.parse_args()
    if os.geteuid() == 0:
        parser.exit(1, "Run this script as your desktop user, without sudo or root.\n")
    try:
        config, data = user_paths()
        if args.command == "sync":
            sync(config, data, args.containment, args.lock_only)
        elif args.command == "install":
            install(config, data)
        else:
            uninstall(config, data)
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"Error: {error}\n")


if __name__ == "__main__":
    main()
