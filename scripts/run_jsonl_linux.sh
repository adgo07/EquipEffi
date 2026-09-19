#!/usr/bin/env bash
set -eu

PYZ_PATH="${1:-}"
if [ -n "$PYZ_PATH" ]; then
    case "$PYZ_PATH" in
        *.pyz) ;;
        *) echo "第一个参数必须是.pyz文件：$PYZ_PATH" >&2; exit 2 ;;
    esac
    [ -f "$PYZ_PATH" ] || { echo "找不到.pyz文件：$PYZ_PATH" >&2; exit 2; }
    exec python3 "$PYZ_PATH" --jsonl
fi

exec python3 -m equipeffi --jsonl
