"""校验EquipEffi便携ZIP的清单、哈希和最小运行文件集合。"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from zipfile import BadZipFile, ZipFile
from typing import Any, Sequence


REQUIRED_MEMBERS = {
    "SHA256SUMS.txt",
    "运行说明.txt",
    "scripts/install_windows.ps1",
    "scripts/install_native_windows.ps1",
    "scripts/install_linux.sh",
    "scripts/install_linux_service.sh",
    "scripts/equipeffi-web.service.template",
    "scripts/run_jsonl_windows.ps1",
    "scripts/run_jsonl_linux.sh",
    "tools/smoke_jsonl.py",
    "tools/validate_android_skeleton.py",
    "docs/10_跨平台运行与模块边界.md",
    "docs/11_JSONL协议与Android桥接.md",
    "android/README.md",
    "android/settings.gradle.kts",
    "android/build.gradle.kts",
    "android/gradle.properties",
    "android/bridge/build.gradle.kts",
    "android/app/build.gradle.kts",
    "android/app/src/main/AndroidManifest.xml",
    "android/app/src/main/kotlin/com/equipeffi/android/MainActivity.kt",
    "android/bridge/src/main/kotlin/com/equipeffi/bridge/JsonlBridgeClient.kt",
}


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def validate(bundle: Path) -> dict[str, Any]:
    bundle = Path(bundle).resolve()
    errors: list[str] = []
    checks: dict[str, Any] = {"path": str(bundle)}
    if not bundle.is_file():
        return {"is_valid": False, "errors": [f"便携ZIP不存在: {bundle}"], "checks": checks}
    try:
        with ZipFile(bundle) as archive:
            names = archive.namelist()
            unique_names = set(names)
            checks["member_count"] = len(names)
            checks["duplicate_members"] = sorted({name for name in names if names.count(name) > 1})
            if checks["duplicate_members"]:
                errors.append("便携ZIP包含重复成员名")
            unsafe = [name for name in names if name.startswith(("/", "\\")) or ".." in Path(name).parts]
            checks["unsafe_members"] = sorted(unsafe)
            if unsafe:
                errors.append("便携ZIP包含不安全路径")
            missing = sorted(REQUIRED_MEMBERS - unique_names)
            checks["missing_required_members"] = missing
            if missing:
                errors.append("便携ZIP缺少必要文件: " + ", ".join(missing))
            if "SHA256SUMS.txt" not in unique_names:
                return {"is_valid": False, "errors": errors, "checks": checks}
            checksum_text = archive.read("SHA256SUMS.txt").decode("utf-8")
            checksum_entries: dict[str, str] = {}
            for line in checksum_text.splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split(None, 1)
                if len(parts) != 2:
                    errors.append(f"SHA256SUMS.txt行格式无效: {line}")
                    continue
                checksum_entries[parts[1].strip()] = parts[0].lower()
            checks["checksum_entry_count"] = len(checksum_entries)
            checksum_errors: list[str] = []
            for name, expected in checksum_entries.items():
                if name not in unique_names:
                    checksum_errors.append(f"清单指向不存在成员: {name}")
                    continue
                actual = _sha256(archive.read(name))
                if actual != expected:
                    checksum_errors.append(f"成员SHA-256不匹配: {name}")
            checks["checksum_errors"] = checksum_errors
            if checksum_errors:
                errors.extend(checksum_errors)
            checks["wheel_members"] = sorted(name for name in names if name.endswith(".whl"))
            checks["zipapp_members"] = sorted(name for name in names if name.endswith(".pyz"))
            if not checks["wheel_members"]:
                errors.append("便携ZIP未包含wheel")
            if not checks["zipapp_members"]:
                errors.append("便携ZIP未包含.pyz")
    except (OSError, BadZipFile, UnicodeDecodeError) as exc:
        errors.append(f"便携ZIP读取失败: {exc}")
    checks["sha256"] = _sha256(bundle.read_bytes()) if bundle.is_file() else ""
    return {"is_valid": not errors, "errors": errors, "checks": checks}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="校验EquipEffi便携ZIP")
    parser.add_argument("bundle", type=Path)
    args = parser.parse_args(argv)
    result = validate(args.bundle)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["is_valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
