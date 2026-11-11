"""Load the version-pinned derived runtime asset without source documents."""
from hashlib import sha256
from importlib import resources
import json
from pathlib import Path
from ...domain.devices.motor_hv.calculator import Gb30254MotorCalculator, HvPackError


def load_motor_hv_pack(path: Path | None = None):
    payload = Path(path).read_bytes() if path is not None else resources.files("equipeffi").joinpath(
        "resources", "standards", "gb30254_2024_candidate.json").read_bytes()
    try:
        pack = json.loads(payload)
        Gb30254MotorCalculator._validate_pack(pack)
    except (ValueError, TypeError) as error:
        raise HvPackError("高压电机标准资源无效") from error
    return pack, sha256(payload).hexdigest().upper()
