"""Read the GB 30253 candidate asset independently of the legacy manifest."""
from importlib import resources
from pathlib import Path

from ...domain.devices.motor_pmsm.pack import PACK_ID, PmsmPack, PmsmPackError


def load_motor_pmsm_pack(path: Path | None = None) -> PmsmPack:
    source = path if path is not None else resources.files("equipeffi").joinpath(
        "resources", "standards", f"{PACK_ID}.json")
    try:
        return PmsmPack.from_bytes(source.read_bytes())
    except OSError as exc:
        raise PmsmPackError("无法读取永磁电机候选数据") from exc
