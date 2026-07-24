#!/usr/bin/env python3
"""
港股数据补充模块
===============
利用 Tushare hk_daily 获取股价/市值数据，
与 AkShare HK 财务指标整合。

数据源:
  1. AkShare: stock_financial_hk_analysis_indicator_em (财务指标)
  2. Tushare: hk_daily (股价/市值) — 免费账户 1次/分钟限制

输出: 港股财务综合数据.xlsx
"""

import sys
sys.stdout.reconfigure(encoding='utf-8')
import time as _time

import logging
from pathlib import Path
import pandas as pd
import numpy as np
import akshare as ak
import tushare as ts

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s', datefmt='%H:%M:%S')
logger = logging.getLogger(__name__)

BASE_DIR = Path(r'F:\（8）Desktop\财务数智决策应用赛_260725')
DATA_DIR = BASE_DIR / 'data'
TUSHARE_TOKEN = "758d87c777e79a7cc5c9f72df92b7799e7b02f63a0fff1824aa2ea86"

pro = ts.pro_api(TUSHARE_TOKEN)

HK_COMPANIES = [
    ('00175.HK', '00175', '吉利汽车'),
    ('02015.HK', '02015', '理想汽车'),
    ('09868.HK', '09868', '小鹏汽车'),
    ('09866.HK', '09866', '蔚来汽车'),
    ('09863.HK', '09863', '零跑汽车'),
]


def get_hk_market_data():
    """通过 Tushare 获取港股行情/市值数据（每次调用间隔15秒防限速）"""
    logger.info('Tushare 港股行情数据...')
    all_data = {}

    for ts_code, code, name in HK_COMPANIES:
        try:
            df = pro.hk_daily(ts_code=ts_code, start_date='20240101', end_date='20251231')
            if df is not None and len(df) > 0:
                df['trade_date'] = pd.to_datetime(df['trade_date'])
                annual_stats = {
                    '年均收盘价': round(df['close'].mean(), 2),
                    '年末收盘价': round(df.sort_values('trade_date').iloc[-1]['close'], 2),
                    '最高价': round(df['high'].max(), 2),
                    '最低价': round(df['low'].min(), 2),
                    '交易天数': len(df),
                }
                all_data[name] = annual_stats
                logger.info(f'  {name}: {len(df)} 天, 年末收盘={annual_stats["年末收盘价"]}')
            else:
                logger.warning(f'  {name}: 无数据')
        except Exception as e:
            logger.warning(f'  {name}: {e}')
        _time.sleep(15)  # Tushare 限速

    return pd.DataFrame(all_data).T if all_data else pd.DataFrame()


def get_hk_financial_summary():
    """通过 AkShare 获取最新 HK 财务指标摘要"""
    logger.info('AkShare 港股财务指标...')
    all_data = {}

    for ts_code, code, name in HK_COMPANIES:
        try:
            df = ak.stock_financial_hk_analysis_indicator_em(symbol=code)
            if df is not None and len(df) > 0:
                latest = df.sort_values('REPORT_DATE', ascending=False).iloc[0]
                key_fields = {
                    '报告期': str(latest.get('REPORT_DATE', ''))[:10],
                    '营业收入(元)': float(latest.get('OPERATE_INCOME', 0)),
                    '营收同比%': round(float(latest.get('OPERATE_INCOME_YOY', 0)), 2),
                    '毛利(元)': float(latest.get('GROSS_PROFIT', 0)),
                    '毛利率%': round(float(latest.get('GROSS_PROFIT_RATIO', 0)), 2),
                    '归母净利润(元)': float(latest.get('HOLDER_PROFIT', 0)),
                    '净利率%': round(float(latest.get('NET_PROFIT_RATIO', 0)), 2),
                    'ROE%': round(float(latest.get('ROE_AVG', 0)), 2),
                    'ROA%': round(float(latest.get('ROA', 0)), 2),
                    '资产负债率%': round(float(latest.get('DEBT_ASSET_RATIO', 0)), 2),
                    '流动比率': round(float(latest.get('CURRENT_RATIO', 0)), 2),
                    '基本EPS': float(latest.get('BASIC_EPS', 0)),
                    '每股净资产': float(latest.get('BPS', 0)),
                    '经营现金流/营收%': round(float(latest.get('OCF_SALES', 0)), 2),
                }
                all_data[name] = key_fields
                logger.info(f'  {name}: 营收={key_fields["营业收入(元)"]/1e8:.0f}亿 ROE={key_fields["ROE%"]:.1f}%')
        except Exception as e:
            logger.warning(f'  {name}: {e}')

    return pd.DataFrame(all_data).T if all_data else pd.DataFrame()


def integrate_hk_data():
    logger.info(f'\n{"="*60}')
    logger.info(f'  港股数据整合 (财务指标 + 市场数据)')
    logger.info(f'{"="*60}\n')

    df_fin = get_hk_financial_summary()
    df_mkt = get_hk_market_data()

    if not df_fin.empty:
        combined = df_fin.copy()
        if not df_mkt.empty:
            for name in combined.index:
                if name in df_mkt.index:
                    combined.loc[name, '年末收盘价'] = df_mkt.loc[name, '年末收盘价']
                    combined.loc[name, '最高价'] = df_mkt.loc[name, '最高价']
                    combined.loc[name, '交易天数'] = df_mkt.loc[name, '交易天数']

        # 计算市盈率
        if '年末收盘价' in combined.columns:
            combined['市盈率(PE)'] = combined.apply(
                lambda r: round(r['年末收盘价'] / r['基本EPS'], 1)
                if r['基本EPS'] and r['基本EPS'] > 0 else None, axis=1
            )
            combined['市净率(PB)'] = combined.apply(
                lambda r: round(r['年末收盘价'] / r['每股净资产'], 1)
                if r['每股净资产'] and r['每股净资产'] > 0 else None, axis=1
            )

        output_path = DATA_DIR / '港股财务综合数据.xlsx'
        combined.to_excel(output_path)
        logger.info(f'\n✅ {output_path.name}')

        # 打印
        logger.info(f'\n{"="*60}')
        logger.info(f'  港股关键指标')
        logger.info(f'{"="*60}')
        display_cols = [c for c in ['营业收入(元)', '营收同比%', '毛利率%', '净利率%', 'ROE%',
                       '资产负债率%', '基本EPS', '市盈率(PE)', '市净率(PB)'] if c in combined.columns]

        df_show = combined[display_cols].copy()
        if '营业收入(元)' in df_show.columns:
            df_show['营业收入(元)'] = df_show['营业收入(元)'].apply(lambda x: f'{x/1e8:.1f}亿')
        if '市盈率(PE)' in df_show.columns:
            df_show['市盈率(PE)'] = df_show['市盈率(PE)'].apply(lambda x: f'{x:.1f}' if pd.notna(x) else '-')

        print(df_show.to_string())
        return combined

    return pd.DataFrame()


if __name__ == '__main__':
    integrate_hk_data()
