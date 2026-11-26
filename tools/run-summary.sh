#!/bin/bash
# Boil a TuxBox game log down to what matters: how the run ended, whether
# anything was drawn, what the shader translator and the driver refused, and
# where work was dropped. Reads only TuxBox's and Wine's own messages: no game
# data. See docs/reading-tuxbox-logs.md for what each line means.
# Usage: tools/run-summary.sh ~/game.log   (best with TUXBOX_TRACE_PRESENT=600)
L="${1:?usage: run-summary.sh <tuxbox log>}"
count() { grep -ac "$1" "$L"; }
{
echo "== how it ended"
grep -aoE "\[TuxBox [^]]+\] (Game exited[^\"]*|Launch interrupted)" "$L" | tail -2
if grep -aq "exit code 3 after" "$L"; then
  echo "   exit code 3 is abort(): look at the last lines before the exit, below"
fi
grep -a "err:vulkan\|libnvidia-glcore\|DEVICE_LOST\|DEVICE_REMOVED" "$L" | tail -3

echo "== display (draws= is what reached the screen image)"
grep -ao "display writes recorded[^\"]*" "$L" | tail -2
grep -ao "present sample[^\"]*" "$L" | tail -2 | cut -c1-120

echo "== shader translation"
echo "translated $(count 'Compiled Xbox shader')  refused $(count 'xshader failed')"
grep -aoE "xshader failed \([0-9]+\): [^\"]{0,90}" "$L" | sed -E 's/0x[0-9a-f]+/ADDR/g' \
  | sort | uniq -c | sort -rn | head -8

echo "== driver pipelines"
echo "created up to: $(grep -aoE 'CreatePipelineState #[0-9]+' "$L" | tail -1)"
echo "over 100 s: $(grep -aoE '(CS|PS) [0-9a-f]{8}[^"]* finished in [0-9]+s' "$L" | awk '{if ($NF+0>100) n++} END {print n+0}')"
echo "deferred (stand-in while compiling): $(count 'deferred after')"
grep -aoE "(CS|PS) [0-9a-f]{8}[^\"]* finished in [0-9]+s" "$L" | sort -t' ' -k2 | awk '{print $NF, $0}' \
  | sort -rn | head -3 | cut -d' ' -f2-
echo "creation failures by code:"
grep -aoE "pipeline creation failed \(0x[0-9a-f]+" "$L" | sort | uniq -c | sort -rn
echo "vkd3d conversion failures (result -3): $(count 'vkd3d result -3')"
echo "wave64 programs on a wave32 host: $(count 'Required WaveSize range')"

echo "== work dropped"
echo "command lists rejected:"
grep -aoE "command list failed 0x[0-9a-f]+[^\"]*" "$L" | sed -E 's/guest caller 0x[0-9a-f]+/caller/' \
  | sort | uniq -c | sort -rn | head -4
grep -aoE "command list cannot record[^\"]{0,120}" "$L" | sort | uniq -c | sort -rn | head -3
echo "skipped draws/dispatches:"
grep -aoE "skipped [^(\"]*" "$L" | sort | uniq -c | sort -rn | head -6

echo "== GPU waits and title checks"
echo "memory waits released after the timeout: $(count 'GPU memory wait released')"
echo "signaller timeouts: $(count 'signaller_worker wait timed out')"
grep -aoE "(continued past|returned early from) [a-z ]*title assert RVA 0x[0-9a-f]+" "$L" \
  | sort | uniq -c | sort -rn | head -4

echo "== runtime services refused"
grep -ao "unsupported API class[^\"]*" "$L" | sort | uniq -c | head -5
grep -ao "unsupported D3D12.x vtable slot[^\"]*" "$L" | sort | uniq -c | head -5

echo "== last lines (frame and cache noise removed)"
grep -avE "present sample|display writes|null usage|presented [0-9]+ frames|Flushing disk cache|cache marked dirty|still running|finished in|Compiled Xbox shader|EXCEPTION_BREAKPOINT|Exception 0x80000003" "$L" \
  | tail -8
} | sed -E 's/\\n"?$//' | cut -c1-220
