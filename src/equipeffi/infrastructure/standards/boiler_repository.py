"""只加载派生候选资产，安装包无需标准原件。"""
from importlib import resources
from hashlib import sha256
from pathlib import Path
import json
from ...domain.devices.boiler.calculator import Gb24500BoilerCalculator, BoilerPackError


def load_boiler_pack(path=None):
    data = Path(path).read_bytes() if path else resources.files("equipeffi").joinpath(
        "resources", "standards", "gb24500_2020_candidate.json").read_bytes()
    try:
        pack = json.loads(data)
        Gb24500BoilerCalculator.validate_pack(pack)
    except (ValueError, TypeError) as e:
        raise BoilerPackError("锅炉标准资源无效") from e
    return pack, sha256(data).hexdigest().upper()
