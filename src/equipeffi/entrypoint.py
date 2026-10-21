"""正式产品命令入口：启动 Qt 桌面 Shell，或执行无界面发布诊断。"""
from __future__ import annotations

import argparse
import json
import sys
from typing import Sequence


def _runtime_status() -> dict[str, object]:
    """检查正式 Qt、V6 模板和两个正式泵 Profile，不创建窗口或用户数据库。"""

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
            V6_TEMPLATE_IDENTITY,
            V6TemplateResource,
        )

        template["template_id"] = V6_TEMPLATE_IDENTITY["template_id"]
        template["template_version"] = V6_TEMPLATE_IDENTITY["template_version"]
        validation = V6TemplateResource().validate()
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

    ready = (
        bool(desktop["available"])
        and bool(template["available"])
        and all(bool(profile["available"]) for profile in profiles.values())
    )
    return {
        "ready": ready,
        "desktop": desktop,
        "template": template,
        "pump_profiles": profiles,
    }


def main(argv: Sequence[str] | None = None) -> int:
    argv = list(sys.argv[1:]) if argv is None else list(argv)
    parser = argparse.ArgumentParser(
        description="EquipEffi V6 离心泵能效分析桌面程序"
    )
    parser.add_argument("--qt", action="store_true", help="启动 PySide6 Qt 桌面程序")
    parser.add_argument("--gui", action="store_true", help="启动 PySide6 Qt 桌面程序（--qt 别名）")
    parser.add_argument("--status", action="store_true", help="无界面检查 Qt、V6 模板和泵标准包可用性")
    args = parser.parse_args(argv)

    if args.qt or args.gui:
        if args.status:
            parser.error("--qt/--gui 不能与 --status 同时使用")
        from .composition import launch_qt

        return launch_qt()
    if args.status:
        status = _runtime_status()
        print(json.dumps(status, ensure_ascii=False, indent=2))
        return 0 if status["ready"] else 1
    if not argv:
        from .composition import launch_qt

        return launch_qt()
    parser.error("请使用 --qt/--gui 启动桌面程序，或使用 --status 检查运行环境")


if __name__ == "__main__":
    raise SystemExit(main())
