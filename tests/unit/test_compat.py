import os, sys, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "compatibility"))
import validate


class T(unittest.TestCase):
    def test_shipped_db_valid(self):
        self.assertEqual(validate.validate(), [])

    def test_fake_verified_rejected(self):
        bad = [{"name": "x", "version": "1", "arch": "amd64", "method": "wine", "runtime": "r", "limitations": "",
                "tested_nx": "none", "last_verified": "never", "status": "verified"}]
        self.assertTrue(validate.validate(bad))


if __name__ == "__main__":
    unittest.main()
