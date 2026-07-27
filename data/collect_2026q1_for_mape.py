#!/usr/bin/env python3
"""
2026Q1 MAPE 数据追加采集 — 赛力斯 & 长安汽车
=============================================
用途: 追加采集 2026Q1 财报数据，提取毛利率和资产负债率实际值
      用于 Prophet 时序预测的 MAPE（平均绝对百分比误差）评估

MAPE = |实际值 - 预测值| / |实际值| × 100%

使用方法:
  1. 先在 notebook 中运行 Prophet 预测 cell → 记录 2026-03-31 预测值
  2. 运行本脚本: python data/collect_2026q1_for_mape.py
  3. 回到 notebook: 重新运行「合并报表」整合 cell + ratio_analysis cell
  4. 手动计算 MAPE: |实际值 - 预测值| / |实际值| × 100%

依赖: collect_financial_data.py (同目录)
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding='utf-8')

import logging
from pathlib import Path

import pandas as pd

# ── 导入 collect_financial_data 的核心函数 ──
from collect_financial_data import (
    logger, DATA_DIR, TIME_START,
    process_company, get_val, to_yuan,
)

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s [%(levelname)s] %(message)s',
                    datefmt='%H:%M:%S')

# ======================== 参数 ========================

TIME_END_EXTENDED = 2026  # 扩展到 2026 年以包含 Q1

TARGETS = [
    ('601127', '赛力斯'),
    ('000625', '长安汽车'),
]

# ======================== 主逻辑 ========================

def collect_2026q1_for_mape():
    """
    追加采集目标公司的 2026Q1 数据，
    提取毛利率和资产负债率实际值，用于 MAPE 评估。
    """
    import collect_financial_data as cfd

    # 临时扩展 TIME_END 到 2026
    _orig_end = cfd.TIME_END
    cfd.TIME_END = TIME_END_EXTENDED

    logger.info(f'\n{"="*60}')
    logger.info(f'  2026Q1 MAPE 数据追加采集')
    logger.info(f'  目标: 赛力斯(601127) & 长安汽车(000625)')
    logger.info(f'  时间范围: {TIME_START}Q1 — {TIME_END_EXTENDED}Q4')
    logger.info(f'{"="*60}')

    mape_actuals = {}

    for symbol, name in TARGETS:
        logger.info(f'\n  ── 处理: {name} ({symbol}) ──')

        result = process_company(symbol, name)
        if not result:
            logger.warning(f'    ⚠️ {name}: 采集失败，跳过')
            continue

        path, issues = result

        # ─── 从原始报表计算 毛利率 和 资产负债率 ───
        xl = pd.ExcelFile(path)

        if '利润表' not in xl.sheet_names or '资产负债表' not in xl.sheet_names:
            logger.warning(f'    ⚠️ {name}: 缺少报表 sheet')
            continue

        df_is = pd.read_excel(xl, '利润表', index_col=0)
        df_bs = pd.read_excel(xl, '资产负债表', index_col=0)

        # 找 2026Q1 列
        q1_cols = [c for c in df_is.columns if '2026Q1' in str(c)]
        if not q1_cols:
            q1_cols = [c for c in df_is.columns if '2026' in str(c)]
        if not q1_cols:
            logger.warning(
                f'    ⚠️ {name}: 利润表中无 2026Q1 列 '
                f'(可用列: {list(df_is.columns[-3:])})'
            )
            continue

        q1_col = q1_cols[0]
        logger.info(f'    目标列: {q1_col}')

        # 毛利率 = 1 - 营业成本 / 营业收入
        rev = get_val(df_is, '营业收入', q1_col)
        cost = get_val(df_is, '营业成本', q1_col)
        gross_margin = (1 - cost / rev) if (rev and cost and rev != 0) else None

        # 资产负债率 = 负债合计 / 资产合计
        tl = (get_val(df_bs, '负债合计', q1_col)
              or get_val(df_bs, '六、负债合计', q1_col))
        ta = (get_val(df_bs, '资产合计', q1_col)
              or get_val(df_bs, '三、资产合计', q1_col))
        debt_ratio = (tl / ta) if (tl and ta and ta != 0) else None

        if gross_margin is not None and debt_ratio is not None:
            mape_actuals[name] = {
                '毛利率': round(gross_margin, 6),
                '资产负债率': round(debt_ratio, 6),
            }
            logger.info(f'    ✅ {name} 2026Q1 实际值:')
            logger.info(f'       毛利率     = {gross_margin:.6f} ({gross_margin*100:.2f}%)')
            logger.info(f'       资产负债率  = {debt_ratio:.6f} ({debt_ratio*100:.2f}%)')
        else:
            logger.warning(
                f'    ⚠️ {name}: 计算失败 '
                f'(毛利率={gross_margin}, 资产负债率={debt_ratio})'
            )

    # ─── 恢复 ───
    cfd.TIME_END = _orig_end

    # ─── 输出摘要 ───
    logger.info(f'\n{"="*60}')
    logger.info(f'  📊 MAPE 评估 — 2026Q1 实际值摘要')
    logger.info(f'{"="*60}')

    if mape_actuals:
        for name, vals in mape_actuals.items():
            logger.info(f'  {name}:')
            logger.info(f'    毛利率     = {vals["毛利率"]:.6f}  ({vals["毛利率"]*100:.2f}%)')
            logger.info(f'    资产负债率  = {vals["资产负债率"]:.6f}  ({vals["资产负债率"]*100:.2f}%)')

        logger.info(f'\n  📐 MAPE 计算公式:')
        logger.info(f'     MAPE = |实际值 - Prophet预测值| / |实际值| × 100%')
        logger.info(f'\n  📋 下一步:')
        logger.info(f'     1. 在 notebook 重新运行「合并报表」整合 cell')
        logger.info(f'     2. 重新运行 ratio_analysis cell（更新 all_ratios）')
        logger.info(f'     3. 用上面的实际值 + Prophet 的 2026-03-31 预测值计算 MAPE')
    else:
        logger.warning(f'  ⚠️ 未能提取任何 2026Q1 数据，请检查 akshare 数据源')

    return mape_actuals


if __name__ == '__main__':
    collect_2026q1_for_mape()
