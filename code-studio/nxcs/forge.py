"""Project Forge: coherent, runnable project templates (python, cli, web, c)."""
import os
from . import workspace

T = {
 "python": {
  "pyproject.toml": '[project]\nname = "{name}"\nversion = "0.1.0"\nrequires-python = ">=3.8"\n',
  "{name}/__init__.py": '__version__ = "0.1.0"\n',
  "tests/test_basic.py": 'import unittest, {name}\n\nclass T(unittest.TestCase):\n    def test_version(self):\n        self.assertEqual({name}.__version__, "0.1.0")\n\nif __name__ == "__main__":\n    unittest.main()\n',
  "README.md": "# {name}\n\nRun tests: `python -m unittest discover -s tests`\n",
  ".gitignore": "__pycache__/\n.venv/\n*.pyc\n"},
 "cli": {
  "pyproject.toml": '[project]\nname = "{name}"\nversion = "0.1.0"\nrequires-python = ">=3.8"\n[project.scripts]\n{name} = "{name}.cli:main"\n',
  "{name}/__init__.py": "",
  "{name}/cli.py": 'import argparse\n\ndef main(argv=None):\n    p = argparse.ArgumentParser(prog="{name}")\n    p.add_argument("name", nargs="?", default="world")\n    print("hello, %s" % p.parse_args(argv).name)\n    return 0\n',
  "tests/test_cli.py": 'import unittest\nfrom {name}.cli import main\n\nclass T(unittest.TestCase):\n    def test_main(self):\n        self.assertEqual(main(["x"]), 0)\n',
  ".gitignore": "__pycache__/\n"},
 "web": {
  "index.html": '<!doctype html><html><head><meta charset="utf-8"><title>{name}</title><link rel="stylesheet" href="style.css"></head><body><h1>{name}</h1><script src="app.js"></script></body></html>\n',
  "style.css": "body { font-family: sans-serif; margin: 2rem; }\n",
  "app.js": "document.title = document.title + ' ✓';\n", ".gitignore": "node_modules/\n"},
 "c": {
  "Makefile": "CC ?= cc\nall: {name}\n{name}: src/main.c\n\t$(CC) -Wall -Wextra -o $@ $<\nclean:\n\trm -f {name}\n",
  "src/main.c": '#include <stdio.h>\nint main(void) {{ puts("{name}"); return 0; }}\n', ".gitignore": "{name}\n"},
}


def create(kind, dest, name):
    if kind not in T:
        raise ValueError("unknown template %r (have: %s)" % (kind, ", ".join(T)))
    if os.path.exists(dest) and os.listdir(dest):
        raise FileExistsError("destination not empty: refusing to overwrite")
    made = []
    for rel, body in T[kind].items():
        p = os.path.join(dest, rel.replace("{name}", name))
        os.makedirs(os.path.dirname(p), exist_ok=True)
        workspace.write_text_atomic(p, body.replace("{{", "\0").replace("}}", "\1").replace("{name}", name).replace("\0", "{").replace("\1", "}"))
        made.append(os.path.relpath(p, dest))
    return sorted(made)
