// Shared logging for xbstub DLLs. Appends to xbstub.log next to the game exe.
#pragma once
#include <windows.h>
#include <stdio.h>
#include <stdarg.h>

static void xb_log(const char *fmt, ...) {
    static char path[MAX_PATH];
    if (!path[0]) {
        GetModuleFileNameA(NULL, path, MAX_PATH);
        char *slash = strrchr(path, '\\');
        strcpy(slash ? slash + 1 : path, "xbstub.log");
    }
    char buf[1024];
    int n = snprintf(buf, sizeof buf, "[%6lu tid=%5lu] ", GetTickCount() % 1000000, GetCurrentThreadId());
    va_list ap; va_start(ap, fmt);
    n += vsnprintf(buf + n, sizeof buf - n - 2, fmt, ap);
    va_end(ap);
    if (n > (int)sizeof buf - 2) n = sizeof buf - 2;
    buf[n++] = '\n'; buf[n] = 0;
    OutputDebugStringA(buf);
    HANDLE h = CreateFileA(path, FILE_APPEND_DATA, FILE_SHARE_READ | FILE_SHARE_WRITE,
                           NULL, OPEN_ALWAYS, FILE_ATTRIBUTE_NORMAL, NULL);
    if (h != INVALID_HANDLE_VALUE) { DWORD w; WriteFile(h, buf, n, &w, NULL); CloseHandle(h); }
}

// Log the first 5 calls of a stub, then every 1000th, so hot functions don't flood the log.
#define XB_LOG_ONCE(name) do { static volatile LONG c_; LONG k_ = InterlockedIncrement(&c_); \
    if (k_ <= 5 || k_ % 1000 == 0) xb_log("STUB %s (call #%ld)", name, k_); } while (0)
