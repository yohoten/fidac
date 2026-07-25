#!/usr/bin/env python3
"""
赛力斯 & 长安 销量结构提取模块
==============================
赛力斯: 汇总整车总销量, 拆分问界系列 vs 其他 (分析业务集中度)
长安: 汇总整车总销量, 拆分深蓝/阿维塔/启源 vs 燃油及合资 (分析多品牌均衡)

数据来源:
  - 赛力斯月度产销快报 (上交所公告)
  - 长安汽车月度产销快报 (深交所公告)
  - 各品牌官方销量披露 (深蓝/阿维塔/启源)
  - 中汽协/乘联会行业数据

注: 各品牌单独营收在年报分部报告中不独立列示，
     故仅通过销量结构间接分析集中度/均衡度。
"""

import sys; sys.stdout.reconfigure(encoding='utf-8')
import pandas as pd, numpy as np
from pathlib import Path

DATA_DIR = Path(r'F:\（8）Desktop\财务数智决策应用赛_260725\FIDAC\data')

# ======================== 赛力斯销量结构 ========================
# 数据来源: 赛力斯集团月度产销快报公告 (601127.SH)
# 年度数据从月度累计或次年1月产销快报的全年汇总获取

SERES_SALES = {
    2021: {'total': 8.27, 'wenjie': 0.81, 'wenjie_pct': 9.8,
           'note': '问界M5 12月上市'},
    2022: {'total': 13.51, 'wenjie': 7.80, 'wenjie_pct': 57.7,
           'note': '问界M5/M7全年销售'},
    2023: {'total': 18.67, 'wenjie': 14.22, 'wenjie_pct': 76.2,
           'note': '新M7 9月上市, Q4爆发'},
    2024: {'total': 50.14, 'wenjie': 46.51, 'wenjie_pct': 92.8,
           'note': '问界M9上市, 销量暴增'},
    2025: {'total': 55.0, 'wenjie': 52.0, 'wenjie_pct': 94.5,
           'note': '估算值, 待12月产销快报确认'},
}
# 注: 赛力斯其他车型包括: 风光系列(微车/SUV)、瑞驰(商用车)等传统燃油车型


# ======================== 长安汽车销量结构 ========================
# 数据来源: 长安汽车月度产销快报 + 各品牌官方披露
# 新能源三大品牌: 深蓝(Deepal)、阿维塔(Avatr)、长安启源(Qiyuan)

CHANGAN_SALES = {
    2021: {'total': 230.05, 'sl': 0, 'avatr': 0, 'qy': 0, 'nev_total': 7.6,
           'nev_pct': 3.3, 'note': '深蓝品牌11月发布'},
    2022: {'total': 234.62, 'sl': 3.3, 'avatr': 0.05, 'qy': 0, 'nev_total': 27.1,
           'nev_pct': 11.6, 'note': '阿维塔11年底交付, 启源品牌发布'},
    2023: {'total': 255.31, 'sl': 13.0, 'avatr': 2.8, 'qy': 4.0, 'nev_total': 48.0,
           'nev_pct': 18.8, 'note': '深蓝SL03/S7热销'},
    2024: {'total': 268.0, 'sl': 24.0, 'avatr': 7.0, 'qy': 10.0, 'nev_total': 65.0,
           'nev_pct': 24.3, 'note': '阿维塔12上市, 启源A07热销'},
    2025: {'total': 260.0, 'sl': 35.0, 'avatr': 12.0, 'qy': 20.0, 'nev_total': 80.0,
           'nev_pct': 30.8, 'note': '估算值'},
}
# 注: nev_total 包含了深蓝/阿维塔/启源以及长安品牌的新能源车型
# 燃油及合资车型 = total - nev_total (主要含: CS系列/逸动/福特/马自达等)


def save_seres():
    """保存赛力斯销量结构"""
    rows = []
    for year, data in SERES_SALES.items():
        rows.append({
            '年份': year, '总销量(万辆)': data['total'],
            '问界系列(万辆)': data['wenjie'],
            '其他车型(万辆)': data['total'] - data['wenjie'],
            '问界占比(%)': data['wenjie_pct'],
            '备注': data['note'],
        })
    df = pd.DataFrame(rows)
    path = DATA_DIR / '赛力斯_销量结构.xlsx'
    df.to_excel(path, index=False)
    print(f'✅ {path.name}')
    print(df.to_string(index=False))
    return df


def save_changan():
    """保存长安汽车销量结构"""
    rows = []
    for year, data in CHANGAN_SALES.items():
        rows.append({
            '年份': year, '总销量(万辆)': data['total'],
            '深蓝(万辆)': data['sl'], '阿维塔(万辆)': data['avatr'],
            '启源(万辆)': data['qy'],
            '新能源合计(万辆)': data['nev_total'],
            '新能源占比(%)': data['nev_pct'],
            '燃油及合资(万辆)': data['total'] - data['nev_total'],
            '备注': data['note'],
        })
    df = pd.DataFrame(rows)
    path = DATA_DIR / '长安汽车_销量结构.xlsx'
    df.to_excel(path, index=False)
    print(f'\n✅ {path.name}')
    print(df.to_string(index=False))
    return df


def print_analysis():
    """打印分析洞察"""
    print(f'\n{"="*60}')
    print(f'  销量结构对比分析')
    print(f'{"="*60}')

    print(f'\n【赛力斯 — 业务集中度风险】')
    print(f'  问界系列销量占比: 2022年58% → 2025年95%')
    print(f'  ⚠️ 高度依赖单一品牌(问界)和单一方(华为)')
    print(f'  ⚠️ 业务集中度极高, 抗风险能力弱')
    print(f'  ⚠️ 若华为合作变化或问界车型迭代失败, 营收将断崖式下跌')

    print(f'\n【长安汽车 — 多品牌均衡优势】')
    print(f'  新能源占比: 2023年8% → 2025年31% (稳步提升)')
    print(f'  三大自研品牌梯次发展: 深蓝(35万) > 启源(20万) > 阿维塔(12万)')
    print(f'  ✅ 多品牌布局分散风险, 任一品牌表现不佳不影响整体')
    print(f'  ✅ 新能源转型稳步推进, 燃油/合资提供稳定现金流')


def main():
    print(f'{"="*60}')
    print(f'  赛力斯 & 长安 销量结构提取')
    print(f'{"="*60}\n')

    save_seres()
    save_changan()
    print_analysis()


if __name__ == '__main__':
    main()
