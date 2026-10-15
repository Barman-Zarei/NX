"""NX Code Studio GUI: tabs editor, project explorer, real terminal, command palette, Claude panel, Git panel."""
import os, sys, threading
from .qt import QtCore, QtGui, QtWidgets, Signal, exec_app, exec_dialog, BINDING
from . import workspace, saferun, claude, gitcc, intel

W = QtWidgets


class Bridge(QtCore.QObject):
    line = Signal(str)
    done = Signal(object)


class Editor(W.QPlainTextEdit):
    def __init__(self, path=None):
        super().__init__()
        self.path = path
        self.setFont(QtGui.QFont("monospace", 10))
        self.setTabStopDistance(32) if hasattr(self, "setTabStopDistance") else None
        if path:
            self.setPlainText(workspace.read_text(path))
        self.document().setModified(False)

    def save(self):
        if not self.path:
            return False
        workspace.write_text_atomic(self.path, self.toPlainText())
        self.document().setModified(False)
        return True


class Palette(W.QDialog):
    def __init__(self, commands, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Command Palette")
        self.commands = commands
        self.box, self.list = W.QLineEdit(), W.QListWidget()
        lay = W.QVBoxLayout(self)
        lay.addWidget(self.box); lay.addWidget(self.list)
        self.box.textChanged.connect(self.refresh)
        self.list.itemActivated.connect(lambda _i: self.accept())
        self.box.returnPressed.connect(self.accept)
        self.refresh("")

    def refresh(self, text):
        self.list.clear()
        for name in self.commands:
            if text.lower() in name.lower():
                self.list.addItem(name)
        if self.list.count():
            self.list.setCurrentRow(0)

    def chosen(self):
        it = self.list.currentItem()
        return it.text() if it else None


class Studio(W.QMainWindow):
    def __init__(self, root=".", ai_enabled=True):
        super().__init__()
        self.root = os.path.abspath(root)
        self.ai_enabled = ai_enabled
        self.setWindowTitle("NX Code Studio (%s)" % BINDING)
        self.tabs = W.QTabWidget(); self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self.tabs.removeTab)
        self.setCentralWidget(self.tabs)
        self.tree = W.QTreeWidget(); self.tree.setHeaderLabel("Explorer")
        self.tree.itemActivated.connect(lambda it, _c: self.open_file(it.data(0, QtCore.Qt.UserRole)))
        self._dock("Explorer", self.tree, QtCore.Qt.LeftDockWidgetArea)
        self.term_out = W.QPlainTextEdit(); self.term_out.setReadOnly(True)
        self.term_in = W.QLineEdit(); self.term_in.setPlaceholderText("command (runs in project dir)")
        self.term_in.returnPressed.connect(self.run_terminal)
        tw = W.QWidget(); tl = W.QVBoxLayout(tw); tl.addWidget(self.term_out); tl.addWidget(self.term_in)
        self._dock("Terminal", tw, QtCore.Qt.BottomDockWidgetArea)
        self.ai_out = W.QPlainTextEdit(); self.ai_out.setReadOnly(True)
        self.ai_in = W.QLineEdit(); self.ai_in.setPlaceholderText("Ask Claude about the current file")
        self.ai_in.returnPressed.connect(self.ask_ai)
        aw = W.QWidget(); al = W.QVBoxLayout(aw); al.addWidget(self.ai_out); al.addWidget(self.ai_in)
        self._dock("Claude", aw, QtCore.Qt.RightDockWidgetArea)
        self.git_out = W.QPlainTextEdit(); self.git_out.setReadOnly(True)
        self._dock("Git", self.git_out, QtCore.Qt.RightDockWidgetArea)
        self.bridge = Bridge(); self.bridge.line.connect(self.term_out.appendPlainText)
        self.bridge.done.connect(self._ai_done)
        self.ai_client = None
        self.commands = {"File: Save": self.save_current, "View: Refresh Explorer": self.refresh_tree,
                         "Git: Refresh Status": self.refresh_git, "Project: Analyze": self.analyze,
                         "AI: Toggle (%s)" % ("on" if ai_enabled else "off"): self.toggle_ai}
        for keys, fn in (("Ctrl+S", self.save_current), ("Ctrl+Shift+P", self.palette)):
            sc = W.QShortcut(QtGui.QKeySequence(keys), self) if hasattr(W, "QShortcut") else QtGui.QShortcut(QtGui.QKeySequence(keys), self)
            sc.activated.connect(fn)
        self.refresh_tree(); self.refresh_git()

    def _dock(self, title, widget, area):
        d = W.QDockWidget(title, self); d.setWidget(widget); self.addDockWidget(area, d)

    def refresh_tree(self):
        self.tree.clear()
        top = {self.root: self.tree.invisibleRootItem()}
        for dp, dn, fn in os.walk(self.root):
            dn[:] = sorted(d for d in dn if d not in workspace.SKIP_DIRS)
            parent = top[dp]
            for d in dn:
                it = W.QTreeWidgetItem(parent, [d]); top[os.path.join(dp, d)] = it
            for f in sorted(fn):
                it = W.QTreeWidgetItem(parent, [f]); it.setData(0, QtCore.Qt.UserRole, os.path.join(dp, f))

    def open_file(self, path):
        if not path:
            return None
        for i in range(self.tabs.count()):
            if self.tabs.widget(i).path == path:
                self.tabs.setCurrentIndex(i); return self.tabs.widget(i)
        ed = Editor(path); self.tabs.addTab(ed, os.path.basename(path)); self.tabs.setCurrentWidget(ed)
        return ed

    def save_current(self):
        ed = self.tabs.currentWidget()
        return ed.save() if ed else False

    def run_terminal(self):
        cmd = self.term_in.text().strip(); self.term_in.clear()
        if not cmd:
            return
        self.term_out.appendPlainText("$ " + cmd)
        def work():
            r = saferun.run(["bash", "-c", cmd], cwd=self.root, timeout=120, restricted=False,
                            on_output=lambda l: self.bridge.line.emit(l.rstrip("\n")))
            self.bridge.line.emit("[exit %d]" % r["returncode"])
        self._term_thread = threading.Thread(target=work, daemon=True); self._term_thread.start()

    def ask_ai(self, transport=None):
        if not self.ai_enabled:
            self.ai_out.appendPlainText("AI is disabled."); return
        q = self.ai_in.text(); self.ai_in.clear()
        ed = self.tabs.currentWidget()
        ctx = {os.path.basename(ed.path): ed.toPlainText()} if ed and ed.path else None
        self.ai_client = claude.Client(transport=transport or getattr(self, "ai_transport", None))
        def work():
            try:
                self.bridge.done.emit(self.ai_client.ask(q, context_files=ctx))
            except claude.ClaudeError as e:
                self.bridge.done.emit(e)
        self._ai_thread = threading.Thread(target=work, daemon=True); self._ai_thread.start()

    def _ai_done(self, r):
        if isinstance(r, claude.ClaudeError):
            self.ai_out.appendPlainText("[error:%s] %s" % (r.kind, r))
        else:
            self.ai_out.appendPlainText("[%s] %s" % (r["source"], r["text"]))

    def toggle_ai(self):
        self.ai_enabled = not self.ai_enabled

    def refresh_git(self):
        try:
            st = gitcc.Repo(self.root).status()
            self.git_out.setPlainText(st["branch"] + "\n" + "\n".join("%s %s" % f for f in st["files"]))
        except Exception as e:
            self.git_out.setPlainText("not a git repository (%s)" % e)

    def analyze(self):
        self.term_out.appendPlainText(str(intel.analyze(self.root)))

    def palette(self):
        p = Palette(list(self.commands), self)
        if exec_dialog(p) and p.chosen():
            self.commands[p.chosen()]()


def main(argv=None):
    argv = argv if argv is not None else sys.argv
    app = W.QApplication(argv)
    win = Studio(argv[1] if len(argv) > 1 else "."); win.resize(1100, 700); win.show()
    return exec_app(app)


if __name__ == "__main__":
    sys.exit(main())
