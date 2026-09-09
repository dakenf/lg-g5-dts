# Reproducing the analysis and porting

## Obtain the right inputs

Start by recording the full model, firmware, webOS and `uname -r`, root method, input port, receiver and output mode. Save read-only diagnostics locally. Obtain a known DTS core and DTS:X source and first establish that the receiver plays them when connected directly. Root/developer access and firmware signing are separate mechanisms: the USB update workflow installs LG update packages; it is not evidence that a modified package will be accepted.

Use the model's official LG support download for comparison firmware and verify that a downloaded file is actually a ZIP/EPK, not an access-error HTML page. During this investigation the archived 33.30.80 download failed, so the running TV was the source of the matching kernel and libraries. The available newer G5 43.21.73 and G4 43.21.71 images were references only.

The extractor used was [openlgtv/epk2extract](https://github.com/openlgtv/epk2extract/tree/2b6af078b56dbedb89efc0f4943036150f1ecae9), revision `2b6af078b56dbedb89efc0f4943036150f1ecae9`. Build it using that revision's instructions. `epk2extract -n -s IMAGE.epk` extracted the comparison packages with their signature checks. Both reference root filesystems began 1,048,576 bytes into `super.pak`, independently described by `dpmeta.pak`; re-read metadata for another image instead of assuming that offset. Extract SquashFS locally with `unsquashfs -no-xattrs` when device nodes are unnecessary.

For a running rooted TV, inspect `/proc/partitions`, the partition map, boot command line and mounts to identify the **active kernel slot** before reading it. The tested slot was captured as `kernel-slot21.bin`; the number is not a portable block-device choice. A read-only copy should have the identified block device as the source and a workstation file as the destination. Never write to a block device for this workflow. Do not blindly copy someone else's `dd` command or assume an inactive slot matches the running kernel.

`epk2extract kernel-slot21.bin` decoded the captured slot's LZ4 data to `kernel-slot21.bin.unlz4`, 36,520,448 bytes. That uncompressed raw image is `inputs/kernel.bin`, with the hash listed in inputs/README.md. Copy an unmodified module with relocations from the same running kernel to `inputs/stock-module.ko`. Obtain kernel configuration through `/proc/config.gz` if available, or upstream `scripts/extract-ikconfig` on the image. No rootfs/firmware dump needs to enter Git.

## Recover semantics before selecting addresses

1. Inspect the config consumers, external-input service, ARC capability construction and codec mappings. ELF32 ARM/Thumb userspace and the ARM64 kernel require different disassembly modes. Thumb symbol addresses may carry a low-bit marker.
2. Recover kernel symbols and validate code against instruction flow and string references. The G4 6.12.44 image exposed a trap: vmlinux-to-elf 1.3.6 misread its address array as 64-bit. Its 71,024 entries were actually 32-bit offsets at raw `0x1c759e0`, with `_stext` raw offset `0x10000`. Do not trust a plausible symbol name without checking the instructions.
3. Trace the DTS gate, public-to-internal codec table, `_set_output`, decoder state structures, eARC format selection, DSP notifications and hardware non-PCM selection. Map **each enum independently**. G4 internal DTS17 is G5 OPUS17; public DTS51, DSP codec6 and output-event codec7 are different namespaces.
4. Establish all absolute code/data addresses, raw/runtime/physical conversions, structure sizes and offsets, callback registers and continuation PCs. Search source for `0x`, private procfs paths, `numid`, kernel strings and fixed instance IDs. Updating `target.json` alone is insufficient.
5. Verify kprobe ABI and stock break-hook registration. Confirm bridge list layout, callback addresses and stock objects. Kprobe offsets used here are addr `0x28`, pre_handler `0x40`, flags `0x80`. A different kernel might not need this bridge at all.
6. Verify module ABI against a stock module: this target has `struct module` size `0x380`, init relocation `0x150`, exit relocation `0x338`. Confirm vermagic, config, module versioning/signing and every imported symbol through the actual vendor kernel exports. Never use forced module loading to conceal ABI mismatches.
7. Trace output-status acceptance **and logging**. Preserving a new codec event without fixing an out-of-range diagnostic name access caused a real crash here. Confirm compressed hardware state before unmuting HD.
8. Map the actual DSP graph, property types/write syntax, input instance ownership, gain module, ALSA control ID/value, and receiver transport for the desired HDMI port. The present controller expects ALSA numid92 value `2,1,0,0,1`, HDMI port2/ADEC1 and particular graph instances.

## Build an explicit new target

Keep the tested profile intact. Add a new profile with a manifest of the new kernel hash, disassembly findings, code fingerprints, build configuration and interface mappings. `scripts/generate-target.py` deliberately refuses any kernel except the known 33.30.80 image; it verifies/regenerates existing guards, not discovers replacements. Do not replace the hash and recapture arbitrary bytes just to pass checks.

Every guard must protect a understood assumption. Current byte guards are incomplete compatibility checks: they cannot guarantee that a data address is mapped or that DSP firmware matches. A kernel release string may be reused across different builds. Test a new target as new hardware until demonstrated otherwise.

## Testing without a TV

Run the policy and controller tests, then audit module ABI/imports and emulate the original instructions with the matching image. Extend negative cases for new ports/codecs, mismatched fingerprints, source disappearance, rejected routes, premature PCM output and cleanup failure. The present tests include the HD non-PCM guard and source-loss restoration; inspect their scenario names for exact scope.

Unicorn provides narrow CPU/control-flow tests. This project contains no complete QEMU LG board model and has not demonstrated booting the proprietary firmware under QEMU. The webOS SDK emulator is not evidence that LG's commercial HDMI/audio DSP path is emulated. A full model would need the SoC memory map, interrupt and device behavior, HDMI/EDID transport, proprietary audio-driver IPC, DSP behavior and eARC timing. Mocking those devices to return desired values can test software paths but cannot validate actual passthrough. Writing a complete emulator is not a prerequisite for this patch; narrowly emulated branches plus controlled hardware tests were useful here.

## Staged hardware validation

Use an explicitly agreed testing window and a recovery plan. Disable the startup service before experimental loading. First validate the image and module ABI offline; then verify matching live instruction bytes, run the gate's default probe and the route module's default isolated self-test. Only then use the packaged controller's `--apply 30` bounded test for a matching live stream. Do not run raw hook modules outside the controller while ordinary playback is active.

Test core before HD, verify the compressed graph, DSP metadata, non-PCM hardware output and receiver indication, then verify unload/restoration. Add source changes, PCM/Dolby, eARC disconnect, service stop, standby/wake and reboot before claiming general or permanent compatibility. Preserve logs locally and publish sanitized conclusions, not device dumps. Exact rollback behavior and a clear abort path are part of a port, not follow-up polish.
