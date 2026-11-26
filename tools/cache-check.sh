#!/bin/bash
# Report the size of each TuxBox prefix's caches and flag an NVIDIA driver
# cache file that has grown past the point where the driver keeps indexing it.
# Past about 5 GB, pipelines written later are never found again, so every
# launch rebuilds them. Rename a flagged file (with the title closed) and the
# next launch starts a clean cache.
# Usage: tools/cache-check.sh
for P in "${XDG_DATA_HOME:-$HOME/.local/share}"/project-tuxbox/prefixes/*/; do
  name=$(basename "$P")
  shaders="$P/drive_c/users/steamuser/AppData/Local/Temp/tuxbox_shader_cache"
  echo "== $name"
  [ -d "$shaders" ] && echo "   translated shaders: $(du -sh "$shaders" 2>/dev/null | cut -f1)"
  [ -d "$P/shadercache" ] && echo "   driver and vkd3d caches: $(du -sh "$P/shadercache" 2>/dev/null | cut -f1)"
  find "$P/shadercache" -type f -size +4G 2>/dev/null | while read -r f; do
    echo "   TOO BIG ($(du -h "$f" | cut -f1)), likely no longer indexed: $f"
    echo "   fix: mv \"$f\" \"$f.old\""
  done
done
