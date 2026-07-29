#!/usr/bin/env python3
"""
Prophet 时序预测 — 赛力斯 vs 长安 财务指标走势预测
===================================================
预测未来6-12个月的: 营业收入、净利润、毛利率、资产负债率
对比两家的走势方向（谁在"往下走"）
"""

import sys; sys.stdout.reconfigure(encoding='utf-8')
import pandas as pd, numpy as np
from pathlib import Path
from datetime import datetime
from prophet import Prophet
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei','SimHei']
plt.rcParams['axes.unicode_minus'] = False

DATA_DIR = Path(r'F:\（8）Desktop\财务数智决策应用赛_260725\FIDAC\data')
OUT_DIR = Path(r'F:\（8）Desktop\财务数智决策应用赛_260725\FIDAC\reports')
OUT_DIR.mkdir(exist_ok=True)

TARGETS = {
    '601127': '赛力斯',
    '000625': '长安汽车',
}

METRICS = ['营业收入', '净利润', '毛利率(%)', '资产负债率(%)']


def load_quarterly_data(code, name):
    """加载季度财务数据并转为 Prophet 格式"""
    path = DATA_DIR / f'{code}_{name}_财务数据.xlsx'
    if not path.exists():
        print(f'  ⚠️ 文件不存在: {path.name}')
        return None

    xl = pd.ExcelFile(path)
    df_is = pd.read_excel(xl, '利润表', index_col=0)
    df_bs = pd.read_excel(xl, '资产负债表', index_col=0)
    df_d = pd.read_excel(xl, '财务分析指标', index_col=0)

    # 构建季度数据
    records = []
    all_periods = [c for c in df_is.columns]

    for period in all_periods:
        dt = _period_to_date(period)
        if dt is None: continue

        rev = _get(df_is, '营业收入', period)
        cost = _get(df_is, '营业成本', period)
        np_ = _get(df_is, '净利润', period)
        ta = _get(df_bs, '资产合计', period) or _get(df_bs, '*资产合计', period)
        tl = _get(df_bs, '负债合计', period) or _get(df_bs, '*负债合计', period)

        gross_margin = (rev - cost) / rev * 100 if rev and cost and rev > 0 else None
        debt_ratio = tl / ta * 100 if tl and ta else None

        records.append({
            'ds': dt,
            'y_revenue': rev / 1e8 if rev else None,
            'y_net_profit': np_ / 1e8 if np_ else None,
            'y_gross_margin': gross_margin,
            'y_debt_ratio': debt_ratio,
        })

    return pd.DataFrame(records).dropna(subset=['y_revenue'])


def _get(df, item, col):
    if item in df.index and col in df.columns:
        v = df.loc[item, col]
        return float(v) if pd.notna(v) else None
    return None


def _period_to_date(period):
    """'2020Q1' → datetime; '2020年报' → datetime"""
    s = str(period)
    try:
        if 'Q' in s:
            y, q = s.split('Q')
            m = {'1':3,'2':6,'3':9}.get(q, 3)
            return pd.Timestamp(f'{y}-{m:02d}-15')
        elif '年报' in s:
            return pd.Timestamp(f'{s.replace("年报","")}-12-31')
        elif 'M' in s:
            parts = s.replace('M','-').split('-')
            return pd.Timestamp(f'{parts[0]}-{parts[1]}-15')
    except: pass
    return None


def run_prophet(df, name, metric, y_col, periods=8):
    """Prophet 预测"""
    df_p = df[['ds', y_col]].dropna().rename(columns={y_col: 'y'})
    if len(df_p) < 12:
        print(f'  {name} {metric}: 数据点不足({len(df_p)})，跳过')
        return None

    m = Prophet(yearly_seasonality=True, weekly_seasonality=False, daily_seasonality=False)
    m.fit(df_p)
    future = m.make_future_dataframe(periods=periods, freq='Q')
    forecast = m.predict(future)

    # 绘制
    fig, ax = plt.subplots(figsize=(12, 5))
    m.plot(forecast, ax=ax)
    ax.set_title(f'{name} — {metric} 季度趋势预测', fontsize=14)
    ax.set_xlabel('日期'); ax.set_ylabel(metric)
    fig.savefig(OUT_DIR / f'{name}_{metric}_prophet.png', dpi=120, bbox_inches='tight')
    plt.close(fig)

    # 趋势方向
    last_hist = forecast[forecast['ds'] <= df_p['ds'].max()]['trend'].iloc[-1]
    last_pred = forecast['trend'].iloc[-1]
    direction = '↑上升' if last_pred > last_hist else '↓下降'

    print(f'  {name} {metric}: 历史趋势={last_hist:.2f} → 预测={last_pred:.2f} [{direction}]')

    return forecast, direction


def main():
    print(f'{"="*60}')
    print(f'  Prophet 时序预测 — 赛力斯 vs 长安')
    print(f'{"="*60}\n')

    results = {}
    for code, name in TARGETS.items():
        print(f'[{name}]')
        df = load_quarterly_data(code, name)
        if df is None: continue
        results[name] = {}
        for metric, y_col in [
            ('营业收入(亿)', 'y_revenue'),
            ('净利润(亿)', 'y_net_profit'),
            ('毛利率', 'y_gross_margin'),
            ('资产负债率', 'y_debt_ratio'),
        ]:
            forecast, direction = run_prophet(df, name, metric, y_col) or (None, None)
            results[name][metric] = direction

    print(f'\n{"="*60}')
    print(f'  预测结论')
    print(f'{"="*60}')
    for name, metrics in results.items():
        directions = [f'{m}:{d}' for m, d in metrics.items() if d]
        print(f'  {name}: {", ".join(directions)}')

    print(f'\n图表已保存到 {OUT_DIR}/')


if __name__ == '__main__':
    main()
