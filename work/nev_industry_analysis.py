#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
新能源汽车行业销量分析模块
================================
基于 CAAM（中国汽车工业协会）月度数据，提供：
  1. NEV 月度销量/产量趋势（2016-2025）
  2. NEV 渗透率估算（NEV / 整体市场）
  3. 8家车企 vs 行业增速对比
  4. 月度季节性模式分析
  5. 同比增速分布与拐点识别
  6. 赛力斯/长安与行业趋势联动分析

可用于 Notebook 直接 import，也可独立运行生成图表。
"""

import os
import warnings
import numpy as np
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

warnings.filterwarnings("ignore")

# ── 中文字体配置 ─────────────────────────────────────────────
plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei", "WenQuanYi Micro Hei",
                                    "Noto Sans CJK SC", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

# ── 路径 ─────────────────────────────────────────────────────
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_DIR, "data")
REPORTS_DIR = os.path.join(PROJECT_DIR, "reports", "nev_industry_analysis")
os.makedirs(REPORTS_DIR, exist_ok=True)

XLSX_PATH = os.path.join(DATA_DIR, "中国汽车行业多维销量数据库.xlsx")


# ═══════════════════════════════════════════════════════════════
# 1. 数据加载
# ═══════════════════════════════════════════════════════════════
def load_nev_monthly() -> pd.DataFrame:
    """加载 CAAM NEV 月度产销数据（增强版，含同比增速）"""
    return pd.read_excel(XLSX_PATH, sheet_name="CAAM_NEV月度同比增速")


def load_nev_annual() -> pd.DataFrame:
    """加载 CAAM NEV 年度汇总"""
    return pd.read_excel(XLSX_PATH, sheet_name="CAAM_NEV年度汇总")


def load_overall_market() -> pd.DataFrame:
    """加载整体市场月度销量（宽表 → 长表）"""
    df = pd.read_excel(XLSX_PATH, sheet_name="整体市场_销量")
    # 宽表转长表: 月份, 2025年, 2026年
    records = []
    for _, row in df.iterrows():
        month_str = str(row["月份"])
        for col in df.columns[1:]:
            if pd.notna(row[col]):
                year = int(col.replace("年", ""))
                records.append({"年份": year, "月份_str": month_str, "整体销量_万辆": float(row[col])})
    return pd.DataFrame(records)


def load_8company_annual() -> pd.DataFrame:
    """加载 8家车企年度销量"""
    return pd.read_excel(XLSX_PATH, sheet_name="8家车企年度销量(万辆)")


def load_8company_penetration() -> pd.DataFrame:
    """加载 8家车企新能源渗透率"""
    return pd.read_excel(XLSX_PATH, sheet_name="8家车企新能源渗透率(%)")


def load_changan_quarterly() -> pd.DataFrame:
    """加载长安汽车季度销量结构数据"""
    path = os.path.join(DATA_DIR, "长安汽车_季度销量结构.xlsx")
    return pd.read_excel(path)


def load_seres_quarterly() -> pd.DataFrame:
    """加载赛力斯季度销量结构数据"""
    path = os.path.join(DATA_DIR, "赛力斯_季度销量结构.xlsx")
    return pd.read_excel(path)


# ═══════════════════════════════════════════════════════════════
# 2. 分析函数
# ═══════════════════════════════════════════════════════════════

def compute_nev_penetration(df_nev: pd.DataFrame, df_overall: pd.DataFrame) -> pd.DataFrame:
    """
    计算 NEV 月度渗透率 = NEV月销量 / 整体市场月销量 × 100%
    返回含渗透率的月度 DataFrame
    """
    # 统一月份格式
    month_map = {f"{i}月": i for i in range(1, 13)}
    df_overall["月份"] = df_overall["月份_str"].map(month_map)

    merged = df_nev.merge(
        df_overall[["年份", "月份", "整体销量_万辆"]],
        on=["年份", "月份"], how="left"
    )
    merged["NEV渗透率_%"] = np.where(
        merged["整体销量_万辆"].notna() & (merged["整体销量_万辆"] > 0),
        merged["新能源汽车销量（万辆）"] / merged["整体销量_万辆"] * 100,
        np.nan
    )
    return merged


def compute_yearly_growth(df_monthly: pd.DataFrame) -> pd.DataFrame:
    """从月度数据聚合年度销量并计算同比增速"""
    yearly = df_monthly.groupby("年份").agg(
        年度产量=("新能源汽车产量（万辆）", "sum"),
        年度销量=("新能源汽车销量（万辆）", "sum"),
        月均销量=("新能源汽车销量（万辆）", "mean"),
    ).reset_index()
    yearly["销量同比增速_%"] = yearly["年度销量"].pct_change() * 100
    yearly["产量同比增速_%"] = yearly["年度产量"].pct_change() * 100
    return yearly


def compute_seasonal_pattern(df_monthly: pd.DataFrame) -> pd.DataFrame:
    """计算各月季节性指数（每月销量 / 年均月销量）"""
    yearly_avg = df_monthly.groupby("年份")["新能源汽车销量（万辆）"].transform("mean")
    df = df_monthly.copy()
    df["季节性指数"] = df["新能源汽车销量（万辆）"] / yearly_avg
    seasonal = df.groupby("月份")["季节性指数"].agg(["mean", "std"]).reset_index()
    seasonal.columns = ["月份", "平均季节性指数", "季节性波动"]
    return seasonal


# ═══════════════════════════════════════════════════════════════
# 3. 可视化函数
# ═══════════════════════════════════════════════════════════════

def plot_nev_monthly_trend(df_monthly: pd.DataFrame, save_path: str = None) -> str:
    """
    图1: NEV 月度销量与产量趋势（2016-2025），双Y轴
    """
    fig, ax1 = plt.subplots(figsize=(16, 7))

    # 构造日期轴
    df = df_monthly.copy()
    df["日期"] = pd.to_datetime(df["时间"] + "-01")
    df = df.sort_values("日期")

    color_sales = "#2196F3"
    color_prod = "#FF9800"

    ax1.fill_between(df["日期"], df["新能源汽车销量（万辆）"], alpha=0.2, color=color_sales)
    ax1.plot(df["日期"], df["新能源汽车销量（万辆）"], color=color_sales, linewidth=1.5, label="NEV 月度销量（万辆）")
    ax1.plot(df["日期"], df["新能源汽车产量（万辆）"], color=color_prod, linewidth=1.5,
             linestyle="--", label="NEV 月度产量（万辆）")

    # 标注关键里程碑
    milestones = {
        "2018-01": "补贴退坡\n过渡期",
        "2020-06": "疫情后\n复苏",
        "2022-06": "爆发式\n增长",
        "2024-12": "月销170万\n新里程碑",
    }
    for date_str, label in milestones.items():
        dt = pd.Timestamp(date_str)
        row = df[df["日期"] == dt]
        if not row.empty:
            val = row["新能源汽车销量（万辆）"].values[0]
            ax1.annotate(label, xy=(dt, val), xytext=(20, 25),
                         textcoords="offset points", fontsize=8,
                         arrowprops=dict(arrowstyle="->", color="gray", lw=0.8),
                         bbox=dict(boxstyle="round,pad=0.3", fc="lightyellow", alpha=0.8))

    ax1.set_ylabel("万辆", fontsize=12, color=color_sales)
    ax1.tick_params(axis="y", labelcolor=color_sales)
    ax1.set_title("中国新能源汽车月度产销量趋势（2016-2025）\n数据来源：中国汽车工业协会(CAAM)",
                  fontsize=14, fontweight="bold")
    ax1.legend(loc="upper left", fontsize=10)
    ax1.grid(True, alpha=0.3)

    fig.tight_layout()
    if save_path is None:
        save_path = os.path.join(REPORTS_DIR, "nev_monthly_trend.png")
    fig.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"[OK] {save_path}")
    return save_path


def plot_nev_yearly_bar(df_yearly: pd.DataFrame, save_path: str = None) -> str:
    """
    图2: NEV 年度销量柱状图 + 同比增速折线
    """
    fig, ax1 = plt.subplots(figsize=(14, 6))

    years = df_yearly["年份"].astype(str)
    bars = ax1.bar(years, df_yearly["年度销量"], color="#4CAF50", alpha=0.7, label="年度销量（万辆）")
    # 数值标注
    for bar, val in zip(bars, df_yearly["年度销量"]):
        ax1.text(bar.get_x() + bar.get_width()/2., bar.get_height() + 5,
                 f"{val:.0f}", ha="center", va="bottom", fontsize=9)

    ax2 = ax1.twinx()
    growth = df_yearly["销量同比增速_%"].values
    colors = ["#F44336" if g < 0 else "#2196F3" for g in growth]
    # 第一个年份无同比
    colors[0] = "#999999"
    ax2.plot(years, growth, "o-", color="#FF5722", linewidth=2, markersize=8, label="同比增速(%)")
    for i, (x, g) in enumerate(zip(years, growth)):
        if not np.isnan(g):
            ax2.annotate(f"{g:+.1f}%", (x, g), textcoords="offset points",
                         xytext=(0, 12), ha="center", fontsize=8, color=colors[i])

    ax1.set_ylabel("万辆", fontsize=12)
    ax2.set_ylabel("同比增速 (%)", fontsize=12, color="#FF5722")
    ax2.axhline(y=0, color="gray", linestyle="--", linewidth=0.8)
    ax2.tick_params(axis="y", labelcolor="#FF5722")

    ax1.set_title("中国新能源汽车年度销量与同比增速（2016-2025）\n数据来源：中国汽车工业协会(CAAM)",
                  fontsize=14, fontweight="bold")
    ax1.legend(loc="upper left", fontsize=9)
    ax2.legend(loc="upper right", fontsize=9)
    ax1.grid(True, alpha=0.3, axis="y")

    fig.tight_layout()
    if save_path is None:
        save_path = os.path.join(REPORTS_DIR, "nev_yearly_growth.png")
    fig.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"[OK] {save_path}")
    return save_path


def plot_nev_penetration(df_merged: pd.DataFrame, save_path: str = None) -> str:
    """
    图3: NEV 月度渗透率趋势
    """
    df = df_merged.dropna(subset=["NEV渗透率_%"]).copy()
    if df.empty:
        print("[WARN] 无渗透率数据（整体市场数据可能不完整），跳过此图")
        return ""

    df["日期"] = pd.to_datetime(df["时间"] + "-01")
    df = df.sort_values("日期")

    # 按月聚合
    monthly_pen = df.groupby("日期")["NEV渗透率_%"].mean().reset_index()

    fig, ax = plt.subplots(figsize=(16, 6))
    ax.fill_between(monthly_pen["日期"], monthly_pen["NEV渗透率_%"], alpha=0.3, color="#9C27B0")
    ax.plot(monthly_pen["日期"], monthly_pen["NEV渗透率_%"], color="#9C27B0", linewidth=2)

    # 标注 50% 里程碑
    ax.axhline(y=50, color="red", linestyle="--", linewidth=0.8, alpha=0.6)
    ax.annotate("50% 渗透率关口", xy=(monthly_pen["日期"].iloc[-1], 50),
                xytext=(-100, 15), textcoords="offset points", fontsize=9, color="red",
                arrowprops=dict(arrowstyle="->", color="red", lw=0.8))

    ax.set_ylabel("NEV 渗透率 (%)", fontsize=12)
    ax.set_title("中国新能源汽车月度渗透率趋势\nNEV销量 / 整体汽车市场销量 × 100%",
                 fontsize=14, fontweight="bold")
    ax.grid(True, alpha=0.3)
    ax.yaxis.set_major_formatter(mticker.FormatStrFormatter("%.0f%%"))

    fig.tight_layout()
    if save_path is None:
        save_path = os.path.join(REPORTS_DIR, "nev_penetration_trend.png")
    fig.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"[OK] {save_path}")
    return save_path


def plot_company_vs_industry(df_8co: pd.DataFrame, df_yearly: pd.DataFrame,
                              save_path: str = None) -> str:
    """
    图4: 重庆上市车企（长安/赛力斯）年度销量与增速 vs 行业NEV 双轴对标
         柱状 = 年度总销量（万辆），折线 = 同比增速（%）
    """
    # ── 数据准备 ──
    df_8co_t = df_8co.set_index("公司").T
    df_8co_t.index = df_8co_t.index.astype(int)
    company_growth = df_8co_t.pct_change() * 100  # 各车企年度增速

    years = df_8co_t.index.values
    x = np.arange(len(years))
    bar_width = 0.28

    ca_sales = df_8co_t["长安汽车"].values
    sr_sales = df_8co_t["赛力斯"].values
    nev_growth = df_yearly.set_index("年份").loc[years, "销量同比增速_%"].values
    ca_growth = company_growth["长安汽车"].values
    sr_growth = company_growth["赛力斯"].values

    # ── 绘图 ──
    fig, ax1 = plt.subplots(figsize=(16, 7))

    # 左Y轴：年度销量分组柱状
    bars_ca = ax1.bar(x - bar_width, ca_sales, bar_width,
                      color="#2196F3", alpha=0.85, label="长安汽车 年销量", zorder=2)
    bars_sr = ax1.bar(x, sr_sales, bar_width,
                      color="#FF5722", alpha=0.85, label="赛力斯 年销量", zorder=2)

    # 柱顶数值标注
    for i in range(len(years)):
        ax1.text(x[i] - bar_width, ca_sales[i] + 3, f"{ca_sales[i]:.0f}",
                 ha="center", fontsize=8, color="#1565C0", fontweight="bold")
        ax1.text(x[i], sr_sales[i] + 3, f"{sr_sales[i]:.0f}",
                 ha="center", fontsize=8, color="#BF360C", fontweight="bold")

    ax1.set_xlabel("年份", fontsize=12)
    ax1.set_ylabel("年销量（万辆）", fontsize=12, color="#333")
    ax1.tick_params(axis="y", labelcolor="#333")
    ax1.set_xticks(x)
    ax1.set_xticklabels(years.astype(str), fontsize=10)
    ax1.set_ylim(0, ax1.get_ylim()[1] * 1.18)

    # 右Y轴：同比增速折线
    ax2 = ax1.twinx()
    ax2.plot(x, nev_growth, "D-", color="#333333", linewidth=2.5, markersize=10,
             markerfacecolor="white", markeredgewidth=2, label="行业NEV增速", zorder=5)
    ax2.plot(x, ca_growth, "o-", color="#1565C0", linewidth=2, markersize=8,
             label="长安汽车增速", zorder=5)
    ax2.plot(x, sr_growth, "s-", color="#BF360C", linewidth=2, markersize=8,
             label="赛力斯增速", zorder=5)

    # 增速数值标注
    for i in range(len(years)):
        for vals, color, offsets in [
            (nev_growth, "#333", (0, 14)),
            (ca_growth, "#1565C0", (0, -16)),
            (sr_growth, "#BF360C", (0, 14)),
        ]:
            v = vals[i]
            if not np.isnan(v):
                ax2.annotate(f"{v:+.1f}%", (x[i], v),
                             textcoords="offset points", xytext=offsets,
                             ha="center", fontsize=7.5, color=color,
                             fontweight="bold")

    ax2.axhline(y=0, color="gray", linestyle="--", linewidth=1, alpha=0.6)
    ax2.set_ylabel("同比增速 (%)", fontsize=12, color="#333")
    ax2.tick_params(axis="y", labelcolor="#333")

    # 图例合并
    bars1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(bars1 + lines2, labels1 + labels2,
               loc="upper left", fontsize=9, ncol=2)

    ax1.set_title("重庆上市车企年度销量与增速对标 —— 长安汽车 · 赛力斯 vs 行业NEV\n"
                  "柱状 = 年销量（左轴） | 折线 = 同比增速（右轴）",
                  fontsize=14, fontweight="bold")
    ax1.grid(True, alpha=0.25, axis="y")

    fig.tight_layout()
    if save_path is None:
        save_path = os.path.join(REPORTS_DIR, "company_vs_nev_industry.png")
    fig.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"[OK] {save_path}")
    return save_path


def plot_seasonal_heatmap(df_monthly: pd.DataFrame, save_path: str = None) -> str:
    """
    图5: NEV 月度销量季节性热力图（年份 × 月份）
    """
    pivot = df_monthly.pivot_table(
        values="新能源汽车销量（万辆）", index="年份", columns="月份", aggfunc="sum"
    )

    fig, ax = plt.subplots(figsize=(14, 8))
    im = ax.imshow(pivot.values, cmap="YlOrRd", aspect="auto")

    # 标注数值
    for i in range(pivot.shape[0]):
        for j in range(pivot.shape[1]):
            val = pivot.values[i, j]
            if not np.isnan(val):
                ax.text(j, i, f"{val:.0f}", ha="center", va="center",
                        fontsize=7, color="black" if val < 80 else "white")

    ax.set_xticks(range(12))
    ax.set_xticklabels([f"{m}月" for m in range(1, 13)], fontsize=10)
    ax.set_yticks(range(pivot.shape[0]))
    ax.set_yticklabels(pivot.index.astype(int), fontsize=10)
    ax.set_title("中国新能源汽车月度销量热力图（万辆）\n数据来源：CAAM",
                 fontsize=14, fontweight="bold")

    cbar = fig.colorbar(im, ax=ax, shrink=0.85)
    cbar.set_label("万辆", fontsize=10)

    fig.tight_layout()
    if save_path is None:
        save_path = os.path.join(REPORTS_DIR, "nev_seasonal_heatmap.png")
    fig.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"[OK] {save_path}")
    return save_path


def plot_yoy_growth_curve(df_monthly: pd.DataFrame, save_path: str = None) -> str:
    """
    图6: NEV 月度销量同比增速曲线（带拐点标注）
    """
    df = df_monthly.dropna(subset=["销量同比增速（%）"]).copy()
    df["日期"] = pd.to_datetime(df["时间"] + "-01")
    df = df.sort_values("日期")

    fig, ax = plt.subplots(figsize=(16, 6))

    growth = df["销量同比增速（%）"].values
    # 正负分色
    pos_mask = growth >= 0
    neg_mask = growth < 0

    ax.fill_between(df["日期"], 0, growth, where=pos_mask, alpha=0.3, color="#4CAF50",
                    label="正增长")
    ax.fill_between(df["日期"], 0, growth, where=neg_mask, alpha=0.3, color="#F44336",
                    label="负增长")
    ax.plot(df["日期"], growth, color="#333333", linewidth=1.2)

    ax.axhline(y=0, color="gray", linestyle="-", linewidth=0.8)
    ax.axhline(y=100, color="orange", linestyle="--", linewidth=0.6, alpha=0.5)
    ax.annotate("100% 增速线", xy=(df["日期"].iloc[-1], 100), fontsize=8, color="orange")

    ax.set_ylabel("同比增速 (%)", fontsize=12)
    ax.set_title("中国新能源汽车月度销量同比增速（2017-2025）\n数据来源：CAAM",
                 fontsize=14, fontweight="bold")
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3)
    ax.yaxis.set_major_formatter(mticker.FormatStrFormatter("%.0f%%"))

    fig.tight_layout()
    if save_path is None:
        save_path = os.path.join(REPORTS_DIR, "nev_yoy_growth_curve.png")
    fig.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"[OK] {save_path}")
    return save_path


# ═══════════════════════════════════════════════════════════════
# 4. 季度分析可视化 —— 长安汽车 & 赛力斯
# ═══════════════════════════════════════════════════════════════

def plot_changan_quarterly_structure(df_ca: pd.DataFrame = None,
                                      save_path: str = None) -> str:
    """
    图7: 长安汽车季度销量结构（新能源 vs 燃油堆叠柱状图 + 新能源品牌细分曲线）
    """
    if df_ca is None:
        df_ca = load_changan_quarterly()

    df = df_ca.copy()
    quarters = df["时期"].tolist()
    x = np.arange(len(quarters))

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(16, 11),
                                   gridspec_kw={"height_ratios": [1.2, 1]})

    # ── 上图：新能源 vs 燃油堆叠柱状图 ──
    nev_total = df["新能源合计(万辆)"].values
    fuel_total = df["燃油及合资(万辆)"].values
    nev_pct = df["新能源占比(%)"].values

    bar_width = 0.55
    bars_fuel = ax1.bar(x, fuel_total, bar_width, color="#90CAF9", alpha=0.85,
                        label="燃油及合资（万辆）", zorder=2)
    bars_nev = ax1.bar(x, nev_total, bar_width, bottom=fuel_total,
                       color="#4CAF50", alpha=0.85, label="新能源合计（万辆）", zorder=2)

    # 柱顶标注新能源占比
    for i in range(len(x)):
        total_h = fuel_total[i] + nev_total[i]
        ax1.text(x[i], total_h + 0.8, f"{nev_pct[i]:.1f}%", ha="center",
                 fontsize=8, fontweight="bold", color="#2E7D32")

    ax1.set_xticks(x)
    ax1.set_xticklabels(quarters, fontsize=9, rotation=30)
    ax1.set_ylabel("万辆", fontsize=11)
    ax1.set_title("长安汽车季度销量结构：新能源 vs 燃油\n（柱顶数字 = 新能源占比）",
                  fontsize=13, fontweight="bold")
    ax1.legend(loc="upper left", fontsize=9)
    ax1.grid(True, alpha=0.25, axis="y")
    ax1.set_ylim(0, ax1.get_ylim()[1] * 1.12)

    # ── 下图：三大新能源品牌季度销量曲线 ──
    ax2.plot(x, df["深蓝(万辆)"].values, "o-", color="#1565C0", linewidth=2,
             markersize=7, label="深蓝")
    ax2.plot(x, df["阿维塔(万辆)"].values, "s--", color="#7B1FA2", linewidth=2,
             markersize=7, label="阿维塔")
    ax2.plot(x, df["启源(万辆)"].values, "D-.", color="#E65100", linewidth=2,
             markersize=7, label="启源")

    for i in range(len(x)):
        for j, col in enumerate(["深蓝(万辆)", "阿维塔(万辆)", "启源(万辆)"]):
            v = df[col].values[i]
            if v > 0:
                offsets = [(-12, 12), (12, -14), (-12, 12)]
                ax2.annotate(f"{v:.1f}", (x[i], v),
                             textcoords="offset points",
                             xytext=offsets[j], fontsize=7,
                             color=["#1565C0", "#7B1FA2", "#E65100"][j])

    ax2.set_xticks(x)
    ax2.set_xticklabels(quarters, fontsize=9, rotation=30)
    ax2.set_ylabel("万辆", fontsize=11)
    ax2.set_title("长安新能源三大品牌季度销量走势",
                  fontsize=13, fontweight="bold")
    ax2.legend(loc="upper left", fontsize=9)
    ax2.grid(True, alpha=0.25)

    fig.suptitle("长安汽车季度销量深度分析\n数据来源：公司财报 & 公开披露",
                 fontsize=15, fontweight="bold", y=1.01)
    fig.tight_layout()
    if save_path is None:
        save_path = os.path.join(REPORTS_DIR, "changan_quarterly_structure.png")
    fig.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"[OK] {save_path}")
    return save_path


def plot_seres_quarterly_structure(df_sr: pd.DataFrame = None,
                                    save_path: str = None) -> str:
    """
    图8: 赛力斯季度销量结构（问界 vs 其他堆叠 + 问界占比走势）
    """
    if df_sr is None:
        df_sr = load_seres_quarterly()

    df = df_sr.copy()
    quarters = df["时期"].tolist()
    x = np.arange(len(quarters))

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(16, 10),
                                   gridspec_kw={"height_ratios": [1.2, 0.8]})

    # ── 上图：问界 vs 其他堆叠柱 ──
    aito = df["问界系列(万辆)"].values
    other = df["其他车型(万辆)"].values
    aito_pct = df["问界占比(%)"].values

    bar_width = 0.55
    ax1.bar(x, other, bar_width, color="#BDBDBD", alpha=0.7, label="其他车型（万辆）", zorder=2)
    ax1.bar(x, aito, bar_width, bottom=other, color="#FF5722", alpha=0.9,
            label="问界系列（万辆）", zorder=2)

    for i in range(len(x)):
        total_h = other[i] + aito[i]
        ax1.text(x[i], total_h + 0.3, f"{aito_pct[i]:.1f}%", ha="center",
                 fontsize=8, fontweight="bold", color="#BF360C")

    # 标注关键里程碑
    for idx, q in enumerate(quarters):
        if q == "2023Q3":
            ax1.annotate("新M7\n9月上市", xy=(idx, other[idx] + aito[idx]),
                         xytext=(15, 20), textcoords="offset points", fontsize=7,
                         arrowprops=dict(arrowstyle="->", color="#BF360C", lw=0.8),
                         bbox=dict(boxstyle="round,pad=0.2", fc="#FFF3E0", alpha=0.8))
        if q == "2024Q2":
            ax1.annotate("M9放量\n双爆款", xy=(idx, other[idx] + aito[idx]),
                         xytext=(15, 20), textcoords="offset points", fontsize=7,
                         arrowprops=dict(arrowstyle="->", color="#BF360C", lw=0.8),
                         bbox=dict(boxstyle="round,pad=0.2", fc="#FFF3E0", alpha=0.8))

    ax1.set_xticks(x)
    ax1.set_xticklabels(quarters, fontsize=9, rotation=30)
    ax1.set_ylabel("万辆", fontsize=11)
    ax1.set_title("赛力斯季度销量结构：问界 vs 其他（柱顶数字 = 问界占比）",
                  fontsize=13, fontweight="bold")
    ax1.legend(loc="upper left", fontsize=9)
    ax1.grid(True, alpha=0.25, axis="y")
    ax1.set_ylim(0, ax1.get_ylim()[1] * 1.12)

    # ── 下图：问界占比趋势 ──
    ax2.fill_between(x, 0, aito_pct, alpha=0.25, color="#FF5722")
    ax2.plot(x, aito_pct, "o-", color="#FF5722", linewidth=2.5, markersize=8)
    ax2.axhline(y=50, color="gray", linestyle="--", linewidth=0.8, alpha=0.5)
    ax2.axhline(y=90, color="#4CAF50", linestyle="--", linewidth=0.8, alpha=0.5)

    for i in range(len(x)):
        ax2.annotate(f"{aito_pct[i]:.1f}%", (x[i], aito_pct[i]),
                     textcoords="offset points", xytext=(0, 10),
                     ha="center", fontsize=8, color="#BF360C")

    ax2.set_xticks(x)
    ax2.set_xticklabels(quarters, fontsize=9, rotation=30)
    ax2.set_ylabel("问界占比 (%)", fontsize=11, color="#FF5722")
    ax2.tick_params(axis="y", labelcolor="#FF5722")
    ax2.set_title("问界系列销量占比季度走势", fontsize=13, fontweight="bold")
    ax2.grid(True, alpha=0.25)

    fig.suptitle("赛力斯季度销量深度分析\n数据来源：公司财报 & 公开披露",
                 fontsize=15, fontweight="bold", y=1.01)
    fig.tight_layout()
    if save_path is None:
        save_path = os.path.join(REPORTS_DIR, "seres_quarterly_structure.png")
    fig.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"[OK] {save_path}")
    return save_path

def _align_quarterly(df_ca: pd.DataFrame, df_sr: pd.DataFrame):
    """对齐长安/赛力斯季度时间轴，返回 (common_q, ca_sub, sr_sub, x)"""
    ca_q = set(df_ca["时期"].tolist())
    sr_q = set(df_sr["时期"].tolist())
    common_q = sorted(ca_q & sr_q)
    ca_sub = df_ca[df_ca["时期"].isin(common_q)].set_index("时期").loc[common_q]
    sr_sub = df_sr[df_sr["时期"].isin(common_q)].set_index("时期").loc[common_q]
    x = np.arange(len(common_q))
    return common_q, ca_sub, sr_sub, x


def plot_quarterly_comparison(df_ca: pd.DataFrame = None,
                               df_sr: pd.DataFrame = None,
                               save_path: str = None) -> str:
    """
    图9: 长安 vs 赛力斯 季度全面对标（上：销量对标，下：新能源/问界渗透率对标）
    """
    if df_ca is None:
        df_ca = load_changan_quarterly()
    if df_sr is None:
        df_sr = load_seres_quarterly()

    common_q, ca_sub, sr_sub, x = _align_quarterly(df_ca, df_sr)
    bar_width = 0.3

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(16, 11),
                                   gridspec_kw={"height_ratios": [1, 0.85]})

    # ── 上图：季度总销量分组柱 + 新能源散点 ──
    ax1.bar(x - bar_width/2, ca_sub["总销量(万辆)"].values, bar_width,
            color="#2196F3", alpha=0.8, label="长安汽车 总销量", zorder=2)
    ax1.bar(x + bar_width/2, sr_sub["总销量(万辆)"].values, bar_width,
            color="#FF5722", alpha=0.8, label="赛力斯 总销量", zorder=2)
    ax1.scatter(x - bar_width/2, ca_sub["新能源合计(万辆)"].values,
                marker="o", s=50, color="#0D47A1", zorder=3, label="长安 新能源销量")
    ax1.scatter(x + bar_width/2, sr_sub["问界系列(万辆)"].values,
                marker="s", s=50, color="#BF360C", zorder=3, label="赛力斯 问界销量")

    for i in range(len(x)):
        ax1.text(x[i] - bar_width/2, ca_sub["总销量(万辆)"].values[i] + 0.5,
                 f"{ca_sub['总销量(万辆)'].values[i]:.1f}", ha="center",
                 fontsize=7, color="#0D47A1")
        ax1.text(x[i] + bar_width/2, sr_sub["总销量(万辆)"].values[i] + 0.5,
                 f"{sr_sub['总销量(万辆)'].values[i]:.1f}", ha="center",
                 fontsize=7, color="#BF360C")

    ax1.set_xticks(x)
    ax1.set_xticklabels(common_q, fontsize=9, rotation=30)
    ax1.set_ylabel("万辆", fontsize=11)
    ax1.set_title("季度总销量与新能源销量对标（柱=总销量，点=新能源/问界）",
                  fontsize=13, fontweight="bold")
    ax1.legend(loc="upper left", fontsize=8, ncol=2)
    ax1.grid(True, alpha=0.25, axis="y")

    # ── 下图：新能源/问界渗透率对比 ──
    ax2.plot(x, ca_sub["新能源占比(%)"].values, "o-", color="#2196F3",
             linewidth=2.5, markersize=9, label="长安汽车 新能源占比(%)")
    ax2.plot(x, sr_sub["问界占比(%)"].values, "s-", color="#FF5722",
             linewidth=2.5, markersize=9, label="赛力斯 问界占比(%)")

    for i in range(len(x)):
        ax2.annotate(f"{ca_sub['新能源占比(%)'].values[i]:.1f}%",
                     (x[i], ca_sub["新能源占比(%)"].values[i]),
                     textcoords="offset points", xytext=(0, -15),
                     ha="center", fontsize=8, color="#1565C0")
        ax2.annotate(f"{sr_sub['问界占比(%)'].values[i]:.1f}%",
                     (x[i], sr_sub["问界占比(%)"].values[i]),
                     textcoords="offset points", xytext=(0, 12),
                     ha="center", fontsize=8, color="#BF360C")

    ax2.axhline(y=50, color="gray", linestyle="--", linewidth=0.8, alpha=0.5)
    ax2.set_xticks(x)
    ax2.set_xticklabels(common_q, fontsize=9, rotation=30)
    ax2.set_ylabel("占比 (%)", fontsize=11)
    ax2.set_title("新能源渗透率季度对标（长安=NEV/总销量，赛力斯=问界/总销量）",
                  fontsize=13, fontweight="bold")
    ax2.legend(loc="upper left", fontsize=9)
    ax2.grid(True, alpha=0.25)
    ax2.set_ylim(0, 105)

    fig.suptitle("长安汽车 vs 赛力斯 季度全面对标分析\n数据来源：公司财报 & 公开披露",
                 fontsize=15, fontweight="bold", y=1.01)
    fig.tight_layout()
    if save_path is None:
        save_path = os.path.join(REPORTS_DIR, "quarterly_comparison.png")
    fig.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"[OK] {save_path}")
    return save_path
    return save_path


# ═══════════════════════════════════════════════════════════════
# 5. 综合报表
# ═══════════════════════════════════════════════════════════════

def generate_summary_report() -> dict:
    """生成NEV行业分析摘要字典，供 Notebook 使用"""
    df_monthly = load_nev_monthly()
    df_annual = load_nev_annual()
    df_8co = load_8company_annual()
    df_pen = load_8company_penetration()
    df_ca = load_changan_quarterly()
    df_sr = load_seres_quarterly()

    yearly = compute_yearly_growth(df_monthly)
    seasonal = compute_seasonal_pattern(df_monthly)
    latest_year_data = df_monthly[df_monthly["年份"] == df_monthly["年份"].max()]
    latest_month = latest_year_data[latest_year_data["月份"] == latest_year_data["月份"].max()]

    # 渗透率表的列名是整数年份
    pen_cols = [c for c in df_pen.columns if c != "公司"]
    latest_pen_year = max(int(c) for c in pen_cols)
    pen_data = df_pen[["公司", latest_pen_year]].rename(columns={latest_pen_year: "渗透率_%"}).to_dict(orient="records") if pen_cols else []

    # 季度最新数据
    latest_ca = df_ca.iloc[-1] if len(df_ca) > 0 else None
    latest_sr = df_sr.iloc[-1] if len(df_sr) > 0 else None

    report = {
        "数据时间范围": f"{df_monthly['年份'].min()}-{df_monthly['年份'].max()}",
        "最新月度数据": {
            "时间": latest_month["时间"].values[0] if len(latest_month) > 0 else "N/A",
            "NEV产量_万辆": float(latest_month["新能源汽车产量（万辆）"].values[0]) if len(latest_month) > 0 else None,
            "NEV销量_万辆": float(latest_month["新能源汽车销量（万辆）"].values[0]) if len(latest_month) > 0 else None,
            "销量同比增速_%": float(latest_month["销量同比增速（%）"].values[0]) if len(latest_month) > 0 and "销量同比增速（%）" in latest_month.columns else None,
        },
        "年度汇总": yearly.to_dict(orient="records"),
        "季节性峰值月份": int(seasonal.loc[seasonal["平均季节性指数"].idxmax(), "月份"]),
        "季节性谷值月份": int(seasonal.loc[seasonal["平均季节性指数"].idxmin(), "月份"]),
        "车企最新渗透率": pen_data,
        "长安汽车最新季度": {
            "时期": str(latest_ca["时期"]) if latest_ca is not None else "N/A",
            "总销量_万辆": float(latest_ca["总销量(万辆)"]) if latest_ca is not None else None,
            "新能源合计_万辆": float(latest_ca["新能源合计(万辆)"]) if latest_ca is not None else None,
            "新能源占比_%": float(latest_ca["新能源占比(%)"]) if latest_ca is not None else None,
        },
        "赛力斯最新季度": {
            "时期": str(latest_sr["时期"]) if latest_sr is not None else "N/A",
            "总销量_万辆": float(latest_sr["总销量(万辆)"]) if latest_sr is not None else None,
            "问界系列_万辆": float(latest_sr["问界系列(万辆)"]) if latest_sr is not None else None,
            "问界占比_%": float(latest_sr["问界占比(%)"]) if latest_sr is not None else None,
        },
    }
    return report


# ═══════════════════════════════════════════════════════════════
# 6. 主入口
# ═══════════════════════════════════════════════════════════════

def run_all_analysis():
    """运行所有分析并生成全部图表"""
    print("=" * 60)
    print("  新能源汽车行业销量分析")
    print("=" * 60)

    # 加载
    df_monthly = load_nev_monthly()
    print(f"[LOAD] CAAM NEV 月度数据: {df_monthly.shape[0]} 行")

    df_overall = load_overall_market()
    print(f"[LOAD] 整体市场月度数据: {df_overall.shape[0]} 行")

    df_8co = load_8company_annual()
    print(f"[LOAD] 8家车企年度销量: {df_8co.shape[0]} 家")

    df_ca = load_changan_quarterly()
    print(f"[LOAD] 长安汽车季度数据: {df_ca.shape[0]} 行")

    df_sr = load_seres_quarterly()
    print(f"[LOAD] 赛力斯季度数据: {df_sr.shape[0]} 行")

    # 计算
    yearly = compute_yearly_growth(df_monthly)
    df_merged = compute_nev_penetration(df_monthly, df_overall)

    # ── 行业级图表 ──
    results = []
    results.append(plot_nev_monthly_trend(df_monthly))
    results.append(plot_nev_yearly_bar(yearly))
    results.append(plot_nev_penetration(df_merged))
    results.append(plot_company_vs_industry(df_8co, yearly))
    results.append(plot_seasonal_heatmap(df_monthly))
    results.append(plot_yoy_growth_curve(df_monthly))

    # ── 季度深度图表：长安 & 赛力斯 ──
    print("\n--- 季度深度分析 ---")
    results.append(plot_changan_quarterly_structure(df_ca))
    results.append(plot_seres_quarterly_structure(df_sr))
    results.append(plot_quarterly_comparison(df_ca, df_sr))

    # 摘要
    report = generate_summary_report()
    print(f"\n📊 摘要报告:")
    print(f"   数据范围: {report['数据时间范围']}")
    latest = report["最新月度数据"]
    print(f"   最新月份: {latest['时间']}  销量: {latest['NEV销量_万辆']}万辆  同比: {latest.get('销量同比增速_%', 'N/A')}%")
    if report.get("季节性峰值月份"):
        print(f"   季节性峰值: {report['季节性峰值月份']}月  谷值: {report['季节性谷值月份']}月")

    ca_q = report.get("长安汽车最新季度", {})
    sr_q = report.get("赛力斯最新季度", {})
    if ca_q:
        print(f"   长安汽车 {ca_q['时期']}: 总销{ca_q['总销量_万辆']}万辆  NEV占比{ca_q['新能源占比_%']}%")
    if sr_q:
        print(f"   赛力斯 {sr_q['时期']}: 总销{sr_q['总销量_万辆']}万辆  问界占比{sr_q['问界占比_%']}%")

    print(f"\n✅ 共生成 {len([r for r in results if r])} 张图表")
    return results, report


if __name__ == "__main__":
    matplotlib.use("Agg")
    run_all_analysis()
