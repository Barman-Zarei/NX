"""SCAFFOLD (untested): minimal PySide2 window for ISO verification. Requires Python 3.8 + PySide2 5.15."""
import os
import sys
from PySide2.QtWidgets import QApplication, QFileDialog, QMessageBox

from nxverify import verify


def main():
    app = QApplication(sys.argv)
    iso, _ = QFileDialog.getOpenFileName(None, "Select NX ISO", "", "ISO (*.iso)")
    if not iso:
        return 0
    sha = iso + ".sha256"
    if not os.path.exists(sha):
        sha, _ = QFileDialog.getOpenFileName(None, "Select .sha256 file", "", "SHA256 (*.sha256)")
    ok, info = verify(iso, sha)
    QMessageBox.information(None, "NX verify", ("OK: " if ok else "MISMATCH: ") + info)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
