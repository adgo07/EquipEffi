#!/usr/bin/env bash
set -eu

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
DRY_RUN=0
if [ "${1:-}" = "--dry-run" ]; then
    DRY_RUN=1
    shift
fi
WHEEL_PATH="${1:-}"
INSTALL_DIR="${2:-$HOME/.local/share/equipeffi}"
HOST_VALUE="${3:-127.0.0.1}"
PORT_VALUE="${4:-8765}"

if [ "$DRY_RUN" -eq 0 ] && { ! command -v systemctl >/dev/null 2>&1 || ! systemctl --user show-environment >/dev/null 2>&1; }; then
    echo "当前用户没有可用的systemd用户会话，未安装服务；可直接运行run_web_linux.sh" >&2
    exit 3
fi
case "$PORT_VALUE" in
    ''|*[!0-9]*) echo "端口必须是数字：$PORT_VALUE" >&2; exit 2 ;;
esac
if [ "$PORT_VALUE" -lt 1 ] || [ "$PORT_VALUE" -gt 65535 ]; then
    echo "端口范围必须为1～65535：$PORT_VALUE" >&2
    exit 2
fi

if [ "$DRY_RUN" -eq 0 ] && [ -z "$WHEEL_PATH" ]; then
    WHEEL_PATH="$(find "$SCRIPT_DIR/../outputs" -maxdepth 2 -type f -name 'equipeffi-*.whl' -print 2>/dev/null | sort | tail -n 1 || true)"
fi
if [ "$DRY_RUN" -eq 0 ] && { [ -z "$WHEEL_PATH" ] || [ ! -f "$WHEEL_PATH" ]; }; then
    echo "未找到wheel，请将equipeffi-*.whl作为第一个参数传入" >&2
    exit 2
fi

PYTHON_BIN="$INSTALL_DIR/.venv/bin/python"

TEMPLATE="$SCRIPT_DIR/equipeffi-web.service.template"
[ -f "$TEMPLATE" ] || { echo "缺少服务模板：$TEMPLATE" >&2; exit 1; }

render_unit() {
    sed \
        -e "s|__EQUIPEFFI_PYTHON__|$PYTHON_BIN|g" \
        -e "s|__EQUIPEFFI_HOST__|$HOST_VALUE|g" \
        -e "s|__EQUIPEFFI_PORT__|$PORT_VALUE|g" \
        "$TEMPLATE"
}

if [ "$DRY_RUN" -eq 1 ]; then
    echo "# dry-run：不会创建目录、虚拟环境或systemd服务"
    render_unit
    exit 0
fi

# 先复用通用离线安装器，安装失败时不创建服务单元。
sh "$SCRIPT_DIR/install_linux.sh" "$WHEEL_PATH" "$INSTALL_DIR"
if [ ! -x "$PYTHON_BIN" ]; then
    echo "安装后未找到Python入口：$PYTHON_BIN" >&2
    exit 1
fi

USER_CONFIG="${XDG_CONFIG_HOME:-$HOME/.config}"
UNIT_DIR="$USER_CONFIG/systemd/user"
UNIT_PATH="$UNIT_DIR/equipeffi-web.service"
mkdir -p "$UNIT_DIR"
if [ -e "$UNIT_PATH" ]; then
    echo "服务单元已存在，为避免覆盖用户配置而停止：$UNIT_PATH" >&2
    exit 4
fi

TEMP_UNIT="$UNIT_PATH.tmp.$$"
trap 'rm -f "$TEMP_UNIT"' EXIT
render_unit > "$TEMP_UNIT"
mv "$TEMP_UNIT" "$UNIT_PATH"
trap - EXIT

systemctl --user daemon-reload
systemctl --user enable --now equipeffi-web.service
echo "EquipEffi Web服务已安装并启动：$UNIT_PATH"
echo "访问地址：http://$HOST_VALUE:$PORT_VALUE/"
