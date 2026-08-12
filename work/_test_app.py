# -*- coding: utf-8 -*-
"""streamlit_app.py 页面级自动化冒烟测试（临时脚本）
通过 STREAMLIT_DEFAULT_PAGE 环境变量指定默认页，逐页验证无异常。
"""
import os
import sys
import io
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parents[1] / "streamlit_app.py")
PAGES = ["🏠 项目总览", "📊 财务指标探索", "🔬 风险评估",
         "🔮 时序预测", "🚗 行业 NEV 分析", "🖼️ 预生成图表库"]


def report(label, at):
    errs = list(at.exception)
    print(f"[{label}] exceptions={len(errs)}")
    for e in errs:
        print(f"   !! {type(e.value).__name__}: {str(e.value)[:300]}")
    return len(errs)


def main():
    total_err = 0
    for p in PAGES:
        os.environ["STREAMLIT_DEFAULT_PAGE"] = p
        at = AppTest.from_file(APP, default_timeout=240)
        at.run(timeout=420)
        total_err += report(p, at)
        os.environ.pop("STREAMLIT_DEFAULT_PAGE", None)

    print("\n=== 汇总 ===")
    print(f"总异常数: {total_err}")
    sys.exit(1 if total_err else 0)


if __name__ == "__main__":
    main()
