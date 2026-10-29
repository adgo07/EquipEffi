"""UI 候选源码验收入口；必须显式指定独立数据目录。"""
import argparse
import os
from pathlib import Path
from equipeffi.composition import launch_qt
from equipeffi.infrastructure.persistence.app_data_paths import AppDataPaths


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--motor-candidate", action="store_true")
    args = parser.parse_args()
    if args.motor_candidate:
        os.environ["EQUIPEFFI_ENABLE_MOTOR_CANDIDATE"] = "1"
    return launch_qt(paths=AppDataPaths(args.data_root.resolve()))


if __name__ == "__main__":
    raise SystemExit(main())
