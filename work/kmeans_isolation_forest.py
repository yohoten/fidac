#!/usr/bin/env python3
"""
K-Means聚类 + 孤立森林异常检测
=============================
K-Means: 17家车企按6个财务维度聚类 → 定位赛力斯/长安的"风险群"
孤立森林: 识别每家企业的异常财务指标 → 对比谁的异常信号更多

依赖: pip install scikit-learn
"""

import sys; sys.stdout.reconfigure(encoding='utf-8')
import pandas as pd, numpy as np
from pathlib import Path
from sklearn.cluster import KMeans
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei','SimHei']
plt.rcParams['axes.unicode_minus'] = False

DATA_DIR = Path(r'F:\（8）Desktop\财务数智决策应用赛_260725\FIDAC\data')
OUT_DIR = Path(r'F:\（8）Desktop\财务数智决策应用赛_260725\FIDAC\reports')
OUT_DIR.mkdir(exist_ok=True)

COMPANIES = [
    ('601127','赛力斯','★主研究·AITO问界'), ('000625','长安汽车','★主研究·深蓝/阿维塔'),
    ('002594','比亚迪','乘用车龙头'), ('600104','上汽集团','乘用车龙头'),
    ('601633','长城汽车','乘用车龙头'), ('601238','广汽集团','乘用车龙头'),
    ('600418','江淮汽车','新能源乘用车'), ('600733','北汽蓝谷','新能源乘用车'),
]

FEATURE_METRICS = ['毛利率(%)','净利率(%)','ROE(%)','资产负债率(%)','流动比率','营收同比(%)']


def load_features():
    """加载17家车企的最新关键财务指标"""
    records = []
    for code, name, cat in COMPANIES:
        path = DATA_DIR / f'{code}_{name}_财务数据.xlsx'
        if not path.exists(): continue
        xl = pd.ExcelFile(path)
        if '财务分析指标' not in xl.sheet_names: continue
        df = pd.read_excel(xl, '财务分析指标', index_col=0)
        annual_cols = [c for c in df.columns if '年报' in str(c)]
        if not annual_cols: continue
        latest = annual_cols[-1]

        row = {'代码':code, '公司':name, '分类':cat}
        for m in FEATURE_METRICS:
            if m in df.index:
                v = df.loc[m, latest]
                row[m] = float(v) if pd.notna(v) else None
        if all(row.get(m) is not None for m in FEATURE_METRICS):
            records.append(row)

    return pd.DataFrame(records)


def run_kmeans(df):
    """K-Means 聚类（K=3或4）"""
    print(f'\n{"="*60}')
    print(f'  K-Means 聚类分析')
    print(f'{"="*60}')

    X = df[FEATURE_METRICS].values
    names = df['公司'].values

    # 标准化
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # 最优K (elbow method)
    inertias = []
    for k in range(2, min(8, len(df))):
        km = KMeans(n_clusters=k, random_state=42, n_init=10)
        km.fit(X_scaled)
        inertias.append(km.inertia_)

    # K=3 聚类
    km = KMeans(n_clusters=3, random_state=42, n_init=10)
    labels = km.fit_predict(X_scaled)

    df['cluster'] = labels
    for i in range(3):
        members = df[df['cluster']==i]['公司'].values
        print(f'  群{i}: {", ".join(members)}')

    # 重点关注目标公司
    for name in ['赛力斯','长安汽车']:
        if name in df['公司'].values:
            c = df[df['公司']==name]['cluster'].values[0]
            others = df[df['cluster']==c]['公司'].values
            print(f'\n  【{name}】在群{c}，同群企业: {", ".join(others)}')

    # PCA 可视化
    pca = PCA(n_components=2)
    X_pca = pca.fit_transform(X_scaled)
    fig, ax = plt.subplots(figsize=(10, 8))
    colors = ['#E74C3C','#3498DB','#2ECC71']
    for i in range(3):
        mask = labels == i
        ax.scatter(X_pca[mask,0], X_pca[mask,1], c=colors[i], s=100, label=f'群{i}', edgecolors='black')
    for j, name in enumerate(names):
        ax.annotate(name, (X_pca[j,0], X_pca[j,1]), fontsize=9, ha='center', xytext=(0,8), textcoords='offset points')
    ax.set_title('17家车企 K-Means聚类 (PCA降维)', fontsize=14)
    ax.legend()
    fig.savefig(OUT_DIR / 'kmeans_clusters.png', dpi=120, bbox_inches='tight')
    plt.close(fig)
    print(f'\n  图表: kmeans_clusters.png')

    return df


def run_isolation_forest(df):
    """孤立森林异常检测"""
    print(f'\n{"="*60}')
    print(f'  孤立森林 异常检测')
    print(f'{"="*60}')

    X = df[FEATURE_METRICS].values
    names = df['公司'].values

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    iso = IsolationForest(contamination=0.15, random_state=42)
    outlier_labels = iso.fit_predict(X_scaled)  # -1=异常, 1=正常
    anomaly_scores = iso.decision_function(X_scaled)  # 越小越异常

    df['anomaly'] = outlier_labels
    df['anomaly_score'] = anomaly_scores

    # 找出异常企业
    anomalies = df[df['anomaly']==-1]
    print(f'  异常企业 ({len(anomalies)}家):')
    for _, row in anomalies.iterrows():
        print(f'    ⚠️ {row["公司"]} (异常得分={row["anomaly_score"]:.3f})')

    # 重点关注
    for name in ['赛力斯','长安汽车']:
        if name in df['公司'].values:
            s = df[df['公司']==name]['anomaly_score'].values[0]
            label = '⚠️ 异常' if df[df['公司']==name]['anomaly'].values[0]==-1 else '✅ 正常'
            print(f'  {name}: {label} (得分={s:.3f}, 越低越异常)')

    # 异常得分可视化
    fig, ax = plt.subplots(figsize=(12, 6))
    sorted_df = df.sort_values('anomaly_score')
    colors = ['#E74C3C' if s < -0.05 else '#2ECC71' for s in sorted_df['anomaly_score']]
    ax.barh(range(len(sorted_df)), sorted_df['anomaly_score'], color=colors)
    ax.set_yticks(range(len(sorted_df)))
    ax.set_yticklabels(sorted_df['公司'].values)
    ax.axvline(x=0, color='black', linestyle='--', alpha=0.5)
    ax.set_xlabel('异常得分 (越低越异常)')
    ax.set_title('孤立森林 — 17家车企异常检测', fontsize=14)
    fig.tight_layout()
    fig.savefig(OUT_DIR / 'isolation_forest.png', dpi=120, bbox_inches='tight')
    plt.close(fig)
    print(f'\n  图表: isolation_forest.png')

    return df


def main():
    print(f'{"="*60}')
    print(f'  K-Means + 孤立森林 — 赛力斯 vs 长安')
    print(f'{"="*60}')

    df = load_features()
    print(f'\n已加载 {len(df)} 家企业, 特征维度: {FEATURE_METRICS}')

    df_kmeans = run_kmeans(df)
    df_iso = run_isolation_forest(df)

    # 整合结论
    print(f'\n{"="*60}')
    print(f'  综合结论')
    print(f'{"="*60}')
    for name in ['赛力斯','长安汽车']:
        if name in df['公司'].values:
            cluster = df_kmeans[df_kmeans['公司']==name]['cluster'].values[0]
            anomaly = df_iso[df_iso['公司']==name]['anomaly'].values[0]
            score = df_iso[df_iso['公司']==name]['anomaly_score'].values[0]
            cluster_risk = '高风险' if cluster==0 else ('中等' if cluster==1 else '低风险')
            anomaly_str = '异常' if anomaly==-1 else '正常'
            print(f'  {name}: 群{cluster}({cluster_risk}) | 异常检测:{anomaly_str}(得分={score:.3f})')

    print(f'\n图表已保存到 {OUT_DIR}/')


if __name__ == '__main__':
    main()
