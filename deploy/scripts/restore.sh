#!/usr/bin/env bash
set -Eeuo pipefail
umask 077

main() {
    local root attempt target name image existing
    root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
    source "$root/deploy/scripts/common.sh"
    source "$root/deploy/scripts/release.sh"
    initialize "$root"
    acquire_lock
    trap failure EXIT
    trap 'exit 130' INT
    trap 'exit 143' TERM
    check_dependencies
    [[ $# -eq 1 && $1 =~ ^[a-zA-Z0-9-]+$ ]] || die "用法：bash deploy/scripts/restore.sh <带备份的发布尝试名>"
    attempt="$RUNTIME/releases/$1"
    [[ -f $attempt/data.tar.gz && -f $attempt/restore-release ]] || die "该尝试没有完整备份或旧版本记录"
    target=$(<"$attempt/restore-release")
    [[ $target =~ ^[a-zA-Z0-9-]+$ ]] || die "旧版本记录无效"
    old_release="$RUNTIME/releases/$target"
    [[ -f $old_release/compose.json ]] || die "旧版本配置不存在"
    name="restored-$(date -u +%Y%m%dT%H%M%SZ)-$$"
    release="$RUNTIME/releases/$name"
    mkdir "$release" "$RUNTIME/$name"
    cp "$old_release/"{compose.json,commit,backend-image,nginx-image} "$release/"
    printf '%s\n' "$RUNTIME/$name" > "$release/data-dir"
    image=$(<"$release/backend-image")
    docker image inspect "$image" >/dev/null
    docker image inspect "$(<"$release/nginx-image")" >/dev/null
    stage="校验并恢复到全新数据目录"
    artifact_tool "$image" restore "releases/$1" "$name"
    artifact_tool "$image" config "releases/$name" "$RUNTIME/$name"
    saved_compose "$release" config --quiet
    stage="停止现有后端并保留失败现场"
    # Existing files are never modified: the replacement container mounts a new directory.
    existing=$(docker ps -aq --filter "label=com.docker.compose.project=$PROJECT" \
        --filter label=com.docker.compose.service=backend)
    [[ -z $existing ]] || docker stop -t 30 $existing
    stage="启动恢复版本"
    saved_compose "$release" up -d --no-build --pull never --force-recreate --wait --wait-timeout 180
    probe_release "$release"
    activate_record "$name"
    log "恢复完成；原数据保留，后续 upgrade.sh 将使用恢复后的数据目录。"
    log "恢复版本凭据与端口来自旧发布配置；下次升级前请核对 deploy/.env。"
}
main "$@"
