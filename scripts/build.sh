#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
root=$PWD
version=5.4.268
archive="$root/.cache/linux-$version.tar.xz"
kernel="$root/.cache/linux-$version"
mkdir -p .cache build/reports
if [[ ! -f "$archive" ]]; then
 curl --fail --location "https://cdn.kernel.org/pub/linux/kernel/v5.x/linux-$version.tar.xz" -o "$archive"
fi
printf '%s  %s\n' afc8aca6cb56fea489f6508bc24357df1cf8a8f3d7dcfbcccd94b7f968492620 "$archive" | sha256sum -c -
[[ -d "$kernel" ]] || tar -xJf "$archive" -C .cache
python3 - "$kernel/scripts/Makefile" <<'PY'
import pathlib,sys
p=pathlib.Path(sys.argv[1])
p.write_text(''.join(line for line in p.read_text().splitlines(True) if not (line.startswith('hostprogs-') and 'extract-cert' in line)))
PY
cp config/build.config "$kernel/.config"
linker=${DTS_LLD:-}
if [[ -z "$linker" ]]; then linker=$(command -v ld.lld || true); fi
if [[ -z "$linker" ]]; then
 linker=$(python3 - <<'PY'
from pathlib import Path
print(next(iter(Path.home().glob('.rustup/toolchains/*/lib/rustlib/*/bin/gcc-ld/ld.lld')), ''))
PY
)
fi
[[ -n "$linker" ]] || { echo 'Install LLVM LLD or set DTS_LLD.' >&2; exit 1; }
args=(ARCH=arm64 CC=clang CLANG_FLAGS=--target=aarch64-linux-gnu LD="$linker" AR=llvm-ar NM=llvm-nm OBJCOPY=llvm-objcopy)
make -C "$kernel" "${args[@]}" olddefconfig modules_prepare
for module in dts-kernel-probe dts-core-route dts-hd-route; do
 make -C "$kernel" "${args[@]}" M="$root/tools/$module" modules
 filename=dts_core_route
 [[ "$module" != dts-kernel-probe ]] || filename=dts_gate
 llvm-objcopy --strip-debug "$root/tools/$module/$filename.ko"
done
python3 scripts/package.py
