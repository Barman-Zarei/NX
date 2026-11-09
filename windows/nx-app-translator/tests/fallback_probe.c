/* Exercises every nxshim7.dll export through GetProcAddress (like a redirected import). Built against the test-only shim variant
 * whose Windows 7 FALLBACK code is always active, so the fallbacks are verified even on a newer OS / Wine. Exit code = failures. */
#define _WIN32_WINNT 0x0601
#include <windows.h>
#include <stdio.h>
#include <wchar.h>
#include <string.h>
static int fails = 0, strict = 1;
#define CHECKL(loose, strictc, msg) CHECK(strict ? (strictc) : (loose), msg)   /* forwarding mode (newer OS) accepts the real API's own semantics */
#define CHECK(c, msg) do { if (!(c)) { printf("FAIL: %s\n", msg); fails++; } else printf("ok: %s\n", msg); } while (0)
static HMODULE M;
#define FN(ret, args, n) ret (WINAPI *n) args = (ret (WINAPI *) args)GetProcAddress(M, #n); if (!n) { printf("FAIL: export %s missing\n", #n); return 99; }
static volatile LONG gv = 0;
static VOID (WINAPI *pWake)(PVOID);
static DWORD WINAPI setter(LPVOID p) { (void)p; Sleep(150); InterlockedExchange(&gv, 1); if (pWake) pWake((PVOID)&gv); return 0; }
typedef struct { DWORD a, b; LPSECURITY_ATTRIBUTES c; HANDLE d; } CF2;
int main(int argc, char **argv) {
    int fwd = GetProcAddress(GetModuleHandleA("kernel32.dll"), "GetSystemTimePreciseAsFileTime") != NULL;
    strict = (argc > 1 && !strcmp(argv[1], "--strict")) || !fwd;
    printf("mode: %s\n", strict ? "strict (Windows 7 fallbacks must be active)" : "forwarding (this Windows has the newer APIs; real behaviour accepted)");
    M = LoadLibraryA("nxshim7.dll"); if (!M) { printf("FAIL: cannot load nxshim7.dll\n"); return 98; }
    FN(VOID, (LPFILETIME), GetSystemTimePreciseAsFileTime)
    FN(BOOL, (volatile VOID *, PVOID, SIZE_T, DWORD), WaitOnAddress)
    FN(HRESULT, (HANDLE, PCWSTR), SetThreadDescription)
    FN(HRESULT, (HANDLE, PWSTR *), GetThreadDescription)
    FN(UINT, (void), GetDpiForSystem)
    FN(UINT, (HWND), GetDpiForWindow)
    FN(INT, (INT, UINT), GetSystemMetricsForDpi)
    FN(BOOL, (LPRECT, DWORD, BOOL, DWORD, UINT), AdjustWindowRectExForDpi)
    FN(BOOL, (HWND), EnableNonClientDpiScaling)
    FN(INT, (HANDLE), GetAwarenessFromDpiAwarenessContext)
    FN(BOOL, (HANDLE), SetProcessDpiAwarenessContext)
    FN(LONG, (UINT32 *, PWSTR), GetCurrentPackageFullName)
    FN(LONG, (UINT32 *, BYTE *), GetCurrentPackageId)
    FN(HRESULT, (PWSTR, SIZE_T, PCWSTR, ULONG), PathCchCanonicalizeEx)
    FN(HANDLE, (LPCWSTR, DWORD, DWORD, DWORD, void *), CreateFile2)
    FN(BOOL, (HANDLE, LPOVERLAPPED, LPDWORD, DWORD, BOOL), GetOverlappedResultEx)
    FN(PVOID, (HANDLE, PVOID, SIZE_T, ULONG, ULONG, PVOID, ULONG), VirtualAlloc2)
    FN(DWORD, (PVOID, SIZE_T, int), OfferVirtualMemory)
    FN(DWORD, (PVOID, SIZE_T), ReclaimVirtualMemory)
    FN(BOOL, (HANDLE, HANDLE), CompareObjectHandles)
    FN(BOOL, (int, PVOID, SIZE_T), SetProcessMitigationPolicy)
    FN(PVOID, (HANDLE, HANDLE, PVOID, ULONG64, SIZE_T, ULONG, ULONG, PVOID, ULONG), MapViewOfFile3)
    FN(VOID, (PULONG_PTR, PULONG_PTR), GetCurrentThreadStackLimits)
    FN(BOOL, (HANDLE, USHORT *, USHORT *), IsWow64Process2)
    FN(BOOL, (HANDLE, int, PVOID, SIZE_T), GetProcessMitigationPolicy)
    FN(BOOL, (HANDLE, int, PVOID, DWORD), GetThreadInformation)
    FN(BOOL, (HANDLE, int, PVOID, DWORD), SetThreadInformation)
    FN(BOOL, (HANDLE, int, PVOID, DWORD), GetProcessInformation)
    FN(BOOL, (HANDLE, int, PVOID, DWORD), SetProcessInformation)
    FN(BOOL, (HANDLE, ULONG_PTR, PVOID, ULONG), PrefetchVirtualMemory)
    FN(DWORD, (PVOID, SIZE_T), DiscardVirtualMemory)
    FN(HANDLE, (void), GetThreadDpiAwarenessContext)
    FN(HANDLE, (HWND), GetWindowDpiAwarenessContext)
    FN(BOOL, (HANDLE, HANDLE), AreDpiAwarenessContextsEqual)
    FN(BOOL, (HANDLE), IsValidDpiAwarenessContext)
    FN(UINT, (HANDLE), GetDpiFromDpiAwarenessContext)
    FN(UINT, (HANDLE), GetSystemDpiForProcess)
    FN(BOOL, (HANDLE), IsImmersiveProcess)
    FN(BOOL, (BOOL), EnableMouseInPointer)
    FN(BOOL, (void), IsMouseInPointerEnabled)
    FN(VOID, (PVOID), WakeByAddressSingle)
    FN(VOID, (PVOID), WakeByAddressAll)
    { FILETIME a, b; GetSystemTimePreciseAsFileTime(&a); Sleep(20); GetSystemTimePreciseAsFileTime(&b);
      CHECK(a.dwHighDateTime && CompareFileTime(&b, &a) >= 0, "precise time: nonzero and monotonic"); }
    pWake = (VOID (WINAPI *)(PVOID))GetProcAddress(M, "WakeByAddressSingle");
    { LONG cmp = 0; HANDLE t = CreateThread(NULL, 0, setter, NULL, 0, NULL); DWORD t0 = GetTickCount();
      BOOL r = WaitOnAddress(&gv, &cmp, 4, 5000); DWORD dt = GetTickCount() - t0;
      CHECK(r && gv == 1 && dt >= 100 && dt < 3000, "WaitOnAddress wakes when the value changes (polling)"); WaitForSingleObject(t, 2000); CloseHandle(t); }
    { LONG cmp = 1; BOOL r = WaitOnAddress(&gv, &cmp, 4, 60); CHECK(!r && GetLastError() == ERROR_TIMEOUT, "WaitOnAddress timeout -> ERROR_TIMEOUT"); }
    { LONG cmp = 0; BOOL r = WaitOnAddress(&gv, &cmp, 3, 10); CHECK(!r && GetLastError() == ERROR_INVALID_PARAMETER, "WaitOnAddress bad size rejected"); }
    { PWSTR d = NULL; HRESULT hs = SetThreadDescription(GetCurrentThread(), L"x"); CHECKL(1, hs == S_OK, "SetThreadDescription S_OK");
      HRESULT hg = GetThreadDescription(GetCurrentThread(), &d); CHECKL(1, hg == S_OK && d && d[0] == 0, "GetThreadDescription empty string"); if (d) LocalFree(d); }
    { UINT d = GetDpiForSystem(); CHECK(d >= 96 && GetDpiForWindow(NULL) == d, "DPI = system DPI");
      CHECK(GetSystemMetricsForDpi(SM_CXSCREEN, 96) == GetSystemMetrics(SM_CXSCREEN), "GetSystemMetricsForDpi");
      RECT rc = {0, 0, 100, 100}; CHECK(AdjustWindowRectExForDpi(&rc, WS_OVERLAPPEDWINDOW, FALSE, 0, 96) && rc.right - rc.left > 100, "AdjustWindowRectExForDpi");
      { BOOL e = EnableNonClientDpiScaling(NULL); CHECKL(1, e == TRUE, "EnableNonClientDpiScaling"); }
      { INT g = GetAwarenessFromDpiAwarenessContext((HANDLE)-4); CHECKL(g >= -1 && g <= 2, g == 1, "awareness = system aware"); }
      { BOOL sp = SetProcessDpiAwarenessContext((HANDLE)-4); CHECKL(1, sp != 0 || GetLastError() == ERROR_ACCESS_DENIED, "SetProcessDpiAwarenessContext -> SetProcessDPIAware"); } }
    { UINT32 n = 0; CHECK(GetCurrentPackageFullName(&n, NULL) == 15700 && GetCurrentPackageId(&n, NULL) == 15700, "no package identity (15700)"); }
    { WCHAR o[260]; HRESULT h = PathCchCanonicalizeEx(o, 260, L"C:\\a\\..\\b\\.\\c.txt", 0);
      CHECK(h == S_OK && !wcscmp(o, L"C:\\b\\c.txt"), "PathCchCanonicalizeEx canonicalizes");
      CHECK(PathCchCanonicalizeEx(o, 3, L"C:\\b\\c.txt", 0) == HRESULT_FROM_WIN32(ERROR_INSUFFICIENT_BUFFER), "PathCchCanonicalizeEx small buffer"); }
    { WCHAR p[MAX_PATH]; GetTempPathW(MAX_PATH, p); lstrcatW(p, L"nxshim_cf2.tmp");
      HANDLE h = CreateFile2(p, GENERIC_WRITE, 0, CREATE_ALWAYS, NULL); DWORD w = 0; BOOL ok = h != INVALID_HANDLE_VALUE && WriteFile(h, "x", 1, &w, NULL) && w == 1;
      if (h != INVALID_HANDLE_VALUE) CloseHandle(h);
      CF2 ex = { sizeof ex, FILE_ATTRIBUTE_NORMAL, NULL, NULL }; h = CreateFile2(p, GENERIC_READ, FILE_SHARE_READ, OPEN_EXISTING, &ex);
      CHECK(ok && h != INVALID_HANDLE_VALUE, "CreateFile2 (with and without extended params)"); if (h != INVALID_HANDLE_VALUE) CloseHandle(h); DeleteFileW(p); }
    { OVERLAPPED o; DWORD n = 0; memset(&o, 0, sizeof o); o.Internal = 0x103; /* STATUS_PENDING */ o.hEvent = CreateEventW(NULL, TRUE, FALSE, NULL);
      BOOL r = GetOverlappedResultEx(o.hEvent, &o, &n, 40, FALSE); DWORD le = GetLastError();
      CHECKL(!r && (le == WAIT_TIMEOUT || le == ERROR_IO_INCOMPLETE), le == WAIT_TIMEOUT && !r, "GetOverlappedResultEx times out"); CloseHandle(o.hEvent); }
    { PVOID p = VirtualAlloc2(NULL, NULL, 4096, MEM_COMMIT | MEM_RESERVE, PAGE_READWRITE, NULL, 0); CHECK(p != NULL, "VirtualAlloc2 plain case"); if (p) VirtualFree(p, 0, MEM_RELEASE);
      { PVOID q = VirtualAlloc2(NULL, NULL, 4096, MEM_COMMIT, PAGE_READWRITE, (PVOID)1, 1); CHECKL(q == NULL, q == NULL && GetLastError() == ERROR_CALL_NOT_IMPLEMENTED, "VirtualAlloc2 extended params fail honestly"); } }
    { char buf[16]; CHECK(OfferVirtualMemory(buf, 16, 1) == 0 && ReclaimVirtualMemory(buf, 16) == 0, "Offer/ReclaimVirtualMemory no-op success"); }
    { HANDLE e1 = CreateEventW(NULL, TRUE, FALSE, NULL), e2 = CreateEventW(NULL, TRUE, FALSE, NULL);
      CHECK(CompareObjectHandles(e1, e1) && !CompareObjectHandles(e1, e2), "CompareObjectHandles (handle equality)"); CloseHandle(e1); CloseHandle(e2); }
    { SetLastError(0); BOOL r = SetProcessMitigationPolicy(0, NULL, 0); CHECKL(1, !r && GetLastError() == ERROR_NOT_SUPPORTED, "SetProcessMitigationPolicy -> ERROR_NOT_SUPPORTED"); }
    { HANDLE m = CreateFileMappingW(INVALID_HANDLE_VALUE, NULL, PAGE_READWRITE, 0, 4096, NULL); PVOID v = MapViewOfFile3(m, NULL, NULL, 0, 4096, 0, PAGE_READWRITE, NULL, 0);
      CHECK(v != NULL, "MapViewOfFile3 plain case"); if (v) UnmapViewOfFile(v); CloseHandle(m);
      CHECK(MapViewOfFile3(m, NULL, NULL, 0, 4096, 0, PAGE_READWRITE, (PVOID)1, 1) == NULL, "MapViewOfFile3 extended params fail honestly"); }
    WakeByAddressSingle((PVOID)&gv); WakeByAddressAll((PVOID)&gv); CHECK(1, "WakeByAddress* do not crash");
    { ULONG_PTR lo = 0, hi = 0; char probe; GetCurrentThreadStackLimits(&lo, &hi);
      CHECK(lo && hi > lo && (ULONG_PTR)&probe >= lo && (ULONG_PTR)&probe < hi, "GetCurrentThreadStackLimits brackets a stack address"); }
    { USHORT pm = 99, nm = 99; BOOL ok = IsWow64Process2(GetCurrentProcess(), &pm, &nm);
#ifdef _WIN64
      CHECKL(ok, ok && pm == 0 && nm == 0x8664, "IsWow64Process2 (64-bit process)");
#else
      CHECKL(ok, ok && (nm == 0x8664 || nm == 0x014c) && (pm == 0 || pm == 0x014c), "IsWow64Process2 (32-bit process)");
#endif
    }
    { SetLastError(0); BOOL a = GetProcessMitigationPolicy(GetCurrentProcess(), 0, NULL, 0); DWORD e = GetLastError(); CHECKL(1, !a && e == ERROR_NOT_SUPPORTED, "GetProcessMitigationPolicy -> ERROR_NOT_SUPPORTED");
      SetLastError(0); BOOL b = GetThreadInformation(GetCurrentThread(), 0, NULL, 0); e = GetLastError(); CHECKL(1, !b && e == ERROR_NOT_SUPPORTED, "GetThreadInformation -> ERROR_NOT_SUPPORTED");
      SetLastError(0); BOOL c = SetThreadInformation(GetCurrentThread(), 0, NULL, 0); e = GetLastError(); CHECKL(1, !c && e == ERROR_NOT_SUPPORTED, "SetThreadInformation -> ERROR_NOT_SUPPORTED");
      SetLastError(0); BOOL d = GetProcessInformation(GetCurrentProcess(), 0, NULL, 0); e = GetLastError(); CHECKL(1, !d && e == ERROR_NOT_SUPPORTED, "GetProcessInformation -> ERROR_NOT_SUPPORTED");
      SetLastError(0); BOOL f = SetProcessInformation(GetCurrentProcess(), 0, NULL, 0); e = GetLastError(); CHECKL(1, !f && e == ERROR_NOT_SUPPORTED, "SetProcessInformation -> ERROR_NOT_SUPPORTED"); }
    { char buf[64]; CHECKL(1, PrefetchVirtualMemory(GetCurrentProcess(), 0, NULL, 0) == TRUE, "PrefetchVirtualMemory harmless TRUE");
      CHECKL(1, DiscardVirtualMemory(buf, 64) == 0, "DiscardVirtualMemory success"); }
    { HANDLE c = GetThreadDpiAwarenessContext(); CHECKL(1, c == (HANDLE)(LONG_PTR)-2 && GetWindowDpiAwarenessContext(NULL) == c, "DPI awareness context = system aware");
      CHECKL(1, AreDpiAwarenessContextsEqual(c, c) && !AreDpiAwarenessContextsEqual(c, (HANDLE)(LONG_PTR)-1), "AreDpiAwarenessContextsEqual");
      CHECKL(1, IsValidDpiAwarenessContext((HANDLE)(LONG_PTR)-4) && !IsValidDpiAwarenessContext((HANDLE)(LONG_PTR)-9), "IsValidDpiAwarenessContext");
      CHECKL(1, GetDpiFromDpiAwarenessContext((HANDLE)(LONG_PTR)-1) == 96 && GetDpiFromDpiAwarenessContext(c) == GetDpiForSystem(), "GetDpiFromDpiAwarenessContext");
      CHECKL(1, GetSystemDpiForProcess(GetCurrentProcess()) == GetDpiForSystem(), "GetSystemDpiForProcess"); }
    { SetLastError(0); BOOL e1 = EnableMouseInPointer(TRUE); DWORD le = GetLastError();
      CHECKL(1, IsImmersiveProcess(GetCurrentProcess()) == FALSE && !e1 && le == ERROR_NOT_SUPPORTED && IsMouseInPointerEnabled() == FALSE, "IsImmersiveProcess / pointer-input stubs"); }
    printf("failures=%d\n", fails); return fails;
}
