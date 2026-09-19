"""输入单台设备参数并返回能效判定结果（当前阶段不处理Excel）。

示例：
python tools/evaluate_device.py --device-type motor_lv --as-of 2026-08-23 --json '{"category":"三相异步电动机（一般用途）","rated_power_kw":7.5,"poles":4,"rated_efficiency":98}'
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from equipeffi.application.services.batch_evaluation_service import BatchEvaluationService  # noqa: E402
from equipeffi.application.services.evaluation_facade import EvaluationFacade  # noqa: E402
from equipeffi.application.services.evaluation_service import EvaluationService  # noqa: E402
from equipeffi.application.services.input_normalization import v4_input_contract  # noqa: E402
from equipeffi.application.services.v4_input_adapter import V4InputAdapter, V4_DEVICE_SHEETS  # noqa: E402
from equipeffi.domain.common.enums import EliminationScope  # noqa: E402
from equipeffi.domain.evaluation.device_types import PUBLIC_DEVICE_NAMES, PUBLIC_DEVICE_TYPES, PUBLIC_INTERNAL_PROFILES, public_device_types  # noqa: E402
from equipeffi.infrastructure.standards.json_repository import JsonStandardRepository  # noqa: E402
from equipeffi.presentation.api.application_api import ApplicationApi  # noqa: E402
from equipeffi.domain.evaluation.device_specs import get_device_spec, list_device_specs  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="输入设备参数并返回能效判定结果")
    parser.add_argument("--device-type", help="15类V4公共设备代码，例如 motor、centrifugal_pump、transformer；兼容旧17类代码")
    parser.add_argument("--v4-sheet", choices=V4_DEVICE_SHEETS, help="按V4模板设备sheet输入；与--device-type二选一")
    parser.add_argument("--record-id", default="CLI-001")
    parser.add_argument("--as-of", default="2026-08-23", help="判定基准日期，格式YYYY-MM-DD")
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--json", dest="json_text", help="设备参数JSON对象")
    source.add_argument("--json-file", type=Path, help="包含设备参数JSON对象的文件")
    parser.add_argument("--elimination-scope", choices=[scope.value for scope in EliminationScope], default=EliminationScope.MOTOR_BATCHES_1_4.value)
    parser.add_argument("--list-device-types", action="store_true", help="列出15类V4公共设备及采用标准")
    parser.add_argument("--status", action="store_true", help="输出标准包和淘汰目录能力状态")
    parser.add_argument("--schema", action="store_true", help="输出指定设备的参数契约")
    parser.add_argument("--example", action="store_true", help="输出指定设备的输入示例")
    args = parser.parse_args()
    try:
        if args.list_device_types:
            public = {
                item["code"]: {
                    "name": item["name"],
                    "sheet": item["sheet"],
                    "internal_profiles": list(PUBLIC_INTERNAL_PROFILES[item["code"]]),
                }
                for item in public_device_types()
            }
            print(json.dumps(public, ensure_ascii=False, indent=2))
            return 0
        if args.status:
            if args.device_type or args.v4_sheet or args.schema or args.example or args.json_text or args.json_file:
                raise ValueError("--status不能与设备类型、工作表、schema、example或判定输入同时使用")
            api = ApplicationApi(EvaluationFacade(EvaluationService(JsonStandardRepository(ROOT))))
            print(json.dumps(api.status(), ensure_ascii=False, indent=2))
            return 0
        if args.v4_sheet and (args.device_type or args.schema or args.example):
            raise ValueError("--v4-sheet只能用于直接判定，不能与--device-type/--schema/--example同时使用")
        if not args.device_type and not args.v4_sheet:
            raise ValueError("判定、查看参数契约或示例时必须提供--device-type，或使用--v4-sheet")
        if args.v4_sheet:
            if not args.json_text and not args.json_file:
                raise ValueError("使用--v4-sheet判定时必须提供--json或--json-file")
            values = json.loads(args.json_text) if args.json_text else json.loads(args.json_file.read_text(encoding="utf-8"))
            if not isinstance(values, dict):
                raise ValueError("输入JSON必须是对象")
            repo = JsonStandardRepository(ROOT)
            service = EvaluationService(repo)
            adapted = V4InputAdapter.adapt(args.record_id, args.v4_sheet, values)
            result = service.evaluate(
                adapted.draft,
                as_of=args.as_of,
                elimination_scope=EliminationScope(args.elimination_scope),
            )
            print(json.dumps(BatchEvaluationService.result_record(result), ensure_ascii=False, indent=2))
            return 0
        if args.schema:
            if args.device_type in PUBLIC_DEVICE_TYPES:
                profiles = list(PUBLIC_INTERNAL_PROFILES[args.device_type])
                print(json.dumps({
                    "code": args.device_type,
                    "name": PUBLIC_DEVICE_NAMES[args.device_type],
                    "sheet": PUBLIC_DEVICE_NAMES[args.device_type],
                    "internal_profiles": profiles,
                    "note": "字段以V4配置sheet为准；profile仅用于公共类型到标准规则的安全路由",
                }, ensure_ascii=False, indent=2))
                return 0
            spec = get_device_spec(args.device_type)
            schema = {key: value for key, value in spec.items() if key != "example"}
            schema["template_v4_compatibility"] = v4_input_contract(args.device_type)
            print(json.dumps(schema, ensure_ascii=False, indent=2))
            return 0
        if args.example:
            if args.device_type in PUBLIC_DEVICE_TYPES:
                examples = {
                    "motor": {"category": "三相异步电动机（一般用途）", "rated_voltage": "0.4", "rated_power": 7.5, "poles": 4, "efficiency": 98},
                    "centrifugal_pump": {"category": "单级单吸清水离心泵", "flow": 100, "head": 50, "speed": 2900, "efficiency": 80},
                    "centrifugal_fan": {"category": "离心通风机", "flow": 10000, "fan_pressure": 800, "rated_power": 15, "speed": 1450, "design_efficiency": 80},
                    "axial_fan": {"category": "轴流通风机", "flow": 10000, "fan_pressure": 400, "rated_power": 15, "speed": 1450, "design_efficiency": 80},
                }
                print(json.dumps(examples.get(args.device_type, {}), ensure_ascii=False, indent=2))
                return 0
            spec = get_device_spec(args.device_type)
            print(json.dumps(spec["example"], ensure_ascii=False, indent=2))
            return 0
        if not args.json_text and not args.json_file:
            raise ValueError("判定时必须提供--json或--json-file")
        values = json.loads(args.json_text) if args.json_text else json.loads(args.json_file.read_text(encoding="utf-8"))
        if not isinstance(values, dict):
            raise ValueError("输入JSON必须是对象")
        repo = JsonStandardRepository(ROOT)
        service = BatchEvaluationService(EvaluationService(repo))
        result = service.evaluate_records(
            [{"record_id": args.record_id, "device_type": args.device_type, "values": values}],
            as_of=args.as_of,
            elimination_scope=EliminationScope(args.elimination_scope),
        )[0]
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:  # CLI需把输入/标准问题以可读错误反馈给调用方
        print(json.dumps({"error": type(exc).__name__, "message": str(exc)}, ensure_ascii=False, indent=2), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
