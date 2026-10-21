"""校验 headless 便携 ZIP 的清单、哈希和正式安装文件。"""
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
    "README.md",
    "scripts/README.md",
    "scripts/install_windows.ps1",
    "scripts/install_native_windows.ps1",
    "scripts/install_linux.sh",
    "tools/validate_portable_bundle.py",
}
FORBIDDEN_MEMBERS = {
    "scripts/install_linux_service.sh",
    "scripts/equipeffi-web.service.template",
    "scripts/run_jsonl_windows.ps1",
    "scripts/run_jsonl_linux.sh",
    "scripts/run_web_windows.ps1",
    "scripts/run_web_linux.sh",
    "tools/smoke_jsonl.py",
    "tools/validate_android_skeleton.py",
    "docs/10_跨平台运行与模块边界.md",
    "docs/11_JSONL协议与Android桥接.md",
}
FORBIDDEN_PREFIXES = ("android/",)


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
            unsafe = [
                name for name in names
                if name.startswith(("/", chr(92))) or ".." in Path(name).parts
            ]
            checks["unsafe_members"] = sorted(unsafe)
            if unsafe:
                errors.append("便携ZIP包含不安全路径")
            missing = sorted(REQUIRED_MEMBERS - unique_names)
            checks["missing_required_members"] = missing
            if missing:
                errors.append("便携ZIP缺少必要文件: " + ", ".join(missing))
            forbidden = sorted(
                name for name in unique_names
                if name in FORBIDDEN_MEMBERS
                or name.startswith(FORBIDDEN_PREFIXES)
                or (name.lower().endswith(".xlsx") and "v4" in name.lower())
            )
            checks["retired_members"] = forbidden
            if forbidden:
                errors.append("便携ZIP包含已退役发布成员: " + ", ".join(forbidden))
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
            checks["optional_zipapp_members"] = sorted(name for name in names if name.endswith(".pyz"))
            if not checks["wheel_members"]:
                errors.append("便携ZIP未包含wheel")
    except (OSError, BadZipFile, UnicodeDecodeError) as exc:
        errors.append(f"便携ZIP读取失败: {exc}")
    checks["sha256"] = _sha256(bundle.read_bytes()) if bundle.is_file() else ""
    return {"is_valid": not errors, "errors": errors, "checks": checks}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="校验EquipEffi headless便携ZIP")
    parser.add_argument("bundle", type=Path)
    args = parser.parse_args(argv)
    result = validate(args.bundle)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["is_valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
