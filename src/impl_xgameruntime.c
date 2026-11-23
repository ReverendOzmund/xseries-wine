// xgameruntime.dll: the GDK static lib LoadLibrary()s this, calls InitializeApiImpl,
// then asks QueryApiImpl for one COM-style interface per API family (XUser, XStore,
// XPackage, XSystem...). We accept init and refuse every interface, logging the
// GUIDs so we can see exactly which runtime services the game needs and in what order.
#include "common.h"

static void guid_str(const GUID *g, char *o) {
    if (!g) { strcpy(o, "(null)"); return; }
    sprintf(o, "%08lx-%04x-%04x-%02x%02x-%02x%02x%02x%02x%02x%02x", g->Data1, g->Data2, g->Data3,
            g->Data4[0], g->Data4[1], g->Data4[2], g->Data4[3], g->Data4[4], g->Data4[5], g->Data4[6], g->Data4[7]);
}

__declspec(dllexport) HRESULT InitializeApiImpl(ULONGLONG gdk, ULONGLONG gs) {
    xb_log("xgameruntime!InitializeApiImpl(gdk=%llx, gs=%llx) -> S_OK", gdk, gs); return S_OK;
}
__declspec(dllexport) HRESULT InitializeApiImplEx(ULONGLONG gdk, ULONGLONG gs, void *opts) {
    xb_log("xgameruntime!InitializeApiImplEx(gdk=%llx, gs=%llx, %p) -> S_OK", gdk, gs, opts); return S_OK;
}
__declspec(dllexport) HRESULT InitializeApiImplEx2(ULONGLONG gdk, ULONGLONG gs, void *a, void *b) {
    xb_log("xgameruntime!InitializeApiImplEx2(gdk=%llx, gs=%llx, %p, %p) -> S_OK", gdk, gs, a, b); return S_OK;
}
__declspec(dllexport) HRESULT QueryApiImpl(const GUID *provider, const GUID *iid, void **out) {
    char a[64], b[64]; guid_str(provider, a); guid_str(iid, b);
    xb_log("xgameruntime!QueryApiImpl(provider=%s, iid=%s) -> E_NOINTERFACE", a, b);
    if (out) *out = NULL;
    return 0x80004002;
}
__declspec(dllexport) void UninitializeApiImpl(void) { xb_log("xgameruntime!UninitializeApiImpl"); }

BOOL WINAPI DllMain(HINSTANCE h, DWORD r, void *x) {
    (void)h; (void)x;
    if (r == DLL_PROCESS_ATTACH) xb_log("xgameruntime.dll (xbstub) loaded");
    return TRUE;
}
