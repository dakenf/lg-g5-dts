# Tested payload provenance

These three module files were copied byte-for-byte from the payload used in the successful OLED77G5RLA 33.30.80 installation:

- `core-route.ko`: core compressed-bypass route with temporary kprobe break-handler bridge.
- `hd-route.ko`: HD revision 2 route with codec7 output acceptance and safe codec-name lookup.
- `dts-gate.ko`: reversible kernel DTS support gate.

They correspond to the source profiles in tools/. The HD binary retains debug information, including the original developer's workspace paths; no keys or device dumps are included. Fresh builds strip debug information and need not have identical hashes because build paths and compiler versions differ. SHA256SUMS authenticates consistency within this checkout, not an independently signed release.

The install package combines these modules with the current checked-in controllers and startup service. The local package installer is newly provided for reproduction and has been checked offline; the working device installation was originally assembled with equivalent file transfers and service commands.
