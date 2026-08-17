# -*- coding: utf-8 -*-
"""tests/integration_test.py - 全流程集成测试（真实项目数据）
清洗 → 判定 → 汇总 → 结果输出（不写回原文件，输出到tests/samples/）
用法: python tests/integration_test.py [Excel路径]
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.cleaner import Cleaner
from core.evaluator import evaluate_all
from core.summary import build_summary

DEFAULT = r"G:\审项目3\2024.7.8 宁鲁石化 设备监察\设备能效分析表（宁鲁石化）.xlsx"


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT
    print(f"输入: {path}")

    # 1. 清洗
    cleaner = Cleaner(path)
    devices = cleaner.run()
    total = sum(len(v) for v in devices.values())
    print(f"\n[清洗] {len(devices)}类设备, {total}台")
    for s in cleaner.summary:
        print(f"  {s['sheet']:<10} {s['key']:<12} {s['devices']:>3}台 问题{s['issues']}")

    # 2. 判定
    results = evaluate_all(devices)
    judged = sum(1 for v in results.values() for it in v if it["result_dict"]["result"] not in ("无法判定", "不在范围"))
    print(f"\n[判定] 成功判定{judged}/{total}台")
    for key, items in results.items():
        for it in items[:3]:
            rd = it["result_dict"]
            print(f"  {key} R{it['row']} {it['name'][:12]}: {rd['result']} {rd.get('note','')[:40]}")

    # 3. 汇总
    summary = build_summary(results)
    print(f"\n[汇总] 总判定分布: {summary['total']}")
    for s in summary["stats"]:
        if s["count"]:
            print(f"  {s['key']:<12} {s['count']:>3}台 {s['levels']} 容量{s['capacity_sum']}{s['capacity_unit'] or ''}")

    # 4. 保存结果JSON（调试用）
    out = Path(__file__).resolve().parent / "samples" / "integration_result.json"
    out.write_text(json.dumps({
        "summary": summary,
        "details": {k: [{"row": i["row"], "name": i["name"], "result": i["result_dict"],
                         "params": i["params"], "issues": i["issues"]} for i in v]
                    for k, v in results.items()},
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n结果已保存: {out}")


if __name__ == "__main__":
    main()
