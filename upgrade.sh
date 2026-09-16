#!/usr/bin/env bash
set -Eeuo pipefail
umask 077

# Parse the whole entry before Git can replace this file during an update.
main() {
    local root
    root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
    source "$root/deploy/scripts/common.sh"
    initialize "$root"
    acquire_lock
    trap failure EXIT
    trap 'exit 130' INT
    trap 'exit 143' TERM
    check_dependencies
    load_settings
    stage="检查工作树"
    [[ -z $(git -C "$ROOT" status --porcelain --untracked-files=all) ]] || die "工作树有本地修改或未跟踪文件"
    if [[ $# -eq 0 ]]; then
        update_source
    elif [[ $# -eq 2 && $1 == --resume ]]; then
        validate_resume "$2"
    else
        die "不支持的参数"
    fi
    source "$ROOT/deploy/scripts/release.sh"
    deploy_release
}
main "$@"
