#!/usr/bin/env bash
# Docker substitutes verify ordering and failure handling, not container behavior.
set -Eeuo pipefail
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
source "$ROOT/deploy/scripts/common.sh"
source "$ROOT/deploy/scripts/release.sh"
BASE="$ROOT/deploy/runtime/test-qa/flow-$$"
mkdir -p "$BASE"
passed=0
for scenario in config build nginx backup up probe success; do
    CASE="$BASE/$scenario"
    mkdir -p "$CASE/releases/old" "$CASE/data"
    printf 'old\n' > "$CASE/current"
    printf '{}\n' > "$CASE/releases/old/compose.json"
    printf '%s\n' "$CASE/data" > "$CASE/releases/old/data-dir"
    printf 'old-image\n' > "$CASE/releases/old/backend-image"
    set +e
    (
        set -Eeuo pipefail
        RUNTIME=$CASE PROJECT=active-system HTTP_PORT=80
        old_release='' release='' restart_old=0 stage=initial
        trap failure EXIT
        git() { printf '0123456789abcdef\n'; }
        docker() {
            printf '%s\n' "$*" >> "$CASE/calls"
            case "$*" in
                *".Image"*) printf 'old-image\n';;
                *".State.Running"*) printf 'false\n';;
                *".State.Health.Status"*) printf 'healthy\n';;
                "image inspect"*) printf 'new-image\n';;
                *"nginx -t"*) [[ $scenario != nginx ]];;
                *"/tool.py backup"*) [[ $scenario != backup ]];;
                *) return 0;;
            esac
        }
        compose() {
            printf '%s\n' "$*" >> "$CASE/calls"
            case "$*" in
                *"config --quiet"*) [[ $scenario != config ]];;
                *"config --format json"*) printf '{}\n';;
                *"build backend nginx"*) [[ $scenario != build ]];;
                *"ps -a -q backend"*) printf 'backend-id\n';;
                *"ps -q "*) printf 'service-id\n';;
                *"up -d"*) [[ $scenario != up ]];;
                *"exec -T nginx"*) [[ $scenario != probe ]];;
                *) return 0;;
            esac
        }
        deploy_release
    ) > "$CASE/output" 2>&1
    result=$?
    set -e
    if [[ $scenario == success ]]; then
        [[ $result == 0 && $(<"$CASE/current") != old && $(<"$CASE/previous") == old ]]
    else
        [[ $result != 0 && $(<"$CASE/current") == old ]]
        grep -q '失败阶段' "$CASE/output"
    fi
    case "$scenario" in
        config|build|nginx) ! grep -Eq 'stop -t|up -d' "$CASE/calls";;
        backup) grep -q 'start backend' "$CASE/calls"; ! grep -q 'up -d' "$CASE/calls";;
        up|probe) ! grep -q 'start backend' "$CASE/calls";;
    esac
    ! grep -q ' down' "$CASE/calls"
    passed=$((passed + 1))
    printf 'PASS %s\n' "$scenario"
done
printf '%s control-flow cases passed; evidence %s\n' "$passed" "$BASE"
for scenario in unmanaged pending-missing pending-match pending-alien image-drift; do
    CASE="$BASE/$scenario"
    mkdir -p "$CASE/releases/old" "$CASE/data"
    printf '{}\n' > "$CASE/releases/old/compose.json"
    printf '%s\n' "$CASE/data" > "$CASE/releases/old/data-dir"
    if [[ $scenario != unmanaged ]]; then printf 'old\n' > "$CASE/pending"; fi
    if [[ $scenario != pending-missing ]]; then
        printf 'old-image\n' > "$CASE/releases/old/backend-image"
        printf 'nginx-image\n' > "$CASE/releases/old/nginx-image"
    fi
    if [[ $scenario == image-drift ]]; then printf 'old\n' > "$CASE/current"; fi
    set +e
    (
        set -Eeuo pipefail
        RUNTIME=$CASE PROJECT=active-system HTTP_PORT=80
        old_release='' release='' restart_old=0 stage=initial
        trap failure EXIT
        git() { printf '0123456789abcdef\n'; }
        docker() {
            case "$*" in
                "ps -aq"*) printf 'existing-id\n';;
                *"com.docker.compose.project"*) printf 'active-system\n';;
                *"com.docker.compose.service"*) printf 'backend\n';;
                *".Destination"*) printf '%s\n' "$CASE/data";;
                *".Image"*)
                    if [[ $scenario == pending-alien || $scenario == image-drift ]]; then
                        printf 'alien-image\n'
                    else printf 'old-image\n'; fi;;
                *) return 0;;
            esac
        }
        compose() {
            printf '%s\n' "$*" >> "$CASE/calls"
            case "$*" in
                *"ps -a -q backend"*) printf 'backend-id\n';;
                *"config --quiet"*) return 77;;
                *) return 0;;
            esac
        }
        deploy_release
    ) > "$CASE/output" 2>&1
    result=$?
    set -e
    if [[ $scenario == pending-match ]]; then
        [[ $result == 77 ]]; grep -q 'config --quiet' "$CASE/calls"
    else
        [[ $result != 0 ]]
        if [[ -f $CASE/calls ]]; then ! grep -q 'config --quiet' "$CASE/calls"; fi
    fi
    printf 'PASS %s\n' "$scenario"
done
printf '5 ownership/retry guard cases passed\n'

for mode in keep-old mixed; do
    CASE="$BASE/continuous-$mode"
    mkdir -p "$CASE/releases" "$CASE/data"
    : > "$CASE/containers"
    for round in B C D; do
        set +e
        (
            set -Eeuo pipefail
            RUNTIME=$CASE PROJECT=active-system HTTP_PORT=80
            old_release='' release='' restart_old=0 stage=initial
            trap failure EXIT
            git() { printf '%s\n' "$round"; }
            docker() {
                local last=${!#}
                case "$*" in
                    "ps -aq"*) cat "$CASE/containers";;
                    *"com.docker.compose.project"*) printf 'active-system\n';;
                    *"com.docker.compose.service"*) printf '%s\n' "${last#*-}";;
                    *".Destination"*) printf '%s\n' "$CASE/data";;
                    *".Image"*) printf '%s-image\n' "$last";;
                    "image inspect"*)
                        if [[ $last == active-system-backend:* ]]; then printf '%s-backend-image\n' "$round"
                        else printf '%s-nginx-image\n' "$round"; fi;;
                    *) return 0;;
                esac
            }
            compose() {
                printf '%s\n' "$*" >> "$CASE/calls-$round"
                case "$*" in
                    *"config --quiet"*) [[ $round != D ]] || return 77;;
                    *"config --format json"*) printf '{}\n';;
                    *"up -d"*)
                        if [[ $round == B ]]; then printf 'B-backend\nB-nginx\n' > "$CASE/containers"
                        elif [[ $mode == mixed ]]; then printf 'C-backend\nB-nginx\n' > "$CASE/containers"; fi
                        return 55;;
                    *) return 0;;
                esac
            }
            deploy_release
        ) > "$CASE/output-$round" 2>&1
        result=$?
        set -e
        if [[ $round == D ]]; then
            [[ $result == 77 ]]; grep -q 'config --quiet' "$CASE/calls-D"
        else
            [[ $result == 55 && ! -f $CASE/current ]]
            if [[ $round == B ]]; then first=$(<"$CASE/pending")
            else
                second=$(<"$CASE/pending")
                [[ $(<"$CASE/releases/$second/pending-parent") == "$first" ]]
            fi
        fi
    done
    printf 'PASS consecutive failures %s\n' "$mode"
done

for scenario in alien-project alien-service alien-image swapped-service alien-data missing cycle wrong-data; do
    CASE="$BASE/chain-$scenario"
    mkdir -p "$CASE/releases/B" "$CASE/releases/C" "$CASE/data"
    for record in B C; do
        printf '{}\n' > "$CASE/releases/$record/compose.json"
        printf '%s\n' "$CASE/data" > "$CASE/releases/$record/data-dir"
        printf '%s-backend-image\n' "$record" > "$CASE/releases/$record/backend-image"
        printf '%s-nginx-image\n' "$record" > "$CASE/releases/$record/nginx-image"
    done
    printf 'B\n' > "$CASE/releases/C/pending-parent"
    case "$scenario" in
        missing) printf 'missing\n' > "$CASE/releases/B/pending-parent";;
        cycle) printf 'C\n' > "$CASE/releases/B/pending-parent";;
        wrong-data) printf '/wrong\n' > "$CASE/releases/B/data-dir";;
    esac
    set +e
    (
        set -Eeuo pipefail
        RUNTIME=$CASE PROJECT=active-system DATA_DIR="$CASE/data"
        docker() {
            case "$*" in
                *"com.docker.compose.project"*)
                    if [[ $scenario == alien-project ]]; then printf 'alien\n'; else printf 'active-system\n'; fi;;
                *"com.docker.compose.service"*)
                    if [[ $scenario == alien-service ]]; then printf 'other\n'; else printf 'backend\n'; fi;;
                *".Destination"*)
                    if [[ $scenario == alien-data ]]; then printf '/wrong\n'; else printf '%s\n' "$CASE/data"; fi;;
                *".Image"*)
                    if [[ $scenario == alien-image ]]; then printf 'alien\n'
                    elif [[ $scenario == swapped-service ]]; then printf 'B-nginx-image\n'
                    else printf 'B-backend-image\n'; fi;;
            esac
        }
        validate_pending 'backend-id' C
    ) > "$CASE/output" 2>&1
    result=$?
    set -e
    [[ $result != 0 ]]
    printf 'PASS reject %s\n' "$scenario"
done
printf '10 predecessor-chain cases passed\n'
