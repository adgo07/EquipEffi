import unittest

from equipeffi.application.errors import FeatureNotEnabledError
from equipeffi.infrastructure.excel.legacy_importer import LegacyWorkbookImporter
from equipeffi.infrastructure.excel.legacy_writer import LegacyWorkbookWriter
from equipeffi.infrastructure.excel.report_exporter import ExcelReportExporter
from equipeffi.infrastructure.excel.template_builder import TemplateBuilder
from equipeffi.infrastructure.persistence.sqlite_project_repository import SqliteProjectRepository
from equipeffi.infrastructure.standards.sqlite_repository import SqliteStandardRepository


class DisabledAdapterTests(unittest.TestCase):
    def assert_disabled(self, call, feature):
        with self.assertRaises(FeatureNotEnabledError) as caught:
            call()
        self.assertEqual(caught.exception.feature, feature)
        self.assertIn("功能未启用", str(caught.exception))

    def test_excel_template_builder_is_explicitly_disabled(self):
        self.assert_disabled(lambda: TemplateBuilder().build("out.xlsx"), "Excel模板自动生成")

    def test_excel_report_exporter_is_explicitly_disabled(self):
        self.assert_disabled(lambda: ExcelReportExporter().export(None, "out.xlsx"), "Excel报告导出")

    def test_legacy_excel_adapters_are_explicitly_disabled(self):
        self.assert_disabled(lambda: LegacyWorkbookImporter().import_records("old.xlsx"), "旧版Excel导入")
        self.assert_disabled(lambda: LegacyWorkbookWriter().export(None, "old.xlsx", "out.xlsx"), "旧版Excel结果回写")

    def test_sqlite_adapters_are_explicitly_disabled(self):
        repository = SqliteStandardRepository()
        self.assert_disabled(lambda: repository.get_pack("transformer"), "SQLite标准数据库读取")
        self.assert_disabled(lambda: repository.find("transformer", {}), "SQLite标准数据库查询")

        project = SqliteProjectRepository()
        self.assert_disabled(lambda: project.save_draft("P1", {}), "SQLite项目快照保存")
        self.assert_disabled(lambda: project.list_drafts("P1"), "SQLite项目草稿读取")


if __name__ == "__main__":
    unittest.main()
