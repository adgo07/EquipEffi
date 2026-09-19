from ...application.errors import FeatureNotEnabledError


class ExcelReportExporter:
    """标准报告模板导出器。"""

    def export(self, report, destination: str) -> str:
        raise FeatureNotEnabledError(
            "Excel报告导出",
            "当前版本只返回结构化评价结果",
        )
