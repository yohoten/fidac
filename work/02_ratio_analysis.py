#!/usr/bin/env python3
"""
财务比率分析 — 基于四维能力框架
================================
从 output/ 读取采集好的标准化财务数据，执行:
  1. 盈利能力分析（毛利率/净利率/ROE/ROA）
  2. 偿债能力分析（流动比/速动比/资产负债率/利息保障倍数）
  3. 营运能力分析（存货周转/应收周转/总资产周转）
  4. 发展能力分析（营收YOY/利润YOY/资本积累率）

框架依据: 《财务报告分析（微课版）》第7-10章
可直接用 jupyter notebook 或 python 运行
"""

import sys
sys.stdout.reconfigure(encoding='utf-8')

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime

# 使用 matplotlib 支持中文
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

# 中文字体设置
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# ======================== 配置 ========================

BASE_DIR = Path(r'F:\（8）Desktop\财务数智决策应用赛_260725')
DATA_DIR = BASE_DIR / 'data'
WORK_DIR = BASE_DIR / 'work'
WORK_DIR.mkdir(exist_ok=True)

COMPANIES = [
    # A股
    ('601127', '赛力斯', '财务数据'), ('002594', '比亚迪', '财务数据'),
    ('000625', '长安汽车', '财务数据'), ('601633', '长城汽车', '财务数据'),
    ('600418', '江淮汽车', '财务数据'), ('600104', '上汽集团', '财务数据'),
    ('601238', '广汽集团', '财务数据'), ('600733', '北汽蓝谷', '财务数据'),
    # 港股 (suffix: _HK)
    ('00175', '吉利汽车', '财务数据_HK'), ('02015', '理想汽车', '财务数据_HK'),
    ('09868', '小鹏汽车', '财务数据_HK'), ('09866', '蔚来汽车', '财务数据_HK'),
    ('09863', '零跑汽车', '财务数据_HK'),
    # 美股
    ('TSLA', '特斯拉', '财务数据_US'),
]

# ======================== 数据加载 ========================

def load_derived_metrics(symbol, name, suffix='财务数据'):
    """加载某公司的派生指标，支持多种文件命名"""
    for pattern in [f'{symbol}_{name}_{suffix}.xlsx', f'{symbol}_{name}_财务数据.xlsx',
                    f'{name}_无公开财报_模板.xlsx']:
        path = DATA_DIR / pattern
        if path.exists():
            xl = pd.ExcelFile(path)
            if '财务分析指标' in xl.sheet_names:
                return pd.read_excel(xl, sheet_name='财务分析指标', index_col=0)
            if '港股财务指标' in xl.sheet_names:
                # HK data is already in indicator format
                return pd.read_excel(xl, sheet_name='港股财务指标', index_col=0)
            break
    return None


def load_financial_statement(symbol, name, sheet, suffix='财务数据'):
    """加载某公司的某张报表"""
    for pattern in [f'{symbol}_{name}_{suffix}.xlsx', f'{symbol}_{name}_财务数据.xlsx']:
        path = DATA_DIR / pattern
        if path.exists():
            xl = pd.ExcelFile(path)
            if sheet in xl.sheet_names:
                return pd.read_excel(xl, sheet_name=sheet, index_col=0)
            break
    return None
    if not path.exists():
        return None
    xl = pd.ExcelFile(path)
    if sheet in xl.sheet_names:
        return pd.read_excel(xl, sheet_name=sheet, index_col=0)
    return None


# ======================== 分析函数 ========================

def analyze_profitability(all_metrics):
    """
    盈利能力分析（第8章）
    核心指标: 毛利率, 净利率, ROE, ROA, 营业利润率
    """
    print('\n' + '='*80)
    print('  盈利能力分析 (第8章: 资本经营→资产经营→商品经营)')
    print('='*80)

    key_metrics = ['毛利率(%)', '净利率(%)', 'ROE(%)', 'ROA(%)',
                   '营业利润率(%)', '研发费用率(%)']

    for name, df in all_metrics.items():
        if df is None or df.empty:
            continue
        annual_cols = [c for c in df.columns if '年报' in str(c)]
        if not annual_cols:
            continue
        latest, prev = annual_cols[-1], annual_cols[-2] if len(annual_cols) > 1 else annual_cols[-1]

        print(f'\n  {name}:')
        for metric in key_metrics:
            if metric in df.index:
                curr = df.loc[metric, latest] if latest in df.columns else None
                prev_val = df.loc[metric, prev] if prev in df.columns and prev in df.index else None
                status = ''
                if curr is not None and prev_val is not None:
                    change = curr - prev_val
                    status = f'(变动: {change:+.2f}pct)'
                curr_str = f'{curr:.2f}%' if curr is not None else 'N/A'
                print(f'    {metric:<20s}: {curr_str:>10s}  {status}')

    return True


def analyze_solvency(all_metrics):
    """
    偿债能力分析（第9章）
    短期: 流动比率, 速动比率, 保守速动比率
    长期: 资产负债率, 产权比率, Altman Z-score
    """
    print('\n' + '='*80)
    print('  偿债能力分析 (第9章: 短期+长期)')
    print('='*80)

    key_metrics = ['流动比率', '速动比率', '保守速动比率',
                   '资产负债率(%)', '产权比率(%)', 'Altman Z-score']

    for name, df in all_metrics.items():
        if df is None or df.empty:
            continue
        annual_cols = [c for c in df.columns if '年报' in str(c)]
        if not annual_cols:
            continue
        latest = annual_cols[-1]

        print(f'\n  {name}:')
        for metric in key_metrics:
            if metric in df.index:
                val = df.loc[metric, latest] if latest in df.columns else None
                if val is not None:
                    # 安全阈值判断
                    warn = ''
                    if metric == '流动比率' and val < 1.5:
                        warn = '⚠️ 偏低'
                    elif metric == '速动比率' and val < 0.8:
                        warn = '⚠️ 偏低'
                    elif metric == '资产负债率(%)' and val > 70:
                        warn = '⚠️ 高杠杆'
                    elif metric == 'Altman Z-score' and val < 1.81:
                        warn = '🔴 危险区'
                    print(f'    {metric:<20s}: {val:>10.2f}  {warn}')
                else:
                    print(f'    {metric:<20s}: {"N/A":>10s}')


def analyze_operational(all_metrics):
    """
    营运能力分析（第7章）
    存货周转率/天数, 应收账款周转率/天数, 总资产周转率
    """
    print('\n' + '='*80)
    print('  营运能力分析 (第7章: 流动资产管理→总资产营运)')
    print('='*80)

    key_metrics = ['存货周转率(次)', '存货周转天数(天)',
                   '应收账款周转率(次)', '应收账款周转天数(天)',
                   '总资产周转率(次)', '流动资产周转率(次)']

    for name, df in all_metrics.items():
        if df is None or df.empty:
            continue
        annual_cols = [c for c in df.columns if '年报' in str(c)]
        if not annual_cols:
            continue
        latest = annual_cols[-1]

        print(f'\n  {name}:')
        for metric in key_metrics:
            if metric in df.index:
                val = df.loc[metric, latest] if latest in df.columns else None
                val_str = f'{val:.2f}' if val is not None else 'N/A'
                print(f'    {metric:<20s}: {val_str:>10s}')


def analyze_growth(all_metrics):
    """
    发展能力分析（第10章）
    营收同比, 净利润同比, 总资产增长率
    """
    print('\n' + '='*80)
    print('  发展能力分析 (第10章: 营业发展+财务发展)')
    print('='*80)

    key_metrics = ['营收同比(%)', '净利润同比(%)', '总资产增长率(%)']

    for name, df in all_metrics.items():
        if df is None or df.empty:
            continue
        annual_cols = [c for c in df.columns if '年报' in str(c)]
        if not annual_cols:
            continue
        latest = annual_cols[-1]

        print(f'\n  {name}:')
        for metric in key_metrics:
            if metric in df.index:
                val = df.loc[metric, latest] if latest in df.columns else None
                val_str = f'{val:.2f}%' if val is not None else 'N/A'
                direction = '↑' if val and val > 0 else ('↓' if val and val < 0 else '→')
                print(f'    {metric:<20s}: {val_str:>10s}  {direction}')


def plot_comparison_radar(all_metrics):
    """
    绘制雷达图：8家公司在关键维度上的对比
    """
    print('\n' + '='*80)
    print('  生成雷达图...')
    print('='*80)

    # 选择5个代表性指标
    radar_metrics = ['毛利率(%)', '净利率(%)', 'ROE(%)',
                     '资产负债率(%)', '总资产周转率(次)']

    values = {}
    for name, df in all_metrics.items():
        if df is None or df.empty:
            continue
        annual_cols = [c for c in df.columns if '年报' in str(c)]
        if not annual_cols:
            continue
        latest = annual_cols[-1]
        vals = []
        for metric in radar_metrics:
            if metric in df.index:
                v = df.loc[metric, latest] if latest in df.columns else None
                vals.append(v if v is not None else 0)
            else:
                vals.append(0)
        values[name] = vals

    # 保存数值到 CSV（后续用Excel画图）
    df_radar = pd.DataFrame(values, index=radar_metrics)
    df_radar.to_excel(WORK_DIR / '雷达图数据.xlsx')
    print(f'  ✅ 雷达图数据已保存: work/雷达图数据.xlsx')

    return df_radar


def generate_summary_report(all_metrics):
    """
    生成综合财务分析报告摘要
    """
    print('\n' + '='*80)
    print('  综合财务分析报告摘要')
    print('='*80)

    # 找出优势公司
    best = {}
    metrics_to_check = ['毛利率(%)', '净利率(%)', 'ROE(%)']
    for name, df in all_metrics.items():
        if df is None or df.empty:
            continue
        annual_cols = [c for c in df.columns if '年报' in str(c)]
        if not annual_cols:
            continue
        latest = annual_cols[-1]

        for metric in metrics_to_check:
            if metric in df.index:
                val = df.loc[metric, latest] if latest in df.columns else None
                if val is not None:
                    if metric not in best or val > best[metric][1]:
                        best[metric] = (name, val)

    print('\n核心指标最佳公司:')
    for metric, (name, val) in best.items():
        print(f'  {metric}: {name} ({val:.2f}%)')


# ======================== 主流程 ========================

def main():
    print(f'{"="*80}')
    print(f'  企业财务大数据智能决策 — 比率分析')
    print(f'  框架: 《财务报告分析》第7-10章 四维能力分析')
    print(f'  {datetime.now():%Y-%m-%d %H:%M}')
    print(f'{"="*80}')

    # 加载所有公司的派生指标
    all_metrics = {}
    for symbol, name, suffix in COMPANIES:
        df = load_derived_metrics(symbol, name, suffix)
        if df is not None and not df.empty:
            all_metrics[name] = df
            print(f'  已加载: {name} ({df.shape[0]} 指标 × {df.shape[1]} 期)')
        else:
            print(f'  ⚠️ 未找到: {name} (等待数据采集完成)')

    if not all_metrics:
        print('\n❌ 未找到财务数据文件！请先运行 data/collect_financial_data.py')
        return

    # 四维分析
    analyze_profitability(all_metrics)
    analyze_solvency(all_metrics)
    analyze_operational(all_metrics)
    analyze_growth(all_metrics)

    # 可视化数据
    plot_comparison_radar(all_metrics)

    # 综合报告
    generate_summary_report(all_metrics)

    print(f'\n{"="*80}')
    print(f'  分析完成')
    print(f'{"="*80}')


if __name__ == '__main__':
    main()
