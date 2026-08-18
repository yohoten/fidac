# -*- coding: utf-8 -*-
"""
xl.16888.com 电动车月度销量爬虫（ev_sales_crawler）

抓取指定时间段内逐月的电动车销量榜单（厂商 / 车型 / 售价区间 / 销量），
合并后导出为 Excel，供 FIDAC 项目数据分析使用。

用法:
    python ev_sales_crawler.py                          # 默认抓取 2023 全年
    python ev_sales_crawler.py 2024 2025                # 2024-01 ~ 2025-12
    python ev_sales_crawler.py 20240101 20240331 -o out.xlsx
"""
import argparse
import math
import re
import time

import pandas as pd
import requests
from lxml import etree

BASE_URL = "https://xl.16888.com/ev-{begin}-{end}-{page}.html"
COOKIES = {
    'car16888_set_provinceId': '31',
    'car16888_set_cityId': '383',
    'car16888_set_area': '359',
    'car16888_set_areaName': '%E6%9D%AD%E5%B7%9E',
    'car16888_set_areaDir': 'hz',
    'car16888_set_iscity': '',
}
HEADERS = {
    'authority': 'xl.16888.com',
    'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
    'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
    'referer': 'https://xl.16888.com/ev-202301-202312-1.html',
    'sec-ch-ua': '"Not A(Brand";v="99", "Microsoft Edge";v="121", "Chromium";v="121"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
    'sec-fetch-dest': 'document',
    'sec-fetch-mode': 'navigate',
    'sec-fetch-site': 'same-origin',
    'sec-fetch-user': '?1',
    'upgrade-insecure-requests': '1',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0',
}

PAGE_SIZE = 50          # 每页 50 行
MAX_RETRIES = 3         # 单页最大重试次数
REQUEST_INTERVAL = 0.8  # 每次请求间隔（秒），礼貌爬取避免被封


def month_sequence(begin_date: str, end_date: str) -> list:
    """生成 [begin_date, end_date] 区间内所有 'YYYYMM' 月份字符串。

    入参支持 'YYYYMMDD' 或 'YYYYMM' 两种格式，例如 '20230101' / '202301'。
    """
    def to_ym(d: str):
        d = d.strip()
        return int(d[:4]), int(d[4:6])

    y1, m1 = to_ym(begin_date)
    y2, m2 = to_ym(end_date)
    if (y1, m1) > (y2, m2):
        raise ValueError(f"begin_date({begin_date}) 不能晚于 end_date({end_date})")

    months = []
    y, m = y1, m1
    while (y, m) <= (y2, m2):
        months.append(f"{y:04d}{m:02d}")
        m += 1
        if m == 13:
            y, m = y + 1, 1
    return months


def _get(session: requests.Session, url: str) -> str:
    """带重试的 GET 请求，返回页面文本。"""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = session.get(url, cookies=COOKIES, headers=HEADERS, timeout=20)
            resp.raise_for_status()
            resp.encoding = resp.apparent_encoding or 'utf-8'
            return resp.text
        except requests.RequestException as exc:
            if attempt == MAX_RETRIES:
                raise
            print(f"[warn] 请求失败({exc})，将重试: {url}")
            time.sleep(2 * attempt)


def fetch_month_sales(session: requests.Session, year_month: str) -> pd.DataFrame:
    """抓取单月销量榜单，返回 DataFrame（年份/月份/厂商/车型/售价/销量）。"""
    url = BASE_URL.format(begin=year_month, end=year_month, page=1)
    tree = etree.HTML(_get(session, url))

    # 1) 从“共N条数据”解析总条数，算出总页数（正则比固定切片健壮）
    page_info = ''.join(tree.xpath('//span[@class="lineBlock va-m"]//text()')) or ''
    total_match = re.search(r'共(\d+)条', page_info)
    if not total_match:
        raise RuntimeError(f"未找到销量总条数，页面结构可能已变化: {url}")
    page_total = max(math.ceil(int(total_match.group(1)) / PAGE_SIZE), 1)

    rows = []
    for page in range(1, page_total + 1):
        page_url = BASE_URL.format(begin=year_month, end=year_month, page=page)
        page_tree = etree.HTML(_get(session, page_url))
        tables = page_tree.xpath(
            '//table[contains(@class,"xl-table-def") and contains(@class,"xl-table-a")]')
        if not tables:
            print(f"[warn] 第 {page} 页未找到数据表，跳过: {page_url}")
            continue

        # 2) 注意用 .//tr 只取该表格内的行，并跳过表头行
        for tr in tables[0].xpath('.//tr')[1:]:
            tds = tr.xpath('.//td')
            if len(tds) < 5:
                continue
            model = ''.join(tds[1].itertext()).strip()
            sales_text = ''.join(tds[2].itertext())
            company = ''.join(tds[3].itertext()).strip()
            price = ''.join(tds[4].itertext()).strip()
            if not model:                      # 空行（如合计/广告行）直接跳过
                continue
            sales = re.sub(r'\D', '', sales_text)   # 去掉千分位等非数字字符
            rows.append({
                '年份': year_month[:4],
                '月份': year_month[4:6],
                '厂商': company,
                '车型': model,
                '售价（万元）': price,
                '销量': int(sales) if sales else None,
            })
        if page < page_total:
            time.sleep(REQUEST_INTERVAL)

    return pd.DataFrame(rows, columns=['年份', '月份', '厂商', '车型', '售价（万元）', '销量'])


def get_sales_data(begin_date: str, end_date: str, output: str = None) -> str:
    """抓取时间段内所有月份并合并导出 Excel，返回输出文件路径。"""
    session = requests.Session()
    months = month_sequence(begin_date, end_date)
    print(f"共 {len(months)} 个月: {months[0]} ~ {months[-1]}")

    frames = []
    for i, ym in enumerate(months, 1):
        print(f"[{i}/{len(months)}] 抓取 {ym} ...")
        frames.append(fetch_month_sales(session, ym))
        if i < len(months):
            time.sleep(REQUEST_INTERVAL)

    df = pd.concat(frames, ignore_index=True)
    if df.empty:
        print("[warn] 未抓到任何数据，不导出文件")
        return ''

    if output is None:
        output = f"EV销量_{months[0]}-{months[-1]}.xlsx"
    df.to_excel(output, index=False)
    print(f"完成：共 {len(df)} 行，已导出 -> {output}")
    return output


def main():
    parser = argparse.ArgumentParser(description='xl.16888.com 电动车月度销量爬虫')
    parser.add_argument('begin', nargs='?', default='20230101',
                        help='开始日期 YYYYMMDD 或 YYYYMM（默认 20230101）')
    parser.add_argument('end', nargs='?', default='20231231',
                        help='结束日期 YYYYMMDD 或 YYYYMM（默认 20231231）')
    parser.add_argument('-o', '--output', help='输出 Excel 路径（默认脚本目录下）')
    args = parser.parse_args()
    get_sales_data(args.begin, args.end, args.output)


if __name__ == '__main__':
    main()
