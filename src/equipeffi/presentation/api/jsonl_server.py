"""无框架 JSON Lines 适配器。

它只负责把标准输入/输出转换成 :class:`ApplicationApi` 调用，不承载设备规则、
Excel 或 Tk 依赖。每行一个 JSON 对象，响应也严格为一行 JSON；因此 Linux 服务、
Android JNI/进程桥接和桌面调试都可以复用同一协议。

请求格式：``{"op":"evaluate","payload":{...}}``。支持 ``status``、
``device_types``、``schema``、``evaluate``、``evaluate_v4``、``evaluate_batch``
和 ``quit``。发生单行错误时只返回该行错误，不终止后续请求。
"""
from __future__ import annotations

import json
from typing import Any, TextIO

from .application_api import ApplicationApi

PROTOCOL_VERSION = "1.0"
MAX_REQUEST_LINE_BYTES = 4 * 1024 * 1024

def _response(*, op: str, result: Any = None, error: dict[str, str] | None = None, request_id: Any = None) -> str:
    body: dict[str, Any] = {"protocol_version": PROTOCOL_VERSION, "ok": error is None, "op": op}
    if request_id is not None:
        body["request_id"] = request_id
    if error is None:
        body["result"] = result
    else:
        body["error"] = error
    return json.dumps(body, ensure_ascii=False, separators=(",", ":"))


def handle_request(api: ApplicationApi, request: Any) -> tuple[str, bool]:
    """处理一个已解析JSON请求，返回``(响应文本, 是否结束)``。"""

    if not isinstance(request, dict):
        return _response(op="", error={"type": "invalid_request", "message": "请求必须是JSON对象"}), False
    op = str(request.get("op", "")).strip()
    request_id = request.get("request_id")
    try:
        request_version = request.get("protocol_version")
        if request_version not in (None, PROTOCOL_VERSION):
            raise ValueError(f"协议版本不兼容：{request_version}")
        if op == "status":
            return _response(op=op, result=api.status(), request_id=request_id), False
        if op == "device_types":
            return _response(op=op, result=api.device_types(), request_id=request_id), False
        if op == "schema":
            return _response(op=op, result=api.schema(str(request.get("device_type", ""))), request_id=request_id), False
        if op in {"evaluate", "evaluate_v4", "evaluate_batch"}:
            payload = request.get("payload")
            if not isinstance(payload, dict):
                raise ValueError("payload必须是JSON对象")
            method = getattr(api, op)
            return _response(op=op, result=method(payload), request_id=request_id), False
        if op == "quit":
            return _response(op=op, result={"stopped": True}, request_id=request_id), True
        raise ValueError(f"未知操作op: {op or '<空>'}")
    except Exception as exc:  # 单行错误不得中断长连接/桥接进程
        return _response(op=op, error={"type": type(exc).__name__, "message": str(exc)}, request_id=request_id), False


def run_jsonl(api: ApplicationApi, input_stream: TextIO, output_stream: TextIO) -> None:
    """从输入流读取请求并逐行写出响应，立即flush以便进程桥接。"""

    for line in input_stream:
        if not line.strip():
            continue
        if len(line.encode("utf-8")) > MAX_REQUEST_LINE_BYTES:
            output_stream.write(
                _response(
                    op="",
                    error={
                        "type": "request_too_large",
                        "message": f"单行请求不得超过{MAX_REQUEST_LINE_BYTES}字节",
                    },
                )
                + "\n"
            )
            output_stream.flush()
            continue
        try:
            request = json.loads(line)
        except json.JSONDecodeError as exc:
            output_stream.write(_response(op="", error={"type": "invalid_json", "message": str(exc)}) + "\n")
            output_stream.flush()
            continue
        response, stopped = handle_request(api, request)
        output_stream.write(response + "\n")
        output_stream.flush()
        if stopped:
            break
