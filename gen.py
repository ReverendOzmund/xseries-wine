#!/usr/bin/env python3
"""xseries-wine generator: reads an Xbox Series (Scarlett) GDK exe's import table
and generates logging stub DLLs for every console-only DLL it needs.

usage: python3 gen.py <game.exe> gen      (outdir must sit inside the repo root)
"""
import os, sys, pefile

KNOWN_CONSOLE = {
    'xmem.dll', 'd3d12_xs.dll', 'xg_xs.dll', 'xboxbvhbuilder.dll', 'xcrdapi.dll',
    'xapu.dll', 'acphal.dll', 'chad.dll', 'gameinput.dll', 'libhttpclient.gdk.dll',
}

def is_console_dll(name):
    n = name.lower()
    return (n in KNOWN_CONSOLE or n.endswith(('_xs.dll', '_x.dll'))
            or 'xbox' in n or 'scarlett' in n)

# Exports with hand-written implementations in impl_<dll>.c (no generic stub).
HANDWRITTEN = {
    'xmem.dll': {'XMemAlloc', 'XMemAllocDefault', 'XMemFree', 'XMemFreeDefault',
                 'XMemVirtualAlloc'},
    'd3d12_xs.dll': {'D3D12XboxCreateDevice'},
}

# Generic stub return value. Pointer-returning APIs must get NULL, not an HRESULT.
def ret_for(dll, name):
    if dll.lower().startswith('bink'):
        return '0'
    if name.startswith('??1'):          # C++ destructor
        return '0'
    return '0x80004001'                 # E_NOTIMPL

def main():
    exe, out = sys.argv[1], sys.argv[2]
    os.makedirs(out, exist_ok=True)
    pe = pefile.PE(exe, fast_load=True)
    pe.parse_data_directories(directories=[
        pefile.DIRECTORY_ENTRY['IMAGE_DIRECTORY_ENTRY_IMPORT']])
    found = {}
    for e in pe.DIRECTORY_ENTRY_IMPORT:
        d = e.dll.decode()
        if is_console_dll(d):
            found[d] = [(i.name.decode() if i.name else None, i.ordinal) for i in e.imports]

    makefile_targets = []
    for dll, imports in found.items():
        base = dll[:-4]
        safe = base.replace('.', '_')
        c, deff = [], [f'LIBRARY "{dll}"', 'EXPORTS']
        c.append('#include "../src/common.h"')
        if os.path.exists(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src', f'impl_{safe}.c')):
            c.append(f'#include "../src/impl_{safe}.c"')
        hw = HANDWRITTEN.get(dll, set())
        for n, (name, ordinal) in enumerate(imports):
            label = name or f'{base}#{ordinal}'
            if name in hw:
                deff.append(f'    {name}')
                continue
            fn = f'stub_{n}'
            if name and name.startswith('??0'):
                # C++ constructor: must return `this` (rcx)
                c.append(f'void* {fn}(void* self) {{ XB_LOG_ONCE("{label}"); return self; }}')
            else:
                c.append(f'unsigned long long {fn}(void) {{ XB_LOG_ONCE("{label}"); '
                         f'return {ret_for(dll, name or "")}; }}')
            if name:
                deff.append(f'    {name}={fn}' if name.isidentifier() else f'    "{name}"={fn}')
            else:
                deff.append(f'    {fn} @{ordinal} NONAME')
        open(f'{out}/{safe}.c', 'w').write('\n'.join(c) + '\n')
        open(f'{out}/{safe}.def', 'w').write('\n'.join(deff) + '\n')
        makefile_targets.append((dll, safe))

    # xgameruntime.dll is loaded dynamically, not imported: always build it.
    makefile_targets.append(('xgameruntime.dll', 'xgameruntime'))
    with open(f'{out}/build.sh', 'w') as f:
        f.write('#!/bin/sh\nset -e\ncd "$(dirname "$0")"\nmkdir -p dll\n')
        for dll, safe in makefile_targets:
            src = f'../src/impl_xgameruntime.c' if safe == 'xgameruntime' else f'{safe}.c'
            dfile = f'../src/xgameruntime.def' if safe == 'xgameruntime' else f'{safe}.def'
            f.write(f'x86_64-w64-mingw32-gcc -O1 -shared -o "dll/{dll}" {src} {dfile} '
                    f'-Wl,--enable-stdcall-fixup -static-libgcc\n')
        f.write('echo built: && ls dll\n')
    os.chmod(f'{out}/build.sh', 0o755)
    for dll, imps in found.items():
        print(f'{dll}: {len(imps)} exports')

if __name__ == '__main__':
    main()
