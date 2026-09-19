#!/usr/bin/env bash
set -eu

HOST_VALUE="${EQUIPEFFI_WEB_HOST:-127.0.0.1}"
PORT_VALUE="${EQUIPEFFI_WEB_PORT:-8765}"
OPEN_BROWSER="${EQUIPEFFI_WEB_OPEN_BROWSER:-0}"
PYZ_PATH=""

if [ "${1:-}" = "--pyz" ]; then
    PYZ_PATH="${2:-}"
    if [ -z "$PYZ_PATH" ]; then
        echo "--pyz后必须提供.pyz文件路径" >&2
        exit 2
    fi
    case "$PYZ_PATH" in
        *.pyz) ;;
        *) echo "--pyz参数必须指向.pyz文件：$PYZ_PATH" >&2; exit 2 ;;
    esac
    [ -f "$PYZ_PATH" ] || { echo "找不到.pyz文件：$PYZ_PATH" >&2; exit 2; }
    shift 2
fi

if [ "$#" -ge 1 ]; then HOST_VALUE="$1"; fi
if [ "$#" -ge 2 ]; then PORT_VALUE="$2"; fi
if [ "$#" -gt 2 ]; then
    echo "用法：sh scripts/run_web_linux.sh [--pyz file.pyz] [host] [port]" >&2
    exit 2
fi

if [ -n "$PYZ_PATH" ]; then
    if [ "$OPEN_BROWSER" = "1" ] || [ "$OPEN_BROWSER" = "true" ]; then
        exec python3 "$PYZ_PATH" --web --host "$HOST_VALUE" --port "$PORT_VALUE" --open-browser
    fi
    exec python3 "$PYZ_PATH" --web --host "$HOST_VALUE" --port "$PORT_VALUE"
fi

if [ "$OPEN_BROWSER" = "1" ] || [ "$OPEN_BROWSER" = "true" ]; then
    exec python3 -m equipeffi --web --host "$HOST_VALUE" --port "$PORT_VALUE" --open-browser
fi
exec python3 -m equipeffi --web --host "$HOST_VALUE" --port "$PORT_VALUE"
