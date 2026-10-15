"""Code Review: deterministic static checks (CONFIRMED findings, with line numbers). AI review, if used,
is labelled SPECULATIVE and never mixed with confirmed findings."""
import ast, re
from . import workspace

SECRET_RX = re.compile(r"""(?i)(api[_-]?key|secret|password|token)\s*=\s*['"][^'"]{8,}['"]""")


def review_python(path):
    text = workspace.read_text(path); f = []
    try:
        tree = ast.parse(text)
    except SyntaxError as e:
        return [{"kind": "confirmed", "severity": "error", "line": e.lineno, "msg": "syntax error: %s" % e.msg}]
    for n in ast.walk(tree):
        if isinstance(n, ast.ExceptHandler) and n.type is None:
            f.append(("warning", n.lineno, "bare 'except:' hides errors"))
        if isinstance(n, ast.Call):
            name = getattr(n.func, "id", getattr(n.func, "attr", ""))
            if name in ("eval", "exec"):
                f.append(("security", n.lineno, "use of %s()" % name))
            if name in ("run", "call", "Popen", "check_output") and any(
                    k.arg == "shell" and getattr(k.value, "value", None) is True for k in n.keywords):
                f.append(("security", n.lineno, "subprocess with shell=True"))
        if isinstance(n, ast.FunctionDef) and not ast.get_docstring(n) and len(n.body) > 25:
            f.append(("maintainability", n.lineno, "long function (%d statements) without docstring" % len(n.body)))
    for i, line in enumerate(text.splitlines(), 1):
        if SECRET_RX.search(line):
            f.append(("security", i, "possible hard-coded secret"))
    return [{"kind": "confirmed", "severity": s, "line": l, "msg": m, "file": path} for s, l, m in sorted(f, key=lambda x: x[1])]


def ai_review(client, path):
    r = client.ask("Review this code for defects. List concrete issues.", context_files={path: workspace.read_text(path)})
    return {"kind": "speculative", "source": r["source"], "text": r["text"]}
