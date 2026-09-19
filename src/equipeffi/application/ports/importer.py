from typing import Protocol

from ...domain.common.models import RawDeviceRecord


class DeviceImporter(Protocol):
    def import_records(self, source: str) -> list[RawDeviceRecord]: ...
