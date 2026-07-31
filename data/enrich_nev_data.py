#!/usr/bin/env python3
"""
中国汽车行业多维销量数据库 — Sheet 一览与校验
==============================================
所有销量数据已统一整合到: 中国汽车行业多维销量数据库.xlsx (22 Sheets)

数据来源:
  - 整体市场/细分市场/燃料类型: 乘联会月度
  - CAAM NEV 月度产销: 中国汽车工业协会 2016-2025
  - 8家车企销量结构: 公司年报/产销快报

运行: python enrich_nev_data.py → 列出所有 Sheet 及行数
"""

import pandas as pd
import os

DATA_DIR = os.path.dirname(os.path.abspath(__file__))
XLSX_PATH = os.path.join(DATA_DIR, "中国汽车行业多维销量数据库.xlsx")


def main():
    if not os.path.exists(XLSX_PATH):
        print(f"[ERROR] 文件不存在: {XLSX_PATH}")
        return

    xl = pd.ExcelFile(XLSX_PATH)
    print(f"数据库: {os.path.basename(XLSX_PATH)}")
    print(f"Sheet 数量: {len(xl.sheet_names)}")
    print(f"{'='*60}")

    total_rows = 0
    for sn in xl.sheet_names:
        df = pd.read_excel(xl, sn)
        total_rows += df.shape[0]
        dim = f"{df.shape[0]}r × {df.shape[1]}c"
        # 分类标记
        tag = ""
        if sn.startswith("CAAM_NEV"):
            tag = " [CAAM NEV 2016-2025]"
        elif sn.startswith("8家车企"):
            tag = " [8家对标车企]"
        elif sn.startswith("整体市场"):
            tag = " [乘联会月度]"
        elif sn.startswith("燃料类型"):
            tag = " [NEV/ICE占比]"
        elif sn.startswith("细分市场"):
            tag = " [轿车/SUV/MPV级别]"
        print(f"  {sn:<36s} {dim:<16s}{tag}")

    print(f"{'='*60}")
    print(f"合计: {len(xl.sheet_names)} Sheets, {total_rows} 行")
    print(f"文件大小: {os.path.getsize(XLSX_PATH)/1024:.0f} KB")


if __name__ == "__main__":
    main()
