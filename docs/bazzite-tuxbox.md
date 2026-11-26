# Running Scarlett titles with TuxBox on Bazzite

xseries-wine's stub generator shows how far an executable gets before it needs
real console services. To go further than that, use
[TuxBox](https://github.com/brcly/TuxBox): it implements those services and
translates RDNA2 shaders. This page covers the parts of setting it up on Bazzite
(or any immutable Fedora) that aren't obvious, plus the debugging tools in
[`tools/`](../tools).

Tested on Bazzite with an RTX 3080 Ti and Proton Experimental.

## Build environment

Bazzite's root filesystem is read-only, so build inside a distrobox:

```sh
distrobox create -n tuxdev -i fedora:41
distrobox enter tuxdev
```

Then follow TuxBox's own build instructions inside the box. Keep the checkout
in your home folder (for example `~/Downloads/TuxBox`) so the host and the box
both see it: build inside the box, run on the host.

Things that tripped us up:

- **Vulkan headers**: if the build can't find them, clone
  `KhronosGroup/Vulkan-Headers` into `build/vulkan-headers/usr/include`.
- **No pip in the box**: use `sudo dnf install python3-<name>` (for example
  `python3-pefile`) instead of `pip install`.
- **Python virtualenvs**: a `.venv` created inside the box won't work on the
  host. Run `deactivate` on the host if it was activated.
- **`dxc` on the host**: the launcher needs it at run time, not just build
  time. Export `DXC=/path/to/dxc` and put its folder on `PATH` before running.
- **Pasting multi-line commands**: after `exit`ing the box, paste the next
  command on its own; a second line pasted together with `exit` gets swallowed.

## Running

Run titles with networking off. That way nothing in the title can phone home
(crash reporters included):

```sh
cd ~/Downloads/TuxBox
UMU_RUNTIME_UPDATE=0 unshare --user --map-current-user --net -- \
    python tuxbox.py run --log-file ~/game.log "/path/to/game folder"
```

`--log-file` must come before the game folder; anything after the folder is
passed to the title.

### Shader cache and first boots

The first boot after a TuxBox update can take 10–20 minutes while shaders are
translated and the driver builds pipelines. The title usually sits on a black
or loading screen the whole time. The progress overlay in the corner shows how
far along it is. Later boots reuse the cache.

If you want a translator update to retry shaders it refused before, move the
cache aside:

```sh
C="$HOME/.local/share/project-tuxbox/prefixes/Proton - Experimental/drive_c/users/steamuser/AppData/Local/Temp/tuxbox_shader_cache"
mv "$C" "$C.old-$(date +%H%M)"
```

## Debugging

### Black screen: is anything being drawn?

Run with `TUXBOX_TRACE_PRESENT=600` and then summarise the log:

```sh
TUXBOX_TRACE_PRESENT=600 UMU_RUNTIME_UPDATE=0 unshare --user --map-current-user --net -- \
    python tuxbox.py run --log-file ~/game.log "/path/to/game folder"
tools/run-summary.sh ~/game.log
```

Every 600 frames, TuxBox reads back the presented image and counts GPU writes to
it:

- `draws=0 ... clears=600` and `lit=0.000`: the title clears the screen and
  draws nothing on it. The problem is earlier in the game's own flow, not the
  display path.
- `draws` above 0 but `lit=0.000`: something is drawn but comes out black.
  Look at shader refusals and null pipelines.
- `lit` above 0: there's a picture.

### Stall: where is every thread stuck?

```sh
WAIT=60 tools/hang-snapshot.sh "/path/to/game folder" game_name_part
```

This starts the title offline. After `WAIT` seconds it attaches WineDbg, records
`info thread` and `bt all` to `~/hang-snapshot.txt`, then detaches. Two details
the script handles for you:

- WineDbg has to be the prefix's own `winedbg.exe`; `umu-run winedbg` can't
  find it.
- `PROTON_VERB=runinprefix` makes the debugger join the running wineserver
  instead of waiting for the game to exit.

### Reporting

Share TuxBox's log lines and summaries, never the game's files, executables or
shader caches (the cache contains game code). For bugs in TuxBox itself, open
an issue on [brcly/TuxBox](https://github.com/brcly/TuxBox).
