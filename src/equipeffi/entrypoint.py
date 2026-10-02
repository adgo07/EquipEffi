"""跨平台命令入口。

该入口只依赖公共应用API，不依赖Tk窗口；桌面窗口可由 ``--gui`` 或纯标准库
浏览器窗口 ``--web`` 提供，Linux服务或安卓桥接层可以直接复用这里的JSON接口。
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
import json
import os
from pathlib import Path
import sys
from typing import Sequence

from .composition import create_application_api
from .domain.common.enums import EliminationScope
from .domain.evaluation.device_specs import get_device_spec
from .domain.evaluation.device_types import PUBLIC_DEVICE_TYPES, profiles_for_public_type, public_device_types
from .presentation.api.application_api import ApplicationApi


def _project_root() -> Path:
    configured = os.environ.get("EQUIPEFFI_PROJECT_ROOT", "")
    if configured:
        return Path(configured).resolve()
    here = Path(__file__).resolve()
    for candidate in (here.parent, *here.parents):
        if (candidate / "src/equipeffi/standard_manifest.json").is_file():
            return candidate
    return Path.cwd().resolve()


def _api(*, load_template: bool = True) -> ApplicationApi:
    # Compatibility helper for tests and callers.  Its historical default
    # keeps the full V4 schema available; the command-line path below uses the
    # lazy core default for JSON/status/device-list requests.
    api, _contract, _resource_manager = create_application_api(
        project_root=_project_root(), load_template=load_template
    )
    return api


def _public_example(device_type: str) -> dict[str, object]:
    """Return a safe, documented example for a public 15-class type."""

    if device_type == "centrifugal_fan":
        # 通风机评价器的公共示例使用V4字段名；旧的flow/fan_pressure等
        # 别名不能满足机号、压力系数和比转速的查表入口。
        return {"category": "离心通风机", "machine_no": 10, "fan_efficiency": 80, "pressure_coefficient": 0.5, "specific_speed": 40}
    if device_type == "axial_fan":
        return {"category": "轴流通风机", "machine_no": 10, "fan_efficiency": 80, "pressure_coefficient": 0.5, "hub_ratio": 0.5}
    if device_type == "motor":
        return {"category": "三相异步电动机（一般用途）", "rated_voltage": "0.4", "rated_power": 7.5, "poles": 4, "rated_speed": 1480, "efficiency": 98}
    if device_type == "centrifugal_pump":
        return {
            "category": "单级单吸清水离心泵",
            "suction": "单吸",
            "stages": "1",
            "flow": "100",
            "head": "50",
            "speed": "2900",
            "efficiency": "80",
        }
    profiles = profiles_for_public_type(device_type)
    if not profiles:
        return {}
    example = get_device_spec(profiles[0]).get("example", {})
    return dict(example) if isinstance(example, dict) else {}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="EquipEffi 15类设备能效公共接口")
    parser.add_argument("--device-type", choices=PUBLIC_DEVICE_TYPES)
    parser.add_argument("--v4-sheet", help="V4设备sheet名称；与--device-type二选一")
    parser.add_argument("--record-id", default="CLI-001")
    parser.add_argument("--as-of", default="2026-08-23", help="判定基准日期，格式YYYY-MM-DD")
    parser.add_argument("--json", dest="json_text", help="设备参数JSON对象")
    parser.add_argument("--batch-json", dest="batch_json_text", help="批量判定JSON对象（含records数组）")
    parser.add_argument("--schema", action="store_true", help="输出V4字段契约")
    parser.add_argument("--example", action="store_true", help="输出指定公共设备类型的输入示例")
    parser.add_argument("--list-device-types", action="store_true", help="列出15类公共类型")
    parser.add_argument("--status", action="store_true", help="输出标准包和淘汰目录能力状态")
    parser.add_argument("--jsonl", action="store_true", help="启动JSON Lines标准输入/输出服务（每行一个请求）")
    parser.add_argument("--web", action="store_true", help="启动纯标准库浏览器窗口（HTTP表单）")
    parser.add_argument("--host", default="127.0.0.1", help="--web监听地址")
    parser.add_argument("--port", type=int, default=8765, help="--web监听端口")
    parser.add_argument("--open-browser", action="store_true", help="--web启动后打开默认浏览器")
    parser.add_argument("--audit-template", help="只读审计V4工作簿结构、保护、公式和禁用字段")
    parser.add_argument("--elimination-scope", choices=[item.value for item in EliminationScope], default=EliminationScope.MOTOR_BATCHES_1_4.value)
    parser.add_argument("--gui", action="store_true", help="从源码工作区转交桌面窗口入口")
    args = parser.parse_args(argv)

    if args.jsonl and any((args.batch_json_text, args.list_device_types, args.status, args.schema, args.example, args.audit_template, args.gui, args.web, args.json_text, args.device_type, args.v4_sheet)):
        parser.error("--jsonl不能与其他输入或操作选项同时使用")
    if args.web and any((args.batch_json_text, args.list_device_types, args.status, args.schema, args.example, args.audit_template, args.gui, args.json_text, args.device_type, args.v4_sheet)):
        parser.error("--web不能与其他输入或操作选项同时使用")
    if args.batch_json_text and (args.list_device_types or args.status or args.schema or args.example or args.audit_template or args.gui or args.web):
        parser.error("--batch-json不能与--list-device-types、--status、--schema、--example、--audit-template或--gui同时使用")

    if args.gui:
        # 使用包内启动器，避免安装wheel后依赖仓库根目录main.py。
        from .presentation.desktop.launcher import launch_packaged_gui
        launch_packaged_gui()
        return 0

    if args.audit_template:
        # Template auditing is an Excel-adapter operation and does not need to
        # construct or load the evaluation API first.
        from .infrastructure.excel.v4_template_audit import audit_v4_template

        print(json.dumps(asdict(audit_v4_template(Path(args.audit_template))), ensure_ascii=False, indent=2, default=str))
        return 0

    # JSON/status/device-list/JSONL paths use the lightweight core API.  Only
    # schema, V4 input, or the Web form needs to parse the V4 workbook.
    api, _contract, _resource_manager = create_application_api(
        project_root=_project_root(),
        load_template=bool(args.schema or args.v4_sheet or args.web),
    )
    if args.web:
        from .presentation.web.server import TemplateTransferPort, run_web
        # 空白模板是静态内置资源，可以直接下载；上传/解析仍由Excel适配器端口负责。
        from .infrastructure.excel.template_resource import V4TemplateResource

        template_resource = V4TemplateResource()
        transfer = TemplateTransferPort(
            download=lambda: (template_resource.template_path.name, template_resource.template_path.read_bytes())
        )
        run_web(api, args.host, args.port, open_browser=args.open_browser, template_transfer=transfer)
        return 0
    if args.jsonl:
        from .presentation.api.jsonl_server import run_jsonl
        run_jsonl(api, sys.stdin, sys.stdout)
        return 0
    if args.list_device_types:
        print(json.dumps({item["code"]: item for item in api.device_types()}, ensure_ascii=False, indent=2))
        return 0
    if args.status:
        print(json.dumps(api.status(), ensure_ascii=False, indent=2))
        return 0
    if args.schema:
        if not args.device_type:
            parser.error("--schema必须同时提供--device-type")
        print(json.dumps(api.schema(args.device_type), ensure_ascii=False, indent=2))
        return 0
    if args.example:
        if not args.device_type or args.v4_sheet:
            parser.error("--example必须同时提供--device-type，且不能与--v4-sheet同时使用")
        if args.device_type not in PUBLIC_DEVICE_TYPES:
            parser.error("--example只支持15类公共设备类型")
        print(json.dumps(_public_example(args.device_type), ensure_ascii=False, indent=2))
        return 0
    if args.batch_json_text:
        if args.json_text or args.v4_sheet or args.device_type:
            parser.error("--batch-json不能与--json、--device-type或--v4-sheet同时使用")
        try:
            batch_payload = json.loads(args.batch_json_text)
        except json.JSONDecodeError as exc:
            parser.error(f"--batch-json不是有效JSON：{exc}")
        if not isinstance(batch_payload, dict):
            parser.error("--batch-json必须是包含records数组的对象")
        batch_payload.setdefault("elimination_scope", args.elimination_scope)
        batch_payload.setdefault("as_of", args.as_of)
        print(json.dumps(api.evaluate_batch(batch_payload), ensure_ascii=False, indent=2))
        return 0
    if not args.json_text:
        parser.error("判定时必须提供--json；或使用--list-device-types/--schema")
    try:
        values = json.loads(args.json_text)
    except json.JSONDecodeError as exc:
        parser.error(f"--json不是有效JSON：{exc}")
    if not isinstance(values, dict):
        parser.error("--json必须是对象")
    payload = {"record_id": args.record_id, "values": values, "elimination_scope": args.elimination_scope, "as_of": args.as_of}
    if args.v4_sheet:
        payload["sheet"] = args.v4_sheet
        result = api.evaluate_v4(payload)
    elif args.device_type:
        payload["device_type"] = args.device_type
        result = api.evaluate(payload)
    else:
        parser.error("判定时必须提供--device-type或--v4-sheet")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
