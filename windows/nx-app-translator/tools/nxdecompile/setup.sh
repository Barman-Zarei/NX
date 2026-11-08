#!/bin/sh
# Builds tools/nxdecompile/bin/NxDecompile.dll (ILSpy v8.2 engine) offline-capable: needs git + github.com access once, and the .NET 8 SDK (apt: dotnet-sdk-8.0).
set -eu
cd "$(dirname "$0")"
rm -rf _ils dec bin && mkdir _ils && cd _ils
git init -q && git remote add origin https://github.com/icsharpcode/ILSpy.git && git config core.sparseCheckout true
echo 'ICSharpCode.Decompiler/' > .git/info/sparse-checkout
git fetch -q --depth 1 origin tag v8.2 && git checkout -q v8.2
cd .. && mkdir dec && cp -r _ils/ICSharpCode.Decompiler/* dec/ && rm -rf _ils
rm -f dec/ICSharpCode.Decompiler.csproj dec/Properties/AssemblyInfo.cs
# net8 already ships these LINQ helpers; the netstandard polyfills in the library would be ambiguous
python3 - <<'PY'
import re
p='dec/Util/CollectionExtensions.cs'
L=open(p,encoding='utf-8-sig').read().split("\n")
pats=[r"IEnumerable<\(A, B\)> Zip<A, B>\(", r"HashSet<T> ToHashSet<T>\(", r"> SkipLast<T>\(", r"> TakeLast<T>\(", r"\bT MinBy<T, K>\(", r"\bT MaxBy<T, K>\("]
for pat in pats:
    while True:
        idx=next((i for i,l in enumerate(L) if re.search(pat,l) and "public static" in l),None)
        if idx is None: break
        j,depth,seen=idx,0,False
        while True:
            for c in L[j]:
                if c=="{": depth+=1; seen=True
                elif c=="}": depth-=1
            if seen and depth==0: break
            j+=1
        del L[idx:j+1]
open(p,'w',encoding='utf-8').write("\n".join(L))
PY
export DOTNET_CLI_TELEMETRY_OPTOUT=1 DOTNET_NOLOGO=1
dotnet build -c Release -o bin 2>&1 | tail -3
echo "built: $(pwd)/bin/NxDecompile.dll"
