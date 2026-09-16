#!/usr/bin/env bash
set -Eeuo pipefail
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
source "$ROOT/deploy/scripts/common.sh"
BASE="$ROOT/deploy/runtime/test-qa/git-$$"
mkdir -p "$BASE"
git init --bare -q "$BASE/remote.git"
git clone -q "$BASE/remote.git" "$BASE/seed"
git -C "$BASE/seed" config user.name QA
git -C "$BASE/seed" config user.email qa@example.invalid
printf 'first\n' > "$BASE/seed/value"
git -C "$BASE/seed" add value
git -C "$BASE/seed" commit -qm '创建测试基线'
git -C "$BASE/seed" push -q origin HEAD
for scenario in equal behind ahead diverged missing-upstream fetch-failed dirty; do
    git clone -q "$BASE/remote.git" "$BASE/$scenario"
    CASE="$BASE/$scenario"
    git -C "$CASE" config user.name QA
    git -C "$CASE" config user.email qa@example.invalid
    case "$scenario" in
        ahead|diverged)
            printf '%s\n' "$scenario" > "$CASE/local"
            git -C "$CASE" add local; git -C "$CASE" commit -qm '添加本地测试改动';;
        missing-upstream) git -C "$CASE" branch --unset-upstream;;
        fetch-failed) git -C "$CASE" remote set-url origin "$BASE/missing.git";;
        dirty) printf 'dirty\n' >> "$CASE/value";;
    esac
    if [[ $scenario == behind || $scenario == diverged ]]; then
        printf '%s\n' "$scenario" >> "$BASE/seed/value"
        git -C "$BASE/seed" commit -qam '更新上游测试内容'
        git -C "$BASE/seed" push -q origin HEAD
    fi
    before=$(git -C "$CASE" rev-parse HEAD)
    set +e
    (
        set -Eeuo pipefail
        ROOT=$CASE RUNTIME="$BASE/tickets-$scenario"
        mkdir -p "$RUNTIME"
        # Capture the handoff; /proc fd inheritance needs a Linux acceptance test.
        exec() { printf '%s\n' "$*" > "$BASE/resume-$scenario"; }
        [[ -z $(git -C "$ROOT" status --porcelain --untracked-files=all) ]] || die 'dirty tree'
        update_source
    ) > "$BASE/$scenario.log" 2>&1
    result=$?
    set -e
    if [[ $scenario == equal || $scenario == behind ]]; then
        [[ $result == 0 && -f $BASE/resume-$scenario ]]
        [[ $(git -C "$CASE" rev-parse HEAD) == $(git -C "$CASE" rev-parse '@{upstream}') ]]
    else
        [[ $result != 0 && ! -f $BASE/resume-$scenario ]]
        [[ $(git -C "$CASE" rev-parse HEAD) == "$before" ]]
    fi
    printf 'PASS %s\n' "$scenario"
done
printf '7 real temporary Git cases passed; resume handoff substituted; evidence %s\n' "$BASE"
