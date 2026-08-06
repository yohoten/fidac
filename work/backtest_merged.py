# ============================================================
# 模型回测（合并精简版）：2026Q1 实际 vs Prophet / 线性 / Ridge 预测
# ============================================================
# 修正点（相对 notebook cell14 + cell15）：
#   ① 训练集剔除 2026Q1 —— 原 cell15 把 2026Q1 纳入回归训练后
#     再预测"下一期"，比较对象错位（预测的是 2026Q2 而非 2026Q1）；
#  ② Prophet 预测直接复用 notebook 已训练 prophet_results
#     （注意：其中 2026Q1 属样本内，仅作方向参考）；
#  ③ 毛利率近零导致 MAPE 失真，追加 MAE 辅助判断；
#  ④ 统一从「财务指标表」读实际值，去除 2026Q1.1 重复行。
#
# 依赖：先运行 Prophet cell 得到 prophet_results（否则自动跳过 Prophet）
# ============================================================
import numpy as np
import pandas as pd
from lib.financial_metrics import forecast_linear, forecast_ridge

TARGETS = [('601127_赛力斯', '毛利率'), ('601127_赛力斯', '资产负债率'),
           ('000625_长安汽车', '毛利率'), ('000625_长安汽车', '资产负债率')]


def _load(code, drop_2026q1=False):
    """读取财务指标表；drop_2026q1=True 时剔除 2026Q1（含 2026Q1.1 重复行）"""
    df = pd.read_excel(f'data/{code}_财务数据.xlsx', sheet_name='财务指标表', index_col=0)
    df.index = df.index.astype(str)
    if drop_2026q1:
        df = df[~df.index.str.startswith('2026')]
    return df


def _mape(a, p):
    """MAPE(%)，实际值为 0 时返回 NaN（避免除零）"""
    return abs(a - p) / abs(a) * 100 if a != 0 else np.nan


rows = []
for code, metric in TARGETS:
    name = code.split('_')[1]
    hist = _load(code, drop_2026q1=True)          # 训练用历史（不含 2026Q1）
    act = _load(code).loc['2026Q1']               # 2026Q1 实际值
    series = hist[metric].replace(0, np.nan).dropna()
    if len(series) < 8 or pd.isna(act[metric]):
        print(f'  ⚠️ {name} {metric}: 数据不足，跳过')
        continue
    a = float(act[metric])

    pred = {}
    # Prophet：复用 notebook 已训练的 prophet_results（若存在）
    pr = globals().get('prophet_results', {})
    if (code, metric) in pr:
        fc = pr[(code, metric)]
        hit = fc[fc['ds'] == '2026-03-31']
        pred['Prophet'] = float(hit['yhat'].values[0]) if len(hit) else np.nan
    else:
        pred['Prophet'] = np.nan
    pred['线性'] = forecast_linear(series, 1)['forecast'][0]
    pred['Ridge'] = forecast_ridge(series, 1)['forecast'][0]

    r = {'公司': name, '指标': metric, '实际值': round(a, 4)}
    for k, v in pred.items():
        r[f'{k}预测'] = round(v, 4)
        r[f'{k}MAPE%'] = round(_mape(a, v), 2)
        r[f'{k}MAE'] = round(abs(a - v), 4)
    rows.append(r)

df = pd.DataFrame(rows)
print(df.to_string(index=False))
print('\n平均 MAPE(%) / MAE：')
print(df[[c for c in df.columns if 'MAPE' in c or c.endswith('MAE')]].mean().round(2).to_string())
