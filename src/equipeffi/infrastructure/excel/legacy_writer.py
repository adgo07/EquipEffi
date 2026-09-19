from ...application.errors import FeatureNotEnabledError


class LegacyWorkbookWriter:
    """旧台账标注导出器；包装现有 core.writer 的 ZIP 补丁能力。"""

    def export(self, report, source: str, destination: str) -> str:
        raise FeatureNotEnabledError(
            "旧版Excel结果回写",
            "旧版台账标注导出逻辑尚未迁移",
        )
