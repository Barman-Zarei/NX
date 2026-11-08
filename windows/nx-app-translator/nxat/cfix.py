"""Deterministic repair of RetDec's C output so it can be compiled again (mingw-w64) - no model needed.
RetDec emits the whole statically linked program (including the C runtime) and redeclares system functions with its own (wrong) types.
Steps: 1. keep only functions reachable from `main` (the runtime is linked from the real CRT instead)
       2. loop on compiler errors: drop RetDec's conflicting prototypes/definitions of system symbols and its struct redefinitions.
Anything the loop cannot fix is returned as an error text (the Brok loop gets it as feedback). Research-grade: works on small programs."""
import re, subprocess, tempfile, os

FUNC_DEF = re.compile(r"^[A-Za-z_][\w\s\*]*?\b([A-Za-z_]\w*)\s*\([^;{}]*\)\s*\{\s*$")
PROTO = re.compile(r"^[A-Za-z_][\w\s\*]*?\b([A-Za-z_]\w*)\s*\([^{};]*\)\s*;\s*$")


def split_functions(lines):
    """-> list of (name, start, end) for top-level function definitions (column-0 header ... column-0 closing brace)."""
    out, i = [], 0
    while i < len(lines):
        m = FUNC_DEF.match(lines[i])
        if m and not lines[i].startswith((" ", "\t", "typedef", "struct", "//")):
            j = i + 1
            while j < len(lines) and lines[j] != "}":
                j += 1
            out.append((m.group(1), i, j)); i = j + 1
        else:
            i += 1
    return out


def is_runtime(name):
    """C-runtime / compiler internals (named when the binary is not stripped): linked from the real CRT instead of the decompiled copy."""
    return name.startswith(("__", "_mingw", "_imp")) or name.startswith("mingw_")


def prune_reachable(text, entry="main"):
    lines = text.split("\n")
    funcs = split_functions(lines)
    by = {n: (s, e) for n, s, e in funcs}
    if entry not in by:
        return text
    keep, todo = set(), [entry]
    while todo:
        n = todo.pop()
        if n in keep:
            continue
        keep.add(n)
        s, e = by[n]
        body = "\n".join(lines[s + 1:e])
        for other in by:
            if other not in keep and not is_runtime(other) and re.search(r"\b%s\b" % re.escape(other), body):
                todo.append(other)
    drop = set()
    for n, s, e in funcs:
        if n not in keep or (is_runtime(n) and n != entry):
            drop.update(range(s, e + 1))
    return "\n".join(l for i, l in enumerate(lines) if i not in drop)


def _remove_struct_block(lines, line_no):
    i = line_no - 1
    if i < 0 or i >= len(lines) or not lines[i].startswith("struct"):
        return False
    j = i
    while j < len(lines) and not lines[j].startswith("};"):
        j += 1
    del lines[i:j + 1]
    return True


def _remove_symbol(lines, name):
    """Remove column-0 prototypes and (if present) the definition of `name`. -> number of removed lines."""
    before = len(lines)
    funcs = [f for f in split_functions(lines) if f[0] == name]
    for n, s, e in sorted(funcs, key=lambda f: -f[1]):
        del lines[s:e + 1]
    lines[:] = [l for l in lines if not (PROTO.match(l) and PROTO.match(l).group(1) == name)]
    return before - len(lines)


def repair(path, gcc, flags=(), max_iter=40):
    """Edit `path` in place until `gcc -fsyntax-only` accepts it. -> (ok, last_error_text)."""
    text = open(path).read()
    open(path, "w").write(prune_reachable(text))
    last = ""
    for _ in range(max_iter):
        r = subprocess.run([gcc, "-fsyntax-only", "-w"] + list(flags) + [path], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True,
                           env=dict(os.environ, LC_ALL="C"))
        if r.returncode == 0:
            return True, ""
        last = r.stdout
        lines = open(path).read().split("\n")
        changed = False
        errs = re.findall(r"^%s:(\d+):\d+: error: (.*)$" % re.escape(path), r.stdout, re.M)
        for ln, msg in errs:
            m = re.match(r"conflicting types for '(\w+)'", msg)
            if m:
                changed |= _remove_symbol(lines, m.group(1)) > 0; break
            if msg.startswith("redefinition of 'struct"):
                changed |= _remove_struct_block(lines, int(ln)); break
            m = re.match(r"duplicate label '(\w+)'", msg)
            if m:                                   # RetDec sometimes emits the same label twice: rename the second definition's line
                i = int(ln) - 1
                if 0 <= i < len(lines) and lines[i].strip().startswith(m.group(1) + ":"):
                    lines[i] = lines[i].replace(m.group(1) + ":", m.group(1) + "_dup:", 1); changed = True
                break
            m = re.match(r"redefinition of '(\w+)'", msg)
            if m:
                changed |= _remove_symbol(lines, m.group(1)) > 0; break
        if not changed:
            return False, last
        open(path, "w").write("\n".join(lines))
    return False, last


def _remove_global(lines, name):
    """Remove column-0 global variable definitions/declarations of `name` (possibly multi-line initialisers)."""
    out, i, removed = [], 0, False
    pat = re.compile(r"^[A-Za-z_][^()]*?\b%s\b[^()]*(=|;)|^[A-Za-z_][^\n]*\(\s*\*\s*%s\s*\)\s*\(" % (re.escape(name), re.escape(name)))
    while i < len(lines):
        l = lines[i]
        if pat.match(l) and not l.startswith(("typedef", "struct " + name)):
            removed = True
            while i < len(lines) and not lines[i].rstrip().endswith(";"):
                i += 1
            i += 1
            continue
        out.append(l); i += 1
    lines[:] = out
    return removed


def rebuild(path, gcc, out_exe, flags=(), max_iter=30):
    """repair() then compile+link into out_exe, fixing 'multiple definition' of decompiled import thunks/globals. -> (ok, error text)."""
    ok, err = repair(path, gcc, flags)
    if not ok:
        return False, err
    last = ""
    for _ in range(max_iter):
        r = subprocess.run([gcc, "-w", "-O1", "-o", out_exe, path] + list(flags) + ["-luser32", "-lgdi32", "-lkernel32", "-ladvapi32", "-lshell32"],
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True, env=dict(os.environ, LC_ALL="C"))
        if r.returncode == 0 and os.path.isfile(out_exe):
            return True, ""
        last = r.stdout
        names = set(re.findall(r"multiple definition of `(\w+)'", r.stdout))
        if not names:
            return False, last
        lines = open(path).read().split("\n")
        cands = names | {n[1:] for n in names if n.startswith("_")}     # x86 linker names carry one extra leading underscore
        if not any([_remove_global(lines, n) or bool(_remove_symbol(lines, n)) for n in cands]):
            return False, last
        open(path, "w").write("\n".join(lines))
    return False, last
