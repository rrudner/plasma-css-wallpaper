"""Run SDDM scripts against temporary paths with a stubbed root identity."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent.parent


class SddmLifecycle(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        binary = self.root / 'bin'
        binary.mkdir()
        stub = binary / 'id'
        stub.write_text('#!/bin/sh\necho 0\n')
        stub.chmod(0o755)
        self.theme = self.root / 'share/sddm/themes/css-wallpaper'
        self.override = self.root / 'etc/sddm.conf.d/zz-css-wallpaper.conf'
        self.env = dict(os.environ, PATH=str(binary) + os.pathsep + os.environ['PATH'],
                        SDDM_BASE_DIR=str(self.root / 'share'),
                        SDDM_ETC_DIR=str(self.root / 'etc'),
                        SDDM_LIB_DIR=str(self.root / 'lib/sddm'))

    def run_script(self, name, success=True):
        result = subprocess.run([str(ROOT / name)], cwd=self.root, env=self.env,
                                capture_output=True, text=True)
        self.assertEqual(result.returncode == 0, success, result.stdout + result.stderr)
        return result

    def write(self, path, content):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)

    def test_fresh_install_upgrade_and_uninstall(self):
        self.run_script('install-sddm-theme.sh')
        self.assertEqual(self.override.read_text(), '[Theme]\nCurrent=css-wallpaper\n')
        self.assertTrue((self.theme / 'html/deep-ocean.html').is_file())
        saved = {'theme.conf': '[General]\nwebFps=144\nfontSize=18\n',
                 'theme.conf.user': '# comment\n[General]\nwebScale=75\n',
                 'html/custom.html': 'custom animation'}
        for name, value in saved.items():
            self.write(self.theme / name, value)
        self.run_script('install-sddm-theme.sh')
        for name, value in saved.items():
            self.assertEqual((self.theme / name).read_text(), value)
        self.run_script('uninstall-sddm-theme.sh')
        self.assertFalse(self.theme.exists())
        self.assertFalse(self.override.exists())

    def test_other_theme_override_is_preserved(self):
        self.run_script('install-sddm-theme.sh')
        content = '[Theme]\nCurrent=css-wallpaper\nCurrent=breeze\n# keep\n'
        self.override.write_text(content)
        self.run_script('uninstall-sddm-theme.sh')
        self.assertEqual(self.override.read_text(), content)
        self.assertFalse(self.theme.exists())

    def test_external_references_block_all_removal(self):
        self.run_script('install-sddm-theme.sh')
        for name in ('etc/sddm.conf', 'etc/sddm.conf.d/kde_settings.conf',
                     'lib/sddm/sddm.conf.d/vendor.conf'):
            with self.subTest(name=name):
                reference = self.root / name
                self.write(reference, '[Other]\nCurrent=breeze\n[Theme]\n Current = css-wallpaper \n')
                result = self.run_script('uninstall-sddm-theme.sh', success=False)
                self.assertIn(str(reference), result.stdout)
                self.assertTrue(self.theme.exists())
                self.assertTrue(self.override.exists())
                reference.unlink()

    def test_unrelated_group_does_not_block(self):
        self.run_script('install-sddm-theme.sh')
        self.write(self.root / 'etc/sddm.conf', '[Other]\nCurrent=css-wallpaper\n[Theme]\nCurrent=breeze\n')
        self.run_script('uninstall-sddm-theme.sh')
        self.assertFalse(self.theme.exists())


if __name__ == '__main__':
    unittest.main()
