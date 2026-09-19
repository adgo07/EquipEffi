from typing import Protocol

from ...domain.common.models import ReportModel


class ReportExporter(Protocol):
    def export(self, report: ReportModel, destination: str) -> str: ...
