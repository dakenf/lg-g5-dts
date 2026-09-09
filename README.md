# DTS and DTS:X passthrough for LG G5

A reversible runtime patch that restores HDMI → eARC DTS passthrough on a rooted **LG OLED77G5RLA running firmware 33.30.80**. Ordinary DTS produced clear audio; DTS:X was confirmed on the Samsung Q950A's front display while playing a DTS:X stream from a Ugoos SK1.

This repository contains the kernel modules, session controllers, startup service, tested binaries, build scripts, offline tests, and investigation notes needed to reproduce that result manually or with a coding agent. It does not flash modified firmware or add a software decoder. The TV's existing DSP forwards the compressed stream, preserving the DTS:X payload.

## Tested setup and limits

| Component | Tested value |
| --- | --- |
| TV | LG OLED77G5RLA, 2025 G5, 77 inches |
| Firmware / webOS | 33.30.80 / webOS 25, 10.3.0-17 |
| Kernel | `5.4.268-329.ptl4tv.5`, ARM64 |
| Source | Ugoos SK1 connected to TV HDMI3 (`HDMI_PORT2`, ADEC1) |
| Receiver | Samsung HW-Q950A connected to TV eARC / HDMI2 |
| Core profile | DTS, 48 kHz |
| HD profile | DTS_HD receiver transport, 192 kHz; DTS:X display confirmed |

**This is an exact-firmware research patch, not a general LG installer.** It uses absolute kernel addresses and private driver/DSP interfaces. Incorrect addresses or a partially compatible firmware can crash the kernel or send compressed data as loud noise. Code fingerprints and session checks reduce these risks; they do not prove compatibility with another build. Read [porting](docs/porting.md) before changing any target check. Begin hardware tests at low receiver volume.

The present watcher handles HDMI3 → eARC only. Internal TV app passthrough, other HDMI inputs, optical output, other sample rates, and other models are not established by these results. Privacy/microphone changes and the separate Ugoos TrueHD/MAT negotiation issue are outside this project.

## Install the tested binaries

Prerequisites: the exact tested firmware, a rooted TV with working SSH, webOSbrew startup at `/var/lib/webosbrew/startup.sh`, and the usual TV tools (`amixer`, `devmem`, `insmod`, `rmmod`, `systemctl`). Rooting is a separate prerequisite; no exploit or credentials are included. Enable eARC and digital sound passthrough in the TV, and bitstream passthrough on the player. The source must send DTS: the watcher detects a received DTS stream before starting its session. A cached source capability list may require playback or HDMI renegotiation; forcing DTS on the source was used during investigation.

First apply and verify the **required `TrueHD+dts` configuration override** using [these commands](docs/investigation.md#required-configuration-prerequisite). The installer does not set this volatile key; recheck it after reboot.

On your Linux workstation:

```sh
git clone https://github.com/dakenf/lg-g5-dts.git
cd lg-g5-dts
python3 scripts/package.py --prebuilt
bash scripts/test.sh
export TV_HOST=YOUR_TV_IP
# Add your own SSH -i/-p options if needed. Never put a private key in this repo.
ssh "root@$TV_HOST" 'mkdir -p /tmp/lg-dts-install'
cat build/lg-g5-dts-33.30.80.tar.gz | ssh "root@$TV_HOST" 'tar -xz -C /tmp/lg-dts-install'
ssh "root@$TV_HOST" 'sh /tmp/lg-dts-install/install.sh --install'
```

Use a fresh empty extraction directory for each package. The installer checks checksums and kernel release, stops an existing installation, refuses leftover experiment modules, backs up the existing payload, installs into `/var/lib/lg-dts-core`, and enables the boot hook. No stock firmware partition is written. The service then watches for matching input and selects the core or HD profile. Both profiles have the same module name and are never loaded together.

Play a known DTS core clip first, then DTS-HD/DTS:X. Confirm the receiver's codec display at playback start; audible sound alone does not establish DTS:X. Successful core playback does not establish HD safety.

```sh
ssh "root@$TV_HOST" 'sh /var/lib/lg-dts-core/control.sh status'
ssh "root@$TV_HOST" 'tail -80 /tmp/lg-dts.log'
# Stop now; automatic startup remains enabled:
ssh "root@$TV_HOST" 'sh /var/lib/lg-dts-core/control.sh stop'
# Stop and disable automatic startup:
ssh "root@$TV_HOST" 'sh /var/lib/lg-dts-core/control.sh disable'
# Enable again, including starting now:
ssh "root@$TV_HOST" 'sh /var/lib/lg-dts-core/control.sh enable'
```

Cleanup restores saved DSP/ALSA state, unloads hooks and the gate, and restarts input integration. This can briefly interrupt HDMI. Unexpected session errors stop the supervisor instead of repeatedly applying a failed patch. If installation/startup fails, inspect the session log and disable it; the installer retains the previous directory but does not automatically restore it. See [recovery](docs/validation.md#recovery).

The combined core/HD service passed live start/stop checks. Its boot mechanism was exercised earlier, but **a reboot of the final combined package has not yet been verified**.

## Build from source

Use Linux with Clang, LLD, LLVM tools, a host C compiler, GNU make/binutils, flex, bison, Python 3, curl, tar, and xz. The recorded clean build used Clang 21.1.8. `DTS_LLD=/path/to/ld.lld` can override linker discovery.

```sh
bash scripts/build.sh
bash scripts/test.sh
# Output: build/lg-g5-dts-33.30.80.tar.gz
```

The build downloads Linux 5.4.268 from kernel.org and verifies its pinned SHA-256, prepares it with the checked-in configuration, compiles all three modules, strips debug information from new builds, and creates a checksummed package. It disables the unused host `extract-cert` build target for module preparation; it does not build a replacement TV kernel. Missing `Module.symvers` warnings are expected for this preparation-only tree: the captured kernel has module versioning disabled. The optional binary audit verifies actual imports against the captured vendor kernel rather than treating a successful link as proof of compatibility.

`config/captured.config` is the device kernel configuration; `config/build.config` is the prepared upstream build configuration. The module vermagic is `5.4.268 SMP preempt mod_unload aarch64`; the vendor suffix is checked separately at runtime. Changing the vermagic string alone cannot port the module.

The prebuilt modules are the exact binaries used by the working installation. A fresh build is functionally reproduced and audited offline, not claimed bit-for-bit identical or separately tested on the TV. See [prebuilt provenance](prebuilt/33.30.80/README.md).

## Offline research and tests

Basic tests use a host C policy test plus mocked shell/controller lifecycle tests; they need no TV. For vendor machine-code tests, obtain your own inputs as described in [inputs/README.md](inputs/README.md), then:

```sh
python3 -m venv .cache/analysis-venv
. .cache/analysis-venv/bin/activate
pip install -r requirements-analysis.txt
python3 scripts/generate-target.py --check
bash scripts/test.sh --firmware
```

These tests audit module layout and PREL32 exports, emulate the original AArch64 routing branch, reproduce the HD PCM fallback and invalid log-pointer bug, and test the corrected callback behavior. Unicorn executes small functions with mocked surrounding state. It does not emulate the TV, HDMI receiver, DSP firmware, or eARC PHY, and cannot prove sound output. Reports go to `build/reports/`.

## How it works and how to port it

The fix needed more than announcing DTS in capabilities: the G5 rejected routing and mishandled HD output events even when DTS reached the input. The implementation temporarily enables the kernel DTS support gate, restores the existing compressed bypass route, configures the HDMI DSP for DTS or DTS-HD, and unmutes only after checks pass. HD additionally preserves the non-PCM output event and prevents an out-of-bounds codec-name lookup.

- [Investigation and architecture](docs/investigation.md): the successful path, failed approaches, addresses, and why each patch exists.
- [Porting guide](docs/porting.md): firmware acquisition, address/ABI recovery, another model or software version, staged hardware tests, and emulation limits.
- [Validation and recovery](docs/validation.md): evidence, limitations, service behavior, and restoring a previous installation.
- [AGENTS.md](AGENTS.md): instructions for an agent continuing the project.

Project code is distributed under GPL-2.0-only; see [LICENSE](LICENSE). Vendor firmware images, proprietary libraries, media samples, personal captures, SSH keys, and privacy-audit data are intentionally absent.
