# -*- coding: utf-8 -*-
"""
基于 K-Means 聚类与多模型时序预测的重庆上市车企财务智能预警研究
=================================================================
Streamlit 交互式可视化看板（单文件多页面）

页面：
  1. 🏠 项目总览         —— 研究背景、核心结论、8 家车企最新快照
  2. 📊 财务指标探索     —— 18 项财务指标时间趋势 / 公司对比 / 热力图
  3. 🔬 风险评估         —— K-Means 聚类、孤立森林、Z-score、沃尔评分、杜邦分析
  4. 🔮 时序预测         —— 6 种模型预测对比 + 2026Q1 样本外回测
  5. 🚗 行业 NEV 分析    —— 行业景气度、渗透率、季度销量结构、赛力斯 vs 长安
  6. 🖼️ 预生成图表库      —— 展示 Notebook / 行业分析输出的 PNG 图

运行： streamlit run streamlit_app.py
部署： Streamlit Community Cloud（关联 GitHub/Gitee 仓库，见 DEPLOY.md）
"""

import os
import sys
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

# ── 路径：无论从哪个目录启动都可用 ──────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
REPORTS_DIR = BASE_DIR / "reports"
sys.path.insert(0, str(BASE_DIR))

from lib import financial_metrics as fm

# ── 页面配置（必须是第一个 st 调用）─────────────────────────────
st.set_page_config(
    page_title="重庆上市车企财务智能预警看板",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "Get Help": None,        # 隐藏 Streamlit 默认帮助链接
        "Report a bug": None,    # 隐藏 Streamlit 默认反馈链接
        "About": "重庆上市车企财务智能预警研究 · FIDAC\nK-Means 聚类 · 多模型时序预测 · 8 家 A 股乘用车整车厂",
    },
)

# ============================================================
# 主题：深蓝黑（deep navy）可视化看板（参考 scenic-flow-prediction 配色）
# ============================================================
THEME = {
    "bg": "#001830",          # 参考主背景（深蓝黑）
    "surface": "#062A48",     # 面板/图表底（参考 #001848）
    "card": "#0C3050",        # 卡片（参考 #183048）
    "primary": "#3B82F6",
    "accent": "#4FC3F7",
    "cyan": "#22D3EE",
    "violet": "#8B5CF6",
    "amber": "#F59E0B",
    "text": "#F0F0F0",        # 参考亮白文字
    "muted": "#9FB4CC",       # 次级文字（蓝灰）
    "dim": "#7A90AB",         # 弱化文字
    "grid": "rgba(159,180,204,0.12)",
}

THEME_CSS = """<style>
/* ── 全局字体与背景 ── */
html, body, [class*="css"], [data-testid="stAppViewContainer"] {
    font-family: "Segoe UI", "Microsoft YaHei", "PingFang SC", "Noto Sans SC", sans-serif;
}
[data-testid="stAppViewContainer"] {
    background:
        radial-gradient(1200px 600px at 85% -10%, rgba(59,130,246,0.16), transparent 60%),
        radial-gradient(900px 520px at -10% 115%, rgba(34,211,238,0.10), transparent 55%),
        linear-gradient(180deg, #001830 0%, #061A2C 100%);
    color: #F0F0F0;
}
[data-testid="stHeader"] { background: transparent; }
[data-testid="stMainBlockContainer"] { padding-top: 1.0rem; }

/* ── 侧边栏 ── */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #001830 0%, #082138 100%);
    border-right: 1px solid rgba(59,130,246,0.18);
}
[data-testid="stSidebar"] .stMarkdown { color: #9FB4CC; }

/* ── 标题 ── */
h1, h2, h3 { letter-spacing: 0.3px; }
[data-testid="stMarkdownContainer"] h1 {
    background: linear-gradient(90deg, #7DD3FC 0%, #3B82F6 55%, #8B5CF6 100%);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    font-weight: 800;
}

/* ── 指标卡 ── */
[data-testid="stMetric"] {
    background: linear-gradient(160deg, rgba(12,48,80,0.92), rgba(6,42,72,0.92));
    border: 1px solid rgba(59,130,246,0.24);
    border-radius: 14px;
    padding: 14px 16px;
    box-shadow: 0 8px 24px rgba(0,0,0,0.35);
}
[data-testid="stMetricLabel"] { color: #9FB4CC; font-size: 0.84rem; }
[data-testid="stMetricValue"] { color: #F0F0F0; font-weight: 700; }

/* ── 数据表 ── */
[data-testid="stDataFrame"] {
    border: 1px solid rgba(59,130,246,0.18);
    border-radius: 12px;
    overflow: hidden;
    background: rgba(6,42,72,0.6);
}

/* ── 标签页 ── */
.stTabs [data-baseweb="tab-list"] { gap: 6px; border-bottom: 1px solid rgba(59,130,246,0.18); }
.stTabs [data-baseweb="tab"] {
    background: rgba(12,48,80,0.72);
    border: 1px solid rgba(148,163,184,0.16);
    border-radius: 10px 10px 0 0;
    padding: 7px 18px;
    color: #9FB4CC;
    transition: all .2s ease;
}
.stTabs [aria-selected="true"] {
    background: linear-gradient(180deg, rgba(59,130,246,0.28), rgba(59,130,246,0.06));
    border-color: rgba(59,130,246,0.55);
    color: #4FC3F7 !important;
    font-weight: 600;
}

/* ── 按钮 / 输入控件 ── */
.stButton button { border-radius: 10px; border: 1px solid rgba(59,130,246,0.3); }
.stButton button[kind="primary"] { background: linear-gradient(135deg, #3B82F6, #2563EB); border: none; }
[data-baseweb="select"] > div { background-color: #0A2A46; border-color: rgba(59,130,246,0.25); }
[data-baseweb="input"] > div { background-color: #0A2A46; border-color: rgba(59,130,246,0.25); }

/* ── 自定义组件 ── */
div.fidac-card {
    background: linear-gradient(160deg, rgba(12,48,80,0.85), rgba(6,42,72,0.85));
    border: 1px solid rgba(59,130,246,0.18);
    border-radius: 14px;
    padding: 16px 20px;
    box-shadow: 0 8px 28px rgba(0,0,0,0.35);
    margin-bottom: 8px;
    color: #D6E2F0;
    line-height: 1.8;
}
.fidac-card b { color: #F0F0F0; }
.fidac-card-title { color: #9FB4CC; font-size: 0.8rem; letter-spacing: 0.5px; }
.fidac-card-value { font-size: 1.7rem; font-weight: 800; color: #F0F0F0; margin: 4px 0; }
.fidac-card-sub { color: #7A90AB; font-size: 0.78rem; }

.fidac-hero { padding: 10px 4px 4px 4px; }
.fidac-badge {
    display: inline-block; font-size: 0.76rem; color: #4FC3F7;
    border: 1px solid rgba(59,130,246,0.45); border-radius: 999px;
    padding: 3px 14px; margin-bottom: 12px;
    background: rgba(59,130,246,0.10); letter-spacing: 1.5px;
}
.fidac-title {
    font-size: 2.15rem; font-weight: 800; line-height: 1.25;
    background: linear-gradient(90deg, #7DD3FC 0%, #3B82F6 55%, #8B5CF6 100%);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
}
.fidac-sub { color: #9FB4CC; margin-top: 6px; font-size: 0.98rem; }

.fidac-section {
    display: flex; align-items: center; gap: 8px;
    margin: 24px 0 12px 0;
    font-size: 1.14rem; font-weight: 700; color: #F0F0F0;
}
.fidac-section::after {
    content: ""; flex: 1; height: 1px;
    background: linear-gradient(90deg, rgba(59,130,246,0.5), transparent);
    margin-left: 10px;
}
.fidac-section-emoji { filter: drop-shadow(0 0 6px rgba(59,130,246,0.5)); }

.fidac-zrow {
    display: flex; align-items: center; gap: 8px;
    padding: 7px 2px;
    border-bottom: 1px dashed rgba(148,163,184,0.14);
}
.fidac-zrow:last-child { border-bottom: none; }

.fidac-sidebar-logo { font-size: 2.1rem; filter: drop-shadow(0 0 8px rgba(59,130,246,0.6)); }
.fidac-sidebar-title { font-size: 1.1rem; font-weight: 800; color: #F0F0F0; margin-top: 4px; }
.fidac-sidebar-sub { color: #9FB4CC; font-size: 0.8rem; margin-top: 2px; line-height: 1.6; }

/* 滚动条 */
::-webkit-scrollbar { width: 8px; height: 8px; }
::-webkit-scrollbar-thumb { background: rgba(59,130,246,0.3); border-radius: 8px; }
::-webkit-scrollbar-track { background: transparent; }

/* ── 打印导出 ── */
@media print {
    [data-testid="stSidebar"], [data-testid="stHeader"] { display: none; }
    [data-testid="stMainBlockContainer"] { max-width: 100%; padding: 0; }
    .fidac-card, [data-testid="stDataFrame"] { break-inside: avoid; box-shadow: none; }
}

/* ── 窄屏适配 ── */
@media (max-width: 768px) {
    [data-testid="stMetric"] { padding: 10px 12px; }
    .fidac-title { font-size: 1.5rem; }
    .fidac-card-value { font-size: 1.3rem; }
}
</style>"""


def inject_theme() -> None:
    """注入全局主题 CSS"""
    st.markdown(THEME_CSS, unsafe_allow_html=True)


# ── Plotly 暗色模板（蓝黑配色）──────────────────────────────
FIDAC_DARK = go.layout.Template(
    layout=dict(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor=THEME["surface"],
        font=dict(color=THEME["text"], family="'Segoe UI','Microsoft YaHei','PingFang SC',sans-serif"),
        colorway=["#3B9EFF", "#22D3EE", "#A78BFA", "#F59E0B", "#34D399", "#F472B6", "#F87171", "#60A5FA"],
        title_font=dict(color=THEME["text"]),
        xaxis=dict(gridcolor=THEME["grid"], zerolinecolor="rgba(148,163,184,0.25)",
                   linecolor="rgba(148,163,184,0.35)", tickfont=dict(color=THEME["muted"]),
                   title_font=dict(color=THEME["muted"])),
        yaxis=dict(gridcolor=THEME["grid"], zerolinecolor="rgba(148,163,184,0.25)",
                   linecolor="rgba(148,163,184,0.35)", tickfont=dict(color=THEME["muted"]),
                   title_font=dict(color=THEME["muted"])),
        legend=dict(font=dict(color=THEME["muted"]), bgcolor="rgba(0,0,0,0)"),
        hoverlabel=dict(bgcolor="#0A2A46", bordercolor=THEME["primary"], font=dict(color=THEME["text"])),
        coloraxis=dict(colorbar=dict(tickfont=dict(color=THEME["muted"]), title_font=dict(color=THEME["muted"]))),
    )
)
pio.templates["fidac_dark"] = FIDAC_DARK
px.defaults.template = "fidac_dark"

inject_theme()


# ── 主题化组件 helper ───────────────────────────────────────
Z_EMOJI = {"安全区": "🟢", "灰色区": "🟡", "危险区": "🔴"}
Z_COLOR = {"安全区": "#34D399", "灰色区": "#FBBF24", "危险区": "#F87171"}


def section_header(text: str, emoji: str = "🔖") -> None:
    """渐变高亮分区标题"""
    st.markdown(
        f'<div class="fidac-section"><span class="fidac-section-emoji">{emoji}</span>'
        f'<span class="fidac-section-text">{text}</span></div>',
        unsafe_allow_html=True,
    )


def stat_card(title: str, value: str, sub: str = "", accent: Optional[str] = None) -> str:
    """指标卡片 HTML"""
    accent = accent or THEME["accent"]
    return (
        f'<div class="fidac-card" style="border-left:3px solid {accent};">'
        f'<div class="fidac-card-title">{title}</div>'
        f'<div class="fidac-card-value">{value}</div>'
        f'<div class="fidac-card-sub">{sub}</div></div>'
    )


def hero_banner() -> None:
    """首页 Hero 横幅"""
    st.markdown(
        '<div class="fidac-hero">'
        '<div class="fidac-badge">FIDAC · 财务大数据智能决策</div>'
        '<div class="fidac-title">重庆上市车企财务智能预警研究</div>'
        '<div class="fidac-sub">K-Means 聚类 · 多模型时序预测 · 8 家 A 股乘用车整车厂</div>'
        '</div>',
        unsafe_allow_html=True,
    )


# ============================================================
# 常量
# ============================================================
COMPANY_MAP = {
    "000625": "长安汽车",
    "002594": "比亚迪",
    "600104": "上汽集团",
    "600418": "江淮汽车",
    "600733": "北汽蓝谷",
    "601127": "赛力斯",
    "601238": "广汽集团",
    "601633": "长城汽车",
}
NAME_TO_CODE = {v: k for k, v in COMPANY_MAP.items()}

RATIO_METRICS = [
    "毛利率", "营业利润率", "净利润率", "净资产收益率",
    "存货周转率", "总资产周转率", "应收账款周转率",
    "流动比率", "速动比率", "利息保障倍数", "资产负债率", "货币资金占比",
    "营业收入增长率", "营业利润增长率", "净利润增长率",
    "有息负债率", "经营现金流/营收", "权益乘数",
]

KMEANS_FEATURES = ["毛利率", "经营现金流/营收", "有息负债率", "存货周转率", "权益乘数"]

NEV_XLSX = "中国汽车行业多维销量数据库.xlsx"

Z_THRESH = fm.ZSCORE_THRESHOLDS["new_energy"]  # danger=1.20, gray=2.20

CLUSTER_COLORS = ["#F87171", "#3B9EFF", "#34D399", "#FBBF24", "#A78BFA"]

# ============================================================
# 数据加载（缓存）
# ============================================================
def _company_file(code: str) -> Path:
    """数据文件名形如 {code}_{公司名}_财务数据.xlsx"""
    return DATA_DIR / f"{code}_{COMPANY_MAP[code]}_财务数据.xlsx"


@st.cache_data(show_spinner=False)
def load_ratios(code: str) -> pd.DataFrame:
    """读取单家公司财务指标表（期 × 18指标）"""
    df = pd.read_excel(_company_file(code), sheet_name="财务指标表", index_col=0)
    df.index = df.index.astype(str)
    return df


@st.cache_data(show_spinner=False)
def load_merged(code: str) -> pd.DataFrame:
    """读取单家公司三大报表合并数据（用于 Z-score / 杜邦 / 聚类特征）"""
    path = _company_file(code)
    df_balance = pd.read_excel(path, sheet_name="资产负债表", index_col=0)
    df_income = pd.read_excel(path, sheet_name="利润表", index_col=0)
    df_cash = pd.read_excel(path, sheet_name="现金流量表", index_col=0)
    df_balance = df_balance.T.add_suffix("_资产")
    df_income = df_income.T.add_suffix("_利润")
    df_cash = df_cash.T.add_suffix("_现金流")
    return pd.concat([df_income, df_balance, df_cash], axis=1).fillna(0)


@st.cache_data(show_spinner=False)
def load_industry_sheet(sheet: str) -> pd.DataFrame:
    """读取行业多维销量数据库指定 Sheet"""
    return pd.read_excel(DATA_DIR / NEV_XLSX, sheet_name=sheet)


@st.cache_data(show_spinner=False)
def load_quarterly_structure(company: str) -> pd.DataFrame:
    """读取赛力斯/长安季度销量结构"""
    fname = f"{company}_季度销量结构.xlsx"
    return pd.read_excel(DATA_DIR / fname)


@st.cache_data(show_spinner=False)
def latest_ratio_snapshot() -> pd.DataFrame:
    """各公司最新一期 18 项指标快照"""
    rows = []
    for code, name in COMPANY_MAP.items():
        df = load_ratios(code).dropna(how="all")
        if df.empty:
            continue
        row = df.iloc[-1]
        period = str(row.name)
        rec = {"代码": code, "公司": name, "报告期": period}
        for m in RATIO_METRICS:
            rec[m] = row.get(m)
        rows.append(rec)
    return pd.DataFrame(rows)


# ============================================================
# 工具函数
# ============================================================
def fmt(v, digits: int = 2) -> str:
    if v is None or not isinstance(v, (int, float, np.number)):
        return "—"
    if pd.isna(v):
        return "—"
    return f"{float(v):.{digits}f}"


def layout_kwargs(title: str, **extra) -> dict:
    kw = dict(
        title=title,
        template="fidac_dark",
        height=480,
        margin=dict(l=40, r=20, t=60, b=40),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    kw.update(extra)
    return kw


def metric_trend_fig(df: pd.DataFrame, metrics: list, title: str) -> go.Figure:
    """时间趋势折线图"""
    fig = go.Figure()
    for m in metrics:
        s = df[m].dropna()
        if s.empty:
            continue
        fig.add_trace(go.Scatter(
            x=[str(i) for i in s.index], y=s.values,
            mode="lines+markers", name=m, connectgaps=False,
        ))
    fig.update_layout(**layout_kwargs(title))
    fig.update_xaxes(type="category")
    return fig


def latest_bar_fig(metric: str) -> go.Figure:
    """各公司最新一期横向条形图"""
    snap = latest_ratio_snapshot()
    d = snap[["公司", metric]].dropna()
    d = d.sort_values(metric)
    fig = px.bar(d, x=metric, y="公司", orientation="h", text_auto=".3f")
    fig.update_layout(**layout_kwargs(f"各公司最新一期 —— {metric}"))
    return fig


def metric_heatmap_fig(metrics: list) -> go.Figure:
    """最新一期 公司 × 指标 热力图"""
    snap = latest_ratio_snapshot()
    rows = {}
    for code, name in COMPANY_MAP.items():
        r = snap[snap["公司"] == name]
        if r.empty:
            continue
        rows[name] = [r.iloc[0].get(m) for m in metrics]
    d = pd.DataFrame(rows, index=metrics).T  # 公司 × 指标
    z = d.values.astype(float)
    fig = go.Figure(go.Heatmap(
        z=z, x=d.columns.tolist(), y=d.index.tolist(),
        colorscale="RdBu_r", zmid=0,
        text=np.round(z, 2), texttemplate="%{text}", textfont=dict(size=10, color="#0F172A"),
        colorbar=dict(title="值", tickfont=dict(color=THEME["muted"])),
    ))
    fig.update_layout(**layout_kwargs(
        "最新一期财务指标热力图（公司 × 指标）",
        height=max(300, 40 * len(metrics) + 180),
    ))
    return fig


# ============================================================
# 风险评估计算（缓存）
# ============================================================
@st.cache_data(show_spinner=False)
def build_feature_matrix() -> pd.DataFrame:
    """构建 8 家车企最新一期 5 维风险特征矩阵"""
    rows = []
    for code, name in COMPANY_MAP.items():
        data = load_merged(code)
        feat = fm.extract_kmeans_features(data, code, name)
        if feat.empty:
            continue
        latest = feat.iloc[-1]
        rec = {"代码": code, "公司": name, "报告期": str(latest.name)}
        for c in KMEANS_FEATURES:
            rec[c] = latest.get(c)
        rows.append(rec)
    return pd.DataFrame(rows)


@st.cache_data(show_spinner=False)
def run_clustering() -> tuple[pd.DataFrame, list, list]:
    """K-Means(K=3) + PCA 降维 + 肘部法则"""
    df = build_feature_matrix()
    X = df[KMEANS_FEATURES].to_numpy(dtype=float)
    scaler = StandardScaler()
    Xs = scaler.fit_transform(X)
    ks = list(range(2, min(7, len(df) + 1)))
    inertias = []
    for k in ks:
        km = KMeans(n_clusters=k, random_state=42, n_init=10).fit(Xs)
        inertias.append(float(km.inertia_))
    km = KMeans(n_clusters=3, random_state=42, n_init=10)
    labels = km.fit_predict(Xs)
    pca = PCA(n_components=2)
    Xp = pca.fit_transform(Xs)
    df["cluster"] = labels
    df["pc1"] = Xp[:, 0]
    df["pc2"] = Xp[:, 1]
    df["explained"] = pca.explained_variance_ratio_.sum()
    return df, ks, inertias


@st.cache_data(show_spinner=False)
def run_isolation() -> pd.DataFrame:
    """孤立森林异常检测"""
    df = build_feature_matrix()
    X = df[KMEANS_FEATURES].to_numpy(dtype=float)
    scaler = StandardScaler()
    Xs = scaler.fit_transform(X)
    iso = IsolationForest(contamination=0.15, random_state=42)
    labels = iso.fit_predict(Xs)
    scores = iso.decision_function(Xs)
    df["anomaly"] = labels
    df["anomaly_score"] = scores
    return df


@st.cache_data(show_spinner=False)
def compute_z_table() -> pd.DataFrame:
    """各公司最新一期 Altman Z-score"""
    rows = []
    for code, name in COMPANY_MAP.items():
        data = load_merged(code)
        try:
            z = fm.compute_zscore(data)
        except Exception:
            z = None
        status = fm.zscore_status(z, "new_energy") if z is not None else "—"
        rows.append({"公司": name, "Z值": round(z, 3) if z is not None else np.nan, "状态": status})
    return pd.DataFrame(rows)


@st.cache_data(show_spinner=False)
def compute_walle_table() -> pd.DataFrame:
    """各公司沃尔评分"""
    rows = []
    for code, name in COMPANY_MAP.items():
        df = load_ratios(code).dropna(how="all")
        if df.empty:
            continue
        res = fm.compute_walle_score(df.iloc[-1])
        detail = res["明细"]
        rows.append({
            "公司": name, "沃尔总分": res["总分"],
            **{k: v["得分"] for k, v in detail.items()},
        })
    return pd.DataFrame(rows)


@st.cache_data(show_spinner=False)
def compute_dupont_df(code: str) -> list:
    """杜邦连环替代法分解"""
    data = load_merged(code)
    return fm.compute_dupont(data)


# ============================================================
# 预测与回测（缓存）
# ============================================================
@st.cache_data(show_spinner=False)
def run_forecasts(code: str, metric: str, periods: int, skip: tuple[str, ...]):
    """运行选定预测方法（逐方法自动回退）"""
    series = load_ratios(code)[metric].dropna()
    if len(series) < 4:
        return None, None
    results = fm.compare_all_forecasts(series, periods, skip_methods=list(skip))
    return series, results


@st.cache_data(show_spinner=False)
def run_backtest(code: str, metric: str) -> Optional[pd.DataFrame]:
    """2026Q1 样本外一步前向回测（MAE/sMAPE/MAPE/方向命中率）"""
    s = load_ratios(code)[metric].dropna()
    if "2026Q1" not in s.index:
        return None
    actual = float(s["2026Q1"])
    train = s.drop("2026Q1")
    rows = []
    for name, func in fm.FORECAST_METHODS.items():
        try:
            res = func(train, 1)
            pred = float(np.asarray(res["forecast"]).ravel()[0])
            mae = abs(pred - actual)
            denom = abs(actual) + abs(pred)
            smape = 200 * abs(pred - actual) / denom if denom > 0 else np.nan
            mape = abs(pred - actual) / abs(actual) * 100 if actual != 0 else np.nan
            hit = 1 if np.sign(pred) == np.sign(actual) else 0
            rows.append({
                "方法": name, "预测值": pred, "实际值": actual,
                "MAE": mae, "sMAPE": smape, "MAPE": mape, "方向命中": hit,
            })
        except Exception:
            continue
    return pd.DataFrame(rows)


def _fit_metrics_table(results: dict, y_hist: np.ndarray) -> pd.DataFrame:
    """汇总各预测方法的样本内拟合指标（R² / sMAPE / MAPE / MAE / σ）"""
    rows = []
    for name, res in results.items():
        fit = np.asarray(res["history_fit"], dtype=float)[: len(y_hist)]
        yt = y_hist[: len(fit)]
        m = fm.compute_forecast_metrics(yt, fit)
        rows.append({"方法": name, "R²": m["R²"], "sMAPE": m["sMAPE"],
                     "MAPE": m["MAPE"], "MAE": m["MAE"], "σ": res.get("sigma", np.nan)})
    return pd.DataFrame(rows)


# ============================================================
# 页面 1：项目总览
# ============================================================
def page_overview():
    hero_banner()
    st.markdown("---")

    with st.spinner("正在加载财务数据…"):
        snap = latest_ratio_snapshot()

    # ── 核心研究问题（卡片） ──────────────────────────────
    st.markdown(
        '<div class="fidac-card">'
        '<b style="color:#4FC3F7">核心研究问题</b>：代工协同模式（赛力斯 · 华为智选）与自主研发模式'
        '（长安 · 深蓝/阿维塔/启源），谁的财务风险更高、更不稳定？<br>'
        '以 <b>8 家 A 股乘用车整车厂</b> 为样本，综合 K-Means 聚类、孤立森林、6 种时序预测'
        '（Ridge / Prophet / ARIMA / LSTM / 三次指数平滑 / 线性回归）、Z-score、沃尔评分、杜邦分析等方法'
        '构建财务智能预警体系。'
        '</div>',
        unsafe_allow_html=True,
    )

    # ── 核心结论指标卡 ────────────────────────────────────
    section_header("核心结论速览", "📌")
    specs = [
        ("601127", "赛力斯 · 毛利率", THEME["accent"]),
        ("000625", "长安汽车 · 毛利率", THEME["amber"]),
        ("601127", "赛力斯 · 资产负债率", THEME["accent"]),
        ("000625", "长安汽车 · 资产负债率", THEME["amber"]),
    ]
    cards = []
    for code, label, accent in specs:
        r = snap[snap["公司"] == COMPANY_MAP[code]]
        metric = label.split(" · ", 1)[1]
        val = r.iloc[0].get(metric) if not r.empty else np.nan
        value = f"{fmt(val*100)}%" if pd.notna(val) else "—"
        period = str(r.iloc[0].get("报告期", "")) if not r.empty else ""
        cards.append(stat_card(label, value, f"最新一期 {period}", accent))
    cols = st.columns(4)
    for col, c in zip(cols, cards):
        col.markdown(c, unsafe_allow_html=True)

    # ── Z-score 与 沃尔评分 ───────────────────────────────
    zt = compute_z_table()
    wt = compute_walle_table().sort_values("沃尔总分", ascending=False)
    c1, c2 = st.columns(2)
    with c1:
        section_header("Z-score 预警（新能源阈值 1.20 / 2.20）", "📉")
        zrows = "".join(
            f'<div class="fidac-zrow"><span>{Z_EMOJI.get(r["状态"], "⚪")}</span>'
            f'<b>{r["公司"]}</b>'
            f'<span style="float:right;color:{Z_COLOR.get(r["状态"], "#F0F0F0")}">{fmt(r["Z值"])} · {r["状态"]}</span></div>'
            for _, r in zt.iterrows()
        )
        st.markdown(f'<div class="fidac-card">{zrows}</div>', unsafe_allow_html=True)
    with c2:
        section_header("沃尔评分排名", "📊")
        wrows = "".join(
            f'<div class="fidac-zrow"><span>{"🥇" if i == 0 else f"{i + 1}."}</span>'
            f'<b>{r["公司"]}</b>'
            f'<span style="float:right;color:#4FC3F7">{fmt(r["沃尔总分"])} 分</span></div>'
            for i, (_, r) in enumerate(wt.iterrows())
        )
        st.markdown(f'<div class="fidac-card">{wrows}</div>', unsafe_allow_html=True)

    # ── 财务快照 ─────────────────────────────────────────
    section_header("8 家车企最新一期财务快照", "🏭")
    st.dataframe(snap, width="stretch", height=320)

    # ── 关键发现 ─────────────────────────────────────────
    section_header("关键发现", "🔑")
    st.markdown(
        '<div class="fidac-card">'
        '<b>1.</b> <b style="color:#4FC3F7">赛力斯</b>：沃尔评分第 1（营收增长突出），但 Z-score 落灰色区'
        '（高杠杆 + 问界销量高度集中 ~95%）；2024 扭亏靠净利率、2025 回落靠杠杆去化。<br>'
        '<b>2.</b> <b style="color:#F59E0B">长安汽车</b>：财务稳健但转型偏慢，近两年 ROE 连续由净利率拖累，规模效应滞后。<br>'
        '<b>3.</b> 样本内 <b>Ridge 综合分第一</b>；2026Q1 样本外回测 <b>LSTM / ARIMA 的 MAE 最低</b>——'
        '综合分衡量拟合优度，不等于预测精度。<br>'
        '<b>4.</b> 预测分层：资产负债率可精确预警（MAPE < 20%），毛利率 2026Q1 近零仅作方向判断。'
        '</div>',
        unsafe_allow_html=True,
    )


# ============================================================
# 页面 2：财务指标探索
# ============================================================
def page_metrics():
    st.title("📊 财务指标探索")
    st.caption("18 项财务指标 · 2016Q1 起 · 季度粒度")

    company = st.selectbox("选择公司", list(COMPANY_MAP.values()))
    code = NAME_TO_CODE[company]
    df = load_ratios(code)

    metrics = st.multiselect(
        "选择指标（可多选）", RATIO_METRICS,
        default=["毛利率", "资产负债率", "营业收入增长率"],
    )

    if not metrics:
        st.info("请至少选择一个指标。")
        return

    tab1, tab2, tab3 = st.tabs(["📈 时间趋势", "🏆 公司对比", "🌡️ 指标热力图"])

    with tab1:
        st.plotly_chart(metric_trend_fig(
            df, metrics, f"{company} —— 财务指标时间趋势"), width="stretch")
        st.caption("注：年报期为年度累计值，季度期为单季值；同比增长率已按同期环比处理。")

    with tab2:
        sel = st.radio("对比方式", ["最新一期横向对比", "全历史叠加对比"], horizontal=True)
        if sel == "最新一期横向对比":
            for m in metrics:
                st.plotly_chart(latest_bar_fig(m), width="stretch")
        else:
            fig = go.Figure()
            for m in metrics:
                for cd, nm in COMPANY_MAP.items():
                    s = load_ratios(cd)[m].dropna()
                    if s.empty:
                        continue
                    fig.add_trace(go.Scatter(
                        x=[str(i) for i in s.index], y=s.values,
                        mode="lines", name=f"{nm}·{m}", connectgaps=False,
                    ))
            fig.update_layout(**layout_kwargs("全历史指标叠加对比", height=560))
            fig.update_xaxes(type="category")
            st.plotly_chart(fig, width="stretch")

    with tab3:
        heat_metrics = st.multiselect(
            "热力图指标", RATIO_METRICS, default=metrics[:6], key="heat_metrics")
        if heat_metrics:
            st.plotly_chart(metric_heatmap_fig(heat_metrics), width="stretch")


# ============================================================
# 页面 3：风险评估
# ============================================================
def page_risk():
    st.title("🔬 风险评估")
    st.caption("K-Means 聚类 · 孤立森林 · Z-score · 沃尔评分 · 杜邦分解")

    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        ["🧩 K-Means 聚类", "🌲 孤立森林", "📉 Z-score", "📊 沃尔评分", "🧮 杜邦分析"])

    # ── K-Means ─────────────────────────────────────────────
    with tab1:
        df, ks, inertias = run_clustering()
        c1, c2 = st.columns([3, 2])
        with c1:
            scatter_df = df.copy()
            scatter_df["cluster"] = scatter_df["cluster"].astype(str)
            fig = px.scatter(
                scatter_df, x="pc1", y="pc2", color="cluster",
                text="公司",
                color_discrete_map={str(i): c for i, c in enumerate(CLUSTER_COLORS)},
                labels={"pc1": "PC1", "pc2": "PC2"},
                title=f"8 家车企 K-Means(K=3) 聚类 · PCA 降维（累计方差解释 {df['explained'].iloc[0]*100:.1f}%）",
            )
            fig.update_traces(textposition="top center", marker=dict(size=14))
            fig.update_layout(**layout_kwargs("", height=500))
            st.plotly_chart(fig, width="stretch")
        with c2:
            st.markdown("**聚类明细（5 维风险特征）**")
            show = df[["公司", "cluster", *KMEANS_FEATURES]].sort_values("cluster")
            show.columns = ["公司", "群组", *KMEANS_FEATURES]
            st.dataframe(show.style.format({c: "{:.3f}" for c in KMEANS_FEATURES}),
                         width="stretch", height=360)
        st.markdown("**肘部法则（寻找最优 K）**")
        elbow = go.Figure(go.Scatter(x=ks, y=inertias, mode="lines+markers"))
        elbow.update_layout(**layout_kwargs("K-Means 肘部法则", height=360))
        st.plotly_chart(elbow, width="stretch")

    # ── 孤立森林 ────────────────────────────────────────────
    with tab2:
        iso = run_isolation()
        iso_sorted = iso.sort_values("anomaly_score")
        fig = px.bar(
            iso_sorted, x="anomaly_score", y="公司", orientation="h",
            color="anomaly",
            color_discrete_map={1: "#2ECC71", -1: "#E74C3C"},
            labels={"anomaly": "是否异常", "anomaly_score": "异常得分（越低越异常）"},
            title="孤立森林 —— 异常得分（红色 = 异常信号）",
        )
        fig.update_layout(**layout_kwargs("", height=420))
        st.plotly_chart(fig, width="stretch")
        st.dataframe(
            iso[["公司", "anomaly_score", "anomaly"]]
              .rename(columns={"anomaly_score": "异常得分", "anomaly": "标签"})
              .sort_values("异常得分"),
            width="stretch",
        )
        st.caption("标签：1=正常，-1=异常（contamination=0.15）")

    # ── Z-score ─────────────────────────────────────────────
    with tab3:
        zt = compute_z_table()
        fig = go.Figure()
        fig.add_trace(go.Bar(x=zt["公司"], y=zt["Z值"], marker_color=[
            "#E74C3C" if s == "危险区" else ("#F1C40F" if s == "灰色区" else "#2ECC71")
            for s in zt["状态"]]))
        fig.add_hline(y=Z_THRESH["gray"], line_dash="dash", line_color="#F39C12",
                      annotation_text=f"安全区下限 {Z_THRESH['gray']}")
        fig.add_hline(y=Z_THRESH["danger"], line_dash="dash", line_color="#E74C3C",
                      annotation_text=f"危险区上限 {Z_THRESH['danger']}")
        fig.update_layout(**layout_kwargs("Altman Z-score（新能源行业阈值）", height=440))
        st.plotly_chart(fig, width="stretch")
        st.dataframe(zt, width="stretch")
        st.caption("判定标准（新能源）：危险 < 1.20 ｜ 灰色 1.20–2.20 ｜ 安全 > 2.20")

    # ── 沃尔评分 ────────────────────────────────────────────
    with tab4:
        wt = compute_walle_table()
        fig = px.bar(wt.sort_values("沃尔总分"), x="沃尔总分", y="公司",
                     orientation="h", text_auto=".1f",
                     title="沃尔评分（预警导向 · 满分 100）")
        fig.update_layout(**layout_kwargs("", height=420))
        st.plotly_chart(fig, width="stretch")
        st.dataframe(wt.sort_values("沃尔总分", ascending=False), width="stretch")
        st.caption("权重：毛利率 15 / 有息负债率 25 / 流动比率 25 / 总资产周转率 15 / 营业收入增长率 20")

    # ── 杜邦分析 ────────────────────────────────────────────
    with tab5:
        company = st.selectbox("选择公司", list(COMPANY_MAP.values()), key="dupont_company")
        code = NAME_TO_CODE[company]
        res = compute_dupont_df(code)
        if not res:
            st.warning("数据不足，无法进行杜邦分解。")
            return
        d = pd.DataFrame(res)
        fig = go.Figure()
        x = d["period"].tolist()
        fig.add_trace(go.Bar(x=x, y=d["net_margin_contrib"], name="净利率贡献"))
        fig.add_trace(go.Bar(x=x, y=d["turnover_contrib"], name="周转率贡献"))
        fig.add_trace(go.Bar(x=x, y=d["leverage_contrib"], name="权益乘数贡献"))
        fig.add_trace(go.Scatter(x=x, y=d["ROE_delta"], mode="lines+markers",
                                 name="ROE 变化", line=dict(color="#2C3E50", width=3)))
        fig.update_layout(**layout_kwargs(f"{company} —— 杜邦 ROE 因素分解（连环替代法）", height=460),
                          barmode="relative")
        st.plotly_chart(fig, width="stretch")
        st.dataframe(d[["period", "ROE_prev", "ROE_curr", "ROE_delta",
                        "net_margin_contrib", "turnover_contrib", "leverage_contrib"]]
                     .round(4), width="stretch")


# ============================================================
# 页面 4：时序预测
# ============================================================
def page_forecast():
    st.title("🔮 多模型时序预测")
    st.caption("Ridge / Prophet / ARIMA / LSTM / 三次指数平滑 / 线性回归 · 逐方法自动回退")

    c1, c2, c3, c4 = st.columns([2, 2, 1, 3])
    company = c1.selectbox("选择公司", list(COMPANY_MAP.values()))
    metric = c2.selectbox("选择指标", RATIO_METRICS, index=0)
    periods = c3.number_input("预测期数", min_value=1, max_value=8, value=4, step=1)

    all_methods = list(fm.FORECAST_METHODS.keys())
    skip_default = [m for m in ["Prophet"] if m in all_methods]  # Prophet 本地/云端较重，默认跳过
    methods = c4.multiselect(
        "预测方法（可多选）", all_methods,
        default=[m for m in all_methods if m not in skip_default],
    )
    skip = tuple(m for m in all_methods if m not in methods)

    code = NAME_TO_CODE[company]
    series, results = run_forecasts(code, metric, int(periods), skip)

    if not results:
        st.warning("所选方法均未成功运行，或数据不足。")
        return

    tab1, tab2, tab3 = st.tabs(["📉 预测图", "📋 方法对比", "🎯 2026Q1 回测"])

    with tab1:
        fig = go.Figure()
        x_hist = [str(i) for i in series.index]
        y_hist = series.values
        fig.add_trace(go.Scatter(x=x_hist, y=y_hist, mode="lines+markers",
                                 name="实际值", line=dict(color="#2C3E50", width=2.5)))
        for name, res in results.items():
            pred = np.asarray(res["forecast"], dtype=float)
            x_fut = [f"F{i+1}" for i in range(len(pred))]
            fig.add_trace(go.Scatter(x=x_fut, y=pred, mode="lines+markers", name=name))
            if "forecast_upper" in res:
                up = np.asarray(res["forecast_upper"], dtype=float)
                lo = np.asarray(res["forecast_lower"], dtype=float)
                fig.add_trace(go.Scatter(
                    x=x_fut + x_fut[::-1], y=list(up) + list(lo[::-1]),
                    fill="toself", fillcolor="rgba(128,128,128,0.12)",
                    line=dict(width=0), name=f"{name} 置信区间", showlegend=False))
        fig.update_layout(**layout_kwargs(
            f"{company} —— {metric} 预测（实际 + 未来 {periods} 期）", height=500))
        fig.update_xaxes(type="category")
        st.plotly_chart(fig, width="stretch")

        # 历史拟合质量
        st.markdown("**样本内拟合质量**")
        st.dataframe(_fit_metrics_table(results, y_hist).round(4), width="stretch")

    with tab2:
        st.markdown("**样本内 6 方法综合对比（sMAPE 口径）**")
        d = _fit_metrics_table(results, y_hist)
        if len(d) >= 2:
            try:
                scored = fm.score_methods(
                    d[["R²", "sMAPE", "σ"]].rename(columns={"sMAPE": "MAPE"}),
                    scheme="entropy", cols=("R²", "MAPE", "σ"), direction=(1, -1, -1))
                scored["方法"] = d["方法"].values
                st.dataframe(scored[["方法", "R²", "MAPE", "σ", "熵权综合分", "排名"]].round(4),
                             width="stretch")
            except Exception:
                st.dataframe(d.round(4), width="stretch")
        else:
            st.dataframe(d.round(4), width="stretch")
        st.caption("熵权法定权：R²(正向) / sMAPE(负向) / σ(负向)。综合分越高越优。")

    with tab3:
        bt = run_backtest(code, metric)
        if bt is None:
            st.info("该指标缺少 2026Q1 实际值，无法回测。")
        else:
            st.markdown(f"**2026Q1 样本外一步前向回测 —— {company} · {metric}**")
            st.dataframe(bt.round(4), width="stretch")
            best = bt.loc[bt["MAE"].idxmin()]
            st.success(f"MAE 最低：**{best['方法']}**（MAE={best['MAE']:.4f}，sMAPE={best['sMAPE']:.1f}%）")
            st.caption("方向命中=1 表示预测与实际同号。毛利率近零时以 MAE/方向命中为主。")
            st.image(str(REPORTS_DIR / "pictures" / "backtest_6method_2026q1.png"),
                     caption="Notebook 预生成回测图", width="stretch")


# ============================================================
# 页面 5：行业 NEV 分析
# ============================================================
def page_industry():
    st.title("🚗 行业 NEV 销量与公司财务联动分析")
    st.caption("数据源：中国汽车工业协会（CAAM）· 中国汽车行业多维销量数据库")

    tab1, tab2, tab3, tab4 = st.tabs(
        ["📈 行业景气度", "🏭 8 家车企销量", "🧩 季度销量结构", "⚔️ 赛力斯 vs 长安"])

    # ── 行业景气度 ──────────────────────────────────────────
    with tab1:
        ann = load_industry_sheet("CAAM_NEV年度汇总").dropna(subset=["年份"])
        fig = go.Figure()
        fig.add_trace(go.Bar(x=ann["年份"], y=ann["年度销量合计（万辆）"], name="年度销量（万辆）"))
        fig.add_trace(go.Scatter(x=ann["年份"], y=ann["年度产量合计（万辆）"],
                                 mode="lines+markers", name="年度产量（万辆）"))
        fig.update_layout(**layout_kwargs("NEV 行业年度产销量趋势", height=420))
        st.plotly_chart(fig, width="stretch")

        pen = load_industry_sheet("8家车企新能源渗透率(%)")
        pen_long = pen.melt(id_vars="公司", var_name="年份", value_name="渗透率%")
        fig = px.line(pen_long, x="年份", y="渗透率%", color="公司",
                      markers=True, title="8 家车企新能源渗透率趋势")
        fig.update_layout(**layout_kwargs("", height=460))
        st.plotly_chart(fig, width="stretch")

        st.markdown("**行业月度同比增速（CAAM）**")
        st.image(str(REPORTS_DIR / "nev_industry_analysis" / "nev_yoy_growth_curve.png"),
                 width="stretch")

    # ── 8 家车企销量 ────────────────────────────────────────
    with tab2:
        sales = load_industry_sheet("8家车企年度销量(万辆)")
        sales_long = sales.melt(id_vars="公司", var_name="年份", value_name="销量(万辆)")
        fig = px.bar(sales_long, x="年份", y="销量(万辆)", color="公司", barmode="group",
                     title="8 家车企年度销量对比（万辆）")
        fig.update_layout(**layout_kwargs("", height=460))
        st.plotly_chart(fig, width="stretch")

        st.image(str(REPORTS_DIR / "nev_industry_analysis" / "company_vs_nev_industry.png"),
                 caption="车企 vs 行业增速", width="stretch")

    # ── 季度销量结构 ────────────────────────────────────────
    with tab3:
        company = st.radio("选择公司", ["赛力斯", "长安汽车"], horizontal=True)
        df = load_quarterly_structure(company)
        num_cols = [c for c in df.columns if "万辆" in c or "销量" in c or c == "新能源合计(万辆)"]
        if company == "赛力斯":
            stack_cols = ["问界系列(万辆)", "其他车型(万辆)"]
            ratio_col = "问界占比(%)"
            title = "赛力斯 —— 问界 / 其他 销量结构"
        else:
            stack_cols = ["深蓝(万辆)", "阿维塔(万辆)", "启源(万辆)", "燃油及合资(万辆)"]
            ratio_col = "新能源占比(%)"
            title = "长安汽车 —— 新能源品牌 / 燃油 销量结构"

        fig = go.Figure()
        colors = px.colors.qualitative.Set2
        for i, c in enumerate(stack_cols):
            if c in df.columns:
                fig.add_trace(go.Bar(x=df["时期"], y=df[c], name=c, marker_color=colors[i % len(colors)]))
        if ratio_col in df.columns:
            fig.add_trace(go.Scatter(x=df["时期"], y=df[ratio_col], name=ratio_col,
                                     mode="lines+markers", yaxis="y2",
                                     line=dict(color="#E74C3C", width=3)))
        fig.update_layout(**layout_kwargs(title, height=480),
                          barmode="stack",
                          yaxis=dict(title="销量（万辆）"),
                          yaxis2=dict(title=ratio_col, overlaying="y", side="right", range=[0, 100]))
        st.plotly_chart(fig, width="stretch")
        st.dataframe(df, width="stretch", height=260)

    # ── 赛力斯 vs 长安 ──────────────────────────────────────
    with tab4:
        cmp = load_industry_sheet("赛力斯vs长安核心对比")
        inds = cmp["指标"].unique()
        sel = st.selectbox("选择对比指标", inds)
        d = cmp[cmp["指标"] == sel]
        fig = go.Figure()
        fig.add_trace(go.Bar(x=d["年度"], y=d["赛力斯"], name="赛力斯"))
        fig.add_trace(go.Bar(x=d["年度"], y=d["长安汽车"], name="长安汽车"))
        fig.update_layout(**layout_kwargs(f"赛力斯 vs 长安 —— {sel}", height=420))
        st.plotly_chart(fig, width="stretch")
        st.dataframe(d[["年度", "赛力斯", "长安汽车", "差异说明"]], width="stretch")


# ============================================================
# 页面 6：预生成图表库
# ============================================================
def page_gallery():
    st.title("🖼️ 预生成图表库")
    st.caption("Notebook 与行业分析模块输出的静态图表（PNG）")

    pics = sorted((REPORTS_DIR / "pictures").glob("*.png"))
    nev = sorted((REPORTS_DIR / "nev_industry_analysis").glob("*.png"))

    section_header("Notebook 主图表", "📊")
    if pics:
        cols = st.columns(2)
        for i, p in enumerate(pics):
            with cols[i % 2]:
                st.image(str(p), caption=p.stem, width="stretch")
    else:
        st.info("未找到图表文件。")

    section_header("NEV 行业分析图表", "🚗")
    if nev:
        cols = st.columns(3)
        for i, p in enumerate(nev):
            with cols[i % 3]:
                st.image(str(p), caption=p.stem, width="stretch")
    else:
        st.info("未找到行业分析图表文件。")


# ============================================================
# 侧边栏 + 导航
# ============================================================
def main():
    with st.sidebar:
        st.markdown(
            '<div class="fidac-sidebar-logo">🚗</div>'
            '<div class="fidac-sidebar-title">财务智能预警看板</div>'
            '<div class="fidac-sidebar-sub">重庆上市车企财务智能预警研究<br>——赛力斯外部协同经营模式对标长安自主研发模式</div>',
            unsafe_allow_html=True,
        )
        st.divider()

    # 默认页（可用环境变量 STREAMLIT_DEFAULT_PAGE 指定，供自动化测试/深链使用）
    default_page = os.environ.get("STREAMLIT_DEFAULT_PAGE", "项目总览")

    def _is_default(title: str) -> bool:
        return title == default_page

    pg = st.navigation([
        st.Page(page_overview, title="项目总览", icon="🏠", default=_is_default("项目总览")),
        st.Page(page_metrics, title="财务指标探索", icon="📊", default=_is_default("财务指标探索")),
        st.Page(page_risk, title="风险评估", icon="🔬", default=_is_default("风险评估")),
        st.Page(page_forecast, title="时序预测", icon="🔮", default=_is_default("时序预测")),
        st.Page(page_industry, title="行业分析", icon="🚗", default=_is_default("行业分析")),
        st.Page(page_gallery, title="预生成图表库", icon="🖼️", default=_is_default("预生成图表库")),
    ])
    pg.run()


if __name__ == "__main__":
    main()
