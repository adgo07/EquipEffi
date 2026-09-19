from ...application.errors import FeatureNotEnabledError


class LegacyWorkbookImporter:
    """旧版台账兼容导入器，最终替代当前 core.cleaner 的 Excel 识别逻辑。"""

    def import_records(self, source: str):
        raise FeatureNotEnabledError(
            "旧版Excel导入",
            "旧版兼容识别逻辑尚未迁移",
        )
