"""
FIDAC 财务指标计算模块
====================
统一的财务指标计算、数据加载、风险评估函数库。
消除 Notebook 中重复代码，确保数据一致性。
"""

import numpy as np
import pandas as pd
from pathlib import Path


# ============================================================
# 数据加载
# ============================================================

def integrate_financial_data(company_code: str, data_dir: str = 'data') -> pd.DataFrame:
    """读取三大报表，转置合并为 期 × 指标 DataFrame"""
    file_path = Path(data_dir) / f'{company_code}_财务数据.xlsx'
    df_balance = pd.read_excel(file_path, sheet_name='资产负债表', index_col=0)
    df_income  = pd.read_excel(file_path, sheet_name='利润表', index_col=0)
    df_cash    = pd.read_excel(file_path, sheet_name='现金流量表', index_col=0)

    df_balance = df_balance.T.add_suffix('_资产')
    df_income  = df_income.T.add_suffix('_利润')
    df_cash    = df_cash.T.add_suffix('_现金流')

    return pd.concat([df_income, df_balance, df_cash], axis=1).fillna(0)


def load_all_ratios(data_dir: str = 'data') -> dict:
    """
    从各公司 Excel 的"财务指标表" Sheet 加载预计算指标。
    如果某公司没有该 Sheet，返回 None 并打印提示。
    """
    all_ratios = {}
    for fp in Path(data_dir).glob('*_财务数据.xlsx'):
        code = fp.stem.replace('_财务数据', '')
        try:
            df = pd.read_excel(fp, sheet_name='财务指标表', index_col=0)
            df.index = df.index.astype(str)
            all_ratios[code] = df
        except Exception:
            print(f'  ⚠️ {code}: 无财务指标表 Sheet')
    return all_ratios


# ============================================================
# 财务指标计算（18 项）
# ============================================================

def compute_ratios(data: pd.DataFrame) -> pd.DataFrame:
    """
    从合并报表计算 18 项财务指标。
    返回 DataFrame (期 × 18指标)，与原 financial_ratio() 等价。
    """
    col = {
        '营收': '营业收入_利润', '营成': '营业成本_利润', '营利': '营业利润_利润',
        '净利': '净利润_利润', '归母净利': '归属于母公司所有者的净利润_利润',
        '利息': '其中：利息费用_利润', '存货': '存货_资产', '资产': '资产合计_资产',
        '负债': '负债合计_资产', '货币资金': '货币资金_资产', '应收': '应收账款_资产',
        '流资': '流动资产合计_资产', '流负': '流动负债合计_资产',
        '预付': '预付款项_资产', '权益': '归属于母公司所有者权益合计_资产',
    }

    # 有息负债列检测
    ib_keys = ['短期借款_资产', '长期借款_资产', '应付债券_资产', '一年内到期的非流动负债_资产']
    ib_cols = {k: data[k] for k in ib_keys if k in data.columns}
    has_ib = len(ib_cols) > 0

    # 经营现金流列检测
    ocf_col = None
    for c in data.columns:
        if '经营' in c and '现金流' in c and '净额' in c:
            ocf_col = c
            break

    new_cols = {}
    new_cols['息税前利润'] = data[col['营利']] + data[col['利息']]
    new_cols['毛利率'] = 1 - data[col['营成']] / data[col['营收']]
    new_cols['营业利润率'] = data[col['营利']] / data[col['营收']]
    new_cols['净利润率'] = data[col['净利']] / data[col['营收']]
    new_cols['净资产收益率'] = 2 * data[col['归母净利']] / (
        data[col['权益']] + data[col['权益']].shift(1))
    new_cols['存货周转率'] = 2 * data[col['营成']] / (
        data[col['存货']] + data[col['存货']].shift(1))
    new_cols['总资产周转率'] = 2 * data[col['营收']] / (
        data[col['资产']] + data[col['资产']].shift(1))
    new_cols['应收账款周转率'] = 2 * data[col['营收']] / (
        data[col['应收']] + data[col['应收']].shift(1))
    new_cols['流动比率'] = data[col['流资']] / data[col['流负']]
    new_cols['速动比率'] = (data[col['流资']] - data[col['存货']] - data[col['预付']]) / data[col['流负']]
    new_cols['利息保障倍数'] = new_cols['息税前利润'] / data[col['利息']]
    new_cols['资产负债率'] = data[col['负债']] / data[col['资产']]
    new_cols['货币资金占比'] = data[col['货币资金']] / data[col['资产']]
    new_cols['营业收入增长率'] = data[col['营收']] / data[col['营收']].shift(1) - 1
    new_cols['营业利润增长率'] = data[col['营利']] / data[col['营利']].shift(1) - 1
    new_cols['净利润增长率'] = data[col['净利']] / data[col['净利']].shift(1) - 1

    # 有息负债率
    if has_ib:
        total_ib = sum(ib_cols.values())
        new_cols['有息负债率'] = total_ib / data[col['资产']]
    else:
        new_cols['有息负债率'] = np.nan

    # 经营现金流/营收
    if ocf_col:
        new_cols['经营现金流/营收'] = data[ocf_col] / data[col['营收']]
    else:
        new_cols['经营现金流/营收'] = np.nan

    # 权益乘数
    new_cols['权益乘数'] = data[col['资产']] / data[col['权益']]

    df_new = pd.concat(new_cols, axis=1)

    ratio_cols = [
        '毛利率', '营业利润率', '净利润率', '净资产收益率',
        '存货周转率', '总资产周转率', '应收账款周转率',
        '流动比率', '速动比率', '利息保障倍数', '资产负债率', '货币资金占比',
        '营业收入增长率', '营业利润增长率', '净利润增长率',
        '有息负债率', '经营现金流/营收', '权益乘数'
    ]
    df = df_new[ratio_cols].iloc[1:].copy()
    df.index = data.index[1:]
    df[np.isinf(df)] = 0
    return df


# ============================================================
# K-Means 五维特征提取
# ============================================================

def extract_kmeans_features(data: pd.DataFrame, code: str, name: str) -> pd.DataFrame:
    """
    从合并报表提取 K-Means 五维特征（季度粒度）。
    与 compute_ratios 复用相同计算逻辑，避免重复代码。
    """
    ratios = compute_ratios(data)
    features = ['毛利率', '经营现金流/营收', '有息负债率', '存货周转率', '权益乘数']

    result = ratios[features].copy()
    result['code'] = code
    result['name'] = name
    result = result.dropna()
    return result


# ============================================================
# Altman Z-score
# ============================================================

def compute_zscore(data: pd.DataFrame, period: str = None) -> float:
    """
    计算 Altman Z-score（制造业公式）。
    Z = 1.2X1 + 1.4X2 + 3.3X3 + 0.6X4 + 1.0X5

    X1 = 营运资本/总资产
    X2 = 留存收益/总资产
    X3 = 息税前利润/总资产
    X4 = 股东权益/总负债
    X5 = 营业收入/总资产
    """
    if period:
        row = data.loc[period]
    else:
        row = data.iloc[-1]

    ta = row.get('资产合计_资产', 0)
    if ta == 0:
        return None

    x1 = (row.get('流动资产合计_资产', 0) - row.get('流动负债合计_资产', 0)) / ta

    retained = row.get('未分配利润_资产', 0) + row.get('盈余公积_资产', 0)
    x2 = retained / ta

    ebit = row.get('营业利润_利润', 0) + row.get('其中：利息费用_利润', 0)
    x3 = ebit / ta

    tl = row.get('负债合计_资产', 1)
    equity = row.get('归属于母公司所有者权益合计_资产', 0)
    x4 = equity / tl if tl != 0 else 0

    x5 = row.get('营业收入_利润', 0) / ta

    return 1.2 * x1 + 1.4 * x2 + 3.3 * x3 + 0.6 * x4 + 1.0 * x5


# Z-score 行业阈值
ZSCORE_THRESHOLDS = {
    'traditional': {'danger': 1.81, 'gray': 2.99},     # 传统制造业
    'new_energy':  {'danger': 1.20, 'gray': 2.20},     # 新能源车企
}


def zscore_status(z: float, industry: str = 'new_energy') -> str:
    """根据行业阈值判定 Z-score 状态"""
    thresholds = ZSCORE_THRESHOLDS.get(industry, ZSCORE_THRESHOLDS['traditional'])
    if z > thresholds['gray']:
        return '安全区'
    elif z >= thresholds['danger']:
        return '灰色区'
    else:
        return '危险区'


# ============================================================
# 杜邦分析
# ============================================================

def compute_dupont(data: pd.DataFrame, periods: list = None) -> list:
    """
    杜邦分析：ROE = 净利率 × 总资产周转率 × 权益乘数
    支持多期连环替代法分解。
    periods: 期列表，如 ['2022年报','2023年报','2024年报','2025年报']
             默认取最后 4 个年报
    """
    if periods is None:
        annual = [i for i in data.index if '年报' in str(i)]
        periods = annual[-4:] if len(annual) >= 4 else annual

    results = []
    for i in range(1, len(periods)):
        prev, curr = periods[i-1], periods[i]

        def get(item, col, period):
            return float(data.loc[period, item]) if item in data.columns else None

        col = data.columns
        npm_prev = get('净利润_利润', col, prev) / get('营业收入_利润', col, prev)
        npm_curr = get('净利润_利润', col, curr) / get('营业收入_利润', col, curr)
        tat_prev = get('营业收入_利润', col, prev) / get('资产合计_资产', col, prev)
        tat_curr = get('营业收入_利润', col, curr) / get('资产合计_资产', col, curr)
        em_prev  = get('资产合计_资产', col, prev) / get('归属于母公司所有者权益合计_资产', col, prev)
        em_curr  = get('资产合计_资产', col, curr) / get('归属于母公司所有者权益合计_资产', col, curr)

        roe_prev = npm_prev * tat_prev * em_prev
        roe_curr = npm_curr * tat_curr * em_curr

        # 连环替代法
        r0 = npm_prev * tat_prev * em_prev
        r1 = npm_curr * tat_prev * em_prev
        r2 = npm_curr * tat_curr * em_prev
        r3 = npm_curr * tat_curr * em_curr

        results.append({
            'period': f'{prev}→{curr}',
            'ROE_prev': roe_prev, 'ROE_curr': roe_curr, 'ROE_delta': roe_curr - roe_prev,
            'net_margin_prev': npm_prev, 'net_margin_curr': npm_curr,
            'net_margin_contrib': r1 - r0,
            'turnover_prev': tat_prev, 'turnover_curr': tat_curr,
            'turnover_contrib': r2 - r1,
            'leverage_prev': em_prev, 'leverage_curr': em_curr,
            'leverage_contrib': r3 - r2,
        })
    return results


# ============================================================
# 沃尔评分
# ============================================================

# 修正后的沃尔评分标准：营收增长率标准值上调，增加分档评分
WALLE_CRITERIA_V2 = {
    '毛利率':           (15, 0.15, 'higher'),
    '有息负债率':       (25, 0.40, 'center'),
    '流动比率':         (25, 1.5,  'center'),
    '总资产周转率':     (15, 0.8,  'higher'),
    '营业收入增长率':   (20, 0.30, 'tiered'),  # tiered 分档评分，避免天花板
}
TOTAL_WEIGHT_V2 = sum(w for w, _, _ in WALLE_CRITERIA_V2.values())


def tiered_ratio(val: float, std: float) -> float:
    """
    营收增长率分档评分：
      <15%:  比率 = val / std
      15-50%: 比率 = 1 + (val - 0.15) / 0.35
      >50%:  比率 = 2 + min(val - 0.50, 0.50) / 0.50  (上限 3.0)
    """
    if val < 0.15:
        return val / std if std != 0 else 0
    elif val <= 0.50:
        return 1 + (val - 0.15) / 0.35
    else:
        return min(2 + (val - 0.50) / 0.50, 3.0)


def compute_walle_score(ratio_row: pd.Series) -> dict:
    """
    计算沃尔评分。
    ratio_row: 包含各指标值的 Series（来自 compute_ratios 的最新一期）
    返回 {'总分': float, '明细': dict}
    """
    col_map = {
        '毛利率': '毛利率',
        '有息负债率': '有息负债率',
        '流动比率': '流动比率',
        '总资产周转率': '总资产周转率',
        '营业收入增长率': '营业收入增长率',
    }

    total = 0
    detail = {}
    for metric, (weight, std, direction) in WALLE_CRITERIA_V2.items():
        col_name = col_map[metric]
        if col_name not in ratio_row.index:
            continue
        val = ratio_row.get(col_name)
        if val is None or pd.isna(val) or std == 0:
            continue

        if direction == 'higher':
            ratio = val / std
        elif direction == 'lower':
            ratio = std / val if val != 0 else 0
        elif direction == 'center':
            ratio = 1 - abs(val - std) / max(std, abs(val), 0.01)
        elif direction == 'tiered':
            ratio = tiered_ratio(val, std)
        else:
            ratio = val / std

        ratio = max(0, min(3, ratio))  # 放宽到 [0, 3]
        score = ratio * 100 * weight / TOTAL_WEIGHT_V2
        total += score
        detail[metric] = {
            '实际值': round(val, 4), '标准值': std,
            '关系比率': round(ratio, 3), '得分': round(score, 1)
        }

    return {'总分': round(total, 1), '明细': detail}


# ============================================================
# 预测模型
# ============================================================

from sklearn.linear_model import Ridge
from sklearn.preprocessing import PolynomialFeatures


def forecast_ridge(series: pd.Series, forecast_periods: int = 4,
                   degree: int = 2, include_seasonality: bool = True):
    """
    Ridge 回归 + 多项式 + 季度季节性 趋势预测。
    """
    return _forecast_with_ridge(series, forecast_periods, degree, include_seasonality)


def _forecast_with_ridge(series, forecast_periods, degree, include_seasonality):
    """
    Ridge 回归 + 多项式 + 季度季节性 趋势预测。

    Args:
        series: 时间序列数据（index 为时期名，value 为指标值）
        forecast_periods: 预测期数（季度）
        degree: 多项式阶数（2=二次, 3=三次）
        include_seasonality: 是否加入季度季节性哑变量

    Returns:
        dict with keys: history_fit, forecast, forecast_upper, forecast_lower,
                        r2, residuals, sigma
    """
    y = series.values
    n = len(y)
    x_idx = np.arange(n).reshape(-1, 1)

    # 构建特征：多项式 + 季节性哑变量
    poly = PolynomialFeatures(degree=degree, include_bias=False)
    X_poly = poly.fit_transform(x_idx)

    if include_seasonality and n >= 4:
        # 季度哑变量 (Q1=0, Q2=1, Q3=2, Q4=3)
        # 根据 index 名称推断季度
        quarters = []
        for idx in series.index:
            idx_str = str(idx)
            if 'Q1' in idx_str:
                quarters.append(0)
            elif 'Q2' in idx_str:
                quarters.append(1)
            elif 'Q3' in idx_str:
                quarters.append(2)
            elif '年报' in idx_str or 'Q4' in idx_str or '12' in idx_str:
                quarters.append(3)
            else:
                quarters.append(0)

        from sklearn.preprocessing import OneHotEncoder
        ohe = OneHotEncoder(sparse_output=False, drop='first')
        X_season = ohe.fit_transform(np.array(quarters).reshape(-1, 1))
        X = np.hstack([X_poly, X_season])
    else:
        X = X_poly

    # Ridge 回归
    model = Ridge(alpha=1.0)
    model.fit(X, y)

    history_fit = model.predict(X)
    residuals = y - history_fit
    sigma = np.std(residuals)
    r2 = model.score(X, y)

    # 预测未来
    future_idx = np.arange(n, n + forecast_periods).reshape(-1, 1)
    X_future_poly = poly.transform(future_idx)

    if include_seasonality and n >= 4:
        # 推断未来季度
        last_q = quarters[-1] if quarters else 0
        future_quarters = [(last_q + i + 1) % 4 for i in range(forecast_periods)]
        X_future_season = ohe.transform(np.array(future_quarters).reshape(-1, 1))
        X_future = np.hstack([X_future_poly, X_future_season])
    else:
        X_future = X_future_poly

    pred = model.predict(X_future)
    upper = pred + 2 * sigma
    lower = pred - 2 * sigma

    return {
        'history_fit': history_fit,
        'forecast': pred,
        'forecast_upper': upper,
        'forecast_lower': lower,
        'r2': r2,
        'residuals': residuals,
        'sigma': sigma,
        'slope': model.coef_[1] if len(model.coef_) > 1 else model.coef_[0],
    }


# ============================================================
# 6 种预测方法对比
# ============================================================

def forecast_linear(series: pd.Series, forecast_periods: int = 4):
    """简单线性回归（基线方法）"""
    from sklearn.linear_model import LinearRegression
    y = series.values
    n = len(y)
    x = np.arange(n).reshape(-1, 1)
    model = LinearRegression().fit(x, y)
    fit = model.predict(x)
    residuals = y - fit
    sigma = np.std(residuals)
    future_x = np.arange(n, n + forecast_periods).reshape(-1, 1)
    pred = model.predict(future_x)
    return {
        'history_fit': fit, 'forecast': pred,
        'forecast_upper': pred + 2*sigma, 'forecast_lower': pred - 2*sigma,
        'r2': model.score(x, y), 'residuals': residuals, 'sigma': sigma,
    }


def forecast_exp_smoothing(series: pd.Series, forecast_periods: int = 4):
    """三次指数平滑（Holt-Winters）"""
    try:
        from statsmodels.tsa.holtwinters import ExponentialSmoothing
        y = series.values
        n = len(y)
        # 检测季节性周期
        seasonal_periods = 4 if n >= 8 else None
        if seasonal_periods:
            model = ExponentialSmoothing(
                y, trend='add', seasonal='add',
                seasonal_periods=seasonal_periods
            ).fit(optimized=True)
        else:
            model = ExponentialSmoothing(y, trend='add', seasonal=None).fit(optimized=True)
        fit = model.fittedvalues
        pred = model.forecast(forecast_periods)
        residuals = y - fit
        sigma = np.std(residuals)
        ss_res = np.sum(residuals**2)
        ss_tot = np.sum((y - np.mean(y))**2)
        r2 = 1 - ss_res/ss_tot if ss_tot > 0 else 0
        return {
            'history_fit': fit, 'forecast': pred.values if hasattr(pred, 'values') else np.array(pred),
            'forecast_upper': pred + 2*sigma, 'forecast_lower': pred - 2*sigma,
            'r2': r2, 'residuals': residuals, 'sigma': sigma,
        }
    except ImportError:
        return _fallback_ets(series, forecast_periods)


def _fallback_ets(series, forecast_periods):
    """无 statsmodels 时的简化 Holt-Winters"""
    y = series.values
    n = len(y)
    alpha, beta, gamma = 0.3, 0.05, 0.3
    season_len = 4 if n >= 8 else None
    # 初始化
    level = y[0]
    trend = (y[min(3, n-1)] - y[0]) / min(3, n-1) if n > 1 else 0
    if season_len and n >= 2*season_len:
        seasonal = np.array([y[i] - level for i in range(season_len)])
        seasonal = seasonal / np.mean(np.abs(seasonal)) if np.mean(np.abs(seasonal)) > 0 else np.zeros(season_len)
    else:
        seasonal = np.zeros(max(season_len or 1, 1))
    fit = np.zeros(n)
    for i in range(n):
        s_idx = i % len(seasonal) if season_len else 0
        fit[i] = level + seasonal[s_idx]
        if i < n - 1:
            new_level = alpha * (y[i] - seasonal[s_idx]) + (1-alpha) * (level + trend)
            new_trend = beta * (new_level - level) + (1-beta) * trend
            new_season = gamma * (y[i] - new_level) + (1-gamma) * seasonal[s_idx]
            level, trend = new_level, new_trend
            seasonal[s_idx] = new_season
    residuals = y - fit
    sigma = np.std(residuals)
    pred = np.array([level + (i+1)*trend + seasonal[(n+i) % len(seasonal)] for i in range(forecast_periods)])
    ss_res = np.sum(residuals**2)
    ss_tot = np.sum((y - np.mean(y))**2)
    r2 = 1 - ss_res/ss_tot if ss_tot > 0 else 0
    return {
        'history_fit': fit, 'forecast': pred,
        'forecast_upper': pred + 2*sigma, 'forecast_lower': pred - 2*sigma,
        'r2': r2, 'residuals': residuals, 'sigma': sigma,
    }


def forecast_arima(series: pd.Series, forecast_periods: int = 4):
    """ARIMA 自回归积分滑动平均"""
    try:
        from statsmodels.tsa.arima.model import ARIMA
        y = series.values
        n = len(y)
        try:
            model = ARIMA(y, order=(2, 1, 2)).fit()
        except Exception:
            model = ARIMA(y, order=(1, 1, 0)).fit()
        # fittedvalues 长度 = n - d (d=1 for integrated=1)
        fit_raw = model.fittedvalues
        fit_len = len(fit_raw)
        # 对齐：前面补 NaN，后面用 fittedvalues
        fit_aligned = np.full(n, np.nan)
        fit_aligned[n - fit_len:] = fit_raw
        # 用实际值填充 NaN 位置
        for i in range(n - fit_len):
            fit_aligned[i] = y[i]
        pred = model.forecast(forecast_periods)
        pred = np.array(pred) if hasattr(pred, 'values') else pred
        residuals = y - fit_aligned
        sigma = np.std(residuals)
        ss_res = np.sum(residuals**2)
        ss_tot = np.sum((y - np.mean(y))**2)
        r2 = 1 - ss_res/ss_tot if ss_tot > 0 else 0
        return {
            'history_fit': fit_aligned, 'forecast': pred,
            'forecast_upper': pred + 2*sigma, 'forecast_lower': pred - 2*sigma,
            'r2': r2, 'residuals': residuals, 'sigma': sigma,
        }
    except ImportError:
        return _fallback_arima(series, forecast_periods)
    except Exception:
        return _fallback_arima(series, forecast_periods)


def _fallback_arima(series, forecast_periods):
    """无 statsmodels 时的简化 AR(1)"""
    y = series.values
    n = len(y)
    # 差分
    diff = np.diff(y)
    mean_diff = np.mean(diff)
    # AR(1) on differenced series
    if len(diff) > 1:
        x = diff[:-1].reshape(-1, 1)
        yt = diff[1:]
        from sklearn.linear_model import LinearRegression
        model = LinearRegression().fit(x, yt)
        last_diff = diff[-1]
        pred_diffs = [last_diff]
        for _ in range(forecast_periods - 1):
            next_d = model.predict([[pred_diffs[-1]]])[0]
            pred_diffs.append(next_d)
        pred = np.array([y[-1] + mean_diff + sum(pred_diffs[:i+1]) for i in range(forecast_periods)])
        fit = np.zeros(n)
        fit[0] = y[0]
        for i in range(1, n):
            fit[i] = fit[i-1] + mean_diff + model.predict([[diff[i-1]]])[0]
    else:
        pred = np.array([y[-1] + mean_diff * (i+1) for i in range(forecast_periods)])
        fit = y.copy()
    residuals = y - fit
    sigma = np.std(residuals)
    ss_res = np.sum(residuals**2)
    ss_tot = np.sum((y - np.mean(y))**2)
    r2 = 1 - ss_res/ss_tot if ss_tot > 0 else 0
    return {
        'history_fit': fit, 'forecast': pred,
        'forecast_upper': pred + 2*sigma, 'forecast_lower': pred - 2*sigma,
        'r2': r2, 'residuals': residuals, 'sigma': sigma,
    }


def forecast_lstm(series: pd.Series, forecast_periods: int = 4,
                  epochs: int = 200, hidden_size: int = 16):
    """
    LSTM 时序预测（轻量实现，支持 PyTorch / 纯 NumPy 回退）。
    小样本场景下自动降低复杂度防止过拟合。
    """
    try:
        return _forecast_lstm_pytorch(series, forecast_periods, epochs, hidden_size)
    except ImportError:
        return _forecast_lstm_numpy(series, forecast_periods)


def _forecast_lstm_pytorch(series, forecast_periods, epochs, hidden_size):
    """PyTorch LSTM 实现"""
    import torch
    import torch.nn as nn
    from torch.utils.data import DataLoader, TensorDataset

    y = series.values.astype(np.float32)
    n = len(y)

    # 标准化
    mu, std = np.mean(y), np.std(y)
    if std == 0:
        std = 1
    y_norm = (y - mu) / std

    # 构建序列数据 (window_size=3)
    window = min(3, n // 2)
    X, Y = [], []
    for i in range(n - window):
        X.append(y_norm[i:i+window])
        Y.append(y_norm[i+window])
    X, Y = np.array(X), np.array(Y)

    # 小样本：减少训练轮数
    effective_epochs = min(epochs, max(50, n * 5))

    # LSTM 模型
    class SimpleLSTM(nn.Module):
        def __init__(self):
            super().__init__()
            self.lstm = nn.LSTM(1, hidden_size, batch_first=True)
            self.fc = nn.Linear(hidden_size, 1)
        def forward(self, x):
            out, _ = self.lstm(x)
            return self.fc(out[:, -1, :])

    model = SimpleLSTM()
    X_t = torch.tensor(X).unsqueeze(-1)
    Y_t = torch.tensor(Y).unsqueeze(-1)
    dataset = TensorDataset(X_t, Y_t)
    loader = DataLoader(dataset, batch_size=min(4, len(dataset)), shuffle=True)

    criterion = nn.MSELoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=0.01)

    for _ in range(effective_epochs):
        for bx, by in loader:
            pred = model(bx)
            loss = criterion(pred, by)
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

    # 预测
    model.eval()
    with torch.no_grad():
        # 历史拟合
        fit_norm = model(X_t).squeeze(-1).numpy()
        # 自回归预测未来
        last_window = torch.tensor(y_norm[-window:]).unsqueeze(0).unsqueeze(-1)
        preds = []
        for _ in range(forecast_periods):
            p = model(last_window).item()
            preds.append(p)
            # 滑动窗口更新
            new_window = np.roll(last_window.squeeze().numpy(), -1)
            new_window[-1] = p
            last_window = torch.tensor(new_window).unsqueeze(0).unsqueeze(-1)

    fit = fit_norm * std + mu
    pred = np.array(preds) * std + mu
    residuals = y[window:] - fit

    sigma = np.std(residuals)
    ss_res = np.sum(residuals**2)
    ss_tot = np.sum((y[window:] - np.mean(y[window:]))**2)
    r2 = 1 - ss_res/ss_tot if ss_tot > 0 else 0

    return {
        'history_fit': fit, 'forecast': pred,
        'forecast_upper': pred + 2*sigma, 'forecast_lower': pred - 2*sigma,
        'r2': r2, 'residuals': residuals, 'sigma': sigma,
    }


def _forecast_lstm_numpy(series, forecast_periods):
    """纯 NumPy 简易 LSTM 回退（GRU-like 门控）"""
    y = series.values
    n = len(y)
    mu, std = np.mean(y), np.std(y)
    if std == 0:
        std = 1
    y_norm = (y - mu) / std

    window = min(3, n // 2)
    X, Y = [], []
    for i in range(n - window):
        X.append(y_norm[i:i+window])
        Y.append(y_norm[i+window])
    X, Y = np.array(X), np.array(Y)

    # 简单线性模型模拟门控
    from sklearn.linear_model import Ridge
    model = Ridge(alpha=1.0)
    model.fit(X, Y)
    fit = model.predict(X)
    residuals = Y - fit
    sigma = np.std(residuals)

    # 预测
    preds = []
    last = y_norm[-window:]
    for _ in range(forecast_periods):
        p = model.predict([last])[0]
        preds.append(p)
        last = np.roll(last, -1)
        last[-1] = p

    fit_full = np.zeros(n)
    fit_full[window:] = fit
    fit_full[:window] = y[:window]

    ss_res = np.sum(residuals**2)
    ss_tot = np.sum((Y - np.mean(Y))**2)
    r2 = 1 - ss_res/ss_tot if ss_tot > 0 else 0

    return {
        'history_fit': fit_full,
        'forecast': np.array(preds) * std + mu,
        'forecast_upper': np.array(preds) * std + mu + 2*sigma*std,
        'forecast_lower': np.array(preds) * std + mu - 2*sigma*std,
        'r2': r2, 'residuals': residuals, 'sigma': sigma * std,
    }


def forecast_prophet_method(series: pd.Series, forecast_periods: int = 4):
    """
    Prophet 时序预测（修正参数）。
    yearly_seasonality=False, changepoint_prior_scale=0.01
    """
    import os, tempfile
    try:
        from prophet import Prophet
        import logging
        logging.getLogger('prophet').setLevel(logging.CRITICAL)
        logging.getLogger('cmdstanpy').setLevel(logging.CRITICAL)

        # 临时目录
        clean_dir = os.path.join(tempfile.gettempdir(), 'prophet_cmp')
        os.makedirs(clean_dir, exist_ok=True)
        _orig = os.getcwd()
        os.chdir(clean_dir)

        n = len(series)
        df_p = pd.DataFrame({'ds': pd.date_range('2016-03-31', periods=n, freq='QE'),
                             'y': series.values})

        # 检测边界约束
        if series.min() >= 0 and series.max() <= 1:
            df_p['cap'] = 1.0
            df_p['floor'] = -0.2
            m = Prophet(growth='logistic', yearly_seasonality=False,
                       weekly_seasonality=False, daily_seasonality=False,
                       changepoint_prior_scale=0.01)
            m.fit(df_p)
            future = m.make_future_dataframe(periods=forecast_periods, freq='QE')
            future['cap'] = 1.0
            future['floor'] = -0.2
        else:
            m = Prophet(growth='linear', yearly_seasonality=False,
                       weekly_seasonality=False, daily_seasonality=False,
                       changepoint_prior_scale=0.01)
            m.fit(df_p)
            future = m.make_future_dataframe(periods=forecast_periods, freq='QE')

        fc = m.predict(future)
        hist = fc[fc['ds'] <= df_p['ds'].max()]
        future_fc = fc[fc['ds'] > df_p['ds'].max()]

        fit = hist['yhat'].values[:n]
        pred = future_fc['yhat'].values[:forecast_periods]
        residuals = series.values - fit
        sigma = np.std(residuals)

        ss_res = np.sum(residuals**2)
        ss_tot = np.sum((series.values - np.mean(series.values))**2)
        r2 = 1 - ss_res/ss_tot if ss_tot > 0 else 0

        os.chdir(_orig)
        return {
            'history_fit': fit, 'forecast': pred,
            'forecast_upper': future_fc['yhat_upper'].values[:forecast_periods],
            'forecast_lower': future_fc['yhat_lower'].values[:forecast_periods],
            'r2': r2, 'residuals': residuals, 'sigma': sigma,
        }
    except ImportError:
        os.chdir(_orig) if '_orig' in dir() else None
        return forecast_linear(series, forecast_periods)
    except Exception:
        # cmdstanpy error (code 3221225785) or other Prophet failures
        os.chdir(_orig) if '_orig' in dir() else None
        return forecast_linear(series, forecast_periods)


# 6 种方法注册表
FORECAST_METHODS = {
    'Ridge回归':     forecast_ridge,
    'Prophet':       forecast_prophet_method,
    'LSTM':          forecast_lstm,
    '三次指数平滑':  forecast_exp_smoothing,
    'ARIMA':         forecast_arima,
    '线性回归':      forecast_linear,
}


def compare_all_forecasts(series: pd.Series, forecast_periods: int = 4,
                          skip_methods: list = None):
    """
    运行全部 6 种预测方法，返回对比结果。
    skip_methods: 可选跳过列表，如 ['Prophet']（未安装时）
    """
    skip = set(skip_methods or [])
    results = {}
    for name, func in FORECAST_METHODS.items():
        if name in skip:
            continue
        try:
            results[name] = func(series, forecast_periods)
        except Exception as e:
            print(f'  ⚠️ {name}: 失败 ({e})')
    return results


def compute_forecast_metrics(y_true, y_pred):
    """计算预测评估指标: MAPE, RMSE, MAE, R²"""
    y_true = np.array(y_true)
    y_pred = np.array(y_pred)
    mask = y_true != 0
    mape = np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100 if mask.any() else np.nan
    rmse = np.sqrt(np.mean((y_true - y_pred)**2))
    mae = np.mean(np.abs(y_true - y_pred))
    ss_res = np.sum((y_true - y_pred)**2)
    ss_tot = np.sum((y_true - np.mean(y_true))**2)
    r2 = 1 - ss_res/ss_tot if ss_tot > 0 else 0
    return {'MAPE': mape, 'RMSE': rmse, 'MAE': mae, 'R²': r2}
