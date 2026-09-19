from ...application.errors import FeatureNotEnabledError


class SqliteStandardRepository:
    """稳定后使用的标准数据库仓库。"""

    def get_pack(self, device_type: str, pack_id: str | None = None):
        raise FeatureNotEnabledError(
            "SQLite标准数据库读取",
            "当前版本使用只读JSON标准仓库",
        )

    def find(self, device_type: str, criteria: dict):
        raise FeatureNotEnabledError(
            "SQLite标准数据库查询",
            "当前版本使用只读JSON标准仓库",
        )
