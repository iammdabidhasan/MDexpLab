import os
import sys
import tempfile
import unittest
from pathlib import Path

import ghostlock


class CoreBehaviorTests(unittest.TestCase):
    def test_password_hash_verification(self):
        record = ghostlock.hash_secret("correct-password")
        self.assertTrue(ghostlock.verify_secret("correct-password", record))
        self.assertFalse(ghostlock.verify_secret("wrong-password", record))

    def test_config_round_trip(self):
        old_appdata = os.environ.get("APPDATA")
        old_localappdata = os.environ.get("LOCALAPPDATA")
        try:
            with tempfile.TemporaryDirectory() as temp:
                os.environ["APPDATA"] = str(Path(temp) / "Roaming")
                os.environ["LOCALAPPDATA"] = str(Path(temp) / "Local")
                config = ghostlock.ConfigManager()
                config.configure("main-password", "backup-password", "Favorite release name?", "GhostLock")

                loaded = ghostlock.ConfigManager()
                self.assertTrue(loaded.is_configured)
                self.assertTrue(loaded.verify_password("main-password"))
                self.assertTrue(loaded.verify_emergency_password("backup-password"))
                self.assertTrue(loaded.verify_security_answer("ghostlock"))
                self.assertFalse(loaded.verify_password("bad-password"))
        finally:
            self._restore_env("APPDATA", old_appdata)
            self._restore_env("LOCALAPPDATA", old_localappdata)

    def test_invocation_modes(self):
        old_argv = sys.argv[:]
        old_executable = sys.executable
        had_frozen = hasattr(sys, "frozen")
        old_frozen = getattr(sys, "frozen", None)
        try:
            sys.frozen = True
            sys.argv = ["Setup.exe"]
            sys.executable = r"C:\Package\Setup.exe"
            self.assertTrue(ghostlock.is_setup_invocation())
            self.assertFalse(ghostlock.is_uninstall_invocation())

            sys.argv = ["GhostLock.exe", "--run"]
            sys.executable = r"C:\Users\Person\AppData\Local\GhostLock\GhostLock.exe"
            self.assertFalse(ghostlock.is_setup_invocation())
            self.assertFalse(ghostlock.is_uninstall_invocation())
            self.assertFalse(ghostlock.is_forced_setup_invocation())

            sys.argv = ["GhostLock.exe", "--setup"]
            self.assertFalse(ghostlock.is_setup_invocation())
            self.assertFalse(ghostlock.is_uninstall_invocation())
            self.assertTrue(ghostlock.is_forced_setup_invocation())

            sys.argv = ["GhostLock.exe", "--uninstall"]
            self.assertFalse(ghostlock.is_setup_invocation())
            self.assertTrue(ghostlock.is_uninstall_invocation())
        finally:
            sys.argv = old_argv
            sys.executable = old_executable
            if had_frozen:
                sys.frozen = old_frozen
            elif hasattr(sys, "frozen"):
                delattr(sys, "frozen")

    @staticmethod
    def _restore_env(name, old_value):
        if old_value is None:
            os.environ.pop(name, None)
        else:
            os.environ[name] = old_value


if __name__ == "__main__":
    unittest.main()
