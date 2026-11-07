/* nx-app-installer.exe - native installer stub for NX APP TRANSLATOR packages (Windows 7 SP1+, x86 build runs on 32- and 64-bit Windows).
 * Package = this exe + payload.zip + manifest JSON + trailer: u64 manifest_len | u64 payload_len | "NXATPKG1" (see nxat/pack.py).
 * Per-user install (no admin): %LOCALAPPDATA%\Programs\<Name>, Start-menu shortcut, HKCU uninstall entry, uninstall.exe (a copy of this exe).
 * Usage:  setup.exe [--silent] [--dir PATH]      |      uninstall.exe --uninstall PATH [--silent]
 * Copyright (c) 2026 Barman. Contains miniz (MIT), see vendor/LICENSE.miniz. */
#define _WIN32_WINNT 0x0601
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <shlobj.h>
#include <shellapi.h>
#include <objbase.h>
#include <stdio.h>
#include <string.h>
#include <stdint.h>
#include <wchar.h>
#include "vendor/miniz.h"

static int g_silent = 0;
static void fail(const wchar_t *msg) {
    if (!g_silent) MessageBoxW(NULL, msg, L"NX App Installer", MB_ICONERROR);
    ExitProcess(1);
}

/* ---------- SHA-256 ---------- */
typedef struct { uint32_t h[8]; uint64_t len; uint8_t buf[64]; size_t n; } sha_t;
static const uint32_t K[64] = {
 0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,
 0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,
 0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,
 0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2};
#define ROR(x,n) (((x)>>(n))|((x)<<(32-(n))))
static void sha_block(sha_t *s, const uint8_t *p) {
    uint32_t w[64], a, b, c, d, e, f, g, h, t1, t2; int i;
    for (i = 0; i < 16; i++) w[i] = ((uint32_t)p[4*i] << 24) | ((uint32_t)p[4*i+1] << 16) | ((uint32_t)p[4*i+2] << 8) | p[4*i+3];
    for (i = 16; i < 64; i++) { uint32_t s0 = ROR(w[i-15],7) ^ ROR(w[i-15],18) ^ (w[i-15] >> 3), s1 = ROR(w[i-2],17) ^ ROR(w[i-2],19) ^ (w[i-2] >> 10); w[i] = w[i-16] + s0 + w[i-7] + s1; }
    a=s->h[0]; b=s->h[1]; c=s->h[2]; d=s->h[3]; e=s->h[4]; f=s->h[5]; g=s->h[6]; h=s->h[7];
    for (i = 0; i < 64; i++) {
        t1 = h + (ROR(e,6) ^ ROR(e,11) ^ ROR(e,25)) + ((e & f) ^ (~e & g)) + K[i] + w[i];
        t2 = (ROR(a,2) ^ ROR(a,13) ^ ROR(a,22)) + ((a & b) ^ (a & c) ^ (b & c));
        h=g; g=f; f=e; e=d+t1; d=c; c=b; b=a; a=t1+t2;
    }
    s->h[0]+=a; s->h[1]+=b; s->h[2]+=c; s->h[3]+=d; s->h[4]+=e; s->h[5]+=f; s->h[6]+=g; s->h[7]+=h;
}
static void sha_init(sha_t *s) {
    static const uint32_t i0[8] = {0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19};
    memcpy(s->h, i0, sizeof i0); s->len = 0; s->n = 0;
}
static void sha_update(sha_t *s, const uint8_t *p, size_t n) {
    s->len += n;
    while (n) { size_t k = 64 - s->n; if (k > n) k = n; memcpy(s->buf + s->n, p, k); s->n += k; p += k; n -= k; if (s->n == 64) { sha_block(s, s->buf); s->n = 0; } }
}
static void sha_final(sha_t *s, char hex[65]) {
    uint64_t bits = s->len * 8; uint8_t pad = 0x80, z = 0, l[8]; int i;
    sha_update(s, &pad, 1); while (s->n != 56) sha_update(s, &z, 1);
    for (i = 0; i < 8; i++) l[i] = (uint8_t)(bits >> (56 - 8 * i));
    sha_update(s, l, 8);
    for (i = 0; i < 8; i++) sprintf(hex + 8 * i, "%08x", s->h[i]);
}

/* ---------- helpers ---------- */
static wchar_t *widen(const char *u8) {
    int n = MultiByteToWideChar(CP_UTF8, 0, u8, -1, NULL, 0); wchar_t *w = (wchar_t *)calloc(n + 1, sizeof(wchar_t));
    MultiByteToWideChar(CP_UTF8, 0, u8, -1, w, n + 1); return w;
}
/* minimal JSON string extractor for the flat manifest written by nxat/pack.py */
static char *jget(const char *json, const char *key) {
    char pat[64]; const char *p; char *out; size_t o = 0;
    snprintf(pat, sizeof pat, "\"%s\"", key);
    p = strstr(json, pat); if (!p) return _strdup("");
    p = strchr(p + strlen(pat), ':'); if (!p) return _strdup("");
    while (*++p == ' ');
    if (*p != '"') return _strdup("");
    out = (char *)malloc(strlen(p) + 1); p++;
    while (*p && *p != '"') {
        if (*p == '\\' && p[1]) {
            p++;
            if (*p == 'u' && p[1] && p[2] && p[3] && p[4]) { unsigned v = 0; sscanf(p + 1, "%4x", &v); p += 4; if (v < 0x80) out[o++] = (char)v; else if (v < 0x800) { out[o++] = (char)(0xC0 | (v >> 6)); out[o++] = (char)(0x80 | (v & 63)); } else { out[o++] = (char)(0xE0 | (v >> 12)); out[o++] = (char)(0x80 | ((v >> 6) & 63)); out[o++] = (char)(0x80 | (v & 63)); } }
            else out[o++] = (*p == 'n') ? '\n' : *p;
            p++;
        } else out[o++] = *p++;
    }
    out[o] = 0; return out;
}
static void safe_name(wchar_t *s) { for (; *s; s++) if (wcschr(L"\\/:*?\"<>|", *s) || *s < 32) *s = L'_'; }
static void mkdirs(const wchar_t *path) {
    wchar_t buf[MAX_PATH * 4]; size_t i; wcsncpy(buf, path, MAX_PATH * 4 - 1); buf[MAX_PATH * 4 - 1] = 0;
    for (i = 3; buf[i]; i++) if (buf[i] == L'\\') { buf[i] = 0; CreateDirectoryW(buf, NULL); buf[i] = L'\\'; }
    CreateDirectoryW(buf, NULL);
}
static int rm_tree(const wchar_t *dir, const wchar_t *keep) {
    WIN32_FIND_DATAW fd; wchar_t pat[MAX_PATH * 4], p[MAX_PATH * 4]; HANDLE h; int left = 0;
    swprintf(pat, MAX_PATH * 4, L"%ls\\*", dir); h = FindFirstFileW(pat, &fd);
    if (h == INVALID_HANDLE_VALUE) return 0;
    do {
        if (!wcscmp(fd.cFileName, L".") || !wcscmp(fd.cFileName, L"..")) continue;
        swprintf(p, MAX_PATH * 4, L"%ls\\%ls", dir, fd.cFileName);
        if (keep && !_wcsicmp(p, keep)) { left++; continue; }
        if (fd.dwFileAttributes & FILE_ATTRIBUTE_REPARSE_POINT) { RemoveDirectoryW(p); DeleteFileW(p); continue; }   /* never follow links */
        if (fd.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY) { if (rm_tree(p, keep)) left++; RemoveDirectoryW(p); }
        else { SetFileAttributesW(p, FILE_ATTRIBUTE_NORMAL); if (!DeleteFileW(p)) left++; }
    } while (FindNextFileW(h, &fd));
    FindClose(h); return left;
}

/* ---------- package ---------- */
typedef struct { HANDLE f; uint64_t off; } rd_t;
static size_t zread(void *op, mz_uint64 file_ofs, void *buf, size_t n) {
    rd_t *r = (rd_t *)op; LARGE_INTEGER li; DWORD got = 0; li.QuadPart = (LONGLONG)(r->off + file_ofs);
    if (!SetFilePointerEx(r->f, li, NULL, FILE_BEGIN) || !ReadFile(r->f, buf, (DWORD)n, &got, NULL)) return 0;
    return got;
}
static size_t zwrite(void *op, mz_uint64 ofs, const void *buf, size_t n) {
    DWORD w = 0; (void)ofs; if (!WriteFile((HANDLE)op, buf, (DWORD)n, &w, NULL)) return 0; return w;
}
static int path_ok(const char *n) {                       /* zip-slip guard */
    if (!n[0] || n[0] == '/' || n[0] == '\\' || (n[1] == ':')) return 0;
    for (const char *p = n; *p; p++) if ((p == n || p[-1] == '/' || p[-1] == '\\') && p[0] == '.' && p[1] == '.' && (p[2] == 0 || p[2] == '/' || p[2] == '\\')) return 0;
    return 1;
}

static void shortcut(const wchar_t *lnk, const wchar_t *target, const wchar_t *dir) {
    IShellLinkW *sl; IPersistFile *pf;
    if (FAILED(CoCreateInstance(&CLSID_ShellLink, NULL, CLSCTX_INPROC_SERVER, &IID_IShellLinkW, (void **)&sl))) return;
    sl->lpVtbl->SetPath(sl, target); sl->lpVtbl->SetWorkingDirectory(sl, dir);
    if (SUCCEEDED(sl->lpVtbl->QueryInterface(sl, &IID_IPersistFile, (void **)&pf))) { pf->lpVtbl->Save(pf, lnk, TRUE); pf->lpVtbl->Release(pf); }
    sl->lpVtbl->Release(sl);
}
static void regset(HKEY k, const wchar_t *n, const wchar_t *v) { RegSetValueExW(k, n, 0, REG_SZ, (const BYTE *)v, (DWORD)((wcslen(v) + 1) * sizeof(wchar_t))); }

static int do_uninstall(const wchar_t *dir, int silent) {
    wchar_t name[MAX_PATH], key[MAX_PATH * 2], lnk[MAX_PATH * 2], sm[MAX_PATH], self[MAX_PATH * 2], cmd[MAX_PATH * 6];
    const wchar_t *b = wcsrchr(dir, L'\\'); b = b ? b + 1 : dir;
    wcsncpy(name, b, MAX_PATH - 1); name[MAX_PATH - 1] = 0;
    { wchar_t mk[MAX_PATH * 4]; HANDLE h; char nb[600]; DWORD got = 0;           /* real name was recorded at install time (custom --dir) */
      swprintf(mk, MAX_PATH * 4, L"%ls\\.nxat-name", dir);
      h = CreateFileW(mk, GENERIC_READ, FILE_SHARE_READ, NULL, OPEN_EXISTING, 0, NULL);
      if (h != INVALID_HANDLE_VALUE) { if (ReadFile(h, nb, sizeof nb - 1, &got, NULL) && got) { wchar_t *w; nb[got] = 0; w = widen(nb); wcsncpy(name, w, MAX_PATH - 1); free(w); } CloseHandle(h); } }
    swprintf(key, MAX_PATH * 2, L"Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\NXAT_%ls", name);
    RegDeleteKeyW(HKEY_CURRENT_USER, key);
    if (SUCCEEDED(SHGetFolderPathW(NULL, CSIDL_PROGRAMS, NULL, 0, sm))) { swprintf(lnk, MAX_PATH * 2, L"%ls\\%ls.lnk", sm, name); DeleteFileW(lnk); }
    GetModuleFileNameW(NULL, self, MAX_PATH * 2);
    if (rm_tree(dir, self)) {                         /* only this running exe is left: let cmd remove it after we exit */
        swprintf(cmd, MAX_PATH * 6, L"cmd.exe /c ping -n 3 127.0.0.1 >nul & rmdir /s /q \"%ls\"", dir);
        STARTUPINFOW si = { sizeof si }; PROCESS_INFORMATION pi; si.dwFlags = STARTF_USESHOWWINDOW; si.wShowWindow = SW_HIDE;
        if (CreateProcessW(NULL, cmd, NULL, NULL, FALSE, CREATE_NO_WINDOW | DETACHED_PROCESS, NULL, NULL, &si, &pi)) { CloseHandle(pi.hThread); CloseHandle(pi.hProcess); }
    } else RemoveDirectoryW(dir);
    if (!silent) MessageBoxW(NULL, L"Removed.", L"NX App Installer", MB_ICONINFORMATION);
    return 0;
}

int wmain(int argc, wchar_t **argv) {
    wchar_t self[MAX_PATH * 2], target[MAX_PATH * 4] = L"", *uninst = NULL; int i;
    HANDLE f; LARGE_INTEGER sz; uint8_t tr[24]; DWORD got; uint64_t mlen, plen, poff; char *man; sha_t sh; char hex[65], *want;
    char *name_u, *entry_u, *ver_u, *pub_u, *name_u_safe; wchar_t *name, *entry, *ver, *pub;
    for (i = 1; i < argc; i++) {
        if (!wcscmp(argv[i], L"--silent")) g_silent = 1;
        else if (!wcscmp(argv[i], L"--dir") && i + 1 < argc) wcsncpy(target, argv[++i], MAX_PATH * 4 - 1);
        else if (!wcscmp(argv[i], L"--uninstall") && i + 1 < argc) uninst = argv[++i];
    }
    CoInitialize(NULL);
    if (uninst) return do_uninstall(uninst, g_silent);
    GetModuleFileNameW(NULL, self, MAX_PATH * 2);
    f = CreateFileW(self, GENERIC_READ, FILE_SHARE_READ | FILE_SHARE_DELETE, NULL, OPEN_EXISTING, 0, NULL);
    if (f == INVALID_HANDLE_VALUE || !GetFileSizeEx(f, &sz) || sz.QuadPart < 24) fail(L"Cannot open the installer file.");
    { LARGE_INTEGER p; p.QuadPart = sz.QuadPart - 24; SetFilePointerEx(f, p, NULL, FILE_BEGIN); }
    if (!ReadFile(f, tr, 24, &got, NULL) || got != 24 || memcmp(tr + 16, "NXATPKG1", 8)) fail(L"This file contains no NX package.");
    memcpy(&mlen, tr, 8); memcpy(&plen, tr + 8, 8);
    if (mlen > (1u << 20) || mlen + plen + 24 > (uint64_t)sz.QuadPart) fail(L"The package is damaged.");
    poff = (uint64_t)sz.QuadPart - 24 - mlen - plen;
    man = (char *)calloc((size_t)mlen + 1, 1);
    { LARGE_INTEGER p; p.QuadPart = (LONGLONG)(poff + plen); SetFilePointerEx(f, p, NULL, FILE_BEGIN); }
    if (!ReadFile(f, man, (DWORD)mlen, &got, NULL) || got != mlen) fail(L"The package is damaged.");
    name_u = jget(man, "name"); entry_u = jget(man, "entry"); ver_u = jget(man, "version"); pub_u = jget(man, "publisher"); want = jget(man, "payload_sha256");
    if (!path_ok(entry_u) || !name_u[0]) fail(L"The package manifest is invalid.");
    /* integrity: SHA-256 of the payload */
    { LARGE_INTEGER p; uint8_t *buf = (uint8_t *)malloc(1 << 20); uint64_t left = plen; p.QuadPart = (LONGLONG)poff; SetFilePointerEx(f, p, NULL, FILE_BEGIN); sha_init(&sh);
      while (left) { DWORD n = left > (1 << 20) ? (1 << 20) : (DWORD)left; if (!ReadFile(f, buf, n, &got, NULL) || got != n) fail(L"Read error."); sha_update(&sh, buf, n); left -= n; }
      free(buf); sha_final(&sh, hex); }
    if (strcmp(hex, want)) fail(L"The installer is corrupt (checksum mismatch). Download it again.");
    name = widen(name_u); entry = widen(entry_u); ver = widen(ver_u); pub = widen(pub_u); safe_name(name);
    { int n8 = WideCharToMultiByte(CP_UTF8, 0, name, -1, NULL, 0, NULL, NULL); name_u_safe = (char *)calloc(n8 + 1, 1); WideCharToMultiByte(CP_UTF8, 0, name, -1, name_u_safe, n8, NULL, NULL); }
    if (!target[0]) { wchar_t la[MAX_PATH]; if (FAILED(SHGetFolderPathW(NULL, CSIDL_LOCAL_APPDATA, NULL, 0, la))) fail(L"No user profile folder."); swprintf(target, MAX_PATH * 4, L"%ls\\Programs\\%ls", la, name); }
    mkdirs(target);
    /* extract */
    { mz_zip_archive z; rd_t r; mz_uint n, k; memset(&z, 0, sizeof z); r.f = f; r.off = poff;
      z.m_pRead = zread; z.m_pIO_opaque = &r; z.m_archive_size = plen;
      if (!mz_zip_reader_init(&z, plen, 0)) fail(L"The payload is not a valid archive.");
      n = mz_zip_reader_get_num_files(&z);
      for (k = 0; k < n; k++) {
          mz_zip_archive_file_stat st; wchar_t *rel, dest[MAX_PATH * 4], *s;
          if (!mz_zip_reader_file_stat(&z, k, &st)) fail(L"Archive read error.");
          if (!path_ok(st.m_filename)) fail(L"Unsafe path inside the package; aborting.");
          rel = widen(st.m_filename); for (s = rel; *s; s++) if (*s == L'/') *s = L'\\';
          swprintf(dest, MAX_PATH * 4, L"%ls\\%ls", target, rel); free(rel);
          if (mz_zip_reader_is_file_a_directory(&z, k)) { mkdirs(dest); continue; }
          { wchar_t *sl = wcsrchr(dest, L'\\'); if (sl) { *sl = 0; mkdirs(dest); *sl = L'\\'; } }
          { HANDLE o = CreateFileW(dest, GENERIC_WRITE, 0, NULL, CREATE_ALWAYS, FILE_ATTRIBUTE_NORMAL, NULL);
            if (o == INVALID_HANDLE_VALUE) fail(L"Cannot write a file (is the program running?).");
            if (!mz_zip_reader_extract_to_callback(&z, k, zwrite, o, 0)) { CloseHandle(o); fail(L"Extraction failed (corrupt archive or disk full)."); }
            CloseHandle(o); }
      }
      mz_zip_reader_end(&z); }
    CloseHandle(f);
    /* uninstaller, shortcut, registry */
    { wchar_t un[MAX_PATH * 4], exe[MAX_PATH * 4], sm[MAX_PATH], lnk[MAX_PATH * 4], key[MAX_PATH * 2], us[MAX_PATH * 6]; HKEY k; wchar_t *e;
      swprintf(un, MAX_PATH * 4, L"%ls\\uninstall.exe", target); CopyFileW(self, un, FALSE);
      { wchar_t mk[MAX_PATH * 4]; HANDLE h; DWORD w; swprintf(mk, MAX_PATH * 4, L"%ls\\.nxat-name", target);
        h = CreateFileW(mk, GENERIC_WRITE, 0, NULL, CREATE_ALWAYS, FILE_ATTRIBUTE_HIDDEN, NULL);
        if (h != INVALID_HANDLE_VALUE) { WriteFile(h, name_u_safe, (DWORD)strlen(name_u_safe), &w, NULL); CloseHandle(h); } }
      swprintf(exe, MAX_PATH * 4, L"%ls\\%ls", target, entry); for (e = exe; *e; e++) if (*e == L'/') *e = L'\\';
      if (SUCCEEDED(SHGetFolderPathW(NULL, CSIDL_PROGRAMS, NULL, 0, sm))) { swprintf(lnk, MAX_PATH * 4, L"%ls\\%ls.lnk", sm, name); shortcut(lnk, exe, target); }
      swprintf(key, MAX_PATH * 2, L"Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\NXAT_%ls", name);
      if (RegCreateKeyExW(HKEY_CURRENT_USER, key, 0, NULL, 0, KEY_WRITE, NULL, &k, NULL) == ERROR_SUCCESS) {
          wchar_t dn[MAX_PATH * 2]; swprintf(dn, MAX_PATH * 2, L"%ls (NX Win7)", name); swprintf(us, MAX_PATH * 6, L"\"%ls\" --uninstall \"%ls\"", un, target);
          regset(k, L"DisplayName", dn); regset(k, L"InstallLocation", target); regset(k, L"Publisher", pub); regset(k, L"DisplayVersion", ver); regset(k, L"UninstallString", us);
          RegCloseKey(k); } }
    if (!g_silent) MessageBoxW(NULL, L"Installation finished.", L"NX App Installer", MB_ICONINFORMATION);
    return 0;
}
