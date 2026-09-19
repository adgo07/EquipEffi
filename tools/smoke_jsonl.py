"""对 JSON Lines 桥接接口执行跨平台协议冒烟检查。

该工具只依赖 Python 标准库，不解析 Excel，也不初始化 Tk。它既可检查源码
模块，也可检查便携 ``.pyz`` 或 PyInstaller 原生可执行文件，便于 Linux、
Windows 和 Android 外层桥接在发布前复用同一组最小验收请求。
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any, Sequence


ROOT = Path(__file__).resolve().parents[1]
MOTOR_VALUES = {
    "category": "三相异步电动机（一般用途）",
    "rated_voltage": "0.4",
    "rated_power": 7.5,
    "poles": 4,
    "rated_speed": 1480,
    "efficiency": 98,
}
PMSM_VALUES = {
    "category": "变频调速永磁同步电动机",
    "rated_power": 7.5,
    "rated_speed": 1500,
    "efficiency_at_90pct_speed": 98,
}
PMSM_NO_DATA_VALUES = {
    "category": "异步起动永磁同步电动机",
    "rated_power": 55,
    "poles": 12,
    "efficiency": 95,
}


def _command(*, python_path: str, pyz: Path | None, executable: Path | None, isolated: bool = False) -> list[str]:
    if pyz is not None and executable is not None:
        raise ValueError("--pyz和--executable不能同时指定")
    if pyz is not None:
        return [python_path, "-S", str(pyz), "--jsonl"] if isolated else [python_path, str(pyz), "--jsonl"]
    if executable is not None:
        return [str(executable), "--jsonl"]
    return [python_path, "-S", "-m", "equipeffi", "--jsonl"] if isolated else [python_path, "-m", "equipeffi", "--jsonl"]


def run_smoke(
    *,
    python_path: str = sys.executable,
    pyz: Path | None = None,
    executable: Path | None = None,
    timeout: float = 20.0,
    root: Path = ROOT,
    isolated: bool = False,
) -> dict[str, Any]:
    command = _command(python_path=python_path, pyz=pyz, executable=executable, isolated=isolated)
    environment = os.environ.copy()
    source = str((Path(root) / "src").resolve())
    environment["PYTHONPATH"] = source + (os.pathsep + environment["PYTHONPATH"] if environment.get("PYTHONPATH") else "")
    requests = [
        {"request_id": "smoke-status", "op": "status"},
        {"request_id": "smoke-schema", "op": "schema", "device_type": "blower"},
        {"request_id": "smoke-motor", "op": "evaluate", "payload": {"record_id": "SMOKE-M", "device_type": "motor", "values": MOTOR_VALUES}},
        {"request_id": "smoke-batch", "op": "evaluate_batch", "payload": {"records": [{"record_id": "SMOKE-B", "device_type": "motor", "values": MOTOR_VALUES}]}},
        {"request_id": "smoke-pmsm", "op": "evaluate", "payload": {"record_id": "SMOKE-P", "device_type": "motor_pmsm", "values": PMSM_VALUES}},
        {"request_id": "smoke-pmsm-no-data", "op": "evaluate", "payload": {"record_id": "SMOKE-P-NODATA", "device_type": "motor_pmsm", "values": PMSM_NO_DATA_VALUES}},
        {"request_id": "smoke-quit", "op": "quit"},
    ]
    # 第一行故意不是JSON，确认桥接层按协议逐行报错而不会终止进程。
    payload = "{this-is-not-json}\n" + "".join(json.dumps(item, ensure_ascii=False) + "\n" for item in requests)
    completed = subprocess.run(
        command,
        cwd=str(Path(root).resolve()),
        input=payload,
        text=True,
        capture_output=True,
        env=environment,
        timeout=timeout,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(f"JSONL进程退出码为{completed.returncode}: {completed.stderr.strip()}")
    lines = [line for line in completed.stdout.splitlines() if line.strip()]
    if len(lines) != len(requests) + 1:
        raise RuntimeError(f"JSONL响应数量错误：期望{len(requests) + 1}，实际{len(lines)}；stderr={completed.stderr.strip()}")
    responses = [json.loads(line) for line in lines]
    malformed = responses[0]
    if malformed.get("ok") is not False or malformed.get("error", {}).get("type") != "invalid_json":
        raise RuntimeError(f"非法JSON行未按协议返回错误：{malformed}")
    for request, response in zip(requests, responses[1:]):
        if response.get("protocol_version") != "1.0":
            raise RuntimeError(f"协议版本错误：{response}")
        if response.get("request_id") != request["request_id"]:
            raise RuntimeError(f"request_id未原样回传：{response}")
        if response.get("ok") is not True:
            raise RuntimeError(f"JSONL请求失败：{response}")
    status = responses[1]["result"]
    schema = responses[2]["result"]
    motor = responses[3]["result"]
    batch = responses[4]["result"]
    pmsm = responses[5]["result"]
    pmsm_no_data = responses[6]["result"]
    quit_result = responses[7]["result"]
    if status.get("public_device_type_count") != 15:
        raise RuntimeError(f"公共设备类型数量错误：{status.get('public_device_type_count')}")
    pmsm_status = next((item.get("status") for item in status.get("standard_packs", []) if item.get("device_type") == "motor_pmsm"), None)
    if pmsm_status != "active":
        raise RuntimeError(f"PMSM标准状态异常：{pmsm_status}")
    if schema.get("allowed_conclusions") != ["不在范围", "无法判定", "淘汰", "未达标", "节能评价值", "能效限定值"]:
        raise RuntimeError(f"设备专用结论集合错误：{schema.get('allowed_conclusions')}")
    result_fields = schema.get("result_fields")
    result_field_ids = {item.get("field_id") for item in result_fields} if isinstance(result_fields, list) else set()
    if not {"standard_code", "reference_grade", "conclusion", "auto_note"}.issubset(result_field_ids):
        raise RuntimeError(f"锁定结果字段契约不完整：{result_fields}")
    if motor.get("conclusion") not in {"1级", "2级", "3级", "未达标"}:
        raise RuntimeError(f"电动机示例结论异常：{motor.get('conclusion')}")
    if not isinstance(batch, list) or len(batch) != 1 or batch[0].get("conclusion") != motor.get("conclusion"):
        raise RuntimeError(f"批量判定响应异常：{batch}")
    if motor.get("trace_schema_version") != "1.0" or not all(
        step.get("step_sequence") == index
        for index, step in enumerate(motor.get("trace", []), start=1)
    ):
        raise RuntimeError("判定轨迹协议字段异常")
    if pmsm.get("conclusion") not in {"1级", "2级", "3级", "未达标", "不在范围", "无法判定"}:
        raise RuntimeError(f"PMSM示例结论异常：{pmsm.get('conclusion')}")
    if pmsm_no_data.get("conclusion") != "不在范围":
        raise RuntimeError(f"PMSM表1/55 kW/12极无数据结论异常：{pmsm_no_data.get('conclusion')}")
    if len(pmsm_no_data.get("lookups", [])) != 3 or not all(item.get("no_data") for item in pmsm_no_data["lookups"]):
        raise RuntimeError("PMSM表1/55 kW/12极未保留三条无数据查表记录")
    if quit_result.get("stopped") is not True:
        raise RuntimeError("quit响应异常")
    return {
        "command": command,
        "isolated": isolated,
        "protocol_version": "1.0",
        "public_device_type_count": status["public_device_type_count"],
        "schema_conclusions_verified": True,
        "schema_result_fields_verified": True,
        "pmsm_status_verified": pmsm_status,
        "motor_conclusion": motor["conclusion"],
        "pmsm_conclusion": pmsm["conclusion"],
        "pmsm_no_data_conclusion": pmsm_no_data["conclusion"],
        "responses": len(responses),
        "malformed_line_continued": True,
        "passed": True,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="EquipEffi JSONL跨平台协议冒烟检查")
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--python", dest="python_path", default=sys.executable)
    parser.add_argument("--pyz", type=Path)
    parser.add_argument("--executable", type=Path)
    parser.add_argument("--isolated", action="store_true", help="使用Python -S运行，检查无site依赖的无Tk/无第三方环境")
    parser.add_argument("--timeout", type=float, default=20.0)
    args = parser.parse_args(argv)
    try:
        result = run_smoke(
            python_path=args.python_path,
            pyz=args.pyz,
            executable=args.executable,
            timeout=args.timeout,
            root=args.root,
            isolated=args.isolated,
        )
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError, json.JSONDecodeError) as exc:
        print(json.dumps({"passed": False, "error": str(exc)}, ensure_ascii=False, indent=2))
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
