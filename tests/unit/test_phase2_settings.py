from contextlib import closing
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
import unittest

from equipeffi.application.services.settings_service import SettingsService
from equipeffi.infrastructure.persistence.app_data_paths import AppDataPaths
from equipeffi.infrastructure.persistence.migrations import (
    DB_POLICIES, Migration, MigrationError, USER_MIGRATIONS, migrate_user_database,
)
from equipeffi.infrastructure.persistence.sqlite_settings_repository import SqliteSettingsRepository


class SettingsTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory(prefix="phase2-中文-")
        self.addCleanup(self.temp.cleanup)
        self.paths = AppDataPaths(Path(self.temp.name))
        migrate_user_database(self.paths.user_db, app_version="0.2.1")
        self.service = SettingsService(SqliteSettingsRepository(self.paths.user_db))

    def test_real_repository_roundtrip_and_reopen(self):
        for key, value in {"window.geometry": "encoded", "window.state": "state", "log.level": "WARNING", "last.directory": "中文目录"}.items():
            self.service.set(key, value)
            reopened = SettingsService(SqliteSettingsRepository(self.paths.user_db))
            self.assertEqual(reopened.get(key), value)
        self.assertEqual(self.service.get("last.directory"), "中文目录")
        self.service.set("last.directory", "changed")
        self.assertEqual(self.service.get("last.directory"), "changed")

    def test_missing_default_and_no_business_keys(self):
        self.assertEqual(self.service.get("window.geometry", "default"), "default")
        for key in ("DeviceDraft", "Workspace", "Record", "pump.input", "evaluation.result"):
            with self.assertRaises(ValueError):
                self.service.set(key, "data")
        with self.assertRaises(TypeError):
            self.service.set("last.directory", 42)
        with self.assertRaises(ValueError):
            self.service.set("log.level", "unknown")

    def test_first_migration_history_and_idempotence_preserve_settings(self):
        self.service.set("last.directory", "keep")
        with closing(sqlite3.connect(self.paths.user_db)) as db, db:
            original = db.execute("SELECT * FROM migration_history").fetchall()
        migrate_user_database(self.paths.user_db, app_version="future-build")
        with closing(sqlite3.connect(self.paths.user_db)) as db, db:
            self.assertEqual(original, db.execute("SELECT * FROM migration_history").fetchall())
        version, id, checksum, applied, app = original[0]
        self.assertEqual((version, id, checksum, app), (1, "001_create_settings", USER_MIGRATIONS[0].checksum, "0.2.1"))
        self.assertTrue(applied.endswith("+00:00"))
        self.assertEqual(self.service.get("last.directory"), "keep")

    def test_checksum_mismatch_never_rebuilds(self):
        self.service.set("last.directory", "keep")
        with closing(sqlite3.connect(self.paths.user_db)) as db, db:
            db.execute("UPDATE migration_history SET checksum = 'tampered'")
        with self.assertRaisesRegex(MigrationError, "校验和"):
            migrate_user_database(self.paths.user_db, app_version="0.2.1")
        self.assertEqual(self.service.get("last.directory"), "keep")

    def test_failed_forward_migration_rolls_back(self):
        self.service.set("last.directory", "keep")
        broken = Migration(2, "002_broken", ("CREATE TABLE transient (value TEXT)", "INVALID SQL"))
        with self.assertRaises(sqlite3.OperationalError):
            migrate_user_database(self.paths.user_db, app_version="0.2.1", migrations=(*USER_MIGRATIONS, broken))
        with closing(sqlite3.connect(self.paths.user_db)) as db, db:
            tables = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            self.assertNotIn("transient", tables)
            self.assertEqual(db.execute("SELECT COUNT(*) FROM migration_history").fetchone()[0], 1)
        self.assertEqual(self.service.get("last.directory"), "keep")

    def test_unknown_future_version_rejected(self):
        with closing(sqlite3.connect(self.paths.user_db)) as db, db:
            db.execute("INSERT INTO migration_history VALUES (2, 'future', 'hash', 'now', 'future')")
        with self.assertRaises(MigrationError):
            migrate_user_database(self.paths.user_db, app_version="0.2.1")

    def test_only_user_database_is_created(self):
        for path in (self.paths.catalog_db, self.paths.records_db):
            with self.assertRaises(MigrationError):
                migrate_user_database(path, app_version="0.2.1")
        self.assertEqual(DB_POLICIES[self.paths.catalog_db.name], "REBUILDABLE_DERIVED")
        self.assertEqual(DB_POLICIES[self.paths.records_db.name], "NEVER_DESTRUCTIVE_RECORD_ASSET")
        self.assertFalse(self.paths.catalog_db.exists())
        self.assertFalse(self.paths.records_db.exists())
        self.assertEqual(self.paths.logs_dir, Path(self.temp.name) / "logs")
        with closing(sqlite3.connect(self.paths.user_db)) as db, db:
            self.assertEqual({row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")},
                             {"settings", "migration_history"})
