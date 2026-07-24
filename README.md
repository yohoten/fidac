# FIDAC - 财务数智决策应用系统

<div align="center">

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)
![AkShare](https://img.shields.io/badge/AkShare-1.12.0-orange.svg)
![Pandas](https://img.shields.io/badge/Pandas-2.0.0-red.svg)

**基于数字化手段的财务决策辅助工具 | 自动化金融数据采集与深度分析**

</div>

---

## 📋 项目简介

FIDAC（Financial Intelligent Decision Application Competition）是一个专为"财务数智决策应用赛"开发的智能化工具，旨在通过自动化数据采集和深度财务分析，为投资决策提供科学依据。

### ✨ 核心特性

- 🔄 **多源数据采集**：支持 A股、港股、美股等多市场金融数据自动采集
- 📊 **标准化处理**：三大财务报表（资产负债表、利润表、现金流量表）标准化输出
- 🧮 **深度财务分析**：内置杜邦分析、Z-score 预警、沃尔评分法等经典模型
- 📈 **可视化展示**：自动生成财务指标图表和分析报告
- 💾 **缓存机制**：智能数据缓存，提升重复查询效率

---

## 🎯 功能模块

### 1️⃣ 数据采集模块 (`data/`)

| 脚本 | 功能描述 |
|------|---------|
| `collect_financial_data.py` | 主财务数据采集脚本，获取三大报表及财务指标 |
| `collect_hk_supplement.py` | 港股补充数据采集 |
| `collect_sales_volume.py` | 销售体量数据采集 |

**支持的企业：**
- 🚗 新能源汽车：比亚迪 (002594)、赛力斯 (601127)、长安汽车 (000625)
- 🏭 传统车企：上汽集团 (600104)、广汽集团 (601238)、江淮汽车 (600418)
- 🔋 其他：长城汽车 (601633)、北汽蓝谷 (600733)
- 🌍 国际企业：特斯拉 (TSLA)、蔚来 (NIO)、小鹏 (XPEV)、理想 (LI)

### 2️⃣ 分析计算模块 (`work/`)

| 脚本 | 功能描述 |
|------|---------|
| `02_ratio_analysis.py` | 财务比率分析（偿债能力、营运能力、盈利能力等） |
| `03_dupont_zscore_wolle.py` | 综合模型分析（杜邦分析 + Z-score + 沃尔评分法） |

**分析模型：**
- 📐 **杜邦分析**：ROE 分解为销售净利率 × 资产周转率 × 权益乘数
- ⚠️ **Z-score 预警**：Altman 破产风险预测模型
- 🏆 **沃尔评分法**：多维度财务健康度评分体系

---

## 🛠️ 技术栈

- **编程语言**: Python 3.8+
- **数据处理**: Pandas, NumPy
- **金融数据源**: AkShare, Tushare, yfinance
- **Excel 处理**: openpyxl
- **数据可视化**: Matplotlib

---

## 📦 快速开始

### 环境要求

- Python 3.8 或更高版本
- pip 包管理工具

### 安装步骤

#### 1. 克隆仓库

```bash
git clone https://gitee.com/yohoten/FIDAC.git
cd FIDAC
```

#### 2. 创建虚拟环境（推荐）

```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# Linux/Mac
python -m venv .venv
source .venv/bin/activate
```

#### 3. 安装依赖

```bash
pip install -r requirements.txt
```

---

## 🚀 使用指南

### 第一步：采集财务数据

```bash
cd data
python collect_financial_data.py
```

**执行效果：**
- 自动从 AkShare 获取指定企业的财务数据
- 生成 Excel 文件：`{股票代码}_{企业名称}_财务数据.xlsx`
- 包含工作表：资产负债表、利润表、现金流量表、财务分析指标
- 自动计算派生指标（ROE、ROA、毛利率等）
- 数据缓存在 `.cache/` 目录，避免重复请求

### 第二步：运行财务分析

```bash
cd work
python 02_ratio_analysis.py
python 03_dupont_zscore_wolle.py
```

**输出结果：**
- 财务比率分析报告
- 杜邦分析拆解图
- Z-score 破产风险评级
- 沃尔评分法综合排名

---

## 📂 项目结构

```
FIDAC/
├── data/                          # 数据采集模块
│   ├── logs/                      # 运行日志
│   ├── .cache/                    # 数据缓存
│   ├── collect_financial_data.py  # 主采集脚本
│   ├── collect_hk_supplement.py   # 港股补充采集
│   ├── collect_sales_volume.py    # 销售数据采集
│   └── *.xlsx                     # 采集的财务数据文件
├── work/                          # 分析计算模块
│   ├── 02_ratio_analysis.py       # 财务比率分析
│   ├── 03_dupont_zscore_wolle.py  # 综合模型分析
│   └── *.xlsx                     # 分析结果文件
├── output/                        # 输出目录（预留）
├── dosc/                          # 文档资料
├── requirements.txt               # Python 依赖清单
└── README.md                      # 项目说明文档
```

---

## 📊 输出示例

### 财务数据文件结构

每个企业的 Excel 文件包含以下工作表：

1. **资产负债表** - 资产、负债、所有者权益科目
2. **利润表** - 收入、成本、费用、利润科目
3. **现金流量表** - 经营、投资、筹资活动现金流
4. **财务分析指标** - 预计算的财务比率和衍生指标

### 分析结果

- ✅ 勾稽关系校验报告
- ✅ 同环比变化分析
- ✅ 行业对比排名
- ✅ 风险预警提示

---

## ⚙️ 配置说明

### 修改目标企业

编辑 `data/collect_financial_data.py` 中的 `COMPANIES` 列表：

```python
COMPANIES = [
    ('601127', '赛力斯'),
    ('002594', '比亚迪'),
    # 添加更多企业...
]
```

### 调整输出路径

修改脚本中的 `OUTPUT_DIR` 变量：

```python
OUTPUT_DIR = BASE_DIR / 'data'  # 默认输出到 data 目录
```

---

## 🔧 常见问题

### Q1: 数据采集失败怎么办？

**A:** 
- 检查网络连接是否正常
- 确认 AkShare 库已正确安装：`pip show akshare`
- 查看 `data/logs/` 目录下的日志文件排查错误
- 清除缓存后重试：删除 `.cache/` 目录

### Q2: 如何更新已有数据？

**A:** 
直接重新运行采集脚本，系统会自动覆盖旧数据：

```bash
python data/collect_financial_data.py
```

### Q3: 支持哪些财务期间？

**A:** 
默认采集最近 5 年的年度数据和最新季度数据，可在脚本中调整时间范围参数。

---

## 📝 开发计划

- [ ] 增加更多财务分析模型（如 EVA、MVA）
- [ ] 支持自定义行业对标分析
- [ ] 添加 Web 可视化界面
- [ ] 实现定时自动采集任务
- [ ] 导出 PDF/Word 格式报告

---

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！

1. Fork 本仓库
2. 创建特性分支：`git checkout -b feature/AmazingFeature`
3. 提交更改：`git commit -m 'Add some AmazingFeature'`
4. 推送到分支：`git push origin feature/AmazingFeature`
5. 提交 Pull Request

---

## 📄 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

---

## 👨‍💻 作者

**Yohoten** - [Gitee Profile](https://gitee.com/yohoten)

---

## 🙏 致谢

- [AkShare](https://github.com/akfamily/akshare) - 优秀的开源金融数据接口库
- [Tushare](https://tushare.pro/) - 免费开放的金融数据社区
- [pandas](https://pandas.pydata.org/) - 强大的数据分析工具

---

<div align="center">

**如果这个项目对你有帮助，请给个 ⭐ Star 支持一下！**

Made with ❤️ by Yohoten

</div>
