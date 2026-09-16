#!/usr/bin/env bash
artifact_tool() {
    local image=$1; shift
    docker run --rm --entrypoint python \
        --mount "type=bind,source=$ROOT/deploy/scripts/artifacts.py,target=/tool.py,readonly" \
        --mount "type=bind,source=$RUNTIME,target=/runtime" "$image" /tool.py "$@"
}

backup_data() {
    local record=$1 output=$2 image data id running
    image=$(<"$record/backend-image")
    data=$(<"$record/data-dir")
    restart_old=1
    saved_compose "$record" stop -t 30 backend
    id=$(saved_compose "$record" ps -a -q backend)
    [[ -n $id ]] || die "找不到旧后端，不能确认数据已停止写入"
    running=$(docker inspect --format '{{.State.Running}}' "$id")
    [[ $running == false ]] || die "后端仍在运行，拒绝备份"
    docker run --rm --entrypoint python \
        --mount "type=bind,source=$ROOT/deploy/scripts/artifacts.py,target=/tool.py,readonly" \
        --mount "type=bind,source=$data,target=/source,readonly" \
        --mount "type=bind,source=$output,target=/output" "$image" /tool.py backup
}

probe_release() {
    local record=$1 path id state
    for service in backend nginx; do
        id=$(saved_compose "$record" ps -q "$service")
        [[ -n $id ]] || die "$service 未启动"
        state=$(docker inspect --format '{{.State.Health.Status}}' "$id")
        [[ $state == healthy ]] || die "$service 未健康"
    done
    for path in /admin/ /screen/ /user/ /api/v1/health; do
        saved_compose "$record" exec -T nginx wget -q -O /dev/null "http://127.0.0.1$path"
    done
}

activate_record() {
    local name=$1
    if [[ -f $RUNTIME/current ]]; then
        cp "$RUNTIME/current" "$RUNTIME/previous.tmp"
        mv "$RUNTIME/previous.tmp" "$RUNTIME/previous"
    fi
    printf '%s\n' "$name" > "$RUNTIME/current.tmp"
    mv "$RUNTIME/current.tmp" "$RUNTIME/current"
    printf '%s\n' "$name" > "$RUNTIME/pending.tmp"
    mv "$RUNTIME/pending.tmp" "$RUNTIME/pending"
}

validate_pending() {
    local existing=$1 name=$2 record id image service project mount item
    local -A visited=() allowed=()
    while [[ -n $name ]]; do
        [[ $name =~ ^[a-zA-Z0-9-]+$ && ! ${visited[$name]+yes} ]] || die "未完成发布前驱链损坏或循环"
        visited[$name]=1
        record="$RUNTIME/releases/$name"
        [[ -d $record && ! -L $record ]] || die "未完成发布记录目录缺失或无效"
        for item in compose.json data-dir backend-image nginx-image; do
            [[ -f $record/$item && ! -L $record/$item ]] || die "未完成发布记录文件缺失或无效"
        done
        [[ $(<"$record/data-dir") == "$DATA_DIR" ]] || die "未完成发布前驱链数据目录不一致"
        for service in backend nginx; do
            image=$(<"$record/$service-image")
            [[ -n $image ]] || die "未完成发布镜像记录为空"
            allowed["$service|$image"]=1
        done
        if [[ -e $record/pending-parent ]]; then
            [[ -f $record/pending-parent && ! -L $record/pending-parent ]] || die "前驱引用无效"
            name=$(<"$record/pending-parent")
            [[ -n $name ]] || die "前驱引用为空"
        else
            name=""
        fi
    done
    for id in $existing; do
        project=$(docker inspect --format '{{index .Config.Labels "com.docker.compose.project"}}' "$id")
        service=$(docker inspect --format '{{index .Config.Labels "com.docker.compose.service"}}' "$id")
        [[ $project == "$PROJECT" && ( $service == backend || $service == nginx ) ]] \
            || die "遗留容器项目或服务不属于本部署"
        image=$(docker inspect --format '{{.Image}}' "$id")
        [[ ${allowed["$service|$image"]+yes} ]] || die "容器镜像不属于受控发布链的对应服务"
        if [[ $service == backend ]]; then
            mount=$(docker inspect --format \
                '{{range .Mounts}}{{if eq .Destination "/app/data"}}{{.Source}}{{end}}{{end}}' "$id")
            [[ $mount == "$DATA_DIR" ]] || die "遗留后端数据挂载不匹配"
        fi
    done
}

deploy_release() {
    local sha name config backend_image nginx_image existing pending="" id image
    stage="检查既有部署"
    old_release=$(current_record)
    if [[ -z $old_release ]]; then
        DATA_DIR="$RUNTIME/data"
        existing=$(docker ps -aq --filter "label=com.docker.compose.project=$PROJECT")
        if [[ -f $RUNTIME/pending ]]; then
            pending=$(<"$RUNTIME/pending")
            [[ -n $pending ]] || die "未完成发布引用为空"
            validate_pending "$existing" "$pending"
        elif [[ -n $existing ]]; then
            die "发现无发布记录的容器，不自动接管"
        fi
    else
        DATA_DIR=$(<"$old_release/data-dir")
        [[ $DATA_DIR == "$RUNTIME/data" || $DATA_DIR == "$RUNTIME"/restored-* ]] || die "数据目录记录异常"
        [[ -d $DATA_DIR && $(realpath "$DATA_DIR") == "$DATA_DIR" ]] || die "持久化数据目录丢失或被替换"
        id=$(saved_compose "$old_release" ps -a -q backend)
        [[ -n $id ]] || die "成功记录的后端不存在，请先人工恢复"
        image=$(docker inspect --format '{{.Image}}' "$id")
        [[ $image == "$(<"$old_release/backend-image")" ]] \
            || die "运行实例与成功记录不一致，请先恢复失败尝试，避免备份与旧镜像错配"
    fi
    export DATA_DIR
    sha=$(git -C "$ROOT" rev-parse HEAD)
    name="${sha}-$(date -u +%Y%m%dT%H%M%SZ)-$$"
    export RELEASE_TAG=$name
    release="$RUNTIME/releases/$name"
    mkdir "$release"
    printf '%s\n' "$sha" > "$release/commit"
    printf '%s\n' "$DATA_DIR" > "$release/data-dir"
    [[ -z $old_release ]] || printf '%s\n' "${old_release##*/}" > "$release/restore-release"
    config="$ROOT/deploy/compose/docker-compose.yml"
    stage="校验 Compose 配置"
    compose -f "$config" config --quiet
    compose -f "$config" config --format json > "$release/compose.json"
    stage="构建镜像"
    compose -f "$config" build backend nginx
    backend_image=$(docker image inspect --format '{{.Id}}' "active-system-backend:$name")
    nginx_image=$(docker image inspect --format '{{.Id}}' "active-system-nginx:$name")
    printf '%s\n' "$backend_image" > "$release/backend-image"
    printf '%s\n' "$nginx_image" > "$release/nginx-image"
    artifact_tool "$backend_image" pin "releases/$name"
    stage="校验 Nginx 配置"
    docker run --rm --add-host backend:127.0.0.1 "$nginx_image" nginx -t
    mkdir -p "$DATA_DIR"
    if [[ -n $old_release ]]; then
        stage="备份旧数据"
        backup_data "$old_release" "$release"
    fi
    stage="启动新版本"
    [[ -z $pending ]] || printf '%s\n' "$pending" > "$release/pending-parent"
    printf '%s\n' "$name" > "$RUNTIME/pending.tmp"
    mv "$RUNTIME/pending.tmp" "$RUNTIME/pending"
    restart_old=0
    saved_compose "$release" up -d --no-build --pull never --force-recreate --wait --wait-timeout 180
    stage="检查站点"
    probe_release "$release"
    activate_record "$name"
    log "部署成功：$sha；访问 http://服务器地址:$HTTP_PORT/admin/"
    log "发布记录：$release"
}
