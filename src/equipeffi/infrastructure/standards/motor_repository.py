"""Load and verify the derived GB 18613-2020 runtime pack."""
from __future__ import annotations

from hashlib import sha256
from importlib import resources
import json
from pathlib import Path
from typing import Any


PACK_SCHEMA = "equipeffi.motor-standard-pack.v1"
PACK_ID = "gb18613_2020_v2"
STANDARD_CODE = "GB 18613-2020"


def _canonical_payload(pack: dict[str, Any]) -> bytes:
    unsigned = {key: value for key, value in pack.items() if key != "integrity"}
    return json.dumps(
        unsigned, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def load_motor_pack(path: Path | None = None) -> tuple[dict[str, Any], str]:
    """Read a validated package and return it with its exact resource-file hash."""
    payload = (
        Path(path).read_bytes()
        if path is not None
        else resources.files("equipeffi").joinpath(
            "resources", "standards", "gb18613_2020.json"
        ).read_bytes()
    )
    try:
        pack = json.loads(payload)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("GB 18613-2020标准包不是有效UTF-8 JSON") from error
    if not isinstance(pack, dict):
        raise ValueError("GB 18613-2020标准包根节点必须是对象")
    if pack.get("schema_version") != PACK_SCHEMA:
        raise ValueError("GB 18613-2020标准包版本不受支持")
    if pack.get("pack_id") != PACK_ID or pack.get("standard_code") != STANDARD_CODE:
        raise ValueError("GB 18613-2020标准包身份不匹配")
    if pack.get("numeric_profile_id") != "EQUIPEFFI_MOTOR_EXACT_LINEAR_V1":
        raise ValueError("GB 18613-2020标准包缺少已声明的电机数值Profile")
    integrity = pack.get("integrity")
    if not isinstance(integrity, dict):
        raise ValueError("GB 18613-2020标准包缺少完整性声明")
    expected = integrity.get("sha256")
    if (
        integrity.get("algorithm") != "sha256"
        or integrity.get("canonicalization")
        != "sorted compact UTF-8 JSON excluding integrity"
        or not isinstance(expected, str)
        or expected != sha256(_canonical_payload(pack)).hexdigest().upper()
    ):
        raise ValueError("GB 18613-2020标准包完整性校验失败")
    tables = pack.get("tables")
    if not isinstance(tables, list) or [
        table.get("table_no") for table in tables if isinstance(table, dict)
    ] != list(range(1, 7)):
        raise ValueError("GB 18613-2020标准包表1至表6不完整或顺序错误")
    source_files = pack.get("source_files")
    if not isinstance(source_files, dict) or not all(
        isinstance(source_files.get(name), dict)
        and isinstance(source_files[name].get("sha256"), str)
        for name in ("mapping", "source_workbook")
    ):
        raise ValueError("GB 18613-2020标准包缺少映射或校对工作簿来源身份")
    return pack, sha256(payload).hexdigest().upper()
