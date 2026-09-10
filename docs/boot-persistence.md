# Boot persistence

The payload already lives in writable persistent `/var/lib/lg-dts-core`, with a webOSbrew `init.d` hook. What was missing was initialization of the **volatile** `tv.model.edidType` key after reboot. The updated service supplies that initialization; it does not change factory bits or signed firmware.

Boot sequence:

1. webOSbrew runs `90-lg-dts-core`. It checks the enabled marker, exact kernel release and payload checksums, installs the runtime systemd unit and starts it.
2. `ExecStartPre` runs `config-override.py ensure`. It waits up to approximately 90 seconds for configd replies, with individually bounded calls. Only `TrueHD` and `TrueHD+dts` are accepted on this target.
3. If needed, it journals the original `TrueHD` value to an atomic mode-0600 file, sets `TrueHD+dts`, and requires matching readback. It refreshes ARC capabilities even when the value was already enabled, because ARC may have cached older capabilities.
4. Only then does the existing DTS core/HD watcher start. No kernel module is loaded until a matching live stream arrives.

The helper uses the TV's explicit `/usr/bin/script` to provide a terminal to `/usr/bin/luna-send`. A direct non-terminal call returned no response; using PATH could select the incompatible BusyBox `script`. Both behaviors were checked on the real TV, and the final helper's `status` command successfully returned `TrueHD+dts`. The Python interpreter needs its JSON, subprocess, OS and time standard-library modules; no third-party Python dependency is used on the TV.

The unit has no ordering dependency on the services it synchronously restarts. Configuration calls, ARC restart and total startup have time limits. Startup failure leaves the watcher stopped. `ExecStopPost` restores the journaled configuration after normal stop or failed startup; this also runs when `control.sh disable` stops the service. Failed restoration retains the journal for diagnosis/retry. An externally changed value is preserved. An already-enabled value with no journal is treated as pre-existing configuration and is not reset on stop.

`config-original.json` is runtime state, not part of the package checksum list. Following an unclean reboot, a retained journal is reused while the volatile setting is reapplied. No automatic retry loop patches an unexpected configuration. If configd starts later than the startup window, inspect the logs and explicitly start the service again.

## Install and verify

Build the updated package with `python3 scripts/package.py --prebuilt` and use the README installer instructions. Installing restarts the service and ARC capabilities, so use a playback test window. Reboot only when ready to interrupt the TV. This update was installed on the project TV without rebooting. The startup initializer exited successfully, the key read back as `TrueHD+dts`, ARC and the watcher were active, and payload checksums and the enabled boot hook passed. The boot ID was unchanged. Because the key was already enabled, this validates startup/ARC refresh, not the setter after a real reboot. **Reboot validation remains pending.**

After installation, check service status and the verified setting:

```sh
sh /var/lib/lg-dts-core/control.sh status
/usr/bin/python3 /var/lib/lg-dts-core/config-override.py status
```

After an actual reboot, confirm that the setting is again `TrueHD+dts`, the service is active, the source advertises DTS, and both core and DTS:X playback work. Observe the receiver's DTS:X display at playback start. Test stop/disable and re-enable, plus standby/wake. Digital sound Pass Through and eARC must remain enabled in TV settings. Sources can cache EDID and may need HDMI/playback renegotiation after ARC restarts.

This mechanism targets reboots on the same firmware. It does not establish survival across firmware updates, factory resets, loss of root, removal of webOSbrew startup, or changes in addresses/DSP interfaces. The exact-version guards must continue refusing incompatible firmware.
