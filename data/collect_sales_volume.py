#!/usr/bin/env python3
"""
新能源汽车 销量/产量 数据采集模块
==============================
数据源:
  1. 乘联会(CPCA)月度厂商销量排行
  2. 各公司月度产销快报（通过 AkShare/巨潮资讯公告）
  3. 新能源汽车整体市场数据

输出:
  - 月度销量对比表.csv (.xlsx)
  - 新能源渗透率趋势.xlsx
  - 各公司月度产销数据.xlsx
"""

import sys
sys.stdout.reconfigure(encoding='utf-8')

import os
import time
import logging
from pathlib import Path
from datetime import datetime

import pandas as pd
import numpy as np
import akshare as ak

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s', datefmt='%H:%M:%S')
logger = logging.getLogger(__name__)

BASE_DIR = Path(r'F:\（8）Desktop\财务数智决策应用赛_260725')
# OUTPUT_DIR = BASE_DIR / 'output'
OUTPUT_DIR = BASE_DIR / 'data'
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# 目标公司（仅A股上市公司，港股美股暂不支持月度产销快报）
TARGET_BRANDS = [
    '比亚迪', '赛力斯', '长安汽车', '长城汽车', '上汽集团',
    '广汽集团', '北汽蓝谷', '江淮汽车',
    '吉利汽车', '理想汽车', '小鹏汽车', '蔚来', '零跑汽车',
    '特斯拉中国', '奇瑞汽车', '一汽大众',
]


def collect_cpca_monthly_rank():
    """
    收集乘联会月度厂商销量排行。
    注意: car_market_man_rank_cpca 返回的是单一月份数据，
    需要多次调用不同时间段的数据。
    """
    logger.info('乘联会厂商排行...')
    try:
        df = ak.car_market_man_rank_cpca()
        if df is not None and len(df) > 0:
            logger.info(f'  OK: {df.shape}')
            return df
    except Exception as e:
        logger.error(f'  ERR: {e}')
    return pd.DataFrame()


def collect_cpca_total_market():
    """收集乘联会整体市场月度数据"""
    logger.info('乘联会整体市场...')
    try:
        df = ak.car_market_total_cpca()
        if df is not None and len(df) > 0:
            logger.info(f'  OK: {df.shape}')
            return df
    except Exception as e:
        logger.error(f'  ERR: {e}')
    return pd.DataFrame()


def collect_cpca_segment():
    """收集乘联会细分市场数据（A00/A0/A/B/C级别）"""
    logger.info('乘联会细分市场...')
    try:
        df = ak.car_market_segment_cpca()
        if df is not None and len(df) > 0:
            logger.info(f'  OK: {df.shape}')
            return df
    except Exception as e:
        logger.error(f'  ERR: {e}')
    return pd.DataFrame()


def collect_cpca_fuel_type():
    """收集乘联会燃料类型销量（新能源 vs 燃油）"""
    logger.info('乘联会燃料类型销量...')
    try:
        df = ak.car_market_fuel_cpca()
        if df is not None and len(df) > 0:
            logger.info(f'  OK: {df.shape}')
            return df
    except Exception as e:
        logger.error(f'  ERR: {e}')
    return pd.DataFrame()


def collect_company_monthly_sales():
    """
    收集各公司月度产销快报数据。
    通过扫描巨潮资讯公告的关键词获取，而非AkShare直接API。

    替代方案: 手动整理各公司官方发布的月度产销快报。
    以下是整理好的各公司近期月度销量参考数据。
    """
    # 从公开信息整理的参考数据
    # 真实数据应从巨潮资讯公告或公司官网IR下载PDF后手工录入
    # 或使用万得(Wind)/Choice终端导出

    # 此处提供数据框架模板
    df_template = pd.DataFrame({
        '日期': pd.date_range('2023-01-01', periods=36, freq='MS'),
    })
    for brand in TARGET_BRANDS:
        df_template[brand] = np.nan

    logger.info(f'  产销数据模板: {df_template.shape} (数据需手工填充)')
    logger.info(f'  建议: 从各公司官网 https://www.xxx.com 的"投资者关系"→"产销快报"下载')
    return df_template


def calculate_nev_penetration(df_total, df_fuel):
    """
    计算新能源渗透率（基于燃料类型数据）。
    新能源渗透率 = 新能源车销量 / 总销量
    """
    if df_total.empty or df_fuel.empty:
        return pd.DataFrame()

    # 燃料类型数据中的某列代表新能源车销量
    # 需要具体解析数据结构后计算
    logger.info('新能源渗透率计算（需根据数据结构调整）')
    return pd.DataFrame()


# ======================== 主流程 ========================

def main():
    logger.info(f'{"="*60}')
    logger.info(f'  新能源汽车销量数据采集')
    logger.info(f'{"="*60}\n')

    # 收集各维度数据
    df_rank = collect_cpca_monthly_rank()
    df_total = collect_cpca_total_market()
    df_segment = collect_cpca_segment()
    df_fuel = collect_cpca_fuel_type()

    # 导出
    writer = pd.ExcelWriter(OUTPUT_DIR / '新能源汽车行业销量数据.xlsx', engine='openpyxl')

    if not df_rank.empty:
        df_rank.to_excel(writer, sheet_name='厂商月度销量排行', index=False)
    if not df_total.empty:
        df_total.to_excel(writer, sheet_name='整体市场月度销量', index=False)
    if not df_segment.empty:
        df_segment.to_excel(writer, sheet_name='细分市场级别销量', index=False)
    if not df_fuel.empty:
        df_fuel.to_excel(writer, sheet_name='燃料类型销量', index=False)

    writer.close()
    logger.info(f'\n✅ 行业销量数据: {OUTPUT_DIR / "新能源汽车行业销量数据.xlsx"}')

    # 各公司月度产销模板
    df_template = collect_company_monthly_sales()
    template_path = OUTPUT_DIR / '各公司月度产销数据_模板.xlsx'
    df_template.to_excel(template_path, index=False)
    logger.info(f'✅ 产销数据模板: {template_path}')

    logger.info(f'\n{"="*60}')
    logger.info(f'  数据采集完成')
    logger.info(f'{"="*60}')
    logger.info(f'\n💡 补充建议:')
    logger.info(f'  1. 各公司月度产销快报可从官网IR下载:')
    logger.info(f'     - 比亚迪: https://www.byd.com/cn/Investor/Announcement')
    logger.info(f'     - 赛力斯: https://www.seres.com.cn/ir/')
    logger.info(f'     - 长安汽车: https://www.changan.com.cn/investor/')
    logger.info(f'  2. 乘联会月度数据: https://www.cpcaauto.com/')
    logger.info(f'  3. 中汽协月度数据: https://www.caam.org.cn/')
    logger.info(f'  4. 亦可通过 AkShare 个股公告获取产销快报:')
    logger.info(f'     ak.stock_notice_report(symbol="601127")  # 赛力斯')


if __name__ == '__main__':
    main()
