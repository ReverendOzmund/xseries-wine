// xmem.dll: console memory allocator mapped onto plain VirtualAlloc.
// Xbox attribute/protection flags carry GPU bits we can't honour; strip them.

__declspec(dllexport) void *XMemAlloc(SIZE_T size, ULONGLONG attrs) {
    void *p = VirtualAlloc(NULL, size ? size : 1, MEM_COMMIT | MEM_RESERVE, PAGE_READWRITE);
    static volatile LONG c; if (InterlockedIncrement(&c) <= 5)
        xb_log("XMemAlloc(%zu, attrs=%llx) -> %p", size, attrs, p);
    return p;
}
__declspec(dllexport) void XMemFree(void *p, ULONGLONG attrs) {
    (void)attrs; if (p) VirtualFree(p, 0, MEM_RELEASE);
}
__declspec(dllexport) void *XMemAllocDefault(SIZE_T size, ULONGLONG attrs) { return XMemAlloc(size, attrs); }
__declspec(dllexport) void XMemFreeDefault(void *p, ULONGLONG attrs) { XMemFree(p, attrs); }

__declspec(dllexport) void *XMemVirtualAlloc(void *addr, SIZE_T size, DWORD type, ULONGLONG a4, DWORD a5) {
    DWORD t = type & (MEM_COMMIT | MEM_RESERVE | MEM_TOP_DOWN);
    if (!t) t = MEM_COMMIT | MEM_RESERVE;
    DWORD prot = (DWORD)(a4 & 0xFF);
    if (!prot) prot = a5 & 0xFF;
    if (!prot) prot = PAGE_READWRITE;
    void *p = VirtualAlloc(addr, size, t, prot);
    if (!p) p = VirtualAlloc(NULL, size, MEM_COMMIT | MEM_RESERVE, PAGE_READWRITE);
    xb_log("XMemVirtualAlloc(%p, %zu, type=%lx, %llx, %lx) -> %p", addr, size, type, a4, a5, p);
    return p;
}
