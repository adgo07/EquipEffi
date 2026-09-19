"""对Android Gradle工程做不依赖SDK的结构校验。"""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Sequence


REQUIRED_FILES = (
    "settings.gradle.kts",
    "build.gradle.kts",
    "gradle.properties",
    "bridge/build.gradle.kts",
    "bridge/src/main/kotlin/com/equipeffi/bridge/JsonlBridgeClient.kt",
    "app/build.gradle.kts",
    "app/src/main/AndroidManifest.xml",
    "app/src/main/kotlin/com/equipeffi/android/MainActivity.kt",
)


def validate(root: Path) -> dict[str, Any]:
    root = Path(root).resolve()
    errors: list[str] = []
    checks: dict[str, Any] = {"root": str(root), "required_files": list(REQUIRED_FILES)}
    for relative in REQUIRED_FILES:
        if not (root / relative).is_file():
            errors.append(f"缺少Android工程文件：{relative}")
    if errors:
        return {"is_valid": False, "errors": errors, "checks": checks}

    settings = (root / "settings.gradle.kts").read_text(encoding="utf-8")
    app_build = (root / "app/build.gradle.kts").read_text(encoding="utf-8")
    manifest = (root / "app/src/main/AndroidManifest.xml").read_text(encoding="utf-8")
    activity = (root / "app/src/main/kotlin/com/equipeffi/android/MainActivity.kt").read_text(encoding="utf-8")
    bridge = (root / "bridge/src/main/kotlin/com/equipeffi/bridge/JsonlBridgeClient.kt").read_text(encoding="utf-8")
    checks.update({
        "modules_declared": ":app" in settings and ":bridge" in settings,
        "bridge_dependency": "project(\":bridge\")" in app_build,
        "internet_permission": "android.permission.INTERNET" in manifest,
        "launcher_declared": "android.intent.action.MAIN" in manifest and "android.intent.category.LAUNCHER" in manifest,
        "activity_entry": "class MainActivity : Activity()" in activity,
        "protocol_client": "PROTOCOL_VERSION = \"1.0\"" in bridge and "fun evaluate" in bridge,
        "bundled_business_data": any(path.suffix.lower() in {".json", ".xlsx", ".pdf"} for path in root.rglob("*")),
    })
    if not checks["modules_declared"]:
        errors.append("settings.gradle.kts未同时声明app和bridge模块")
    if not checks["bridge_dependency"]:
        errors.append("app未依赖bridge模块")
    if not checks["internet_permission"]:
        errors.append("AndroidManifest.xml未声明网络权限")
    if not checks["launcher_declared"] or not checks["activity_entry"]:
        errors.append("Android演示入口未正确声明")
    if not checks["protocol_client"]:
        errors.append("bridge协议客户端缺少v1.0或判定接口")
    if checks["bundled_business_data"]:
        errors.append("Android工程不应携带标准JSON、Excel或PDF业务数据")
    checks["file_count"] = sum(1 for path in root.rglob("*") if path.is_file())
    return {"is_valid": not errors, "errors": errors, "checks": checks}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="校验EquipEffi Android工程结构")
    parser.add_argument("root", type=Path)
    args = parser.parse_args(argv)
    import json

    result = validate(args.root)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["is_valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
