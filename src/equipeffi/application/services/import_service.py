from typing import Any

from ...domain.common.models import RawDeviceRecord
from ..ports.importer import DeviceImporter


class ImportService:
    def __init__(self, importer: DeviceImporter):
        self.importer = importer

    def import_source(self, source: str) -> list[RawDeviceRecord]:
        return self.importer.import_records(source)
