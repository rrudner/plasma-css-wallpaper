"""Isolated lifecycle checks; never use the session's configuration or SDDM."""

import importlib.util
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("wallpaper", ROOT / "scripts/wallpaper.py")
w = importlib.util.module_from_spec(spec)
spec.loader.exec_module(w)


class Lifecycle(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.config = self.root / "config"
        self.data = self.root / "data"
        self.config.mkdir()
        self.lock = self.config / "kscreenlockerrc"
        self.desktop = self.config / "plasma-org.kde.plasma.desktop-appletsrc"
        self.target = self.data / "plasma/wallpapers" / w.PLUGIN_ID
        self.env = dict(os.environ, XDG_CONFIG_HOME=str(self.config), XDG_DATA_HOME=str(self.data))

    def command(self, script, *args, success=True):
        result = subprocess.run([str(ROOT / script), *args], cwd=self.root, env=self.env,
                                text=True, capture_output=True)
        self.assertEqual(result.returncode == 0, success, result.stdout + result.stderr)
        return result

    def values(self):
        return w.Config(self.lock).values(w.lock_group(w.PLUGIN_ID))

    def desktop_group(self, number, plugin=w.PLUGIN_ID, values=""):
        return (f"[Containments][{number}]\nwallpaperplugin={plugin}\n"
                f"[Containments][{number}][Wallpaper][{w.PLUGIN_ID}][General]\n{values}")

    def test_fresh_and_reinstall_from_other_directory(self):
        self.command("install.sh")
        self.assertEqual(self.values(), w.defaults())
        self.assertEqual(w.Config(self.lock).values("[Greeter]")["WallpaperPlugin"], w.PLUGIN_ID)
        backup = self.lock.with_name("kscreenlockerrc.css-wallpaper.bak")
        self.assertEqual(backup.read_bytes(), b"")
        custom = self.target / "contents/html/custom.html"
        custom.write_text("custom")
        bundled = self.target / "contents/html/deep-ocean.html"
        bundled.write_text("edited bundled animation")
        config = w.Config(self.lock)
        config.set(w.lock_group(w.PLUGIN_ID), "HtmlFile", "custom.html")
        config.set(w.lock_group(w.PLUGIN_ID), "Freeze", "true")
        config.save()
        self.command("install.sh")
        self.assertEqual(self.values()["HtmlFile"], "custom.html")
        self.assertEqual(self.values()["Freeze"], "true")
        self.assertEqual(custom.read_text(), "custom")
        self.assertEqual(bundled.read_text(), "edited bundled animation")
        self.assertEqual(backup.read_bytes(), b"")

    def test_migration_and_per_key_precedence(self):
        old = self.data / "plasma/wallpapers" / w.OLD_ID / "contents/html"
        old.mkdir(parents=True)
        (old / "mine.html").write_text("legacy custom")
        original = (f"[Greeter]\nWallpaperPlugin={w.OLD_ID}\n"
                    f"{w.lock_group(w.OLD_ID)}\nHtmlFile=mine.html\nFrameRate=25\nFreeze=true\n"
                    f"{w.lock_group(w.PLUGIN_ID)}\nFrameRate=144\n"
                    "[Other]\nKeep=yes\n")
        self.lock.write_text(original)
        self.command("install.sh")
        self.assertEqual(self.values(), dict(w.defaults(), HtmlFile="mine.html", FrameRate="144", Freeze="true"))
        self.assertNotIn(w.OLD_ID, self.lock.read_text())
        self.assertIn("Keep=yes", self.lock.read_text())
        self.assertEqual((self.target / "contents/html/mine.html").read_text(), "legacy custom")
        self.assertEqual(self.lock.with_name("kscreenlockerrc.css-wallpaper.bak").read_text(), original)

    def test_numeric_active_selection_and_explicit_selection(self):
        self.command("install.sh")
        self.desktop.write_text(self.desktop_group(10, values="FrameRate=120\n") +
                                self.desktop_group(1, "org.kde.image", "FrameRate=99\n") +
                                self.desktop_group(2, values="Freeze=true\n"))
        self.command("sync-login-wallpaper.sh", "--lock-only")
        self.assertEqual(self.values(), dict(w.defaults(), Freeze="true"))
        self.command("sync-login-wallpaper.sh", "10", "--lock-only")
        self.assertEqual(self.values()["FrameRate"], "120")
        before = self.lock.read_bytes()
        for number in ("1", "999", "garbage"):
            self.command("sync-login-wallpaper.sh", "--lock-only", number, success=False)
            self.assertEqual(self.lock.read_bytes(), before)

    def test_invalid_values_never_write(self):
        self.command("install.sh")
        before = self.lock.read_bytes()
        for values in ("FrameRate=0", "FrameRate=361", "FrameRate=abc", "FrameRate=",
                       "RenderScale=9", "RenderScale=101", "Freeze=maybe",
                       "HtmlFile=missing.html", "HtmlFile=../metadata.json"):
            with self.subTest(values=values):
                self.desktop.write_text(self.desktop_group(2, values=values + "\n"))
                self.command("sync-login-wallpaper.sh", "--lock-only", success=False)
                self.assertEqual(self.lock.read_bytes(), before)

    def test_uninstall_backs_up_both_ids_and_leaves_desktop(self):
        self.command("install.sh")
        old = self.data / "plasma/wallpapers" / w.OLD_ID
        old.mkdir()
        (old / "custom.html").write_text("recover me")
        self.desktop.write_text(self.desktop_group(2))
        before = self.desktop.read_bytes()
        result = self.command("uninstall.sh")
        self.assertIn("choose another wallpaper", result.stdout)
        self.assertEqual(self.desktop.read_bytes(), before)
        self.assertEqual(w.Config(self.lock).values("[Greeter]")["WallpaperPlugin"], "org.kde.image")
        self.assertFalse(self.target.exists())
        self.assertFalse(old.exists())
        backups = list((self.data / "plasma/css-wallpaper-backups").iterdir())
        self.assertEqual(len(backups), 1)
        self.assertEqual((backups[0] / w.OLD_ID / "custom.html").read_text(), "recover me")
        self.assertTrue((backups[0] / w.PLUGIN_ID / "metadata.json").is_file())
        self.command("uninstall.sh")

    def test_uninstall_preserves_other_plugin_and_cleans_legacy(self):
        for selected in ("other.plugin", w.OLD_ID):
            self.lock.write_text(f"[Greeter]\nWallpaperPlugin={selected}\n"
                                 f"{w.lock_group(w.OLD_ID)}\nFreeze=true\n"
                                 "[Greeter][Wallpaper][other.plugin][General]\nKeep=yes\n")
            self.command("uninstall.sh")
            result = self.lock.read_text()
            self.assertIn("Keep=yes", result)
            self.assertNotIn(w.OLD_ID, result)
            self.assertIn("WallpaperPlugin=" + ("org.kde.image" if selected == w.OLD_ID else selected), result)

    def test_failed_new_write_keeps_legacy_settings(self):
        self.lock.write_text(f"{w.lock_group(w.OLD_ID)}\nFreeze=true\n")
        original = self.lock.read_bytes()
        with patch.object(w.os, "replace", side_effect=OSError("simulated write failure")):
            with self.assertRaises(OSError):
                w.write_lock(w.Config(self.lock), w.defaults())
        self.assertEqual(self.lock.read_bytes(), original)

    def test_root_refused(self):
        with patch.object(w.os, "geteuid", return_value=0), patch("sys.argv", ["wallpaper.py", "install"]):
            with self.assertRaises(SystemExit) as result:
                w.main()
        self.assertEqual(result.exception.code, 1)
        self.assertFalse(self.lock.exists())

    def test_sddm_sync_preserves_unrelated_content(self):
        self.command("install.sh")
        self.desktop.write_text(self.desktop_group(2, values="FrameRate=144\nRenderScale=70\nFreeze=true\n"))
        sddm = self.root / "sddm"
        sddm.mkdir()
        override = sddm / "theme.conf.user"
        override.write_text("# keep comment\n[General]\ntype=color\nfontSize=17\n[Other]\nx=y\n")
        run = subprocess.run

        def fake_pkexec(command, **kwargs):
            self.assertEqual(command[0], "pkexec")
            return run(command[1:], **kwargs)

        with patch.object(w, "SDDM", sddm), patch.object(w.subprocess, "run", side_effect=fake_pkexec):
            w.sync(self.config, self.data, None, False)
        result = override.read_text()
        for expected in ("# keep comment", "fontSize=17", "[Other]\nx=y", "type=web", "webFps=144", "webScale=70"):
            self.assertIn(expected, result)
        self.assertTrue((sddm / "html/deep-ocean.html").is_file())
        with patch.object(w, "SDDM", sddm), patch.object(w.subprocess, "run") as privileged:
            w.sync(self.config, self.data, None, True)
            privileged.assert_not_called()


if __name__ == "__main__":
    unittest.main()
