#!/usr/bin/env python3
"""
杜邦分析 + Z-score预警 + 沃尔评分法
====================================
综合财务评价与预警模型（《财务报告分析》第11-12章）

包含:
  1. 杜邦分析（ROE分解 + 因素分析法）
  2. Altman Z-score 破产预警
  3. 沃尔评分法（Wolle Scoring）
  4. 综合对比排名
"""

import sys
sys.stdout.reconfigure(encoding='utf-8')

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(r'F:\（8）Desktop\财务数智决策应用赛_260725')
DATA_DIR = BASE_DIR / 'data'
WORK_DIR = BASE_DIR / 'work'
WORK_DIR.mkdir(exist_ok=True)

COMPANIES = [
    ('601127', '赛力斯'), ('002594', '比亚迪'), ('000625', '长安汽车'),
    ('601633', '长城汽车'), ('600418', '江淮汽车'), ('600104', '上汽集团'),
    ('601238', '广汽集团'), ('600733', '北汽蓝谷'),
]


def load_data(symbol, name):
    path = DATA_DIR / f'{symbol}_{name}_财务数据.xlsx'
    if not path.exists():
        return None, None, None, None
    xl = pd.ExcelFile(path)
    df_bs = pd.read_excel(xl, '资产负债表', index_col=0) if '资产负债表' in xl.sheet_names else None
    df_is = pd.read_excel(xl, '利润表', index_col=0) if '利润表' in xl.sheet_names else None
    df_cf = pd.read_excel(xl, '现金流量表', index_col=0) if '现金流量表' in xl.sheet_names else None
    df_d = pd.read_excel(xl, '财务分析指标', index_col=0) if '财务分析指标' in xl.sheet_names else None
    return df_bs, df_is, df_cf, df_d


def get_val(df, item, col):
    if df is not None and item in df.index and col in df.columns:
        v = df.loc[item, col]
        return float(v) if pd.notna(v) else None
    return None


def safe_div(a, b):
    return a / b if a and b and b != 0 else None


def dupont_analysis(df_bs, df_is, df_d):
    """
    杜邦分析: ROE = 净利率 × 总资产周转率 × 权益乘数
    因素分析法（连环替代法）量化各因子贡献
    """
    if df_is is None or df_bs is None:
        return {}

    annual_cols = [c for c in df_is.columns if '年报' in str(c)]
    if len(annual_cols) < 2:
        return {}

    results = {}
    for i, (prev, curr) in enumerate(zip(annual_cols[:-1], annual_cols[1:])):
        # 净利率
        npm_prev = get_val(df_is, '净利率(%)', prev) or \
                   (get_val(df_d, '净利率(%)', prev) if df_d is not None else None)
        npm_curr = get_val(df_is, '净利率(%)', curr) or \
                   (get_val(df_d, '净利率(%)', curr) if df_d is not None else None)

        # 总资产周转率
        rev_prev = get_val(df_is, '营业收入', prev)
        rev_curr = get_val(df_is, '营业收入', curr)
        ta_prev = get_val(df_bs, '三、资产合计', prev) or get_val(df_bs, '*资产合计', prev)
        ta_curr = get_val(df_bs, '三、资产合计', curr) or get_val(df_bs, '*资产合计', curr)
        tat_prev = safe_div(rev_prev, ta_prev) if rev_prev and ta_prev else None
        tat_curr = safe_div(rev_curr, ta_curr) if rev_curr and ta_curr else None

        # 权益乘数
        eq_prev = get_val(df_bs, '所有者权益（或股东权益）合计', prev)
        eq_curr = get_val(df_bs, '所有者权益（或股东权益）合计', curr)
        em_prev = safe_div(ta_prev, eq_prev) if ta_prev and eq_prev else None
        em_curr = safe_div(ta_curr, eq_curr) if ta_curr and eq_curr else None

        # ROE
        roe_prev = get_val(df_bs, 'ROE(%)', prev) or \
                   (get_val(df_d, 'ROE(%)', prev) if df_d is not None else None)
        roe_curr = get_val(df_bs, 'ROE(%)', curr) or \
                   (get_val(df_d, 'ROE(%)', curr) if df_d is not None else None)
        if roe_prev is None:
            roe_prev = npm_prev * tat_curr * em_curr if npm_prev and tat_curr and em_curr else None
        if roe_curr is None:
            roe_curr = npm_curr * tat_curr * em_curr if npm_curr and tat_curr and em_curr else None

        if all([npm_prev, npm_curr, tat_prev, tat_curr, em_prev, em_curr]):
            # 连环替代法
            r0 = npm_prev * tat_prev * em_prev  # 基期
            r1 = npm_curr * tat_prev * em_prev  # 替代净利率
            r2 = npm_curr * tat_curr * em_prev  # 替代周转率
            r3 = npm_curr * tat_curr * em_curr  # 替代权益乘数(=当前)

            delta_npm = r1 - r0  # 净利率变动影响
            delta_tat = r2 - r1  # 周转率变动影响
            delta_em = r3 - r2   # 权益乘数变动影响
            delta_total = r3 - r0  # ROE 总变动

            year_pair = f'{prev}→{curr}'
            results[year_pair] = {
                'ROE基期': r0, 'ROE当前': r3,
                'ROE变动': delta_total,
                '净利率贡献': delta_npm,
                '周转率贡献': delta_tat,
                '杠杆贡献': delta_em,
                '净利率基期': npm_prev, '净利率当期': npm_curr,
                '周转率基期': tat_prev, '周转率当期': tat_curr,
                '权益乘数基期': em_prev, '权益乘数当期': em_curr,
            }

    return results


def wolle_scoring(df_d, df_bs, df_is, df_cf):
    """
    沃尔评分法（第11.4节）
    选定9个关键比率 → 赋权 → 标准化 → 综合得分
    满分100分，盈利能力权重最大
    """
    if df_d is None or df_d.empty:
        return None

    annual_cols = [c for c in df_d.columns if '年报' in str(c)]
    if not annual_cols:
        return None
    latest = annual_cols[-1]

    # 指标定义: (指标名, 权重, 标准值, 方向)
    # 方向: 'higher' = 越高越好, 'lower' = 越低越好, 'center' = 越接近越好
    criteria = [
        ('净利率(%)', 20, 8.0, 'higher'),
        ('ROE(%)', 25, 10.0, 'higher'),
        ('总资产周转率(次)', 15, 1.5, 'higher'),
        ('资产负债率(%)', 10, 50.0, 'center'),
        ('流动比率', 10, 2.0, 'center'),
        ('存货周转率(次)', 8, 6.0, 'higher'),
        ('营收同比(%)', 10, 10.0, 'higher'),
        ('经营现金流/净利润', 2, 1.0, 'center'),
    ]
    weights = {name: w for name, w, std, dir in criteria}

    scores = {}
    total_score = 0
    total_weight = sum(weights.values())

    for metric, weight, std_val, direction in criteria:
        if metric in df_d.index:
            val = df_d.loc[metric, latest] if latest in df_d.columns else None
        elif metric == '存货周转率(次)' and df_bs is not None:
            val = get_val(df_bs, '存货周转率(次)', latest)
        elif metric == '流动比率' and df_d is not None:
            # Try from df_d
            pass
        else:
            val = None

        if val is None or np.isnan(val) or std_val == 0:
            scores[metric] = None
            continue

        if direction == 'higher':
            ratio = val / std_val
        elif direction == 'lower':
            ratio = std_val / val if val != 0 else 0
        else:  # center
            ratio = 1 - abs(val - std_val) / max(std_val, abs(val), 1)

        # 限制关系比率范围 [0, 2]
        ratio = max(0, min(2, ratio))
        scored = ratio * 100
        scores[metric] = scored
        total_score += scored * weight / total_weight

    return {
        '综合得分(满分100)': total_score,
        '各指标得分': scores,
        '评分日期': latest,
    }


def print_dupont_results(all_dupont):
    print('\n' + '='*80)
    print('  杜邦分析 — ROE 因素分解')
    print('='*80)
    for name, results in all_dupont.items():
        if not results:
            continue
        print(f'\n  {name}:')
        for period, data in list(results.items())[-2:]:  # 最近两期
            print(f'    [{period}]')
            print(f'      ROE: {data.get("ROE基期",0):.2f}% → {data.get("ROE当前",0):.2f}% '
                  f'(变动: {data.get("ROE变动",0):+.2f}%)')
            print(f'        净利率: {data.get("净利率基期",0):.2f}%→{data.get("净利率当期",0):.2f}% '
                  f'(贡献: {data.get("净利率贡献",0):+.2f}%)')
            print(f'        周转率: {data.get("周转率基期",0):.2f}→{data.get("周转率当期",0):.2f} '
                  f'(贡献: {data.get("周转率贡献",0):+.2f}%)')
            print(f'        权益乘数: {data.get("权益乘数基期",0):.2f}→{data.get("权益乘数当期",0):.2f} '
                  f'(贡献: {data.get("杠杆贡献",0):+.2f}%)')


def print_zscore_analysis(all_df_d):
    print('\n' + '='*80)
    print('  Altman Z-score 破产预警')
    print('  Z > 2.99 = 安全 | 1.81 ≤ Z ≤ 2.99 = 灰色 | Z < 1.81 = 危险')
    print('='*80)
    for name, df_d in all_df_d.items():
        if df_d is None or df_d.empty:
            continue
        annual_cols = [c for c in df_d.columns if '年报' in str(c)]
        if not annual_cols:
            continue
        latest = annual_cols[-1]
        z = get_val(df_d, 'Altman Z-score', latest)
        status = get_val(df_d, 'Z-score 判定', latest) if 'Z-score 判定' in df_d.index else None
        if z is not None:
            status_icon = '✅' if z > 2.99 else ('⚠️' if z >= 1.81 else '🔴')
            print(f'  {name:<10s}: Z={z:.2f}  {status_icon}  {status or ""}')


def print_wolle_ranking(all_wolle):
    print('\n' + '='*80)
    print('  沃尔评分法 — 综合排名')
    print('='*80)
    ranking = [(name, data['综合得分(满分100)']) for name, data in all_wolle.items()
               if data and data['综合得分(满分100)'] > 0]
    ranking.sort(key=lambda x: x[1], reverse=True)

    for rank, (name, score) in enumerate(ranking, 1):
        medal = '🥇' if rank == 1 else ('🥈' if rank == 2 else ('🥉' if rank == 3 else f'  {rank}'))
        print(f'  {medal}. {name:<10s}: {score:.1f} 分')


# ======================== 主流程 ========================

def main():
    print(f'{"="*80}')
    print(f'  杜邦分析 + Z-score + 沃尔评分')
    print(f'  《财务报告分析》第11-12章')
    print(f'  {datetime.now():%Y-%m-%d %H:%M}')
    print(f'{"="*80}')

    all_dupont = {}
    all_wolle = {}
    all_df_d = {}

    for symbol, name in COMPANIES:
        df_bs, df_is, df_cf, df_d = load_data(symbol, name)
        if df_d is None or df_d.empty:
            print(f'  ⚠️ 未找到: {name}')
            continue
        print(f'  已加载: {name}')
        all_df_d[name] = df_d

        # 杜邦分析
        dupont = dupont_analysis(df_bs, df_is, df_d)
        all_dupont[name] = dupont

        # 沃尔评分
        wolle = wolle_scoring(df_d, df_bs, df_is, df_cf)
        all_wolle[name] = wolle

    if not all_df_d:
        print('\n❌ 无数据，请先运行 data/collect_financial_data.py')
        return

    # 输出分析结果
    print_dupont_results(all_dupont)
    print_zscore_analysis(all_df_d)
    print_wolle_ranking(all_wolle)

    # 导出综合排名
    ranking = [(name, data['综合得分(满分100)']) for name, data in all_wolle.items()
               if data and data['综合得分(满分100)'] > 0]
    ranking.sort(key=lambda x: x[1], reverse=True)
    df_rank = pd.DataFrame(ranking, columns=['公司', '沃尔综合得分'])
    df_rank.to_excel(WORK_DIR / '沃尔评分排名.xlsx', index=False)

    print(f'\n{"="*80}')
    print(f'  分析完成 — 结果已导出到 work/')
    print(f'{"="*80}')


if __name__ == '__main__':
    main()
