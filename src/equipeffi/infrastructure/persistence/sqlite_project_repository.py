from ...application.errors import FeatureNotEnabledError


class SqliteProjectRepository:
    """项目快照、人工修订和判定历史的持久化入口。"""

    def save_draft(self, project_id: str, draft) -> None:
        raise FeatureNotEnabledError(
            "SQLite项目快照保存",
            "当前版本不持久化项目草稿",
        )

    def list_drafts(self, project_id: str):
        raise FeatureNotEnabledError(
            "SQLite项目草稿读取",
            "当前版本不持久化项目草稿",
        )
