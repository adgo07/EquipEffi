from collections import Counter

from ...domain.common.enums import Conclusion
from ...domain.common.models import EvaluationResult, ReportModel


class ReportService:
    """生成与展示层无关的项目汇总。

    汇总只基于已经完成的 ``EvaluationResult``，不读取Excel，也不重新执行判定。
    结论顺序固定，便于桌面窗口、HTTP和移动端得到稳定的输出结构。
    """

    def build(self, project_id: str, results: list[EvaluationResult]) -> ReportModel:
        conclusion_counts = Counter(result.conclusion.value for result in results)
        public_counts = Counter(
            result.public_device_type or "未标注"
            for result in results
        )
        internal_counts = Counter(
            result.internal_device_type or "未标注"
            for result in results
        )
        ordered_conclusions = {
            conclusion.value: conclusion_counts.get(conclusion.value, 0)
            for conclusion in Conclusion
        }
        summary = {
            "total_records": len(results),
            "by_conclusion": ordered_conclusions,
            "by_public_device_type": dict(sorted(public_counts.items())),
            "by_internal_device_type": dict(sorted(internal_counts.items())),
            "eliminated_records": conclusion_counts.get(Conclusion.ELIMINATED.value, 0),
            "unable_records": conclusion_counts.get(Conclusion.UNABLE_TO_JUDGE.value, 0),
            "data_quality_issue_records": sum(bool(result.data_quality_issues) for result in results),
        }
        return ReportModel(project_id=project_id, results=results, summary=summary)
