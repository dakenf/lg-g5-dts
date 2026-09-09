# Working on this repository

Start with README.md and docs/{investigation,porting,validation}.md. This is an exact-target kernel/DSP patch. Treat all absolute addresses, enum mappings, structure offsets, ALSA control IDs, and procfs syntax as firmware-specific.

- Work offline by default. Building, packaging, disassembly and mocked tests do not require a TV.
- Do not infer deployment authorization from a request to review, build or port. Follow the user's current session authorization; do not interrupt their playback without an authorized hardware test window.
- Never weaken fingerprint, target, codec, port or output checks merely to make a test pass. Another firmware requires a newly analyzed target, not a renamed release string.
- Preserve cleanup and exact restoration of captured state, single-profile operation, HD non-PCM-before-unmute ordering, and the bounded default experiment window.
- Never add `After=extinput-integration.service` to the service: controller cleanup synchronously restarts it, which previously deadlocked service stop ordering.
- Never commit raw firmware, rootfs dumps, SSH keys, LAN addresses, tokens, private audit data or proprietary player libraries. Keep researcher inputs under ignored inputs/ and local outputs under build/ or .cache/.
- Use scripts/build.sh, scripts/test.sh, and optionally scripts/test.sh --firmware. Distinguish mocked tests, emulation, ABI auditing and observed hardware behavior in every report.
- Source profiles are separate and share the same kernel module name. Do not load both. Audit common changes in both copies, including break_bridge.h and target.h.
- Installation files are packaged explicitly by scripts/package.py. Verify checksums after changes and document any change to rollback or boot behavior.
- No software DTS decoder is part of the goal: preserve compressed DTS-HD/DTS:X payloads through eARC.
