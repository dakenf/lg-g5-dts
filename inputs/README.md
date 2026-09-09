# Private analysis inputs

These files are not distributed and are ignored by Git:

- `kernel.bin`: the **uncompressed raw kernel image** from the tested, unmodified 33.30.80 installation. SHA-256: `91f58f1471d21d6d5190e0d95b53764edbbf527ddb3ee13f478482141127239c`. An EPK container, compressed boot slot or symbolized ELF is not interchangeable with this raw file.
- `stock-module.ko`: an unmodified loadable module from that same installation. The reference audit used `aspectratiodrv.ko`, including its module metadata and relocation sections.

See ../docs/porting.md for acquisition and analysis. Do not publish these files or put credentials here. The common target manifest contains raw-file offsets and a runtime base so address conversions are explicit. `scripts/generate-target.py --check` verifies the captured image and the checked-in guards. Omitting `--check` regenerates guards only for this known image; it is not an automatic firmware porter.
