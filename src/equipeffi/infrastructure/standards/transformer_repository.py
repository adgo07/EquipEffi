"""读取已派生的变压器包；安装包不需要冻结Excel或标准原文。"""
from hashlib import sha256
from importlib import resources
import json
from pathlib import Path


def load_transformer_pack(path: Path | None = None) -> tuple[dict, str]:
    payload = (Path(path).read_bytes() if path is not None else
               resources.files("equipeffi").joinpath(
                   "resources", "standards", "gb20052_2024_v21.json").read_bytes())
    pack = json.loads(payload)
    if pack.get("schema_version") != "equipeffi.transformer-standard-pack.v1":
        raise ValueError("变压器标准包版本不受支持")
    canonical = json.dumps(
        {key: value for key, value in pack.items() if key != "integrity"},
        ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    integrity = pack.get("integrity", {})
    if (integrity.get("algorithm") != "sha256"
            or integrity.get("payload_sha256") != sha256(canonical).hexdigest().upper()):
        raise ValueError("变压器标准包完整性校验失败")
    tables = pack.get("tables", [])
    if [table.get("table_no") for table in tables] != list(range(1, 36)):
        raise ValueError("变压器标准包表1至35不完整或顺序错误")
    return pack, sha256(payload).hexdigest().upper()
