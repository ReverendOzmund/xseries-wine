#!/bin/bash
# Launch a Scarlett title through TuxBox with no network, wait, then snapshot
# every thread with WineDbg (attach, info thread, bt all, detach). Read-only:
# the debugger detaches and the game keeps running.
#
# Usage:
#   tools/hang-snapshot.sh "/path/to/game folder" [exe-name-substring]
# Environment:
#   WAIT=55          seconds to wait before sampling
#   TUXBOX=~/Downloads/TuxBox   TuxBox checkout
#   APP_ID=...       --app-id passed to tuxbox.py, if the title needs one
#   OUT=~/hang-snapshot.txt     snapshot output
#   LOG=~/hang-run.log          game log
set -u
GAME_DIR="${1:?usage: hang-snapshot.sh \"/path/to/game folder\" [exe-name-substring]}"
EXE_MATCH="${2:-.exe}"

if [ -z "${HANG_SNAPSHOT_INNER:-}" ]; then
    # Run inside a network-less user namespace so nothing in the title can
    # phone home, and so the debugger shares the game's namespace.
    export HANG_SNAPSHOT_INNER=1
    exec unshare --user --map-current-user --net -- bash "$0" "$@"
fi

TUXBOX="${TUXBOX:-$HOME/Downloads/TuxBox}"
PREFIX="${PREFIX:-$HOME/.local/share/project-tuxbox/prefixes/Proton - Experimental}"
PROTON="${PROTON:-$HOME/.steam/steam/steamapps/common/Proton - Experimental}"
OUT="${OUT:-$HOME/hang-snapshot.txt}"
LOG="${LOG:-$HOME/hang-run.log}"
WINEDBG="$PREFIX/drive_c/windows/system32/winedbg.exe"
export UMU_RUNTIME_UPDATE=0

[ -f "$WINEDBG" ] || { echo "winedbg.exe not found at $WINEDBG (run the game once first)"; exit 1; }
cd "$TUXBOX" || exit 1
: > "$OUT"
echo "== starting, sampling in ${WAIT:-55}s" | tee -a "$OUT"

wdbg() {  # runinprefix joins the running wineserver instead of waiting for it
    PROTON_VERB=runinprefix WINEPREFIX="$PREFIX" PROTONPATH="$PROTON" \
        GAMEID=umu-default umu-run "$WINEDBG" "$@" 2>&1
}

snapshot() {
    sleep "${WAIT:-55}"
    echo "== process list" >> "$OUT"
    wdbg --command "info process" >> "$OUT"
    PID=$(grep -ai -- "$EXE_MATCH" "$OUT" | grep -aoE "^[[:space:]>]*[0-9a-fA-F]{8}" | tr -d ' >' | head -1)
    if [ -z "$PID" ]; then
        echo "!! no process matching '$EXE_MATCH'; is it still running?" >> "$OUT"
    else
        echo "== attaching to 0x$PID" >> "$OUT"
        CMDS="$HOME/.hang-snapshot-cmds.txt"
        printf 'attach 0x%s\ninfo thread\nbt all\ndetach\nquit\n' "$PID" > "$CMDS"
        wdbg --file "Z:$(realpath "$CMDS" | tr / '\\')" >> "$OUT"
    fi
    echo "== SNAPSHOT DONE: you can close the game now" | tee -a "$OUT"
}

snapshot < /dev/null &
python tuxbox.py run --log-file "$LOG" ${APP_ID:+--app-id "$APP_ID"} "$GAME_DIR"
wait
