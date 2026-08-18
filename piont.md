## 一、🔴 P0 BUG

| #        | 问题                                                         | 位置                                                         |
| -------- | ------------------------------------------------------------ | ------------------------------------------------------------ |
| **P0-1** | **硬编码旧路径** FIDAC（含全角括号）                         | collect_financial_data.py、kmeans_isolation_forest.py、prophet_forecast.py、extract_sales_structure.py |
| **P0-2** | `collect_sales_data()` 用 `pd.ExcelWriter(path)` 无 `mode='a'`，**重跑会整体覆盖主库**，丢 8家车企/CAAM/EV 销量等 17 个表 | collect_financial_data.py 模块2                              |
| **P0-3** | add_company_sales.py 全表重写丢格式（`index=False` + 不保留样式） | add_company_sales.py                                         |

> P0-1 意味着这 4 个脚本**现在根本跑不起来**（项目在 D 盘，路径指向 F 盘旧目录）。项目里 add_company_sales.py、nev_industry_analysis.py、streamlit_app.py 已经用 `Path(__file__)` 相对路径——**两种风格并存，重构只做了一半**。

## 二、🟠 P1 高优

1. **文件命名两套约定**：磁盘是 `000625_长安汽车_财务数据.xlsx`，但 `integrate_financial_data('000625')` 会找不到文件——接口语义不清。建议统一以股票代码为 key + 中文名映射表。
2. **Notebook 与 lib 双份代码**：主 notebook cell 07/10 内嵌旧版 `integrate_financial_data` 和 3051 字的 `financial_ratio`，与 `lib.compute_ratios` 并存，改一处另一处漂移。
3. **同一指标 3~4 套列名/口径**：`毛利率` vs `毛利率(%)`、`净资产收益率` vs `ROE(%)`，跨模块要手工映射。
4. **估算值混存无标注**：extract_sales_structure.py 2025Q3/Q4、"8家车企"表的手工字典均缺来源列。
5. **销量三源口径未对齐**：16888 榜单（零售）vs 产销快报（批发）vs CAAM，139 个厂商名需要归一化主数据表。
6. **2026Q2 财务缺失**：EV 销量已到 2026Q2，财务只有赛力斯/长安 2026Q1——单点回测局限未解决。

## 三、🟡 P2 提升

README/校验脚本写死"22 Sheets"（实际 23）；requirements 全 `>=` 未锁版；backtest_merged.py 依赖 notebook 全局变量不可独立跑；主 notebook 有 3 个超 4000 字的巨型 cell；Git 有 5 个未提交文件。

## 四、分析建议

1. **销量-财务联动**（现有数据即可做，性价比最高）：车型销量份额→营收增速的领先滞后；问界销量占比→赛力斯毛利率回归；单车均价→毛利率交叉——把新抓的 18,634 行车型数据用起来，直接回应"代工协同 vs 自研"的核心论点。
2. **补 2026Q2 → 两点滚动回测**：把已知问题 4 的"单点回测"升级为"两点验证"，评审说服力大增。
3. **敏感性分析**：Z-score 阈值、沃尔权重、聚类 K 值各做切换，证明结论不依赖主观参数。
4. **预警面板扩展**：预测对象从 2 家扩到 8 家，输出"2026 下半年谁在往下走"。