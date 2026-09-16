#!/usr/bin/env bash
set -Eeuo pipefail
root=$(cd "$(dirname "$0")/../.." && pwd -P)
source "$root/deploy/scripts/common.sh"
mkdir -p "$root/deploy/runtime/test-dev"
test_dir=$(mktemp -d "$root/deploy/runtime/test-dev/settings.XXXXXX")
SETTINGS="$test_dir/settings"
valid() {
    printf '%s\n' 'SUPERUSER_PASSWORD=Secure-user-987654' \
        'JWT_SECRET=ab0123456789abcdef0123456789abcdef' 'LOTTERY_SECURITY_CODE=45678901' 'HTTP_PORT=8088'
}
valid > "$SETTINGS"
export SUPERUSER_PASSWORD=ignored JWT_SECRET=ignored
load_settings
[[ $SUPERUSER_PASSWORD == Secure-user-987654 && $HTTP_PORT == 8088 ]]
for bad in 'JWT_SECRET=duplicate' 'UNKNOWN_KEY=value'; do
    valid > "$SETTINGS"
    printf '%s\n' "$bad" >> "$SETTINGS"
    if (load_settings) > "$test_dir/output" 2>&1; then
        printf 'Expected rejection\n' >&2; exit 1
    fi
    ! grep -q 'touch stolen' "$test_dir/output"
done
for bad in 'HTTP_PORT=70000' 'SUPERUSER_PASSWORD=$(touch stolen)'; do
    valid | grep -v "^${bad%%=*}=" > "$SETTINGS"
    printf '%s\n' "$bad" >> "$SETTINGS"
    if (load_settings) > "$test_dir/output" 2>&1; then exit 1; fi
    ! grep -q 'touch stolen' "$test_dir/output"
done
valid | grep -v '^JWT_SECRET=' > "$SETTINGS"
if (load_settings) > "$test_dir/output" 2>&1; then exit 1; fi
printf '%s\n' 'SUPERUSER_PASSWORD=CHANGE_ME_PASSWORD' \
    'JWT_SECRET=ab0123456789abcdef0123456789abcdef' 'LOTTERY_SECURITY_CODE=45678901' > "$SETTINGS"
if (load_settings) > "$test_dir/output" 2>&1; then exit 1; fi
printf 'settings: valid, inherited override, duplicate, unknown, invalid port, injection, placeholder passed\n'
