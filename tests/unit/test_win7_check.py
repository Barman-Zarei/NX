import os, sys, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "windows"))
import check_win7_compat as c


class T(unittest.TestCase):
    def test_ok(self):
        self.assertEqual(c.violations((6, 1), (6, 1), ["CreateFileW"]), [])

    def test_os_version(self):
        self.assertTrue(c.violations((10, 0), (6, 1), []))

    def test_subsystem_version(self):
        self.assertTrue(c.violations((6, 0), (6, 2), []))

    def test_post_win7_import(self):
        self.assertIn("SetThreadDescription", c.violations((6, 1), (6, 1), ["SetThreadDescription"])[0])


if __name__ == "__main__":
    unittest.main()
