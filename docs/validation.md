# Validation and recovery

## Hardware evidence

On OLED77G5RLA 33.30.80 with Ugoos SK1 on HDMI3 and Q950A over eARC:

- User confirmed clear ordinary DTS audio after restoring compressed routing and renderer gain.
- Initial HD attempt produced garbled audio and a kernel Oops. Those binaries are not included.
- HD revision 2 preserved non-PCM event7, fixed its invalid codec-name lookup, and passed the low-level format guard. User heard sound and explicitly observed **DTS:X** on the receiver display.
- Final combined supervisor was installed, active with an HD session, and passed live stop/start after correcting a systemd ordering deadlock.
- The earlier boot-hook mechanism was exercised; reboot of the final combined package, long-duration playback and exhaustive format/source transitions remain unverified.
- Configuration `tv.model.edidType=TrueHD+dts` and digital Pass Through were set before the successful tests. The volatile model override is a manual prerequisite and is not made persistent by this package.

Receiver HTTP queries did not yield a reliable active-codec field. The brief front-display indication was the decisive DTS:X confirmation. An earlier audible “TrueHD” test was actually EAC3 at the TV; it is not counted as verified TrueHD passthrough.

## Repository validation

A fresh upstream Linux 5.4.268 tree with the pinned archive and checked-in config successfully built all three modules using Clang 21.1.8. The preparation-only build emits a missing Module.symvers warning; actual vendor export/ABI auditing is a separate check.

`bash scripts/test.sh` exercises the exhaustive core scope predicate and 8 core + 9 HD mocked controller lifecycle scenarios. The firmware-dependent suite verifies stock module layout/imports, executes the original routing branch, and emulates the HD callback failure and corrected path. Tests do not simulate the real DSP or guarantee acoustic output. Freshly built binaries have not been separately loaded on the TV during repository preparation.

The package script is local-only and uses an explicit file list. Its checksums cover modules, controllers, unit, startup hook, installer and manifest. The standalone installer is new reproduction tooling; syntax/package tests do not establish a new on-device installation test. The already-working TV was not changed to prepare this repository.

## Runtime files

Payload: `/var/lib/lg-dts-core`, with HD files in `hd/`. Startup: `/var/lib/webosbrew/init.d/90-lg-dts-core`. Unit: `/run/systemd/system/lg-dts-core.service`. The `enabled` marker controls startup; `control.sh disable` removes it and stops the service.

Diagnostics: `/tmp/lg-dts.log` and `/tmp/dts-core-test-*` or `/tmp/dts-hd-test-*`. Supervised session snapshots overwrite the latest sample instead of accumulating one file per second. Separate session directories can still accumulate across many sessions until reboot. `/var/log/dbg-log` was useful for LG service diagnostics on the tested image; systemd journal content was not consistently available. Do not interpret absent journal messages as successful cleanup.

## Recovery

For ordinary rollback run:

```sh
sh /var/lib/lg-dts-core/control.sh disable
lsmod | grep -E '^dts_(gate|core_route) '
```

No matching modules should remain. Cleanup errors are printed in the session log; stop testing if restoration is incomplete. If the TV is unresponsive, recover it with a power cycle. If you can reach SSH before another session starts, disable the startup marker. A service restart alone is not a substitute for recovering from a kernel Oops. Root access/boot recovery availability is a prerequisite for experimental ports.

To restore a backup made by the installer, first disable/stop the current installation and verify the modules are gone. Substitute the actual backup directory printed during installation; perform these commands on the TV:

```sh
# Choose an unused name for the failed payload; retain it for diagnosis.
mv /var/lib/lg-dts-core /var/lib/lg-dts-core-disabled-copy
mv /var/lib/lg-dts-backup-REPLACE_WITH_ACTUAL_NAME /var/lib/lg-dts-core
cp /var/lib/lg-dts-core/90-lg-dts-core /var/lib/webosbrew/init.d/90-lg-dts-core
chmod 700 /var/lib/webosbrew/init.d/90-lg-dts-core
sh /var/lib/lg-dts-core/control.sh enable
```

A backup may have its enabled marker intact; explicitly choose whether to enable it. If there was no previous installation, leaving the new payload disabled is sufficient; no stock firmware needs reflashing. Restore the separately recorded EDID configuration and digital output preference if undoing the whole experiment, as described in investigation.md.
