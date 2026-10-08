import hashlib, os, sys, tempfile, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "windows", "media-tool"))
import nxverify


class T(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.iso = os.path.join(self.d, "a.iso")
        with open(self.iso, "wb") as f:
            f.write(b"hello")
        self.sha = self.iso + ".sha256"

    def test_ok(self):
        with open(self.sha, "w") as f:
            f.write(hashlib.sha256(b"hello").hexdigest() + "  a.iso\n")
        self.assertTrue(nxverify.verify(self.iso, self.sha)[0])

    def test_mismatch(self):
        with open(self.sha, "w") as f:
            f.write("0" * 64 + "  a.iso\n")
        self.assertFalse(nxverify.verify(self.iso, self.sha)[0])

    def test_missing_entry(self):
        with open(self.sha, "w") as f:
            f.write("0" * 64 + "  other.iso\n")
        self.assertFalse(nxverify.verify(self.iso, self.sha)[0])


if __name__ == "__main__":
    unittest.main()
