from pathlib import Path

from .v4_reader import V4WorkbookReaderImpl


class StrictTemplateImporter(V4WorkbookReaderImpl):
    """V4严格模板导入器的兼容名称。

    当前提供配置契约和设备数据行读取；结果写回仍由独立writer端口负责。
    """

    def import_records(self, source: str):
        return self.read_rows(Path(source))
