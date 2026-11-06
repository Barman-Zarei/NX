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

static FARPROC real(const char *mod, const char *name) {
    HMODULE m = GetModuleHandleA(mod);
    if (!m) m = LoadLibraryA(mod);
    return m ? GetProcAddress(m, name) : NULL;
}
#define REAL(type, mod, name) ((type)real(mod, name))

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
    PC pc = REAL(PC, "shlwapi.dll", "PathCanonicalizeW");
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
    S s = REAL(S, "user32.dll", "SetProcessDPIAware");
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

BOOL WINAPI DllMain(HINSTANCE h, DWORD why, LPVOID r) { (void)h; (void)why; (void)r; return TRUE; }
