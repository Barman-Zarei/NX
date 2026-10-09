import os, sys, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "software-center"))
import nxsoft


class T(unittest.TestCase):
    def test_valid(self):
        self.assertTrue(nxsoft.valid("vim-tiny"))
        for bad in ("-rf", "a;b", "a b", "../x", "", None, "A"):
            self.assertFalse(nxsoft.valid(bad), bad)

    def test_search_parse_and_option_injection(self):
        r = nxsoft.search("vim", lambda a: (0, "vim - editor\nvim-tiny - small editor\n"))
        self.assertEqual(r[1]["name"], "vim-tiny")
        self.assertEqual(nxsoft.search("--evil"), [])

    def test_info_parse(self):
        out = "Package: vim\nVersion: 1\nArchitecture: amd64\nDescription: x\n y\n\nPackage: other\n"
        i = nxsoft.info("vim", lambda a: (0, out))
        self.assertEqual(i["Version"], "1"); self.assertNotIn("other", str(i))

    def test_install_needs_approval(self):
        calls = []
        st, msg = nxsoft.apply("install", "vim", runner=lambda a: calls.append(a) or (0, ""))
        self.assertEqual(st, "needs_approval"); self.assertEqual(calls, [])

    def test_install_approved_and_invalid(self):
        calls = []
        st, _ = nxsoft.apply("install", "vim", approved=True, runner=lambda a: calls.append(a) or (0, "ok"))
        self.assertEqual(st, "done"); self.assertIn("vim", calls[0])
        self.assertEqual(nxsoft.apply("install", "vim; rm -rf /", approved=True)[0], "denied")
        self.assertEqual(nxsoft.apply("purge", "vim", approved=True)[0], "denied")

    def test_compat_unknown(self):
        self.assertEqual(nxsoft.compat_report("nonexistent-app")["status"], "unknown")


if __name__ == "__main__":
    unittest.main()
