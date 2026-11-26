# Running Scarlett titles with TuxBox on Bazzite

xseries-wine's stub generator shows how far an executable gets before it needs
real console services. To go further than that, use
[TuxBox](https://github.com/brcly/TuxBox): it implements those services and
translates RDNA2 shaders. This page covers the parts of setting it up on Bazzite
(or any immutable Fedora) that aren't obvious, plus the debugging tools in
[`tools/`](../tools).

Tested on Bazzite with an RTX 3080 Ti, a Ryzen 5 7600X and GE-Proton11-14.

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

## Proton

TuxBox pins a GE-Proton release (GE-Proton11-14 at the time of writing), because
its shader converter handles large translated shaders far faster than older
releases. If the launcher says to install it, note that the release file names
carry the architecture:

```sh
cd /tmp
V=GE-Proton11-14
curl -LO https://github.com/GloriousEggroll/proton-ge-custom/releases/download/$V/$V-x86_64.tar.gz
curl -LO https://github.com/GloriousEggroll/proton-ge-custom/releases/download/$V/$V-x86_64.sha512sum
sha512sum -c $V-x86_64.sha512sum && tar -xf $V-x86_64.tar.gz -C ~/.steam/root/compatibilitytools.d
```

Each Proton gets its own prefix under `~/.local/share/project-tuxbox/prefixes/`.
A new default prefix copies the translated-shader cache from the prefix you used
last, so switching Proton doesn't start translation from zero. On Btrfs, which
Bazzite uses, the copy shares disk blocks and is instant.

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

The first boot after a TuxBox update can take a long time: every shader the
translator now handles differently is translated again, and the NVIDIA driver
then builds each pipeline. On a 6-core CPU, a large title can sit on a black or
loading screen for hours. The progress overlay in the corner shows how far along
it is. Later boots reuse the cache. What helped:

- **Translate up front.** `python tuxbox.py run --prepare-only ...` translates
  every recorded shader without starting the title, using all cores.
- **Don't oversubscribe the CPU.** `TUXBOX_LARGE_COMPILES` limits how many big
  driver compiles run at once. Setting it to your thread count made every
  compile 3–4 times slower and starved the title; about half the thread count
  worked better on a 7600X.
- **Don't pull TuxBox every day while you're testing.** Each translator change
  makes part of the cache cold again. Warm one build fully, then update.
- **Keep the NVIDIA driver cache small.** Past about 5 GB, the driver stops
  indexing its cache file, and every launch rebuilds the same pipelines.
  Current TuxBox caps the cache at 4 GiB, but a file that already grew past
  that stays broken. Check for one:

  ```sh
  find ~/.local/share/project-tuxbox/prefixes/*/shadercache -type f -size +4G -exec ls -lh {} \;
  ```

  Rename any it finds (add `.old` to the name) with the title closed. The next
  launch rebuilds a clean, indexed cache.

If you want a translator update to retry shaders it refused before, move the
translation cache aside (it lives inside the prefix):

```sh
C="$(ls -d ~/.local/share/project-tuxbox/prefixes/GE-Proton*/drive_c/users/steamuser/AppData/Local/Temp/tuxbox_shader_cache | tail -1)"
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

### Contributing from Bazzite

TuxBox asks for `python tuxbox.py check` on every pull request. On Bazzite it
stops at the build step, because `lld-link` and `clang-cl` only exist in the
distrobox. Build in the box and run the GPU suites on the host instead:

```sh
distrobox enter tuxdev -- bash -lc 'cd ~/Downloads/TuxBox && python3 build.py'
python tuxbox.py verify --prefix ~/.local/share/project-tuxbox/prefixes/verify-scratch \
    --output ~/verify.json
```

- **Use a separate prefix for `verify`.** Sharing the prefix of a running title
  made nearly every test time out.
- **Don't build or verify while a title is compiling shaders.** Running all
  three at once exhausted memory and froze the desktop until a hard reset.
- **Use a worktree per pull request** (`git worktree add ~/tuxbox-pr upstream/main`),
  so your main checkout can keep running a title while you work on a branch.

### Tools

- `tools/run-summary.sh LOG`: how a run ended, what was drawn, what the
  translator and the driver refused, and where work was dropped.
  [Reading a TuxBox log](reading-tuxbox-logs.md) explains each line.
- `tools/cache-check.sh`: cache sizes per prefix, and NVIDIA cache files too
  big to stay indexed.
- `tools/dmpinfo.py FILE.dmp`: the exception record of a minidump and the
  module it hit, without memory contents.
- `tools/dxc-bench.py LOG`: compiles the slowest compute shaders of a run with
  DXC's optimiser off and on, and prints only timings and sizes.

### Reporting

Share TuxBox's log lines and summaries, never the game's files, executables or
shader caches (the cache contains game code). For bugs in TuxBox itself, open
an issue on [brcly/TuxBox](https://github.com/brcly/TuxBox).
