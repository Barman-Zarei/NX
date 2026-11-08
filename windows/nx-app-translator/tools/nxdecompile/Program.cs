// NxDecompile: tiny command-line wrapper around the ILSpy decompiler engine (MIT, https://github.com/icsharpcode/ILSpy, tag v8.2).
// usage: dotnet NxDecompile.dll ASSEMBLY OUT.cs [csharp-version: 7.3 | 8 | 9 | latest]
using System;
using System.IO;
using ICSharpCode.Decompiler;
using ICSharpCode.Decompiler.CSharp;
using ICSharpCode.Decompiler.Metadata;

static class NxDecompile
{
    static int Main(string[] a)
    {
        if (a.Length < 2) { Console.Error.WriteLine("usage: NxDecompile ASSEMBLY OUT.cs [7.3|8|9|latest]"); return 2; }
        var lang = a.Length > 2 && a[2] == "7.3" ? LanguageVersion.CSharp7_3 : a.Length > 2 && a[2] == "8" ? LanguageVersion.CSharp8_0 : LanguageVersion.Latest;
        var module = new PEFile(a[0]);
        var resolver = new UniversalAssemblyResolver(a[0], false, module.DetectTargetFrameworkId());
        var settings = new DecompilerSettings(lang) { ThrowOnAssemblyResolveErrors = false };
        File.WriteAllText(a[1], new CSharpDecompiler(a[0], resolver, settings).DecompileWholeModuleAsString());
        return 0;
    }
}
