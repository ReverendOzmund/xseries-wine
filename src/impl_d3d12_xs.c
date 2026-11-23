// d3d12_xs.dll: the console graphics device. This is the milestone marker:
// if this line shows up in xbstub.log, the game got all the way to GPU init.

__declspec(dllexport) HRESULT D3D12XboxCreateDevice(void *adapter, const void *params,
                                                    const GUID *riid, void **device) {
    (void)adapter; (void)params;
    xb_log("*** MILESTONE: D3D12XboxCreateDevice reached (riid=%08lx-...) -> E_NOTIMPL ***",
           riid ? riid->Data1 : 0);
    if (device) *device = NULL;
    return 0x80004001;
}
