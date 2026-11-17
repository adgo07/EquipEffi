"""只加载派生候选资产，安装包无需标准原件。"""
from importlib import resources
from hashlib import sha256
from pathlib import Path
import json
from ...domain.devices.compressor.calculator import Gb19153CompressorCalculator, CompressorPackError


def load_compressor_pack(path=None):
    data = Path(path).read_bytes() if path else resources.files("equipeffi").joinpath(
        "resources", "standards", "gb19153_2019_candidate.json").read_bytes()
    try:
        pack = json.loads(data)
        Gb19153CompressorCalculator.validate_pack(pack)
    except (ValueError, TypeError) as e:
        raise CompressorPackError("空压机标准资源无效") from e
    return pack, sha256(data).hexdigest().upper()
