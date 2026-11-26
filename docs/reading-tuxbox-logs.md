# Reading a TuxBox log

What the messages in a TuxBox game log mean, and which ones matter. Learnt the
hard way over a week of long runs on an RTX 3080 Ti. `tools/run-summary.sh`
pulls all of these out of a log for you.

Messages change as TuxBox develops. If one here no longer matches, the source
is the authority: search for the message text in the TuxBox repository.

## How the run ended

| Message | Meaning |
|---|---|
| `Game exited with exit code 0` | Closed normally, or you closed it. |
| `Game exited with exit code 3` | The title called `abort()`, usually after a failed check or a fatal error from a call it made. There is often no crash report. The lines just before the exit say why. |
| `Launch interrupted` | You pressed Ctrl+C, or the launcher was stopped. |
| `err:vulkan:vkAllocateMemory Exception 0xc0000005 in Unix call` with `libnvidia-glcore` in the backtrace | The NVIDIA driver itself crashed while allocating GPU memory. Log VRAM with `nvidia-smi --query-gpu=timestamp,memory.used --format=csv -l 30` next run, to see whether memory ran out. |
| `VK_ERROR_DEVICE_LOST`, or `Xid 13` in `journalctl -k` | The GPU faulted on a command. `VKD3D_CONFIG=breadcrumbs` makes vkd3d-proton log which command was running. |

A crash report from the title and a minidump may also be written. Run
`tools/dmpinfo.py file.dmp` to print only the exception record and the module
it hit, never memory contents. A write to address 0 from inside the title is
often deliberate: titles have watchdogs that crash on purpose when the main
loop stops making progress.

## Is anything on screen?

Run with `TUXBOX_TRACE_PRESENT=600` to get these every 600 frames:

| Message | Meaning |
|---|---|
| `present sample ... lit=0.000 mean=(0,0,0)` | The presented image is completely black. |
| `present sample ... lit=1.000 mean=(...)` | Something is on screen. The mean colour tells screens apart: the same mean in two runs is usually the same screen. |
| `display writes recorded: draws=0 ... clears=600` | The title clears the screen and draws nothing on it. The problem is earlier in the title's own flow. |
| `presented N frames in 10s` | Frame rate of the presentation loop, including loading screens. Millions of frames on a loading screen are not progress. |

## Shaders

| Message | Meaning |
|---|---|
| `Compiled Xbox shader <hash>` | A console shader was translated to HLSL and DXIL for the first time on this translator build. |
| `xshader failed (65): <reason>` | The translator refused a shader. The title gets an empty stand-in pipeline. The reason names the construct; tally them with `run-summary.sh` to see which refusals block the most shaders. |
| `Required WaveSize range [64, 64]` | A program needs 64-lane waves and the GPU only has 32-lane waves (NVIDIA). Newer TuxBox refuses these before the driver compile, or translates them for 32-lane hosts. |
| Overlay `N shaders compiled (N new)` | "new" counts translations this run. After a translator update, it starts from zero again for every shader the update changed. |

## Driver pipelines

| Message | Meaning |
|---|---|
| `CreatePipelineState #N ... still running Ns` | The driver is still compiling. Normal for large compute programs, which can take minutes each. |
| `... finished in Ns` | Compile time. Many over 100 s on a warm cache points to a cache problem (see the NVIDIA cache size check below) or an overloaded CPU. |
| `... deferred after 20s; compile continues` | The title got an empty stand-in so it can keep going, and the real pipeline replaces it when ready. `TUXBOX_PIPELINE_DEADLINE` sets the 20 s. |
| `waits for one of N large compile slots` | `TUXBOX_LARGE_COMPILES` is limiting big compiles. Setting it near your thread count slows every compile down and starves the title. About half the thread count worked better. |
| `pipeline creation failed (0x80070057...)` | Invalid argument: vkd3d-proton rejected how the pipeline was described. |
| `pipeline creation failed (0x80004005...)` | General failure, often the DXIL-to-SPIR-V conversion refusing the shader. |
| `pipeline creation failed (0x80004001...)` | Not implemented: usually a shader with no translation yet. |
| `vkd3d_compile_shader_stage: Failed to compile shader, vkd3d result -3` | vkd3d-proton's converter refused a shader. |
| `vkd3d_pipeline_library_disk_thread_main: Flushing disk cache` | Harmless. vkd3d-proton is saving its pipeline cache. |

A failed pipeline becomes an empty stand-in too. It does not block the title,
but whatever it would have drawn or computed is missing.

## Work dropped

| Message | Meaning |
|---|---|
| `command list cannot record <command> ...` then `command list failed 0x80070057 ... in the command at <file>:<line>` then `Close rejected` | TuxBox could not translate one command, and the whole command list was thrown away. The `cannot record` line gives the details a fix needs. Worth reporting with the line. |
| `skipped draw: pipeline has no paged descriptor layout: <reason>` | A draw or dispatch was dropped because its root signature can't use TuxBox's descriptor paging. The reason says which of three cases it was. |
| `skipped ...` (other) | A single draw or dispatch was dropped, and the rest of its list kept. |

## GPU waits and title checks

| Message | Meaning |
|---|---|
| `GPU memory wait released` | The title waited for a GPU value that never arrived, and TuxBox let it go after a timeout. Work that depended on it may run too early. Many of these usually mean a synchronisation problem. |
| `continued past recoverable title assert RVA 0x...` | One of the title's own internal checks failed, and TuxBox stepped past it. A count climbing into the hundreds means something is failing in a loop. |
| `EXCEPTION_BREAKPOINT` spam | The same title asserts, seen from Wine. Usually harmless on its own. |

## Before you blame the log: check the caches

```sh
tools/cache-check.sh
```

The NVIDIA driver stops indexing a cache file that grows past about 5 GB. After
that, every launch rebuilds the same pipelines and looks like a cold cache.
Rename a flagged file (with the title closed). TuxBox now caps the cache at 4 GiB.

## Reporting

Share log lines and summaries, never the title's files, executables or shader
caches: the cache contains code compiled from the title.
