"""NX Control Center (GUI): lists all 50 features and runs their read-only check. Not a full UI per feature."""
import json, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from nxsys.qtshim import QtWidgets, QtCore, BINDING
from nxsys import controlcenter


class Center(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("NX Control Center (%s)" % BINDING); self.resize(900, 600)
        self.search = QtWidgets.QLineEdit(); self.search.setPlaceholderText("Search features…")
        self.list = QtWidgets.QListWidget(); self.out = QtWidgets.QPlainTextEdit(); self.out.setReadOnly(True)
        self.btn = QtWidgets.QPushButton("Run read-only check")
        left = QtWidgets.QWidget(); l = QtWidgets.QVBoxLayout(left); l.addWidget(self.search); l.addWidget(self.list); l.addWidget(self.btn)
        sp = QtWidgets.QSplitter(); sp.addWidget(left); sp.addWidget(self.out); sp.setStretchFactor(1, 2)
        self.setCentralWidget(sp)
        self.search.textChanged.connect(self.fill); self.btn.clicked.connect(self.run_selected)
        self.list.itemDoubleClicked.connect(lambda *_: self.run_selected())
        self.fill()

    def fill(self):
        q = self.search.text().lower(); self.list.clear()
        for n, name, has in controlcenter.features():
            if q in name.lower() or q == str(n):
                it = QtWidgets.QListWidgetItem("%d. %s%s" % (n, name, "" if has else "  (API only)"))
                it.setData(QtCore.Qt.UserRole, n); self.list.addItem(it)

    def run_selected(self):
        it = self.list.currentItem()
        if not it: return
        n = it.data(QtCore.Qt.UserRole)
        self.out.setPlainText(json.dumps(controlcenter.run_check(n), indent=2, ensure_ascii=False, default=str))


def main():
    app = QtWidgets.QApplication(sys.argv); w = Center(); w.show()
    return app.exec() if BINDING == "PySide6" else app.exec_()


if __name__ == "__main__":
    sys.exit(main())
