/* nxshim7.dll - NX APP TRANSLATOR compatibility shim for Windows 7 SP1.
 * Exports user-mode APIs that exist only on Windows 8/10+. Where the real API exists (newer OS) the shim forwards to it,
 * so the same translated program still works on newer Windows. Where it does not, a Windows 7 fallback is used.
 * Fallbacks are semantic approximations (documented per function in README.md); they are NOT bit-exact equivalents.
 * Build: shim/build.sh (mingw-w64, x64 + i686). Copyright (c) 2026 Barman. */
#define _WIN32_WINNT 0x0601
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <string.h>

#define EXPORT __declspec(dllexport)

static FARPROC lookup(const char *mod, const char *name) {
    HMODULE m = GetModuleHandleA(mod);
    if (!m) m = LoadLibraryA(mod);
    return m ? GetProcAddress(m, name) : NULL;
}
/* real(): the NEWER (Win8/10) implementation if this OS has it. Building with -DNXSHIM_FORCE_FALLBACK makes it always NULL, so the
 * Windows 7 fallback code can be exercised and tested on any OS (tests only; never shipped). */
#ifdef NXSHIM_FORCE_FALLBACK
static FARPROC real(const char *mod, const char *name) { (void)mod; (void)name; return NULL; }
#else
static FARPROC real(const char *mod, const char *name) { return lookup(mod, name); }
#endif
#define REAL(type, mod, name) ((type)real(mod, name))
#define WIN7(type, mod, name) ((type)lookup(mod, name))      /* APIs that exist on Windows 7 itself */

/* ---- time ---- */
EXPORT VOID WINAPI GetSystemTimePreciseAsFileTime(LPFILETIME out) {
    typedef VOID (WINAPI *F)(LPFILETIME);
    F f = REAL(F, "kernel32.dll", "GetSystemTimePreciseAsFileTime");
    if (f && f != GetSystemTimePreciseAsFileTime) { f(out); return; }
    GetSystemTimeAsFileTime(out);              /* ~1-15 ms resolution instead of <1 us */
}

/* ---- thread description (cosmetic) ---- */
EXPORT HRESULT WINAPI SetThreadDescription(HANDLE h, PCWSTR d) {
    typedef HRESULT (WINAPI *F)(HANDLE, PCWSTR);
    F f = REAL(F, "kernel32.dll", "SetThreadDescription");
    if (f && f != SetThreadDescription) return f(h, d);
    (void)h; (void)d; return S_OK;
}
EXPORT HRESULT WINAPI GetThreadDescription(HANDLE h, PWSTR *d) {
    typedef HRESULT (WINAPI *F)(HANDLE, PWSTR *);
    F f = REAL(F, "kernel32.dll", "GetThreadDescription");
    if (f && f != GetThreadDescription) return f(h, d);
    (void)h;
    PWSTR p = (PWSTR)LocalAlloc(LMEM_FIXED | LMEM_ZEROINIT, sizeof(WCHAR));
    if (!p) return E_OUTOFMEMORY;
    *d = p; return S_OK;                         /* empty string, caller frees with LocalFree */
}

/* ---- WaitOnAddress family: polling fallback (correct, slower) ---- */
typedef BOOL (WINAPI *WOA)(volatile VOID *, PVOID, SIZE_T, DWORD);
typedef VOID (WINAPI *WBA)(PVOID);
static WOA real_woa(void) { WOA f = REAL(WOA, "kernel32.dll", "WaitOnAddress"); if (!f) f = REAL(WOA, "api-ms-win-core-synch-l1-2-0.dll", "WaitOnAddress"); return f; }
EXPORT BOOL WINAPI WaitOnAddress(volatile VOID *addr, PVOID cmp, SIZE_T size, DWORD ms) {
    WOA f = real_woa();
    if (f && f != WaitOnAddress) return f(addr, cmp, size, ms);
    if (size != 1 && size != 2 && size != 4 && size != 8) { SetLastError(ERROR_INVALID_PARAMETER); return FALSE; }
    DWORD start = GetTickCount(); unsigned spins = 0;
    for (;;) {
        if (memcmp((const void *)addr, cmp, size) != 0) return TRUE;
        if (ms != INFINITE && (DWORD)(GetTickCount() - start) >= ms) { SetLastError(ERROR_TIMEOUT); return FALSE; }
        if (++spins < 64) SwitchToThread(); else Sleep(1);
    }
}
EXPORT VOID WINAPI WakeByAddressSingle(PVOID a) {
    WBA f = REAL(WBA, "kernel32.dll", "WakeByAddressSingle");
    if (!f) f = REAL(WBA, "api-ms-win-core-synch-l1-2-0.dll", "WakeByAddressSingle");
    if (f && f != WakeByAddressSingle) f(a);      /* else: waiters poll, nothing to wake */
}
EXPORT VOID WINAPI WakeByAddressAll(PVOID a) {
    WBA f = REAL(WBA, "kernel32.dll", "WakeByAddressAll");
    if (!f) f = REAL(WBA, "api-ms-win-core-synch-l1-2-0.dll", "WakeByAddressAll");
    if (f && f != WakeByAddressAll) f(a);
}

/* ---- file / path ---- */
typedef struct { DWORD dwSize, dwSecurityQosFlags; LPSECURITY_ATTRIBUTES lpSecurityAttributes; HANDLE hTemplateFile; } NX_CREATEFILE2_EXTENDED_PARAMETERS;
EXPORT HANDLE WINAPI CreateFile2(LPCWSTR name, DWORD access, DWORD share, DWORD disp, NX_CREATEFILE2_EXTENDED_PARAMETERS *p) {
    typedef HANDLE (WINAPI *F)(LPCWSTR, DWORD, DWORD, DWORD, void *);
    F f = REAL(F, "kernel32.dll", "CreateFile2");
    if (f && (void *)f != (void *)CreateFile2) return f(name, access, share, disp, p);
    DWORD attrs = 0; LPSECURITY_ATTRIBUTES sa = NULL; HANDLE tmpl = NULL;
    if (p) { attrs = p->dwSecurityQosFlags; sa = p->lpSecurityAttributes; tmpl = p->hTemplateFile; }
    return CreateFileW(name, access, share, sa, disp, attrs, tmpl);
}
EXPORT BOOL WINAPI GetOverlappedResultEx(HANDLE h, LPOVERLAPPED o, LPDWORD n, DWORD ms, BOOL alertable) {
    typedef BOOL (WINAPI *F)(HANDLE, LPOVERLAPPED, LPDWORD, DWORD, BOOL);
    F f = REAL(F, "kernel32.dll", "GetOverlappedResultEx");
    if (f && f != GetOverlappedResultEx) return f(h, o, n, ms, alertable);
    if (ms == 0 || ms == INFINITE) return GetOverlappedResult(h, o, n, ms == INFINITE);
    HANDLE ev = o->hEvent ? o->hEvent : h;
    DWORD r = WaitForSingleObjectEx(ev, ms, alertable);
    if (r == WAIT_OBJECT_0) return GetOverlappedResult(h, o, n, FALSE);
    SetLastError(r == WAIT_TIMEOUT ? WAIT_TIMEOUT : (r == WAIT_IO_COMPLETION ? WAIT_IO_COMPLETION : GetLastError()));
    return FALSE;
}
EXPORT HRESULT WINAPI PathCchCanonicalizeEx(PWSTR out, SIZE_T cch, PCWSTR in, ULONG flags) {
    typedef HRESULT (WINAPI *F)(PWSTR, SIZE_T, PCWSTR, ULONG);
    F f = REAL(F, "kernelbase.dll", "PathCchCanonicalizeEx");
    if (f && f != PathCchCanonicalizeEx) return f(out, cch, in, flags);
    typedef BOOL (WINAPI *PC)(LPWSTR, LPCWSTR);
    PC pc = WIN7(PC, "shlwapi.dll", "PathCanonicalizeW");
    WCHAR tmp[MAX_PATH];
    (void)flags;
    if (!pc || lstrlenW(in) >= MAX_PATH) return HRESULT_FROM_WIN32(ERROR_FILENAME_EXCED_RANGE);
    if (!pc(tmp, in)) return HRESULT_FROM_WIN32(ERROR_BAD_PATHNAME);
    if ((SIZE_T)lstrlenW(tmp) + 1 > cch) return HRESULT_FROM_WIN32(ERROR_INSUFFICIENT_BUFFER);
    lstrcpyW(out, tmp); return S_OK;
}

/* ---- DPI (Win7: system DPI only; per-monitor DPI does not exist) ---- */
static UINT sys_dpi(void) { HDC dc = GetDC(NULL); int d = dc ? GetDeviceCaps(dc, LOGPIXELSX) : 96; if (dc) ReleaseDC(NULL, dc); return (UINT)(d > 0 ? d : 96); }
EXPORT UINT WINAPI GetDpiForSystem(void) { return sys_dpi(); }
EXPORT UINT WINAPI GetDpiForWindow(HWND w) { (void)w; return sys_dpi(); }
EXPORT BOOL WINAPI SetProcessDpiAwarenessContext(HANDLE ctx) {
    typedef BOOL (WINAPI *F)(HANDLE);
    F f = REAL(F, "user32.dll", "SetProcessDpiAwarenessContext");
    if (f && f != SetProcessDpiAwarenessContext) return f(ctx);
    typedef BOOL (WINAPI *S)(void);
    S s = WIN7(S, "user32.dll", "SetProcessDPIAware");
    return s ? s() : FALSE;
}
EXPORT INT WINAPI GetAwarenessFromDpiAwarenessContext(HANDLE ctx) {
    typedef INT (WINAPI *F)(HANDLE);
    F f = REAL(F, "user32.dll", "GetAwarenessFromDpiAwarenessContext");
    if (f && f != GetAwarenessFromDpiAwarenessContext) return f(ctx);
    return 1;                                     /* DPI_AWARENESS_SYSTEM_AWARE */
}
EXPORT INT WINAPI GetSystemMetricsForDpi(INT idx, UINT dpi) {
    typedef INT (WINAPI *F)(INT, UINT);
    F f = REAL(F, "user32.dll", "GetSystemMetricsForDpi");
    if (f && f != GetSystemMetricsForDpi) return f(idx, dpi);
    return GetSystemMetrics(idx);
}
EXPORT BOOL WINAPI AdjustWindowRectExForDpi(LPRECT r, DWORD style, BOOL menu, DWORD ex, UINT dpi) {
    typedef BOOL (WINAPI *F)(LPRECT, DWORD, BOOL, DWORD, UINT);
    F f = REAL(F, "user32.dll", "AdjustWindowRectExForDpi");
    if (f && f != AdjustWindowRectExForDpi) return f(r, style, menu, ex, dpi);
    return AdjustWindowRectEx(r, style, menu, ex);
}
EXPORT BOOL WINAPI EnableNonClientDpiScaling(HWND w) {
    typedef BOOL (WINAPI *F)(HWND);
    F f = REAL(F, "user32.dll", "EnableNonClientDpiScaling");
    if (f && f != EnableNonClientDpiScaling) return f(w);
    return TRUE;
}

/* ---- packaging / mitigation / memory ---- */
EXPORT LONG WINAPI GetCurrentPackageFullName(UINT32 *len, PWSTR name) { (void)len; (void)name; return APPMODEL_ERROR_NO_PACKAGE; }
EXPORT LONG WINAPI GetCurrentPackageId(UINT32 *len, BYTE *buf) { (void)len; (void)buf; return APPMODEL_ERROR_NO_PACKAGE; }
EXPORT BOOL WINAPI SetProcessMitigationPolicy(int policy, PVOID buf, SIZE_T len) {
    typedef BOOL (WINAPI *F)(int, PVOID, SIZE_T);
    F f = REAL(F, "kernel32.dll", "SetProcessMitigationPolicy");
    if (f && f != SetProcessMitigationPolicy) return f(policy, buf, len);
    SetLastError(ERROR_NOT_SUPPORTED); return FALSE;
}
EXPORT PVOID WINAPI VirtualAlloc2(HANDLE proc, PVOID base, SIZE_T size, ULONG type, ULONG prot, PVOID ext, ULONG n) {
    typedef PVOID (WINAPI *F)(HANDLE, PVOID, SIZE_T, ULONG, ULONG, PVOID, ULONG);
    F f = REAL(F, "kernelbase.dll", "VirtualAlloc2");
    if (f && f != VirtualAlloc2) return f(proc, base, size, type, prot, ext, n);
    if (n == 0 && (!proc || proc == GetCurrentProcess())) return VirtualAlloc(base, size, type, prot);  /* plain case only */
    SetLastError(ERROR_CALL_NOT_IMPLEMENTED); return NULL;
}
EXPORT PVOID WINAPI MapViewOfFile3(HANDLE m, HANDLE p, PVOID b, ULONG64 off, SIZE_T sz, ULONG t, ULONG prot, PVOID ext, ULONG n) {
    typedef PVOID (WINAPI *F)(HANDLE, HANDLE, PVOID, ULONG64, SIZE_T, ULONG, ULONG, PVOID, ULONG);
    F f = REAL(F, "kernelbase.dll", "MapViewOfFile3");
    if (f && f != MapViewOfFile3) return f(m, p, b, off, sz, t, prot, ext, n);
    (void)p; (void)t; (void)ext; (void)prot; (void)b;
    if (n == 0) { PVOID v = MapViewOfFile(m, FILE_MAP_READ | FILE_MAP_WRITE, (DWORD)(off >> 32), (DWORD)off, sz); if (v) return v; }
    SetLastError(ERROR_CALL_NOT_IMPLEMENTED); return NULL;
}
EXPORT DWORD WINAPI OfferVirtualMemory(PVOID a, SIZE_T s, int pri) {
    typedef DWORD (WINAPI *F)(PVOID, SIZE_T, int);
    F f = REAL(F, "kernel32.dll", "OfferVirtualMemory");
    if (f && f != OfferVirtualMemory) return f(a, s, pri);
    return ERROR_SUCCESS;                          /* keep the pages: always legal */
}
EXPORT DWORD WINAPI ReclaimVirtualMemory(PVOID a, SIZE_T s) {
    typedef DWORD (WINAPI *F)(PVOID, SIZE_T);
    F f = REAL(F, "kernel32.dll", "ReclaimVirtualMemory");
    if (f && f != ReclaimVirtualMemory) return f(a, s);
    return ERROR_SUCCESS;
}
EXPORT BOOL WINAPI CompareObjectHandles(HANDLE a, HANDLE b) {
    typedef BOOL (WINAPI *F)(HANDLE, HANDLE);
    F f = REAL(F, "kernelbase.dll", "CompareObjectHandles");
    if (f && f != CompareObjectHandles) return f(a, b);
    return a == b;                                  /* approximation: identical handle values only */
}

/* ---- batch 2: simple APIs with exact or harmless Windows 7 fallbacks ---- */
EXPORT VOID WINAPI GetCurrentThreadStackLimits(PULONG_PTR low, PULONG_PTR high) {
    typedef VOID (WINAPI *F)(PULONG_PTR, PULONG_PTR);
    F f = REAL(F, "kernel32.dll", "GetCurrentThreadStackLimits");
    if (f && f != GetCurrentThreadStackLimits) { f(low, high); return; }
    NT_TIB *tib = (NT_TIB *)NtCurrentTeb();                       /* exact: the TEB holds the same two values */
    *low = (ULONG_PTR)tib->StackLimit; *high = (ULONG_PTR)tib->StackBase;
}
EXPORT BOOL WINAPI IsWow64Process2(HANDLE h, USHORT *proc, USHORT *native) {
    typedef BOOL (WINAPI *F)(HANDLE, USHORT *, USHORT *);
    F f = REAL(F, "kernel32.dll", "IsWow64Process2");
    if (f && f != IsWow64Process2) return f(h, proc, native);
    BOOL wow = FALSE;
    if (!IsWow64Process(h, &wow)) return FALSE;
#ifdef _WIN64
    *native = 0x8664; *proc = 0;                                 /* a 64-bit process cannot be WOW64 */
    (void)wow;
#else
    *proc = wow ? 0x014c : 0; *native = wow ? 0x8664 : 0x014c;   /* 32-bit process: on 64-bit Windows it is WOW64 (x64 host) */
#endif
    return TRUE;
}
EXPORT BOOL WINAPI GetProcessMitigationPolicy(HANDLE h, int policy, PVOID buf, SIZE_T len) {
    typedef BOOL (WINAPI *F)(HANDLE, int, PVOID, SIZE_T);
    F f = REAL(F, "kernel32.dll", "GetProcessMitigationPolicy");
    if (f && f != GetProcessMitigationPolicy) return f(h, policy, buf, len);
    SetLastError(ERROR_NOT_SUPPORTED); return FALSE;
}
EXPORT BOOL WINAPI GetThreadInformation(HANDLE h, int cls, PVOID buf, DWORD len) {
    typedef BOOL (WINAPI *F)(HANDLE, int, PVOID, DWORD);
    F f = REAL(F, "kernel32.dll", "GetThreadInformation");
    if (f && f != GetThreadInformation) return f(h, cls, buf, len);
    SetLastError(ERROR_NOT_SUPPORTED); return FALSE;
}
EXPORT BOOL WINAPI SetThreadInformation(HANDLE h, int cls, PVOID buf, DWORD len) {
    typedef BOOL (WINAPI *F)(HANDLE, int, PVOID, DWORD);
    F f = REAL(F, "kernel32.dll", "SetThreadInformation");
    if (f && f != SetThreadInformation) return f(h, cls, buf, len);
    SetLastError(ERROR_NOT_SUPPORTED); return FALSE;
}
EXPORT BOOL WINAPI GetProcessInformation(HANDLE h, int cls, PVOID buf, DWORD len) {
    typedef BOOL (WINAPI *F)(HANDLE, int, PVOID, DWORD);
    F f = REAL(F, "kernel32.dll", "GetProcessInformation");
    if (f && f != GetProcessInformation) return f(h, cls, buf, len);
    SetLastError(ERROR_NOT_SUPPORTED); return FALSE;
}
EXPORT BOOL WINAPI SetProcessInformation(HANDLE h, int cls, PVOID buf, DWORD len) {
    typedef BOOL (WINAPI *F)(HANDLE, int, PVOID, DWORD);
    F f = REAL(F, "kernel32.dll", "SetProcessInformation");
    if (f && f != SetProcessInformation) return f(h, cls, buf, len);
    SetLastError(ERROR_NOT_SUPPORTED); return FALSE;
}
EXPORT BOOL WINAPI PrefetchVirtualMemory(HANDLE h, ULONG_PTR n, PVOID entries, ULONG flags) {
    typedef BOOL (WINAPI *F)(HANDLE, ULONG_PTR, PVOID, ULONG);
    F f = REAL(F, "kernel32.dll", "PrefetchVirtualMemory");
    if (f && f != PrefetchVirtualMemory) return f(h, n, entries, flags);
    (void)h; (void)n; (void)entries; (void)flags; return TRUE;      /* advisory hint only */
}
EXPORT DWORD WINAPI DiscardVirtualMemory(PVOID a, SIZE_T s) {
    typedef DWORD (WINAPI *F)(PVOID, SIZE_T);
    F f = REAL(F, "kernel32.dll", "DiscardVirtualMemory");
    if (f && f != DiscardVirtualMemory) return f(a, s);
    (void)a; (void)s; return ERROR_SUCCESS;                          /* advisory: keeping the pages is always legal */
}
EXPORT HANDLE WINAPI GetThreadDpiAwarenessContext(void) {
    typedef HANDLE (WINAPI *F)(void);
    F f = REAL(F, "user32.dll", "GetThreadDpiAwarenessContext");
    if (f && f != GetThreadDpiAwarenessContext) return f();
    return (HANDLE)(LONG_PTR)-2;                                     /* DPI_AWARENESS_CONTEXT_SYSTEM_AWARE */
}
EXPORT HANDLE WINAPI GetWindowDpiAwarenessContext(HWND w) {
    typedef HANDLE (WINAPI *F)(HWND);
    F f = REAL(F, "user32.dll", "GetWindowDpiAwarenessContext");
    if (f && f != GetWindowDpiAwarenessContext) return f(w);
    return (HANDLE)(LONG_PTR)-2;
}
EXPORT BOOL WINAPI AreDpiAwarenessContextsEqual(HANDLE a, HANDLE b) {
    typedef BOOL (WINAPI *F)(HANDLE, HANDLE);
    F f = REAL(F, "user32.dll", "AreDpiAwarenessContextsEqual");
    if (f && f != AreDpiAwarenessContextsEqual) return f(a, b);
    return a == b;
}
EXPORT BOOL WINAPI IsValidDpiAwarenessContext(HANDLE c) {
    typedef BOOL (WINAPI *F)(HANDLE);
    F f = REAL(F, "user32.dll", "IsValidDpiAwarenessContext");
    if (f && f != IsValidDpiAwarenessContext) return f(c);
    LONG_PTR v = (LONG_PTR)c; return v >= -5 && v <= -1;
}
EXPORT UINT WINAPI GetDpiFromDpiAwarenessContext(HANDLE c) {
    typedef UINT (WINAPI *F)(HANDLE);
    F f = REAL(F, "user32.dll", "GetDpiFromDpiAwarenessContext");
    if (f && f != GetDpiFromDpiAwarenessContext) return f(c);
    LONG_PTR v = (LONG_PTR)c; return v == -1 ? 96 : (v >= -5 && v <= -2 ? sys_dpi() : 0);
}
EXPORT UINT WINAPI GetSystemDpiForProcess(HANDLE p) {
    typedef UINT (WINAPI *F)(HANDLE);
    F f = REAL(F, "user32.dll", "GetSystemDpiForProcess");
    if (f && f != GetSystemDpiForProcess) return f(p);
    (void)p; return sys_dpi();
}
EXPORT BOOL WINAPI IsImmersiveProcess(HANDLE p) {
    typedef BOOL (WINAPI *F)(HANDLE);
    F f = REAL(F, "user32.dll", "IsImmersiveProcess");
    if (f && f != IsImmersiveProcess) return f(p);
    (void)p; return FALSE;                                          /* Windows 7 has no immersive (Store) processes */
}
EXPORT BOOL WINAPI EnableMouseInPointer(BOOL on) {
    typedef BOOL (WINAPI *F)(BOOL);
    F f = REAL(F, "user32.dll", "EnableMouseInPointer");
    if (f && f != EnableMouseInPointer) return f(on);
    (void)on; SetLastError(ERROR_NOT_SUPPORTED); return FALSE;
}
EXPORT BOOL WINAPI IsMouseInPointerEnabled(void) {
    typedef BOOL (WINAPI *F)(void);
    F f = REAL(F, "user32.dll", "IsMouseInPointerEnabled");
    if (f && f != IsMouseInPointerEnabled) return f();
    return FALSE;
}

BOOL WINAPI DllMain(HINSTANCE h, DWORD why, LPVOID r) { (void)h; (void)why; (void)r; return TRUE; }
