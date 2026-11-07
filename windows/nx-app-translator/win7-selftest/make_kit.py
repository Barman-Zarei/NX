"""Builds the Windows 7 self-test kit (run on NX/Linux with mingw-w64): kit/{x86,x64}/ with
  probe.exe + nxshim7.dll (REAL shim: on Windows 7 the genuine fallbacks run), hello_original.exe (uses Win8+ APIs: expected to FAIL on Win7),
  hello-setup.exe (the same program translated by NX APP TRANSLATOR + native installer: expected to PASS), RUN-ME.bat.
Usage: python3 win7-selftest/make_kit.py OUTDIR"""
import os, shutil, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, ".."))
from nxat import analyze as A, adapt as D, pack as K

HELLO = r'''#define _WIN32_WINNT 0x0A00
#include <windows.h>
#include <stdio.h>
int main(void){ FILETIME f; GetSystemTimePreciseAsFileTime(&f); volatile LONG v=1; LONG c=2; BOOL w=WaitOnAddress(&v,&c,4,10);
 printf("HELLO-OK precise=%d waitonaddress=%d dpi=%u\n", f.dwHighDateTime!=0, w, GetDpiForSystem()); return 0; }
'''
CC = {"x86": "i686-w64-mingw32-gcc", "x64": "x86_64-w64-mingw32-gcc"}


def main(out):
    for arch, cc in CC.items():
        cc = shutil.which(cc)
        d = os.path.join(out, arch); os.makedirs(d, exist_ok=True)
        t = tempfile.mkdtemp()
        open(os.path.join(t, "hello.c"), "w").write(HELLO)
        subprocess.check_call([cc, "-O1", "-o", os.path.join(d, "hello_original.exe"), os.path.join(t, "hello.c"), "-lkernel32", "-luser32", "-lsynchronization"])
        subprocess.check_call([cc, "-O1", "-o", os.path.join(d, "probe.exe"), os.path.join(ROOT, "tests", "fallback_probe.c")])
        shutil.copy2(os.path.join(ROOT, "shim", "bin", arch, "nxshim7.dll"), d)
        app = os.path.join(t, "app"); os.makedirs(app); shutil.copy2(os.path.join(d, "hello_original.exe"), os.path.join(app, "hello.exe"))
        rep = A.analyze(app); D.adapt(app, rep)
        assert A.analyze(app)["compatible_now"]
        K.build_installer(os.path.join(ROOT, "stub", "bin", "x86", "nx-app-installer.exe"), K.make_payload(app, os.path.join(t, "p.zip")),
                          {"name": "NXAT Selftest Hello", "entry": "hello.exe", "version": "1", "publisher": "NX"}, os.path.join(d, "hello-setup.exe"))
    shutil.copy2(os.path.join(HERE, "RUN-ME.bat"), out)
    shutil.copy2(os.path.join(HERE, "README.txt"), out)


if __name__ == "__main__":
    main(sys.argv[1])
