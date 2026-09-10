# Investigation and implementation

These are observations from the project, including unsuccessful experiments, rather than claims of support across LG's range. Firmware numbers below matter: the newer downloaded G5 comparison firmware was not the firmware running on the TV.

## Capability advertisement was the first layer

The unmodified G5 rejected forcibly supplied DTS. G4 43.21.71 and G5 43.21.73 comparison images contained byte-identical copies of four relevant userspace libraries (`libextinput-service`, `libarccontrollerLib`, `libumi`, `libhdmi-conn-protocol`). Their configuration differed: the G4 factory option table exposed DTS variants of `tv.model.edidType`, while the G5 table exposed only `ac3` and `TrueHD`.

The installed G5 33.30.80 libraries differed from those comparison images, but retained the same useful checks: external-input code accepted EDID enum 2 or 4, and the ARC library looked for the `dts` substring. A runtime `TrueHD` → `TrueHD+dts` override removed the unsupported-format warning. Restarting ARC control and selecting digital Pass Through exposed DTS and DTS-HD in the HDMI capabilities. The input still produced no sound.

### Required configuration prerequisite

This override preceded the successful module tests. The current service now applies it automatically through `config-override.py` before starting the watcher; see [boot persistence](boot-persistence.md). The commands below record the original manual procedure. The key belongs to configd's volatile model database, so persistence means reapplying it after boot rather than changing factory provisioning.

Run these commands inside an interactive root SSH session (`ssh -t root@YOUR_TV_IP`), recording the original response first:

```sh
luna-send -n 1 -f luna://com.webos.service.config/getConfigs '{"configNames":["tv.model.edidType"]}'
luna-send -n 1 -f luna://com.webos.service.config/setConfigs '{"configs":{"tv.model.edidType":"TrueHD+dts"}}'
luna-send -n 1 -f luna://com.webos.service.config/getConfigs '{"configNames":["tv.model.edidType"]}'
systemctl restart arccontroller.service
```

Require `returnValue: true` and a readback of `TrueHD+dts`; an empty non-PTY response is inconclusive. Root access does not universally bypass Luna permissions on another release. Select HDMI3 bitstream input, eARC enabled, and digital sound output **Pass Through** in the TV UI. Renegotiate/restart source playback if it caches EDID. When manually running the older package, repeat the override and ARC restart after reboot if the key resets. The new automatic initializer has offline tests and passed installation/live startup with the key already enabled. A real reboot and reset-key initialization test remain pending.

The original tested value was `TrueHD`. Restore your recorded value with the same setter and restart ARC control when undoing the prerequisite. The project's setter did not change the hash of `/var/preferences/configd_db.json`; no factory bits were edited. The TV's digital output setting is a separate persistent user preference.

## Kernel support gate and missing decoder

The installed kernel's `aud_hal_dts_supported` was `mov w0,0; ret`. The gate module temporarily changes the return value to one through the vendor kernel's `aarch64_insn_patch_text`, under the CPU hotplug read lock, and restores the instruction on unload. This allowed the input ADEC to start but did not create a working output path.

The public DTS codec family (48–53) mapped to internal codec 2, AC3. There was no registered DTS decoder. Copying G4's internal DTS enum 17 would select OPUS on this G5. However, the HDMI DSP itself retained compressed DTS recognition: a software decoder was unnecessary for passthrough.

## Recovering the existing compressed route

`_set_output(index, output_descriptor, codec, bypass, mix)` has an existing compressed route branch. The scoped hook changes routing arguments only for ADEC1, the eARC output mask, a started decoder and the selected public DTS codec. It supplies neutral routing codec 0 and bypass 1. Payload format remains DSP metadata; compressed bytes are not intentionally relabeled PCM.

The graph becomes `renderer_1_out100 → mixer_0_in100 → output_3_in0`. The apparent `output_set_format` function was a logging-only stub; modifying its argument would not establish hardware format. The controller checks the actual graph and renderer gain instance, saves state, and adjusts the DSP properties. Writes use `property value`, not `property=value`. `start` resets dropping behavior, so `drop 0` must follow `start 1`.

| Property | DTS core | DTS-HD / DTS:X |
| --- | --- | --- |
| Driver public codec | 48 | 51 |
| HDMI receiver | DTS / 48000 | DTS_HD / 192000 |
| DSP codec / mode | 5 / 1 | 6 / 4 |
| Transport channels / sample rate | 2 / 48000 | 8 / 192000 |
| IEC61937 burst type observed | 11 | 17 |

Renderer gain was independently muted despite a connected bypass route. Restoring it was necessary for clear core audio. The HD controller additionally waits for the low-level non-PCM state before unmuting.

## Why a temporary break-handler bridge exists

An early kprobe attempt crashed at BRK. The kernel contained the stock kprobe handlers, but their break-hook list links were null. Each route module checks this state and temporarily registers module-owned hooks forwarding the existing BRK4 and BRK6 callbacks. It checks for conflicts, runs a module-local self-test, and removes its hooks with RCU synchronization on cleanup. Core self-test changes an input register and observes result 11; HD additionally exercises PC redirection, observing result 10. This bridge is target-specific, not a generic kprobe repair.

## Why HD required two additional hooks

The first HD experiment produced garbled output and a kernel Oops. `_cb_output_status` accepted codec values only through 4. The DTS-HD event uses 7, so the callback selected PCM. Later it still indexed the original value 7 into a codec-name pointer table containing only entries 0–5. The supposed pointer was actually text bytes (`0x6d756c6f765f7465`), causing an Oops in the logging path.

HD revision 2 redirects only the eARC type-3, started public-codec-51, event-codec-7 case into the existing supported branch, preserving codec 7. A second hook replaces the out-of-range name load with a valid static label and skips the original load. `_set_type` uses nonzero output codec to choose hardware non-PCM; the controller requires its cached HAL argument to equal 1 before unmuting. This combination produced audible output and the user confirmed **DTS:X** on the Q950A display.

A separately reported apparent TV hang was subsequently identified by the user as the Ugoos hanging. That incident is distinct from the earlier confirmed kernel Oops.

## Address reference for the tested raw kernel

Raw kernel SHA-256: `91f58f1471d21d6d5190e0d95b53764edbbf527ddb3ee13f478482141127239c`. Convert raw offsets with runtime base `0xffffffc010088000`; do not confuse this with physical address conversion.

| Object | Runtime address |
| --- | --- |
| DTS support gate | `0xffffffc010f79130` |
| Instruction patch function | `0xffffffc01132f520` |
| `_set_output` | `0xffffffc010f5d240` |
| ADEC1 public codec / open / started | `0xffffffc01264ceb4` / `0xffffffc01264cea8` / `0xffffffc01264ceaa` |
| Break-hook list | `0xffffffc011f94090` |
| Stock break-hook objects | `0xffffffc011f962a8`, `0xffffffc011f962c8` |
| BRK4 / BRK6 callbacks | `0xffffffc01132f8c0`, `0xffffffc01132f7b0` |
| Register / unregister break hook | `0xffffffc01008e604`, `0xffffffc01008e654` |
| HD compare / supported branch | `0xffffffc010f3b56c` / `0xffffffc010f3b66c` |
| HD codec-name load | `0xffffffc010f3b62c` |

The cached eARC non-PCM HAL argument is read at **physical** `0x264d5bc`. Full code fingerprints are checked into `target.json`, `target.h`, and `status_guards.h`. Other private structure offsets and interfaces reside in the C headers and shell controllers; this table is not a complete porting manifest.

## Service design

The supervisor selects one controller from the live HDMI receiver state, scopes it to HDMI3/eARC, and permits an indefinite session only under supervision. Standalone module/controller defaults remain self-test or time-bounded. Source-loss cleanup recognizes a stale owned DTS DSP instance, quiesces it before unloading HD output hooks, restores saved state, and lets LG input integration recreate the current route.

Do not add `After=extinput-integration.service` to the unit. Cleanup synchronously restarts that service; the added ordering dependency caused stop to deadlock. The current unit passed live stop/start after that dependency was removed.
