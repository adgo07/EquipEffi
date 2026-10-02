"""平台数据路径只在 Infrastructure 解析；调用者可以注入独立根目录。"""
from dataclasses import dataclass
import os
from pathlib import Path
import sys


@dataclass(frozen=True)
class AppDataPaths:
    root: Path

    def __post_init__(self):
        object.__setattr__(self, "root", Path(self.root))

    @classmethod
    def default(cls):
        if sys.platform == "win32":
            root = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        elif sys.platform == "darwin":
            root = Path.home() / "Library" / "Application Support"
        else:
            root = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
        return cls(root / "EquipEffi")

    @property
    def user_db(self) -> Path:
        return self.root / "user.sqlite"

    @property
    def catalog_db(self) -> Path:
        return self.root / "catalog.sqlite"

    @property
    def records_db(self) -> Path:
        return self.root / "records.sqlite"

    @property
    def logs_dir(self) -> Path:
        return self.root / "logs"
