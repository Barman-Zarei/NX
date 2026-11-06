import os, stat, sys, tempfile, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from nxsys import actions


class T(unittest.TestCase):
    def test_no_build_is_reported_not_crash(self):
        old = os.environ.pop("NX_STUDIO_CODE_BIN", None)
        try:
            r = actions._code_studio(tempfile.gettempdir())
            if r.get("started_pid") is None:
                self.assertIn("not built", r["error"])
        finally:
            if old: os.environ["NX_STUDIO_CODE_BIN"] = old

    @unittest.skipIf(os.name == "nt", "posix shell stub")
    def test_launches_configured_binary(self):
        d = tempfile.mkdtemp(); exe = os.path.join(d, "nx-studio-code")
        with open(exe, "w") as f:
            f.write("#!/bin/sh\nexit 0\n")
        os.chmod(exe, os.stat(exe).st_mode | stat.S_IXUSR)
        os.environ["NX_STUDIO_CODE_BIN"] = exe
        try:
            r = actions._code_studio(d)
            self.assertEqual(r["exe"], exe); self.assertTrue(r["started_pid"])
        finally:
            del os.environ["NX_STUDIO_CODE_BIN"]


if __name__ == "__main__":
    unittest.main()
