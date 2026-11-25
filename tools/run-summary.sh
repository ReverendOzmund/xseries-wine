#!/bin/bash
# Boil a TuxBox game log down to what matters when a title shows a black
# screen or stalls. Contains only TuxBox's own messages: no game data.
# Usage: tools/run-summary.sh ~/game.log   (best with TUXBOX_TRACE_PRESENT=600)
L="${1:?usage: run-summary.sh <tuxbox log>}"
{
echo "== display (draws= is what reached the screen image)"
grep -ao "display writes recorded[^\"]*" "$L" | tail -4
grep -ao "present sample[^\"]*" "$L" | tail -2
echo "== shaders"
echo "compiled $(grep -ac 'Compiled Xbox shader' "$L")  refused $(grep -ac 'xshader failed' "$L")"
grep -aoE "xshader failed \([0-9]+\): [^0-9]{0,70}" "$L" | sort | uniq -c | sort -rn | head -8
echo "== runtime services refused"
grep -ao "unsupported API class[^\"]*" "$L" | sort | uniq -c
grep -ao "unsupported D3D12.x vtable slot[^\"]*" "$L" | sort | uniq -c
echo "== GPU timeouts: $(grep -ac 'signaller_worker wait timed out' "$L")"
echo "== end"
grep -a -E "Project TuxBox|err:seh|exited|Launch interrupted" "$L" | grep -v fencetrace | tail -6
} | cut -c1-220
