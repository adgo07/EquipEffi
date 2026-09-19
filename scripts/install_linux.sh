#!/usr/bin/env bash
set -eu

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
WHEEL_PATH="${1:-}"
INSTALL_DIR="${2:-$HOME/.local/share/equipeffi}"

if [ -z "$WHEEL_PATH" ]; then
    WHEEL_PATH="$(find "$SCRIPT_DIR/../dist" -maxdepth 1 -type f -name 'equipeffi-*.whl' -print 2>/dev/null | sort | tail -n 1 || true)"
fi
if [ -z "$WHEEL_PATH" ] || [ ! -f "$WHEEL_PATH" ]; then
    echo "未找到wheel，请将 equipeffi-*.whl 作为第一个参数传入" >&2
    exit 2
fi
case "$WHEEL_PATH" in
    *.whl) ;;
    *) echo "第一个参数必须是.whl文件：$WHEEL_PATH" >&2; exit 2 ;;
esac

mkdir -p "$INSTALL_DIR"
VENV="$INSTALL_DIR/.venv"
if [ ! -x "$VENV/bin/python" ]; then
    python3 -m venv "$VENV"
fi
"$VENV/bin/python" -m pip install --no-deps --no-index --upgrade "$WHEEL_PATH"

echo "EquipEffi已安装到：$INSTALL_DIR"
echo "启动核心CLI：$VENV/bin/python -m equipeffi --list-device-types"
echo "启动窗口（系统提供Tk时）：$VENV/bin/python -m equipeffi --gui"
