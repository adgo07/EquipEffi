"""正式产品命令入口：启动 Qt 桌面 Shell，或执行无界面发布诊断。"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Sequence


def _runtime_status() -> dict[str, object]:
    """检查Qt、统一模板和设备实现，不创建窗口或用户数据库。"""

    from .composition import motor_candidate_enabled
    motor_enabled = motor_candidate_enabled()
    desktop: dict[str, object] = {"surface": "PySide6 Qt", "available": False}
    try:
        from PySide6 import QtWidgets

        desktop["available"] = hasattr(QtWidgets, "QApplication")
        if not desktop["available"]:
            desktop["error"] = "PySide6.QtWidgets 缺少 QApplication"
    except Exception as exc:
        desktop["error"] = f"{type(exc).__name__}: {exc}"

    template: dict[str, object] = {
        "template_id": "",
        "template_version": "",
        "available": False,
        "issues": [],
    }
    try:
        from .infrastructure.excel.template_resource import (
            V61_TEMPLATE_IDENTITY,
            V61TransformerTemplateResource,
        )

        template["template_id"] = V61_TEMPLATE_IDENTITY["template_id"]
        template["template_version"] = V61_TEMPLATE_IDENTITY["template_version"]
        resource = V61TransformerTemplateResource()
        if motor_enabled:
            from .infrastructure.excel.template_resource import V63_TEMPLATE_IDENTITY, V63MotorTemplateResource
            template.update(template_id=V63_TEMPLATE_IDENTITY["template_id"],
                            template_version=V63_TEMPLATE_IDENTITY["template_version"])
            resource = V63MotorTemplateResource()
        validation = resource.validate()
        template["available"] = validation.is_valid
        template["issues"] = list(validation.issues)
        if validation.missing_sheets:
            template["issues"].extend(
                f"缺少工作表：{sheet}" for sheet in validation.missing_sheets
            )
        if not validation.is_valid and not template["issues"]:
            template["issues"].append(validation.message)
    except Exception as exc:
        template["issues"] = [f"{type(exc).__name__}: {exc}"]

    profiles: dict[str, dict[str, object]] = {
        name: {
            "available": False,
            "support_status": None,
            "pack_id": None,
        }
        for name in ("pump_water", "pump_chemical")
    }
    try:
        from .composition import create_pump_analysis_service

        overview = create_pump_analysis_service(with_persistence=False).standard_overview()
        scopes = {
            str(scope.get("rule_profile")): scope
            for scope in overview.get("scopes", ())
            if isinstance(scope, dict)
        }
        for name, profile in profiles.items():
            scope = scopes.get(name, {})
            profile["support_status"] = scope.get("support_status")
            profile["pack_id"] = scope.get("pack_id")
            profile["available"] = (
                scope.get("support_status") == "SUPPORTED"
                and bool(scope.get("pack_id"))
            )
    except Exception as exc:
        for profile in profiles.values():
            profile["error"] = f"{type(exc).__name__}: {exc}"

    transformer = {"available": False, "support_status": "SUPPORTED"}
    try:
        from .composition import create_transformer_analysis_service
        service = create_transformer_analysis_service(with_persistence=False)
        transformer.update(service.standard_overview())
        transformer["available"] = bool(service.input_contract.categories)
    except Exception as exc:
        transformer["error"] = f"{type(exc).__name__}: {exc}"

    motor = {"enabled": motor_enabled, "available": False, "support_status": "SUPPORTED"}
    if motor_enabled:
        try:
            from .composition import create_motor_analysis_service
            service = create_motor_analysis_service(with_persistence=False)
            motor.update(service.standard_overview())
            motor["available"] = bool(service.input_contract.categories)
        except Exception as exc:
            motor["error"] = f"{type(exc).__name__}: {exc}"

    ready = (
        bool(desktop["available"])
        and bool(template["available"])
        and all(bool(profile["available"]) for profile in profiles.values())
        and bool(transformer["available"])
        and (not motor_enabled or bool(motor["available"]))
    )
    return {
        "ready": ready,
        "desktop": desktop,
        "template": template,
        "pump_profiles": profiles,
        "transformer": transformer,
        "motor": motor,
    }


def main(argv: Sequence[str] | None = None) -> int:
    argv = list(sys.argv[1:]) if argv is None else list(argv)
    parser = argparse.ArgumentParser(
        description="EquipEffi 设备能效分析桌面程序"
    )
    parser.add_argument("--motor-candidate", action="store_true",
                        help="兼容旧入口，启用GB18613电动机（本版本默认启用）")
    parser.add_argument("--qt", action="store_true", help="启动 PySide6 Qt 桌面程序")
    parser.add_argument("--gui", action="store_true", help="启动 PySide6 Qt 桌面程序（--qt 别名）")
    parser.add_argument("--status", action="store_true", help="无界面检查 Qt、统一模板和设备标准包可用性")
    parser.add_argument(
        "--status-file",
        type=Path,
        help="将 --status 的 JSON 写入 UTF-8 文件（适用于无控制台启动）",
    )
    args = parser.parse_args(argv)
    if args.motor_candidate:
        import os
        os.environ["EQUIPEFFI_ENABLE_MOTOR_CANDIDATE"] = "1"

    if args.status_file is not None and not args.status:
        parser.error("--status-file 只能与 --status 同时使用")

    if args.qt or args.gui:
        if args.status or args.status_file is not None:
            parser.error("--qt/--gui 不能与 --status 同时使用")
        from .composition import launch_qt

        return launch_qt()
    if args.status:
        status = _runtime_status()
        payload = json.dumps(status, ensure_ascii=False, indent=2)
        if args.status_file is not None:
            status_file = args.status_file.expanduser()
            status_file.parent.mkdir(parents=True, exist_ok=True)
            status_file.write_text(payload + "\n", encoding="utf-8")
        if sys.stdout is not None:
            print(payload)
        return 0 if status["ready"] else 1
    if not argv or args.motor_candidate:
        from .composition import launch_qt

        return launch_qt()
    parser.error("请使用 --qt/--gui 启动桌面程序，或使用 --status 检查运行环境")


if __name__ == "__main__":
    raise SystemExit(main())
