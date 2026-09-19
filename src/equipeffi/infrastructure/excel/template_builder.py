from ...application.errors import FeatureNotEnabledError


class TemplateBuilder:
    """由字段契约生成内置模板的入口。"""

    def build(self, destination: str) -> str:
        raise FeatureNotEnabledError(
            "Excel模板自动生成",
            "当前版本使用已完成的V4空白模板下载接口",
        )
