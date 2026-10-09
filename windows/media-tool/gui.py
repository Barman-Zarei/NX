"""NX Media Tool GUI: verifies an NX ISO against its .sha256 file. PySide6 / Qt 6 (Windows 10+). Windows 7: use the LEGACY branch.
USB writing is NOT implemented. Tested headless on Linux (offscreen) with Python 3.12 + PySide6; never run on Windows."""
import os
import sys

from PySide6.QtWidgets import QApplication, QFileDialog, QLabel, QPushButton, QVBoxLayout, QWidget

from nxverify import verify


class VerifyWindow(QWidget):
    def __init__(self):
        super(VerifyWindow, self).__init__()
        self.setWindowTitle("NX Media Tool - verify ISO")
        self.iso = self.sha = None
        lay = QVBoxLayout(self)
        self.info = QLabel("Choose an NX ISO and its .sha256 file")
        self.result_label = QLabel("")
        b1, b2, b3 = QPushButton("Choose ISO..."), QPushButton("Choose .sha256..."), QPushButton("Verify")
        b1.clicked.connect(self.pick_iso); b2.clicked.connect(self.pick_sha); b3.clicked.connect(self.run_verify)
        for w in (self.info, b1, b2, b3, self.result_label):
            lay.addWidget(w)

    def set_files(self, iso, sha):
        self.iso, self.sha = iso, sha
        self.info.setText("%s\n%s" % (iso, sha))

    def pick_iso(self):
        p, _ = QFileDialog.getOpenFileName(self, "NX ISO", "", "ISO (*.iso)")
        if p:
            self.iso = p
            if os.path.exists(p + ".sha256"):
                self.sha = p + ".sha256"
            self.set_files(self.iso, self.sha or "")

    def pick_sha(self):
        p, _ = QFileDialog.getOpenFileName(self, "SHA256", "", "SHA256 (*.sha256)")
        if p:
            self.set_files(self.iso or "", p)

    def run_verify(self):
        if not self.iso or not self.sha:
            self.result_label.setText("ERROR: choose both files"); return
        try:
            ok, info = verify(self.iso, self.sha)
        except (OSError, ValueError) as e:
            self.result_label.setText("ERROR: %s" % e); return
        self.result_label.setText(("OK: " if ok else "MISMATCH: ") + info)


def main():
    app = QApplication(sys.argv)
    w = VerifyWindow(); w.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
