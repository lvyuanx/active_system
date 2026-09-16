#!/usr/bin/env bash
# Shared by upgrade and explicit recovery; never source deployment credentials.
initialize() {
    ROOT=$1
    RUNTIME="$ROOT/deploy/runtime"
    SETTINGS="$ROOT/deploy/.env"
    PROJECT=active-system
    stage="初始化"
    restart_old=0
    old_release=""
    release=""
    mkdir -p "$RUNTIME/releases"
    chmod 700 "$RUNTIME" "$RUNTIME/releases"
    unset COMPOSE_FILE COMPOSE_PROJECT_NAME COMPOSE_PROFILES COMPOSE_ENV_FILES COMPOSE_PROJECT_DIRECTORY
    export COMPOSE_DISABLE_ENV_FILE=1
}

die() { printf '错误：%s\n' "$*" >&2; exit 1; }
log() { printf '[部署] %s\n' "$*"; }
compose() { docker compose --project-name "$PROJECT" --env-file /dev/null "$@"; }
saved_compose() { local record=$1; shift; compose -f "$record/compose.json" "$@"; }

acquire_lock() {
    command -v flock >/dev/null || die "缺少 flock（Linux util-linux）"
    if [[ -e /proc/$$/fd/9 && $(readlink -f "/proc/$$/fd/9") == "$RUNTIME/upgrade.lock" ]]; then
        flock -n 9 || die "另一个部署或恢复正在执行"
    else
        exec 9>"$RUNTIME/upgrade.lock"
        flock -n 9 || die "另一个部署或恢复正在执行"
    fi
}

check_dependencies() {
    stage="检查依赖"
    local cmd
    for cmd in git docker realpath mktemp sha256sum; do
        command -v "$cmd" >/dev/null || die "缺少命令：$cmd"
    done
    docker info >/dev/null 2>&1 || die "Docker daemon 不可用或当前用户无权限"
    docker compose version >/dev/null || die "需要 Docker Compose v2"
    docker compose up --help | grep -q -- --wait-timeout || die "Compose 版本不支持 --wait-timeout，请升级"
}

load_settings() {
    stage="校验配置"
    [[ -f $SETTINGS && ! -L $SETTINGS ]] || die "请先复制 deploy/.env.example 为 deploy/.env 并设置密钥"
    chmod 600 "$SETTINGS"
    local key value line n=0
    local -A seen=()
    unset SUPERUSER_USERNAME SUPERUSER_PASSWORD JWT_SECRET LOTTERY_SECURITY_CODE HTTP_PORT APP_CORS_ORIGINS
    while IFS= read -r line || [[ -n $line ]]; do
        n=$((n + 1))
        line=${line%$'\r'}
        [[ -z $line || $line == \#* ]] && continue
        [[ $line =~ ^([A-Z_]+)=(.*)$ ]] || die "配置第 $n 行必须是 KEY=value"
        key=${BASH_REMATCH[1]}; value=${BASH_REMATCH[2]}
        case "$key" in
            SUPERUSER_USERNAME|SUPERUSER_PASSWORD|JWT_SECRET|LOTTERY_SECURITY_CODE|HTTP_PORT|APP_CORS_ORIGINS) ;;
            *) die "配置第 $n 行使用未知键" ;;
        esac
        [[ ! ${seen[$key]+yes} ]] || die "配置第 $n 行键重复"
        # Deliberately restrict literals so neither Compose nor a shell can reinterpret credentials.
        [[ $value =~ ^[a-zA-Z0-9_.,:/@%+=!?~-]*$ ]] || die "配置第 $n 行包含不支持的字符（禁止引号、空格、美元符号）"
        seen[$key]=1
        export "$key=$value"
    done < "$SETTINGS"
    for key in SUPERUSER_PASSWORD JWT_SECRET LOTTERY_SECURITY_CODE; do
        value=${!key:-}
        [[ -n $value ]] || die "$key 必须填写"
        case "${value,,}" in
            *change*|*example*|*development*|password|admin|123456|secret) die "$key 不能使用示例值" ;;
        esac
    done
    [[ ${#SUPERUSER_PASSWORD} -ge 12 ]] || die "SUPERUSER_PASSWORD 至少 12 字符"
    [[ ${#JWT_SECRET} -ge 32 ]] || die "JWT_SECRET 至少 32 字符"
    [[ ${#LOTTERY_SECURITY_CODE} -ge 6 ]] || die "LOTTERY_SECURITY_CODE 至少 6 字符"
    export SUPERUSER_USERNAME=${SUPERUSER_USERNAME:-admin} HTTP_PORT=${HTTP_PORT:-80}
    export APP_CORS_ORIGINS=${APP_CORS_ORIGINS:-}
    [[ $HTTP_PORT =~ ^[1-9][0-9]{0,4}$ && $HTTP_PORT -le 65535 ]] || die "HTTP_PORT 必须是 1-65535"
}

update_source() {
    stage="拉取代码"
    local branch remote upstream sha ticket
    branch=$(git -C "$ROOT" symbolic-ref --quiet --short HEAD) || die "需要具名分支"
    remote=$(git -C "$ROOT" config --get "branch.$branch.remote") || die "当前分支没有上游"
    [[ $remote != . ]] || die "上游必须是远程仓库"
    upstream=$(git -C "$ROOT" rev-parse --abbrev-ref '@{upstream}') || die "当前分支没有上游"
    git -C "$ROOT" fetch -- "$remote"
    git -C "$ROOT" merge-base --is-ancestor HEAD "$upstream" || die "本地超前或与上游分叉，拒绝更新"
    git -C "$ROOT" merge --ff-only "$upstream"
    sha=$(git -C "$ROOT" rev-parse HEAD)
    ticket=$(mktemp "$RUNTIME/resume.XXXXXX")
    printf '%s\n%s\n' "$$" "$sha" > "$ticket"
    # exec keeps fd 9 and PID; the latest script reloads configuration under the same lock.
    exec bash "$ROOT/upgrade.sh" --resume "$ticket"
}

validate_resume() {
    local ticket=$1 pid sha
    [[ $ticket == "$RUNTIME"/resume.* && -f $ticket && ! -L $ticket ]] || die "无效续跑凭据"
    [[ $(readlink -f "/proc/$$/fd/9") == "$RUNTIME/upgrade.lock" ]] || die "续跑锁丢失"
    { IFS= read -r pid; IFS= read -r sha; } < "$ticket"
    [[ $pid == "$$" && $sha == "$(git -C "$ROOT" rev-parse HEAD)" ]] || die "续跑版本不匹配"
    rm -- "$ticket"
}

current_record() {
    [[ -f $RUNTIME/current ]] || return 0
    local name
    name=$(<"$RUNTIME/current")
    [[ $name =~ ^[a-zA-Z0-9-]+$ && -f $RUNTIME/releases/$name/compose.json ]] || die "成功记录损坏"
    printf '%s' "$RUNTIME/releases/$name"
}

failure() {
    local status=$?
    trap - EXIT INT TERM
    if [[ $status -ne 0 ]]; then
        if [[ $restart_old == 1 && -n $old_release ]]; then
            log "备份阶段失败，恢复旧后端"
            saved_compose "$old_release" start backend && wait_backend "$old_release" \
                || printf '严重：旧后端恢复失败，请立即检查容器。\n' >&2
        fi
        printf '失败阶段：%s；退出码：%s\n' "$stage" "$status" >&2
        printf '诊断：docker compose -p active-system -f %q ps\n' "${release:-$old_release}/compose.json" >&2
        printf '日志：docker compose -p active-system -f %q logs --tail=100\n' \
            "${release:-$old_release}/compose.json" >&2
        printf '记录保留于 %s；人工恢复见 deploy/README.md。\n' "$RUNTIME" >&2
    fi
    exit "$status"
}

wait_backend() {
    local record=$1 id state count
    id=$(saved_compose "$record" ps -a -q backend)
    [[ -n $id ]] || return 1
    for count in {1..60}; do
        state=$(docker inspect --format '{{.State.Health.Status}}' "$id") || return 1
        [[ $state == healthy ]] && return 0
        sleep 2
    done
    return 1
}
