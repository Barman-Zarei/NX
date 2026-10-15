"""Project Intelligence: languages, entry points, symbols (real AST for Python), dependencies."""
import ast, collections, json, os, re
from . import workspace

LANGS = {".py": "Python", ".js": "JavaScript", ".ts": "TypeScript", ".html": "HTML", ".css": "CSS",
         ".c": "C", ".h": "C", ".cpp": "C++", ".cc": "C++", ".hpp": "C++", ".sh": "Shell", ".md": "Markdown"}
BUILD_FILES = ("pyproject.toml", "setup.py", "requirements.txt", "package.json", "Makefile",
               "CMakeLists.txt", "Dockerfile", "tox.ini", "pytest.ini")


def languages(root):
    c = collections.Counter()
    for p in workspace.iter_files(root):
        l = LANGS.get(os.path.splitext(p)[1].lower())
        if l:
            c[l] += 1
    return dict(c.most_common())


def python_symbols(path):
    try:
        tree = ast.parse(workspace.read_text(path), filename=path)
    except SyntaxError as e:
        return {"error": "%s (line %s)" % (e.msg, e.lineno), "symbols": []}
    syms = []
    for n in ast.walk(tree):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            syms.append(("function", n.name, n.lineno))
        elif isinstance(n, ast.ClassDef):
            syms.append(("class", n.name, n.lineno))
    return {"error": None, "symbols": sorted(syms, key=lambda s: s[2])}


def python_imports(path):
    try:
        tree = ast.parse(workspace.read_text(path))
    except SyntaxError:
        return set()
    mods = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            mods.update(a.name.split(".")[0] for a in n.names)
        elif isinstance(n, ast.ImportFrom) and n.module and not n.level:
            mods.add(n.module.split(".")[0])
    return mods


def entry_points(root):
    eps = []
    for p in workspace.iter_files(root):
        if p.endswith(".py") and re.search(r"if\s+__name__\s*==\s*['\"]__main__['\"]", workspace.read_text(p)):
            eps.append(os.path.relpath(p, root))
    return eps


def dependencies(root):
    deps = {}
    rq = os.path.join(root, "requirements.txt")
    if os.path.exists(rq):
        deps["requirements.txt"] = [l.strip() for l in workspace.read_text(rq).splitlines()
                                    if l.strip() and not l.startswith("#")]
    pj = os.path.join(root, "package.json")
    if os.path.exists(pj):
        try:
            j = json.loads(workspace.read_text(pj))
            deps["package.json"] = sorted(list(j.get("dependencies", {})) + list(j.get("devDependencies", {})))
        except ValueError:
            deps["package.json"] = ["<invalid JSON>"]
    return deps


def related_to_error(root, traceback_text):
    """Files named in a Python traceback that exist inside the project."""
    found = []
    for m in re.finditer(r'File "([^"]+)", line (\d+)', traceback_text):
        p = os.path.abspath(m.group(1))
        if p.startswith(os.path.abspath(root)) and os.path.exists(p):
            found.append((os.path.relpath(p, root), int(m.group(2))))
    return found


def analyze(root):
    return {"languages": languages(root), "entry_points": entry_points(root),
            "build_files": [b for b in BUILD_FILES if os.path.exists(os.path.join(root, b))],
            "dependencies": dependencies(root)}
