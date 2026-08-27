# -*- coding: utf-8 -*-
"""
基于 K-Means 聚类与多模型时序预测的重庆上市车企财务智能预警研究
=================================================================
Streamlit 交互式可视化看板（单文件多页面）

页面：
  1. 🖥️ 可视化大屏       —— 1920×1080 指挥中心式大屏（路线 A：内嵌 ECharts）
  2. 🏠 项目总览         —— 研究背景、核心结论、8 家车企最新快照
  3. 📊 财务指标探索     —— 18 项财务指标时间趋势 / 公司对比 / 热力图
  4. 🔬 风险评估         —— K-Means 聚类、孤立森林、Z-score、沃尔评分、杜邦分析
  5. 🔮 时序预测         —— 6 种模型预测对比 + 2026Q1 样本外回测
  6. 🚗 行业 NEV 分析    —— 行业景气度、渗透率、季度销量结构、赛力斯 vs 长安
  7. 🖼️ 预生成图表库      —— 展示 Notebook / 行业分析输出的 PNG 图

运行： streamlit run streamlit_app.py
部署： Streamlit Community Cloud（关联 GitHub/Gitee 仓库，见 DEPLOY.md）
"""

import os
import sys
from pathlib import Path
from typing import Optional

import json
import re

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st
import streamlit.components.v1 as components
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


# ── 数据期（as-of）工具：支持按历史期截断 ──────────────────
_Q_ONLY_PAT = re.compile(r"^(\d{4})Q([1-4])$")
_ANNUAL_PAT = re.compile(r"^(\d{4})年报$")


def _normalize_period(label) -> str:
    """'2026Q1.1' → '2026Q1'（去掉源表重复期后缀）"""
    return re.sub(r"\.\d+$", "", str(label).strip())


def _period_key(label) -> Optional[tuple]:
    """'2025Q3'→(2025,3)，'2025年报'→(2025,5)，无法解析→None"""
    s = _normalize_period(label)
    m = _Q_ONLY_PAT.match(s)
    if m:
        return (int(m.group(1)), int(m.group(2)))
    m = _ANNUAL_PAT.match(s)
    if m:
        return (int(m.group(1)), 5)
    return None


def _asof_frame(df: pd.DataFrame, period: Optional[str]) -> pd.DataFrame:
    """截取截至 period（含）的行；period 为 None 时原样返回。

    源表期标签按时间升序排列，按"最后一个期键 ≤ 目标期键"的位置整体截断，
    保留重复期标签（如 2026Q1.1），与"最新一期"口径完全一致。
    """
    if period is None:
        return df
    pk = _period_key(period)
    if pk is None:
        return df
    cut = -1
    for i, lb in enumerate(df.index):
        k = _period_key(lb)
        if k is not None and k <= pk:
            cut = i
    return df.iloc[:cut + 1] if cut >= 0 else df.iloc[0:0]


@st.cache_data(show_spinner=False)
def load_ratios(code: str, period: Optional[str] = None) -> pd.DataFrame:
    """读取单家公司财务指标表（期 × 18指标）；period 指定时截取截至该期"""
    df = pd.read_excel(_company_file(code), sheet_name="财务指标表", index_col=0)
    df.index = df.index.astype(str)
    return _asof_frame(df, period)


@st.cache_data(show_spinner=False)
def load_merged(code: str, period: Optional[str] = None) -> pd.DataFrame:
    """读取单家公司三大报表合并数据（用于 Z-score / 杜邦 / 聚类特征）；支持 as-of 截断"""
    path = _company_file(code)
    df_balance = pd.read_excel(path, sheet_name="资产负债表", index_col=0)
    df_income = pd.read_excel(path, sheet_name="利润表", index_col=0)
    df_cash = pd.read_excel(path, sheet_name="现金流量表", index_col=0)
    df_balance = df_balance.T.add_suffix("_资产")
    df_income = df_income.T.add_suffix("_利润")
    df_cash = df_cash.T.add_suffix("_现金流")
    merged = pd.concat([df_income, df_balance, df_cash], axis=1).fillna(0)
    return _asof_frame(merged, period)


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
def latest_ratio_snapshot(period: Optional[str] = None) -> pd.DataFrame:
    """各公司最新一期（或截至 period 一期）18 项指标快照"""
    rows = []
    for code, name in COMPANY_MAP.items():
        df = load_ratios(code, period).dropna(how="all")
        if df.empty:
            continue
        row = df.iloc[-1]
        period = str(row.name)
        rec = {"代码": code, "公司": name, "报告期": period}
        for m in RATIO_METRICS:
            rec[m] = row.get(m)
        rows.append(rec)
    return pd.DataFrame(rows)


@st.cache_data(show_spinner=False)
def available_periods() -> list:
    """全部可选数据期（归一化标签，按时间倒序）——用于大屏数据期切换"""
    seen: dict = {}
    for code in COMPANY_MAP:
        for lb in load_ratios(code).index:
            k = _period_key(lb)
            if k is not None:
                seen[_normalize_period(lb)] = k
    return [p for p, _ in sorted(seen.items(), key=lambda kv: kv[1], reverse=True)]


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
def build_feature_matrix(period: Optional[str] = None) -> pd.DataFrame:
    """构建 8 家车企最新一期（或截至 period 一期）5 维风险特征矩阵"""
    rows = []
    for code, name in COMPANY_MAP.items():
        data = load_merged(code, period)
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
def run_clustering(period: Optional[str] = None) -> tuple[pd.DataFrame, list, list]:
    """K-Means(K=3) + PCA 降维 + 肘部法则（period 指定时按历史期截面）"""
    df = build_feature_matrix(period)
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
def run_isolation(period: Optional[str] = None) -> pd.DataFrame:
    """孤立森林异常检测（period 指定时按历史期截面）"""
    df = build_feature_matrix(period)
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
def compute_z_table(period: Optional[str] = None) -> pd.DataFrame:
    """各公司最新一期（或截至 period 一期）Altman Z-score"""
    rows = []
    for code, name in COMPANY_MAP.items():
        data = load_merged(code, period)
        try:
            z = fm.compute_zscore(data)
        except Exception:
            z = None
        status = fm.zscore_status(z, "new_energy") if z is not None else "—"
        rows.append({"公司": name, "Z值": round(z, 3) if z is not None else np.nan, "状态": status})
    return pd.DataFrame(rows)


@st.cache_data(show_spinner=False)
def compute_walle_table(period: Optional[str] = None) -> pd.DataFrame:
    """各公司沃尔评分（period 指定时按历史期截面）"""
    rows = []
    for code, name in COMPANY_MAP.items():
        df = load_ratios(code, period).dropna(how="all")
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
def compute_dupont_df(code: str, period: Optional[str] = None) -> list:
    """杜邦连环替代法分解（period 指定时只用截至该期的年报）"""
    data = load_merged(code, period)
    return fm.compute_dupont(data)


# ============================================================
# 预测与回测（缓存）
# ============================================================
@st.cache_data(show_spinner=False)
def run_forecasts(code: str, metric: str, periods: int, skip: tuple[str, ...],
                  period: Optional[str] = None):
    """运行选定预测方法（逐方法自动回退）；period 指定时以截至该期的历史为训练集"""
    series = load_ratios(code, period)[metric].dropna()
    if len(series) < 4:
        return None, None
    results = fm.compare_all_forecasts(series, periods, skip_methods=list(skip))
    return series, results


@st.cache_data(show_spinner=False)
def run_backtest(code: str, metric: str, period: Optional[str] = None) -> Optional[pd.DataFrame]:
    """样本外一步前向回测（MAE/sMAPE/MAPE/方向命中率）。

    period=None：以最新一期为 holdout（与原 2026Q1 口径一致）；
    period 指定：以截至该期的最后一期为 holdout。
    重复期标签（如 '2026Q1.1'）先归并（保留最后一条），
    避免 holdout 期数值以重复行形式泄入训练集。
    """
    s = load_ratios(code, period)[metric].dropna()
    pos: dict = {}
    for i, lb in enumerate(s.index):
        pos[_normalize_period(lb)] = i
    if pos:
        s = s.iloc[sorted(pos.values())]
    if len(s) < 5:
        return None
    actual = float(s.iloc[-1])
    train = s.iloc[:-1]
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
# 页面 7：可视化大屏（路线 A · Streamlit 内嵌 ECharts）
# 1920×1080 设计基准 + JS 等比缩放；数据全部复用现有缓存函数
# ============================================================
ECHARTS_LOCAL = BASE_DIR / "lib" / "echarts.min.js"
ECHARTS_CDN = "https://cdn.jsdelivr.net/npm/echarts@5.5.0/dist/echarts.min.js"
SCREEN_COMPANY = "赛力斯"
SCREEN_METRIC = "资产负债率"

SCREEN_STRIP_CSS = """<style>
/* 大屏模式：去掉主区域留白，让 1920 画布占满 */
[data-testid="stMainBlockContainer"] {
    padding: 0 !important;
    max-width: 100% !important;
}
[data-testid="stHeader"] { background: transparent !important; }
</style>"""


def _safe(fn):
    """执行数据函数，任何异常返回 None（大屏不允许白屏）"""
    try:
        return fn()
    except Exception:
        return None


def _next_quarter_labels(last_label: str, n: int) -> list:
    """由 '2025Q4' 之类的末期标签推出未来 n 期标签（容忍 '2026Q1.1' 重复后缀）"""
    label = re.sub(r"\.\d+$", "", str(last_label))
    m = re.match(r"(\d{4})Q([1-4])$", label)
    if not m:
        return [f"F{i + 1}" for i in range(n)]
    y, q = int(m.group(1)), int(m.group(2))
    out = []
    for i in range(1, n + 1):
        q2, y2 = q + i, y
        while q2 > 4:
            q2 -= 4
            y2 += 1
        out.append(f"{y2}Q{q2}")
    return out


def build_screen_payload(period: Optional[str] = None) -> dict:
    """汇总大屏全部数据（全部命中现有 @st.cache_data 缓存）。

    period=None 展示最新一期；period='2025Q4' 等历史期则整屏回看该期截面。
    """
    code = NAME_TO_CODE[SCREEN_COMPANY]
    requested = _normalize_period(period) if period is not None else None

    # ── Z-score / 沃尔 / 孤立森林 ────────────────────────
    zrows = []
    zt = _safe(lambda: compute_z_table(requested))
    if zt is not None:
        for _, r in zt.iterrows():
            zrows.append({
                "company": str(r["公司"]),
                "z": None if pd.isna(r["Z值"]) else round(float(r["Z值"]), 3),
                "status": str(r["状态"]) if str(r["状态"]) in ("安全区", "灰色区", "危险区") else "未知",
            })
    zrows.sort(key=lambda r: (r["z"] is None, r["z"] if r["z"] is not None else 0))

    wrows = []
    wt = _safe(lambda: compute_walle_table(requested))
    if wt is not None:
        for i, (_, r) in enumerate(wt.sort_values("沃尔总分", ascending=False).iterrows()):
            wrows.append({
                "rank": i + 1, "company": str(r["公司"]),
                "score": None if pd.isna(r["沃尔总分"]) else round(float(r["沃尔总分"]), 1),
            })

    irows = []
    iso = _safe(lambda: run_isolation(requested))
    if iso is not None:
        for _, r in iso.sort_values("anomaly_score").iterrows():
            irows.append({
                "company": str(r["公司"]),
                "score": round(float(r["anomaly_score"]), 3),
                "anomaly": int(r["anomaly"]) == -1,
            })

    # ── K-Means 聚类散点 ─────────────────────────────────
    points, explained = [], 0.0
    cl_res = _safe(lambda: run_clustering(requested))
    if cl_res is not None:
        cl = cl_res[0]
        explained = float(cl["explained"].iloc[0])
        wscore = {w["company"]: (w["score"] or 50) for w in wrows}
        for _, r in cl.iterrows():
            points.append({
                "company": str(r["公司"]),
                "pc1": round(float(r["pc1"]), 3),
                "pc2": round(float(r["pc2"]), 3),
                "cluster": int(r["cluster"]),
                "size": wscore.get(str(r["公司"]), 50),
            })

    # ── 时序预测（旗舰：赛力斯 · 资产负债率）─────────────
    forecast = {"company": SCREEN_COMPANY, "metric": SCREEN_METRIC,
                "x": [], "y": [], "flabels": [], "methods": [], "champion": None}
    fres = _safe(lambda: run_forecasts(code, SCREEN_METRIC, 4, ("Prophet",), requested))
    if fres is not None:
        series, results = fres
        if series is not None and results:
            # 去重：源表存在 '2026Q1' / '2026Q1.1' 之类重复期，按期标签去重并保留最后一条
            dedup: dict = {}
            for lb, v in zip(series.index, series.values):
                dedup[re.sub(r"\.\d+$", "", str(lb))] = v
            x_hist = list(dedup.keys())
            forecast["x"] = x_hist
            forecast["y"] = [None if pd.isna(v) else round(float(v), 4) for v in dedup.values()]
            first = next(iter(results.values()))
            n_steps = int(np.asarray(first["forecast"]).ravel().shape[0])
            forecast["flabels"] = _next_quarter_labels(x_hist[-1] if x_hist else "", n_steps)
            for name, res in results.items():
                entry = {"name": name, "pred": [round(float(v), 4)
                            for v in np.asarray(res["forecast"], dtype=float).ravel()],
                         "upper": None, "lower": None}
                if res.get("forecast_upper") is not None:
                    entry["upper"] = [round(float(v), 4)
                                      for v in np.asarray(res["forecast_upper"], dtype=float).ravel()]
                    entry["lower"] = [round(float(v), 4)
                                      for v in np.asarray(res["forecast_lower"], dtype=float).ravel()]
                forecast["methods"].append(entry)

    # ── 样本外回测（最新期或截至 period 的最后一期为 holdout）──
    brows, best = [], None
    bt = _safe(lambda: run_backtest(code, SCREEN_METRIC, requested))
    if bt is not None and len(bt):
        for _, r in bt.sort_values("MAE").iterrows():
            brows.append({"method": str(r["方法"]), "mae": round(float(r["MAE"]), 4)})
        best = brows[0]
        names = [m["name"] for m in forecast["methods"]]
        if best["method"] in names:
            forecast["champion"] = best["method"]

    # ── KPI 带（以 Z 列表实际呈现的家数为准，与左侧预警榜口径一致）──
    kpi = {
        "companies": len(zrows),
        "danger": sum(r["status"] == "危险区" for r in zrows),
        "gray":   sum(r["status"] == "灰色区" for r in zrows),
        "safe":   sum(r["status"] == "安全区" for r in zrows),
        "best_model": best["method"] if best else "—",
        "best_mae": best["mae"] if best else None,
    }

    # ── 风险雷达（5 维特征归一化）────────────────────────
    radar = {"indicators": list(KMEANS_FEATURES), "series": []}
    fmat = _safe(lambda: build_feature_matrix(requested))
    if fmat is not None and len(fmat):
        lo = fmat[KMEANS_FEATURES].min()
        hi = fmat[KMEANS_FEATURES].max()

        def _norm(row) -> list:
            vals = []
            for c in KMEANS_FEATURES:
                v = row.get(c)
                if v is None or pd.isna(v) or hi[c] <= lo[c]:
                    vals.append(50.0)
                else:
                    vals.append(float(round((float(v) - float(lo[c])) / (float(hi[c]) - float(lo[c])) * 100, 1)))
            return vals

        for name in ["赛力斯", "长安汽车"]:
            r = fmat[fmat["公司"] == name]
            if len(r):
                radar["series"].append({"name": name, "values": _norm(r.iloc[0])})

    # ── 杜邦分解（最新一期）─────────────────────────────
    dupont = None
    dp = _safe(lambda: compute_dupont_df(code, requested))
    if dp:
        d = dp[-1]
        dupont = {
            "company": SCREEN_COMPANY, "period": str(d.get("period", "")),
            "start": round(float(d.get("ROE_prev") or 0), 4),
            "contribs": [
                {"name": "净利率", "value": round(float(d.get("net_margin_contrib") or 0), 4)},
                {"name": "周转率", "value": round(float(d.get("turnover_contrib") or 0), 4)},
                {"name": "权益乘数", "value": round(float(d.get("leverage_contrib") or 0), 4)},
            ],
        }

    # ── NEV 行业产销量 ──────────────────────────────────
    nev = {"years": [], "sales": [], "production": []}
    ann = _safe(lambda: load_industry_sheet("CAAM_NEV年度汇总"))
    if ann is not None:
        ann = ann.dropna(subset=["年份"])
        nev["years"] = [str(int(y)) if isinstance(y, (int, float)) else str(y) for y in ann["年份"]]
        nev["sales"] = [round(float(v), 1) for v in ann["年度销量合计（万辆）"]]
        nev["production"] = [round(float(v), 1) for v in ann["年度产量合计（万辆）"]]

    # ── 跑马灯预警事件 ──────────────────────────────────
    msgs = []
    for r in zrows:
        if r["status"] == "危险区" and r["z"] is not None:
            msgs.append(f"预警 · {r['company']} Altman Z={r['z']:.2f} 落入危险区")
        elif r["status"] == "灰色区" and r["z"] is not None:
            msgs.append(f"关注 · {r['company']} Z={r['z']:.2f} 处于灰色区")
    msgs += [f"孤立森林标记异常：{r['company']}" for r in irows if r["anomaly"]]
    if wrows:
        msgs.append(f"沃尔评分末位：{wrows[-1]['company']}（{wrows[-1]['score'] or '—'} 分）")
    if not msgs:
        msgs = ["全部样本 Z-score 处于安全区，暂无预警事件"]

    # ── 数据期（最新期 or 历史回看）──────────────────────
    snap = _safe(lambda: latest_ratio_snapshot(requested))
    snap_latest = _safe(latest_ratio_snapshot)

    def _mode_period(df) -> str:
        if df is None or not len(df):
            return "—"
        mode = df["报告期"].mode()
        return _normalize_period(mode.iloc[0]) if len(mode) \
            else _normalize_period(df["报告期"].iloc[0])

    latest_period = _mode_period(snap_latest)
    display_period = requested or _mode_period(snap)

    # 回测 holdout 期标签（与 run_backtest 的去重口径一致）
    bt_series = _safe(lambda: load_ratios(code, requested)[SCREEN_METRIC].dropna())
    bt_period = None
    if bt_series is not None and len(bt_series):
        bt_period = _normalize_period(bt_series.index[-1])

    if requested:
        msgs.insert(0, f"历史期回看 · {requested}（点击右上角数据期可返回最新）")

    return {
        "period": display_period, "requested": requested,
        "is_latest": requested is None, "latest_period": latest_period,
        "periods": _safe(available_periods) or [], "bt_period": bt_period,
        "kpi": kpi, "zscore": zrows, "walle": wrows, "iso": irows,
        "clusters": {"points": points, "explained": explained},
        "forecast": forecast, "backtest": brows, "radar": radar, "dupont": dupont,
        "nev": nev, "marquee": msgs,
    }


# ── 大屏 HTML 模板（1920×1080 设计稿）────────────────────
SCREEN_HTML = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8"/>
<style>
*{margin:0;padding:0;box-sizing:border-box}
html,body{width:100%;height:100%;overflow:hidden;background:#001830;
  font-family:'Segoe UI','Microsoft YaHei','PingFang SC',sans-serif;color:#F0F0F0}
#stage{position:absolute;left:50%;top:50%;width:1920px;height:1080px}
#screen{width:100%;height:100%;display:grid;grid-template-rows:88px 120px 1fr 44px;gap:14px;
  padding:10px 18px 12px 18px;
  background:
    radial-gradient(1200px 600px at 85% -10%, rgba(59,130,246,0.16), transparent 60%),
    radial-gradient(900px 520px at -10% 115%, rgba(34,211,238,0.10), transparent 55%),
    linear-gradient(180deg,#001830 0%,#061A2C 100%)}
/* ── 顶部标题栏 ── */
.hd{position:relative;display:flex;align-items:center;justify-content:space-between;padding:0 28px;
  background:linear-gradient(90deg,rgba(12,48,80,0.92),rgba(6,42,72,0.45),rgba(12,48,80,0.92));
  border:1px solid rgba(59,130,246,0.35);border-radius:12px;overflow:visible}
.hd-title{font-size:40px;font-weight:800;letter-spacing:6px;
  background:linear-gradient(90deg,#7DD3FC,#3B82F6 55%,#8B5CF6);
  -webkit-background-clip:text;-webkit-text-fill-color:transparent}
.hd-sub{margin-top:4px;font-size:15px;color:#9FB4CC;letter-spacing:3px}
.hd-side{display:flex;flex-direction:column;gap:5px;font-size:15px;color:#9FB4CC;min-width:280px}
.hd-side.right{text-align:right}
.hd-brand{font-size:19px;font-weight:800;color:#4FC3F7;letter-spacing:3px}
#clock{font-size:23px;color:#4FC3F7;font-weight:700;font-variant-numeric:tabular-nums}
/* 数据期切换菜单 */
.pwrap{position:relative;cursor:pointer;user-select:none}
.parr{font-size:11px;color:#4FC3F7;margin-left:4px}
#pmenu{display:none;position:absolute;right:0;top:30px;z-index:99;min-width:150px;max-height:420px;
  overflow:auto;background:#062A48;border:1px solid rgba(79,195,247,.45);border-radius:8px;padding:5px 0;
  box-shadow:0 10px 30px rgba(0,0,0,.55);text-align:left}
.pitem{padding:6px 20px;font-size:14px;color:#D6E2F0;white-space:nowrap}
.pitem:hover{background:rgba(79,195,247,.14);color:#4FC3F7}
.pitem.cur{color:#4FC3F7;font-weight:700}
.phint{padding:6px 20px;font-size:11px;color:#7A90AB;border-top:1px solid rgba(79,195,247,.18);
  margin-top:4px;white-space:normal;max-width:220px}
.sweep{position:absolute;top:0;left:-30%;width:16%;height:100%;pointer-events:none;
  background:linear-gradient(105deg,transparent,rgba(79,195,247,0.10),transparent);
  animation:sweep 6s linear infinite}
@keyframes sweep{to{left:115%}}
/* ── KPI 带 ── */
.kpis{display:grid;grid-template-columns:repeat(6,1fr);gap:14px}
.kpi{position:relative;display:flex;flex-direction:column;justify-content:center;padding:0 24px;
  background:linear-gradient(160deg,rgba(12,48,80,0.92),rgba(6,42,72,0.92));
  border:1px solid rgba(59,130,246,0.24);border-radius:12px;overflow:hidden}
.kpi::before{content:'';position:absolute;left:0;top:0;bottom:0;width:3px;background:var(--a)}
.kpi .lb{font-size:15px;color:#9FB4CC;letter-spacing:1px}
.kpi .vl{font-size:42px;font-weight:800;color:var(--c);line-height:1.2;font-variant-numeric:tabular-nums}
.kpi .sub{font-size:13px;color:#7A90AB}
/* ── 主体三列 ── */
.main{display:grid;grid-template-columns:430px 1fr 430px;gap:14px;min-height:0}
.col{display:grid;grid-template-rows:repeat(3,1fr);gap:14px;min-height:0}
.center{display:grid;grid-template-rows:1.25fr 1fr;gap:14px;min-height:0}
.center-bottom{display:grid;grid-template-columns:1.25fr 1fr;gap:14px;min-height:0}
.panel{position:relative;background:linear-gradient(160deg,rgba(12,48,80,0.55),rgba(6,42,72,0.85));
  border:1px solid rgba(59,130,246,0.28);border-radius:12px;padding:10px 14px 8px 14px;
  display:flex;flex-direction:column;animation:enter .6s ease both}
@keyframes enter{from{opacity:0;transform:translateY(14px)}to{opacity:1;transform:none}}
.corner::before,.corner::after{content:'';position:absolute;width:14px;height:14px;
  border:2px solid rgba(79,195,247,0.75)}
.corner::before{top:-1px;left:-1px;border-right:none;border-bottom:none}
.corner::after{bottom:-1px;right:-1px;border-left:none;border-top:none}
.ptitle{display:flex;align-items:center;gap:10px;font-size:18px;font-weight:700;color:#F0F0F0;
  flex:0 0 auto;padding:2px 0 6px 0}
.ptitle::before{content:'';width:4px;height:18px;border-radius:2px;
  background:linear-gradient(180deg,#4FC3F7,#3B82F6)}
.ptitle small{font-size:13px;color:#7A90AB;font-weight:400}
.pbody{flex:1;min-height:0;position:relative}
.chart{position:absolute;inset:0}
.nodata{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;
  color:#7A90AB;font-size:15px}
/* ── 排行列表 ── */
.zrow{display:flex;align-items:center;gap:10px;height:12.5%}
.dot{width:9px;height:9px;border-radius:50%;flex:0 0 auto}
.dot.danger{background:#F87171;box-shadow:0 0 8px rgba(248,113,113,0.9);
  animation:breath 1.6s ease-in-out infinite}
.dot.gray{background:#FBBF24}.dot.safe{background:#34D399}
@keyframes breath{50%{opacity:.35}}
.zname{width:88px;font-size:15px;color:#D6E2F0;flex:0 0 auto}
.ztrack{flex:1;height:7px;border-radius:4px;background:rgba(159,180,204,0.14);overflow:hidden}
.zfill{height:100%;border-radius:4px}
.zval{width:168px;text-align:right;font-size:14px;color:#9FB4CC;font-variant-numeric:tabular-nums}
/* ── 底部状态栏 ── */
.status{display:flex;align-items:center;gap:18px;padding:0 18px;
  background:rgba(6,42,72,0.7);border:1px solid rgba(59,130,246,0.2);border-radius:10px;
  font-size:14px;color:#9FB4CC;overflow:hidden}
.marquee{flex:1;overflow:hidden;position:relative;height:100%}
.mtrack{position:absolute;white-space:nowrap;line-height:42px;color:#FBBF24;
  animation:marq 36s linear infinite}
@keyframes marq{from{transform:translateX(0)}to{transform:translateX(-50%)}}
@media (prefers-reduced-motion: reduce){*{animation:none!important}}
</style>
</head>
<body>
<div id="stage"><div id="screen">

  <div class="hd corner">
    <div class="hd-side">
      <span class="hd-brand">FIDAC</span>
      <span>财务大数据智能决策</span>
    </div>
    <div style="text-align:center">
      <div class="hd-title">重庆上市车企财务智能预警大屏</div>
      <div class="hd-sub">K-Means 聚类 · 多模型时序预测 · 8 家 A 股乘用车整车厂</div>
    </div>
    <div class="hd-side right">
      <span id="clock">--</span>
      <span class="pwrap" id="pwrap" title="点击切换数据期">数据期 <b id="period" style="color:#4FC3F7"></b><span class="parr">▾</span>
        <div id="pmenu"></div></span>
    </div>
    <div class="sweep"></div>
  </div>

  <div class="kpis" id="kpis"></div>

  <div class="main">
    <div class="col">
      <div class="panel corner" style="animation-delay:.05s">
        <div class="ptitle">Altman Z-score 预警榜 <small>阈值 1.20 / 2.20</small></div>
        <div class="pbody" id="zlist"></div>
      </div>
      <div class="panel corner" style="animation-delay:.15s">
        <div class="ptitle">沃尔评分排名 <small>满分 100</small></div>
        <div class="pbody"><div class="chart" id="chart-walle"></div></div>
      </div>
      <div class="panel corner" style="animation-delay:.25s">
        <div class="ptitle">孤立森林 · 异常信号 <small>得分越低越异常</small></div>
        <div class="pbody" id="ilist"></div>
      </div>
    </div>

    <div class="center">
      <div class="panel corner" style="animation-delay:.1s">
        <div class="ptitle">8 家车企风险画像 · K-Means 聚类 <small id="cluster-sub"></small></div>
        <div class="pbody"><div class="chart" id="chart-cluster"></div></div>
      </div>
      <div class="center-bottom">
        <div class="panel corner" style="animation-delay:.2s">
          <div class="ptitle" id="fc-title">多模型时序预测</div>
          <div class="pbody"><div class="chart" id="chart-forecast"></div></div>
        </div>
        <div class="panel corner" style="animation-delay:.3s">
          <div class="ptitle">风险雷达 · 赛力斯 vs 长安 <small>五维特征归一化</small></div>
          <div class="pbody"><div class="chart" id="chart-radar"></div></div>
        </div>
      </div>
    </div>

    <div class="col">
      <div class="panel corner" style="animation-delay:.05s">
        <div class="ptitle" id="dp-title">杜邦 ROE 因素分解</div>
        <div class="pbody"><div class="chart" id="chart-dupont"></div></div>
      </div>
      <div class="panel corner" style="animation-delay:.15s">
        <div class="ptitle">NEV 行业产销量趋势 <small>万辆 · CAAM</small></div>
        <div class="pbody"><div class="chart" id="chart-nev"></div></div>
      </div>
      <div class="panel corner" style="animation-delay:.25s">
        <div class="ptitle" id="bt-title">样本外回测 · MAE 排行 <small>越低越优</small></div>
        <div class="pbody"><div class="chart" id="chart-backtest"></div></div>
      </div>
    </div>
  </div>

  <div class="status">
    <span>数据源：公司季报 · CAAM · FIDAC</span>
    <div class="marquee"><div class="mtrack" id="marq"></div></div>
    <span id="refreshed">刷新中…</span>
  </div>

</div></div>

<script src="__ECHARTS_CDN__"></script>
<script>
const D = __PAYLOAD_JSON__;

const C = {danger:'#F87171', gray:'#FBBF24', safe:'#34D399', primary:'#3B82F6',
  accent:'#4FC3F7', cyan:'#22D3EE', amber:'#F59E0B', violet:'#8B5CF6',
  muted:'#9FB4CC', text:'#F0F0F0', grid:'rgba(159,180,204,0.12)'};
const CLUSTER_COLORS = ['#F87171','#3B9EFF','#34D399','#FBBF24','#A78BFA'];
const PALETTE = ['#22D3EE','#8B5CF6','#34D399','#F59E0B','#F472B6','#60A5FA'];
const statusColor = s => s==='危险区'?C.danger : s==='灰色区'?C.gray : C.safe;
const fmt = (v,d) => (v==null || isNaN(v)) ? '—' : Number(v).toFixed(d==null?2:d);
const noEcharts = () => !window.echarts;
const nodata = id => { const el=document.getElementById(id); if(el) el.innerHTML =
  '<div class="nodata">'+(noEcharts()?'图表引擎未加载':'数据不足')+'</div>'; };

/* ── 时钟 / 数据期 ── */
(function(){
  const p=x=>String(x).padStart(2,'0');
  const tick=()=>{const n=new Date();
    document.getElementById('clock').textContent =
      n.getFullYear()+'-'+p(n.getMonth()+1)+'-'+p(n.getDate())+' '+
      p(n.getHours())+':'+p(n.getMinutes())+':'+p(n.getSeconds());};
  tick(); setInterval(tick,1000);
  document.getElementById('refreshed').textContent =
    '刷新 ' + new Date().toLocaleTimeString('zh-CN',{hour12:false});
})();

/* ── 数据期切换（零常驻控件：点击展开 / URL ?period= 直达）── */
(function(){
  const pel=document.getElementById('period');
  if(!pel) return;
  pel.textContent = D.period;
  if(!D.is_latest){ pel.style.color='#F59E0B'; pel.textContent += ' · 回看'; }
  const wrap=document.getElementById('pwrap'), menu=document.getElementById('pmenu');
  if(!wrap || !menu) return;
  const items=[{t:'最新期（'+D.latest_period+'）',v:null}];
  (D.periods||[]).forEach(p=>{ if(p!==D.latest_period) items.push({t:p,v:p}); });
  menu.innerHTML = items.map(it=>{
      const cur = (D.requested==null && it.v==null) || (D.requested!=null && it.v===D.requested);
      return '<div class="pitem'+(cur?' cur':'')+'" data-v="'+(it.v||'')+'">'+it.t+'</div>';
    }).join('') +
    '<div class="phint">URL 直达任意期：地址栏追加 ?period=2025Q4</div>';
  wrap.addEventListener('click',e=>{ e.stopPropagation();
    menu.style.display = (menu.style.display==='block') ? 'none' : 'block'; });
  document.addEventListener('click',e=>{ if(!wrap.contains(e.target)) menu.style.display='none'; });
  menu.querySelectorAll('.pitem').forEach(it=>it.addEventListener('click',()=>{
    const v = it.dataset.v || null;
    try{
      const u = new URL(window.parent.location.href);
      if(v) u.searchParams.set('period',v); else u.searchParams.delete('period');
      window.parent.location.href = u.toString();
    }catch(err){
      /* 沙箱拦截父窗口导航时降级为提示 */
      menu.style.display='none';
      const hint=document.querySelector('.phint');
      if(hint) hint.textContent='当前环境限制了页面跳转，请手动在地址栏追加 ?period='+(v||'');
    }
  }));
})();

/* ── KPI 带（数字滚动）── */
(function(){
  const k = D.kpi;
  const cards = [
    {lb:'监测车企',   vl:k.companies, su:'A 股乘用车整车厂',   c:C.text,   a:C.primary, num:1, d:0},
    {lb:'危险区',     vl:k.danger,     su:'Altman Z < 1.20',   c:C.danger, a:C.danger, num:1, d:0},
    {lb:'灰色区',     vl:k.gray,       su:'1.20 ≤ Z < 2.20',   c:C.gray,   a:C.gray,   num:1, d:0},
    {lb:'安全区',     vl:k.safe,       su:'Z ≥ 2.20',          c:C.safe,   a:C.safe,   num:1, d:0},
    {lb:'最优回测模型', vl:k.best_model, su:(D.bt_period||'样本外')+' · MAE 最低', c:C.accent, a:C.primary, num:0},
    {lb:'冠军模型 MAE', vl:(k.best_mae==null?'—':k.best_mae), su:k.best_model+' · '+D.forecast.metric,
      c:C.cyan, a:C.primary, num:(k.best_mae==null?0:1), d:4},
  ];
  document.getElementById('kpis').innerHTML = cards.map(c =>
    '<div class="kpi" style="--a:'+c.a+';--c:'+c.c+'">' +
    '<div class="lb">'+c.lb+'</div>' +
    '<div class="vl" data-v="'+c.vl+'" data-d="'+(c.d||0)+'" data-num="'+(c.num||0)+'">'+c.vl+'</div>' +
    '<div class="sub">'+c.su+'</div></div>').join('');
  document.querySelectorAll('.vl[data-num="1"]').forEach(el=>{
    const t=parseFloat(el.dataset.v); if(!isFinite(t)) return;
    const d=parseInt(el.dataset.d)||0;
    el.textContent = t.toFixed(d);   // 大屏稳态显示，直接终值，避免动画时序错位
  });
})();

/* ── Z-score 列表 ── */
(function(){
  document.getElementById('zlist').innerHTML = D.zscore.map(r=>{
    const col = statusColor(r.status);
    const w = r.z==null ? 0 : Math.max(2, Math.min((r.z+1)/5*100, 100));
    const dot = r.status==='危险区'?'danger':(r.status==='灰色区'?'gray':'safe');
    return '<div class="zrow"><span class="dot '+dot+'"></span>' +
      '<span class="zname">'+r.company+'</span>' +
      '<div class="ztrack"><div class="zfill" style="width:'+w+'%;background:'+col+'"></div></div>' +
      '<span class="zval" style="color:'+col+'">'+fmt(r.z,3)+' · '+r.status+'</span></div>';
  }).join('');
})();

/* ── 孤立森林列表 ── */
(function(){
  const scs = D.iso.map(r=>r.score).filter(v=>v!=null);
  const smin = Math.min(...scs), smax = Math.max(...scs);
  const wfrac = s => (smax<=smin) ? 50 : Math.max(6, Math.min((s-smin)/(smax-smin)*100, 100));
  document.getElementById('ilist').innerHTML = D.iso.map(r=>{
    const col = r.anomaly ? C.danger : C.safe;
    return '<div class="zrow"><span class="dot '+(r.anomaly?'danger':'safe')+'"></span>' +
      '<span class="zname">'+r.company+'</span>' +
      '<div class="ztrack"><div class="zfill" style="width:'+
        wfrac(r.score)+'%;background:'+col+';opacity:.75"></div></div>' +
      '<span class="zval" style="color:'+col+'">'+fmt(r.score,3)+' · '+
        (r.anomaly?'异常':'正常')+'</span></div>';
  }).join('');
})();

/* ── ECharts ── */
const charts = [];
function mk(id, opt){
  const el = document.getElementById(id);
  if(!el) return;
  if(noEcharts()){ el.innerHTML='<div class="nodata">图表引擎未加载</div>'; return; }
  try{
    opt.animationDuration = 700;
    const c = echarts.init(el, null, {renderer:'canvas'});
    c.setOption(opt); charts.push(c);
  }catch(e){ el.innerHTML='<div class="nodata">渲染失败</div>'; }
}
const AX = {axisLabel:{color:C.muted,fontSize:13},
  splitLine:{lineStyle:{color:C.grid}}};
const TIP = {backgroundColor:'rgba(10,42,70,0.95)',borderColor:C.primary,
  textStyle:{color:C.text,fontSize:14}};

/* 沃尔评分 */
(function(){
  if(!D.walle.length){ nodata('chart-walle'); return; }
  const w = D.walle.slice().reverse();
  const colOf = r => r.rank===1 ? C.accent
                    : r.rank<=3 ? C.primary
                    : '#1E3A8A';
  mk('chart-walle', {grid:{left:6,right:64,top:8,bottom:8,containLabel:true},
    xAxis:{type:'value',show:false,min:0,max:100},
    yAxis:{type:'category',data:w.map(r=>r.company),
      axisLabel:{color:'#D6E2F0',fontSize:15},axisLine:{show:false},axisTick:{show:false}},
    series:[{type:'bar',barWidth:14,
      label:{show:true,position:'right',color:C.text,fontSize:15,formatter:p=>fmt(p.value,1)},
      data:w.map(r=>({value:r.score==null?0:r.score,
        itemStyle:{color:colOf(r),opacity:r.rank<=3?1:0.6,
          borderRadius:7}}))}],
    tooltip:Object.assign({trigger:'item',formatter:'{b}：{c} 分'},TIP)});
})();

/* K-Means 聚类散点 */
(function(){
  const cl = D.clusters;
  if(!cl.points.length){ nodata('chart-cluster'); return; }
  document.getElementById('cluster-sub').textContent =
    'PCA 累计方差解释 '+(cl.explained*100).toFixed(1)+'% · 气泡=沃尔总分 · 红/蓝/绿 = 簇 1/2/3';
  mk('chart-cluster', {grid:{left:64,right:72,top:30,bottom:50},
    xAxis:Object.assign({type:'value',name:'PC1',nameTextStyle:{color:C.muted},
      axisLine:{lineStyle:{color:'rgba(148,163,184,0.35)'}}},AX),
    yAxis:Object.assign({type:'value',name:'PC2',nameTextStyle:{color:C.muted},
      min:function(v){return Math.floor(v.min-0.5);},
      max:function(v){return Math.ceil(v.max+0.5);},
      axisLine:{lineStyle:{color:'rgba(148,163,184,0.35)'}}},AX),
    series:[{type:'scatter',
      symbolSize:32,
      itemStyle:{opacity:0.95,borderColor:'rgba(255,255,255,0.55)',borderWidth:1},
      label:{show:true,position:'top',distance:14,color:C.text,fontSize:12,
        backgroundColor:'rgba(6,26,44,0.9)',borderColor:'rgba(79,195,247,0.55)',
        borderWidth:1,borderRadius:4,padding:[1,5],
        formatter:p=>p.data.company},
      labelLayout:{hideOverlap:true,moveOverlap:'shiftY'},
      data:cl.points.map(p=>({name:p.company, value:[p.pc1,p.pc2],
        company:p.company, cluster:p.cluster, size:p.size,
        itemStyle:{color:CLUSTER_COLORS[p.cluster%5]}}))}],
    tooltip:Object.assign({trigger:'item',
      formatter:p=>p.data.company+'<br/>簇 '+(p.data.cluster+1)+' · 沃尔 '+fmt(p.data.size,1)},TIP)});
})();

/* 多模型时序预测 */
(function(){
  const F = D.forecast;
  if(!F.methods.length || !F.x.length){ nodata('chart-forecast'); return; }
  document.getElementById('fc-title').innerHTML =
    '多模型时序预测 <small>'+F.company+' · '+F.metric+' · 未来 '+F.flabels.length+' 期</small>';
  const x = F.x.concat(F.flabels);
  const series = [{name:'实际值',type:'line',data:F.y,z:5,
    lineStyle:{color:C.text,width:3},itemStyle:{color:C.text},symbolSize:7}];
  const pre = Array(F.x.length).fill(null);
  F.methods.forEach((m,i)=>{
    const col = PALETTE[i%PALETTE.length];
    series.push({name:m.name,type:'line',data:pre.concat(m.pred),
      lineStyle:{color:col,width:2,type:'dashed'},itemStyle:{color:col},symbolSize:6});
  });
  const champ = F.methods.find(m=>m.name===F.champion) ||
                F.methods.find(m=>m.upper && m.upper.length);
  if(champ && champ.upper){
    const band = pre.concat(champ.upper.map((u,i)=>+(u-champ.lower[i]).toFixed(4)));
    series.push({name:'下界',type:'line',stack:'band',data:pre.concat(champ.lower),
      lineStyle:{opacity:0},symbol:'none',silent:true});
    series.push({name:'冠军置信带',type:'line',stack:'band',data:band,
      lineStyle:{opacity:0},symbol:'none',silent:true,
      areaStyle:{color:'rgba(34,211,238,0.14)'}});
  }
  mk('chart-forecast', {grid:{left:70,right:24,top:44,bottom:38},
    legend:{top:0,textStyle:{color:C.muted,fontSize:13},type:'scroll',
      pageIconColor:C.accent,pageTextStyle:{color:C.muted}},
    xAxis:Object.assign({type:'category',data:x,
      axisLine:{lineStyle:{color:'rgba(148,163,184,0.35)'}}},AX),
    yAxis:Object.assign({type:'value',scale:true,
      axisLine:{lineStyle:{color:'rgba(148,163,184,0.35)'}}},AX),
    series:series,
    tooltip:Object.assign({trigger:'axis'},TIP)});
})();

/* 风险雷达 */
(function(){
  if(!D.radar.series.length){ nodata('chart-radar'); return; }
  const cols = [C.accent, C.amber];
  mk('chart-radar', {legend:{bottom:0,textStyle:{color:C.muted,fontSize:14}},
    radar:{indicator:D.radar.indicators.map(n=>({name:n,max:100})),
      splitArea:{areaStyle:{color:['rgba(6,42,72,0.5)','rgba(12,48,80,0.5)']}},
      axisName:{color:C.muted,fontSize:14},
      splitLine:{lineStyle:{color:C.grid}},axisLine:{lineStyle:{color:C.grid}}},
    series:[{type:'radar',data:D.radar.series.map((s,i)=>({value:s.values,name:s.name,
      areaStyle:{opacity:0.25},lineStyle:{width:2,color:cols[i%2]},
      itemStyle:{color:cols[i%2]},symbolSize:5}))}],
    tooltip:Object.assign({trigger:'item'},TIP)});
})();

/* 杜邦 ROE 瀑布 */
(function(){
  const dp = D.dupont;
  if(!dp){ nodata('chart-dupont'); return; }
  document.getElementById('dp-title').innerHTML =
    '杜邦 ROE 因素分解 <small>'+dp.company+' · '+dp.period+'</small>';
  const cats = ['期初 ROE'], bases = [0], bars = [], labels = [fmt(dp.start,3)];
  let cum = dp.start;
  const dcols = [C.safe, C.primary, C.amber];
  dp.contribs.forEach((c,i)=>{
    const base = c.value >= 0 ? cum : cum + c.value;
    bases.push(+base.toFixed(4));
    bars.push({value:+Math.abs(c.value).toFixed(4),
      itemStyle:{color:dcols[i%3],borderRadius:4}});
    labels.push((c.value>=0?'+':'')+fmt(c.value,3));
    cats.push(c.name);
    cum += c.value;
  });
  cats.push('期末 ROE');
  bases.push(0);
  bars.push({value:+Math.abs(cum).toFixed(4), itemStyle:{color:C.accent,borderRadius:4}});
  labels.push(fmt(cum,3));
  mk('chart-dupont', {grid:{left:70,right:20,top:36,bottom:34},
    xAxis:Object.assign({type:'category',data:cats,
      axisLine:{lineStyle:{color:'rgba(148,163,184,0.35)'}},
      axisLabel:{color:C.muted,fontSize:13}},{}),
    yAxis:Object.assign({type:'value',scale:true,
      axisLabel:{color:C.muted,fontSize:13,formatter:v=>v.toFixed(2)},
      splitLine:{lineStyle:{color:C.grid}}},{}),
    series:[
      {type:'bar',stack:'wf',itemStyle:{color:'transparent'},data:bases,silent:true},
      {type:'bar',stack:'wf',
        // 期初/期末柱单独着色
        data:[{value:+Math.abs(dp.start).toFixed(4),
          itemStyle:{color:C.primary,borderRadius:4}}].concat(bars),
        label:{show:true,position:'top',color:C.text,fontSize:13},
        barWidth:'46%'}
    ],
    tooltip:Object.assign({trigger:'axis',
      formatter:ps=>{const i=ps[1].dataIndex;return cats[i]+'：'+labels[i];}},TIP)});
})();

/* NEV 行业产销量 */
(function(){
  if(!D.nev.years.length){ nodata('chart-nev'); return; }
  mk('chart-nev', {grid:{left:58,right:22,top:38,bottom:32},
    legend:{top:0,textStyle:{color:C.muted,fontSize:13}},
    xAxis:Object.assign({type:'category',data:D.nev.years,
      axisLine:{lineStyle:{color:'rgba(148,163,184,0.35)'}}},AX),
    yAxis:Object.assign({type:'value',name:'万辆',nameTextStyle:{color:C.muted}},AX),
    series:[
      {name:'销量',type:'bar',data:D.nev.sales,barWidth:'52%',
        itemStyle:{color:C.cyan,borderRadius:[4,4,0,0]}},
      {name:'产量',type:'line',data:D.nev.production,
        lineStyle:{color:C.safe,width:2.5},itemStyle:{color:C.safe},symbolSize:7}],
    tooltip:Object.assign({trigger:'axis'},TIP)});
})();

/* 样本外回测排行 */
(function(){
  if(!D.backtest.length){ nodata('chart-backtest'); return; }
  const t=document.getElementById('bt-title');
  if(t && D.bt_period) t.innerHTML = D.bt_period+' 样本外回测 · MAE 排行 <small>越低越优</small>';
  const b = D.backtest.slice().reverse();   // 冠军（MAE 最低）在顶部
  mk('chart-backtest', {grid:{left:6,right:72,top:8,bottom:8,containLabel:true},
    xAxis:{type:'value',show:false},
    yAxis:{type:'category',data:b.map(r=>r.method),
      axisLabel:{color:'#D6E2F0',fontSize:14},axisLine:{show:false},axisTick:{show:false}},
    series:[{type:'bar',barWidth:14,
      label:{show:true,position:'right',color:C.text,fontSize:13,formatter:p=>fmt(p.value,4)},
      data:b.map((r,i)=>({value:r.mae,
        itemStyle:{color:i===b.length-1?C.safe:'#2563EB',borderRadius:7}}))}],
    tooltip:Object.assign({trigger:'item',formatter:'{b}：MAE {c}'},TIP)});
})();

/* ── 跑马灯（内容加倍实现无缝滚动）── */
(function(){
  const msg = D.marquee.join('      ◆      ') + '      ◆      ';
  document.getElementById('marq').textContent = msg + msg;
})();

/* ── 1920×1080 等比缩放适配 ── */
(function(){
  const stage = document.getElementById('stage');
  function fit(){
    const sc = Math.min(window.innerWidth/1920, window.innerHeight/1080);
    stage.style.transform = 'translate(-50%,-50%) scale(' + sc + ')';
  }
  fit(); window.addEventListener('resize', fit);
})();
</script>
</body>
</html>"""


def page_screen():
    """1920×1080 指挥中心式可视化大屏（路线 A）

    数据期切换：URL 追加 ?period=2025Q4 可回看任意历史期截面；
    不带参数即最新一期。顶部"数据期"可点击直接切换。
    """
    st.markdown(SCREEN_STRIP_CSS, unsafe_allow_html=True)
    period = st.query_params.get("period") or None
    if period is not None and _period_key(period) is None:
        period = None   # 非法期标签按最新期处理
    with st.spinner("正在装配大屏数据…"):
        payload = build_screen_payload(period)
    html = SCREEN_HTML.replace("__PAYLOAD_JSON__", json.dumps(payload, ensure_ascii=False))
    try:
        echarts_js = ECHARTS_LOCAL.read_text(encoding="utf-8")
    except Exception:
        echarts_js = None
    if echarts_js:
        html = html.replace(
            '<script src="__ECHARTS_CDN__"></script>',
            "<script>" + echarts_js + "</script>",
        )
    else:
        html = html.replace("__ECHARTS_CDN__", ECHARTS_CDN)
    components.html(html, height=1080, scrolling=False)


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
        st.Page(page_screen, title="可视化大屏", icon="🖥️", default=_is_default("可视化大屏")),
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
