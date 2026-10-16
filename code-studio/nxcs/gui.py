"""NX Code Studio GUI: tabs, explorer, terminal, Claude panel, Git panel, command palette."""
import os, sys, threading
from .qt import QtCore, QtGui, QtWidgets, QAction, BINDING
from . import workspace, saferun, claude, gitcc, intel

Qt = QtCore.Qt


class PyHighlighter(QtGui.QSyntaxHighlighter):
    KW = ("def class return if elif else for while import from as try except finally with "
          "lambda yield pass break continue raise in not and or is None True False").split()

    def __init__(self, doc):
        super().__init__(doc)
        self.kw = QtGui.QTextCharFormat(); self.kw.setForeground(QtGui.QColor("#c678dd"))
        self.st = QtGui.QTextCharFormat(); self.st.setForeground(QtGui.QColor("#98c379"))
        self.cm = QtGui.QTextCharFormat(); self.cm.setForeground(QtGui.QColor("#7f848e"))
        import re
        self.rx = [(re.compile(r"\b(%s)\b" % "|".join(self.KW)), self.kw),
                   (re.compile(r"(\"[^\"\n]*\"|'[^'\n]*')"), self.st), (re.compile(r"#[^\n]*"), self.cm)]

    def highlightBlock(self, text):
        for rx, fmt in self.rx:
            for m in rx.finditer(text):
                self.setFormat(m.start(), m.end() - m.start(), fmt)


class Editor(QtWidgets.QPlainTextEdit):
    def __init__(self, path=None):
        super().__init__()
        self.path = path
        self.setFont(QtGui.QFontDatabase.systemFont(QtGui.QFontDatabase.FixedFont))
        self.setLineWrapMode(QtWidgets.QPlainTextEdit.NoWrap)
        if path:
            self.setPlainText(workspace.read_text(path))
            if path.endswith(".py"):
                self.hl = PyHighlighter(self.document())
        self.document().setModified(False)

    def save(self, path=None):
        path = path or self.path
        if not path:
            return False
        workspace.write_text_atomic(path, self.toPlainText())
        self.path = path
        self.document().setModified(False)
        return True


class Bridge(QtCore.QObject):
    term_line = QtCore.Signal(str)
    ai_done = QtCore.Signal(str, str)


class Studio(QtWidgets.QMainWindow):
    def __init__(self, root=".", ai_transport=None):
        super().__init__()
        self.root = os.path.abspath(root)
        self.ai_transport = ai_transport
        self.ai_enabled = True
        self.bridge = Bridge()
        self.setWindowTitle("NX Code Studio — %s (%s)" % (os.path.basename(self.root), BINDING))
        self.resize(1100, 700)
        self.tabs = QtWidgets.QTabWidget(); self.tabs.setTabsClosable(True); self.tabs.setDocumentMode(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.setCentralWidget(self.tabs)
        self._build_explorer(); self._build_panels(); self._build_menu()
        self.bridge.term_line.connect(self.term_out.appendPlainText)
        self.bridge.ai_done.connect(self._ai_show)
        self.refresh_git()

    # --- UI ---
    def _build_explorer(self):
        self.model = QtWidgets.QFileSystemModel(); self.model.setRootPath(self.root)
        self.tree = QtWidgets.QTreeView(); self.tree.setModel(self.model)
        self.tree.setRootIndex(self.model.index(self.root))
        for c in (1, 2, 3):
            self.tree.hideColumn(c)
        self.tree.doubleClicked.connect(lambda i: self.open_file(self.model.filePath(i)))
        d = QtWidgets.QDockWidget("Explorer"); d.setWidget(self.tree)
        self.addDockWidget(Qt.LeftDockWidgetArea, d)

    def _build_panels(self):
        self.term_out = QtWidgets.QPlainTextEdit(); self.term_out.setReadOnly(True)
        self.term_in = QtWidgets.QLineEdit(); self.term_in.setPlaceholderText("command (runs in project root)")
        self.term_in.returnPressed.connect(self.run_terminal_cmd)
        tw = QtWidgets.QWidget(); l = QtWidgets.QVBoxLayout(tw); l.addWidget(self.term_out); l.addWidget(self.term_in)
        self.git_view = QtWidgets.QPlainTextEdit(); self.git_view.setReadOnly(True)
        self.ai_out = QtWidgets.QPlainTextEdit(); self.ai_out.setReadOnly(True)
        self.ai_in = QtWidgets.QLineEdit(); self.ai_in.setPlaceholderText("Ask Claude about the open file")
        self.ai_in.returnPressed.connect(self.ask_ai)
        aw = QtWidgets.QWidget(); l2 = QtWidgets.QVBoxLayout(aw); l2.addWidget(self.ai_out); l2.addWidget(self.ai_in)
        self.panel = QtWidgets.QTabWidget()
        for w, n in ((tw, "Terminal"), (self.git_view, "Git"), (aw, "Claude")):
            self.panel.addTab(w, n)
        d = QtWidgets.QDockWidget("Panel"); d.setWidget(self.panel)
        self.addDockWidget(Qt.BottomDockWidgetArea, d)

    def _build_menu(self):
        self.actions_map = {}
        def act(menu, text, fn, key=None):
            a = QAction(text, self)
            if key:
                a.setShortcut(key)
            a.triggered.connect(lambda *_: fn())
            menu.addAction(a); self.actions_map[text] = fn
        fm = self.menuBar().addMenu("&File")
        act(fm, "Save", self.save_current, "Ctrl+S")
        act(fm, "Open File…", self.open_dialog, "Ctrl+O")
        vm = self.menuBar().addMenu("&View")
        act(vm, "Command Palette", self.palette, "Ctrl+Shift+P")
        act(vm, "Analyze Project", self.analyze)
        act(vm, "Toggle AI (disable/enable)", self.toggle_ai)
        act(vm, "Refresh Git", self.refresh_git)

    # --- behavior ---
    def open_file(self, path):
        if not os.path.isfile(path):
            return None
        for i in range(self.tabs.count()):
            if self.tabs.widget(i).path == path:
                self.tabs.setCurrentIndex(i); return self.tabs.widget(i)
        ed = Editor(path); self.tabs.setCurrentIndex(self.tabs.addTab(ed, os.path.basename(path)))
        return ed

    def open_dialog(self):
        p, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Open", self.root)
        if p:
            self.open_file(p)

    def current(self):
        return self.tabs.currentWidget()

    def save_current(self):
        ed = self.current()
        return bool(ed and ed.save())

    def close_tab(self, i):
        self.tabs.removeTab(i)

    def palette(self):
        names = sorted(self.actions_map)
        n, ok = QtWidgets.QInputDialog.getItem(self, "Command Palette", "Command:", names, 0, False)
        if ok:
            self.actions_map[n]()

    def analyze(self):
        a = intel.analyze(self.root)
        self.term_out.appendPlainText("languages: %s | entry points: %s" % (a["languages"], a["entry_points"]))

    def run_terminal_cmd(self, text=None):
        cmd = text if text is not None else self.term_in.text()
        self.term_in.clear()
        if not cmd.strip():
            return None
        self.term_out.appendPlainText("$ " + cmd)
        done = threading.Event()
        def work():
            saferun.run(["bash", "-c", cmd], cwd=self.root, timeout=120, restricted=False,
                        on_output=lambda l: self.bridge.term_line.emit(l.rstrip("\n")))
            done.set()
        threading.Thread(target=work, daemon=True).start()
        return done

    def refresh_git(self):
        try:
            st = gitcc.Repo(self.root).status()
            self.git_view.setPlainText("branch: %s\n" % st["branch"] + "\n".join("%s %s" % f for f in st["files"]))
        except gitcc.GitError as e:
            self.git_view.setPlainText("not a git repository: %s" % e)

    def toggle_ai(self):
        self.ai_enabled = not self.ai_enabled
        self.ai_out.appendPlainText("AI %s" % ("enabled" if self.ai_enabled else "DISABLED"))

    def ask_ai(self, text=None):
        q = text if text is not None else self.ai_in.text(); self.ai_in.clear()
        ed = self.current(); ctx = {os.path.basename(ed.path): ed.toPlainText()} if ed and ed.path else None
        cl = claude.Client(enabled=self.ai_enabled, transport=self.ai_transport)
        done = threading.Event(); self._ai_done = done
        def work():
            try:
                r = cl.ask(q, context_files=ctx)
                self.bridge.ai_done.emit("[source: %s]" % r["source"], r["text"])
            except claude.ClaudeError as e:
                self.bridge.ai_done.emit("[error: %s]" % e.kind, str(e))
            done.set()
        threading.Thread(target=work, daemon=True).start()
        return done

    def _ai_show(self, tag, text):
        self.ai_out.appendPlainText("%s\n%s\n" % (tag, text))


def main(argv=None):
    app = QtWidgets.QApplication(argv or sys.argv)
    w = Studio(sys.argv[1] if len(sys.argv) > 1 else ".")
    w.show()
    return app.exec() if BINDING == "PySide6" else app.exec_()


if __name__ == "__main__":
    sys.exit(main())
