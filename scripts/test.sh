#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p build/reports
cc -O2 -Wall -Wextra -Werror tools/dts-core-route/tests/policy_test.c -o build/policy-test
build/policy-test
python3 tools/dts-core-route/tests/config_test.py
python3 tools/dts-core-route/tests/controller_test.py
python3 tools/dts-hd-route/tests/controller_test.py
for f in tools/dts-core-route/*.sh tools/dts-hd-route/*.sh scripts/install-on-tv.sh; do sh -n "$f"; done
if [[ ${1:-} == --firmware ]]; then
 python3 scripts/generate-target.py --check
 python3 tools/dts-core-route/tests/audit_binary.py
 python3 tools/dts-core-route/tests/emulate_route.py
 python3 tools/dts-hd-route/tests/emulate_status.py
fi
