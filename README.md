# scarlett-shim

An experimental boot harness for **Xbox Series X|S (Scarlett) GDK executables** on PC and Linux (Wine/Proton).

Xbox Series games are x86-64 PE files, but they import console-only DLLs (`d3d12_xs.dll`,
`xmem.dll`, `xapu.dll`, ...) and the GDK runtime (`xgameruntime.dll`). This project reads a
game's import table, generates stand-in DLLs for every console-only import, and logs each
call. That shows how far a title boots and which console services it needs.

**Status: research harness, not a playable layer.** Nothing renders yet. The main blocker is
`D3D12XboxCreateDevice`: Scarlett titles ship native RDNA2 shader binaries and use console
D3D12 extensions, which would need a shader recompiler and a GPU command translator to run.

## What it does

| DLL | Behaviour |
|---|---|
| `xmem.dll` | Working: XMem allocations mapped onto `VirtualAlloc` |
| `xgameruntime.dll` | Accepts init, logs every `QueryApiImpl` GUID, returns `E_NOINTERFACE` |
| `d3d12_xs.dll` | Logs a milestone and returns `E_NOTIMPL` |
| everything else | Auto-generated stubs: log the first 5 calls, return `E_NOTIMPL` (Bink returns NULL) |

All calls are logged to `xbstub.log` next to the game exe.

## Legal

- This repo contains **no game code, assets, keys, or Microsoft GDK binaries**, and it never will.
- You must supply your own legally obtained executable and data. Do not open issues or PRs
  containing game files, download links, or decryption material; they will be deleted.
- This project does not bypass licensing or DRM, and PRs that do will not be accepted.

## Build

Needs Python 3 and a MinGW-w64 cross-compiler.

```sh
pip install pefile
python3 gen.py /path/to/game.exe gen
./gen/build.sh            # DLLs land in gen/dll/
```

On Bazzite or other immutable distros, use a distrobox:

```sh
distrobox create -n xbdev -i fedora:41 && distrobox enter xbdev
sudo dnf install -y mingw64-gcc python3-pip && pip install --user pefile
```

## Run (Steam + Proton)

1. Copy `gen/dll/*.dll` next to the game exe.
2. In Steam, go to Add a Non-Steam Game → pick the exe → Properties → Compatibility → force Proton Experimental.
3. Set Launch Options to: `PROTON_LOG=1 WINEDEBUG=+loaddll,+seh,err+module %command%`
4. Launch it, then read `xbstub.log` (game folder) and `~/steam-<appid>.log`.

The goal for each title is the line `*** MILESTONE: D3D12XboxCreateDevice reached ***`.

## Roadmap

- [ ] Real `xgameruntime` interfaces (XSystem, XPackage, XUser offline, XGameSave)
- [ ] GameInput → SDL/evdev controller backend
- [ ] DirectStorage (`XCRDAPI`) → plain file I/O
- [ ] Audio: XApu/ACP/XDsp → XAudio2/FAudio
- [ ] Graphics: D3D12.X → vkd3d-proton (the hard part: RDNA2 ISA → SPIR-V)

## Related projects

- WinDurango: open-source Xbox One translation layer
- [shadPS4](https://github.com/shadps4-emu/shadPS4): GCN shader recompilation reference

## License

MIT
