"""NX Control Center: one interactive page per feature (1-50), generated from nxsys.actions.
Each action has a form, a Run button and an output pane. Actions that change the system need an explicit
confirmation (checkbox + dialog). Pages are auto-generated forms, not hand-designed screens."""
import json, os, sys, threading
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from nxsys.qtshim import QtWidgets, QtCore, BINDING
from nxsys import actions as ACT, controlcenter

NAMES = controlcenter.NAMES


class Bridge(QtCore.QObject):
    done = QtCore.Signal(str)


class Page(QtWidgets.QWidget):
    def __init__(self, n, out_cb, confirm_cb):
        super().__init__()
        self.n, self.out_cb, self.confirm_cb = n, out_cb, confirm_cb
        lay = QtWidgets.QVBoxLayout(self)
        t = QtWidgets.QLabel("<h2>%d. %s</h2>" % (n, NAMES[n])); lay.addWidget(t)
        self.boxes = []
        for act in ACT.R[n]:
            gb = QtWidgets.QGroupBox(act.label + ("   [CHANGES SYSTEM]" if act.danger else ""))
            form = QtWidgets.QFormLayout(gb); fields = {}
            if act.help:
                form.addRow(QtWidgets.QLabel(act.help))
            for name, kind, default, label in act.params:
                w = self._widget(kind, default); fields[name] = (kind, w); form.addRow(label + ":", w)
            confirm = None
            if act.danger:
                confirm = QtWidgets.QCheckBox("I understand this changes the system / my data"); form.addRow(confirm)
            btn = QtWidgets.QPushButton("Run"); form.addRow(btn)
            btn.clicked.connect(lambda _=False, a=act, f=fields, c=confirm: self.run(a, f, c))
            lay.addWidget(gb); self.boxes.append((act, fields, confirm, btn))
        lay.addStretch(1)

    @staticmethod
    def _widget(kind, default):
        if kind == "bool":
            w = QtWidgets.QCheckBox(); w.setChecked(bool(default)); return w
        if kind.startswith("choice:"):
            w = QtWidgets.QComboBox(); w.addItems(kind[7:].split("|")); w.setCurrentText(str(default)); return w
        if kind == "int":
            w = QtWidgets.QSpinBox(); w.setRange(0, 2 ** 31 - 1); w.setValue(int(default)); return w
        w = QtWidgets.QLineEdit(str(default))
        if kind == "secret":
            w.setEchoMode(QtWidgets.QLineEdit.Password)
        return w

    @staticmethod
    def read(kind, w):
        if kind == "bool": return w.isChecked()
        if kind.startswith("choice:"): return w.currentText()
        if kind == "int": return w.value()
        return w.text()

    def values(self, fields):
        return {k: self.read(kind, w) for k, (kind, w) in fields.items()}

    def run(self, act, fields, confirm):
        vals = self.values(fields); ok = False
        if act.danger:
            if not (confirm and confirm.isChecked()):
                self.out_cb("Not run: tick the confirmation box first."); return None
            ok = self.confirm_cb(act)
            if not ok:
                self.out_cb("Cancelled."); return None
        return self.out_cb(None, act, vals, ok)


class Center(QtWidgets.QMainWindow):
    def __init__(self, auto_confirm=None):
        super().__init__()
        self.auto_confirm = auto_confirm      # tests only; the real GUI always asks
        self.bridge = Bridge(); self.bridge.done.connect(self._show)
        self.setWindowTitle("NX Control Center (%s)" % BINDING); self.resize(1050, 700)
        self.search = QtWidgets.QLineEdit(); self.search.setPlaceholderText("Search features…")
        self.list = QtWidgets.QListWidget(); self.stack = QtWidgets.QStackedWidget()
        self.out = QtWidgets.QPlainTextEdit(); self.out.setReadOnly(True)
        left = QtWidgets.QWidget(); l = QtWidgets.QVBoxLayout(left); l.addWidget(self.search); l.addWidget(self.list)
        right = QtWidgets.QSplitter(QtCore.Qt.Vertical)
        sa = QtWidgets.QScrollArea(); sa.setWidgetResizable(True); sa.setWidget(self.stack)
        right.addWidget(sa); right.addWidget(self.out); right.setStretchFactor(0, 2)
        sp = QtWidgets.QSplitter(); sp.addWidget(left); sp.addWidget(right); sp.setStretchFactor(1, 3)
        self.setCentralWidget(sp)
        self.pages = {}
        self.search.textChanged.connect(self.fill)
        self.list.currentItemChanged.connect(self._select)
        self.fill()

    def fill(self):
        q = self.search.text().lower(); self.list.clear()
        for n in sorted(NAMES):
            if q in NAMES[n].lower() or q == str(n):
                it = QtWidgets.QListWidgetItem("%d. %s" % (n, NAMES[n])); it.setData(QtCore.Qt.UserRole, n); self.list.addItem(it)

    def page(self, n):
        if n not in self.pages:
            p = Page(n, self._cb, self._confirm); self.pages[n] = p; self.stack.addWidget(p)
        return self.pages[n]

    def _select(self, cur, _prev=None):
        if cur is not None:
            self.stack.setCurrentWidget(self.page(cur.data(QtCore.Qt.UserRole)))

    def _confirm(self, act):
        if self.auto_confirm is not None:
            return self.auto_confirm
        r = QtWidgets.QMessageBox.question(self, "Confirm", "Really run: %s ?\nThis changes the system or your data." % act.label)
        return r == QtWidgets.QMessageBox.Yes

    def _cb(self, msg, act=None, vals=None, confirmed=False):
        if msg is not None:
            self.out.appendPlainText(msg); return None
        done = threading.Event(); self._last_done = done

        def work():
            try:
                res = ACT.execute(act, vals, confirmed=confirmed)
                txt = json.dumps(res, indent=2, ensure_ascii=False, default=str)
            except Exception as e:
                txt = "ERROR %s: %s" % (type(e).__name__, e)
            self.bridge.done.emit("== %s ==\n%s" % (act.label, txt)); done.set()
        threading.Thread(target=work, daemon=True).start()
        return done

    def _show(self, text):
        self.out.appendPlainText(text)


def main():
    app = QtWidgets.QApplication(sys.argv); w = Center(); w.show()
    return app.exec() if BINDING == "PySide6" else app.exec_()


if __name__ == "__main__":
    sys.exit(main())
