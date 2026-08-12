# Streamlit 在线可视化看板部署指南

本文档说明如何将本项目的 Streamlit 看板（`streamlit_app.py`）部署到
**Streamlit Community Cloud**，并通过 `https://<应用名>.streamlit.app` 在线访问，
同时将代码托管到 **GitHub 或 Gitee** 仓库。

> ⚠️ 关键前提：Streamlit Community Cloud（免费版）**只支持 GitHub 仓库**。
> 若你的代码托管在 Gitee，有两种方案：
> - **方案 A（推荐）**：代码放 GitHub，部署到 Streamlit Cloud；
> - **方案 B**：代码放 Gitee，同时镜像到 GitHub（或直接将仓库设为 GitHub），再部署到 Streamlit Cloud。

---

## 一、看板功能一览

| 页面 | 功能 |
| ---- | ---- |
| 🏠 项目总览 | 研究背景、核心结论、8 家车企最新财务快照、Z-score / 沃尔评分速览 |
| 📊 财务指标探索 | 18 项指标时间趋势、公司对比、最新一期热力图 |
| 🔬 风险评估 | K-Means 聚类（PCA 降维 + 肘部法则）、孤立森林、Z-score、沃尔评分、杜邦分解 |
| 🔮 时序预测 | 6 种模型预测对比（置信区间）、样本内拟合质量、2026Q1 样本外回测 |
| 🚗 行业 NEV 分析 | 行业景气度、8 家车企销量、赛力斯/长安季度销量结构、赛力斯 vs 长安 |
| 🖼️ 预生成图表库 | 展示 Notebook 与行业分析输出的全部 PNG 图表 |

**技术栈**：Streamlit（`st.navigation` 多页面）+ Plotly（交互式图表）+ pandas / scikit-learn。
所有图表可缩放、悬停查看数值，支持下载为 PNG。

---

## 二、本地运行

```bash
# 1) 激活虚拟环境（Windows）
.venv\Scripts\activate

# 2) 安装依赖（已安装可跳过）
pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/

# 3) 启动看板
streamlit run streamlit_app.py
```

浏览器自动打开 `http://localhost:8501`，即可查看完整看板。

---

## 三、准备 GitHub/Gitee 仓库

### 3.1 创建 GitHub 仓库（Streamlit Cloud 必需）

1. 登录 [github.com](https://github.com)，点击右上角 **+ → New repository**；
2. 仓库名建议：`FIDAC-financial-dashboard`（或其它），选择 **Public**（免费版必须公开）；
3. **不要勾选** "Add a README / .gitignore"（避免与本地冲突）；
4. 创建完成后，复制仓库地址（HTTPS 或 SSH）。

### 3.2 初始化本地 Git 并推送

在项目根目录 `FIDAC/` 执行（Windows cmd / PowerShell）：

```bash
git init
git add .
git commit -m "feat: 重庆上市车企财务智能预警 Streamlit 看板"
git branch -M main
git remote add origin https://github.com/<你的用户名>/FIDAC-financial-dashboard.git
git push -u origin main
```

> 提示：仓库体积较大（含 `.venv/` 与数据文件）。强烈建议先创建 `.gitignore`
> 排除 `.venv/`、`__pycache__/`、`*.pyc`、`.streamlit/secrets.toml` 等，再提交。
> 数据文件 `data/*.xlsx` 与 `reports/*.png` **需要提交**（看板依赖它们）。

示例 `.gitignore`：

```gitignore
.venv/
__pycache__/
*.pyc
.streamlit/secrets.toml
.ipynb_checkpoints/
```

### 3.3 镜像到 Gitee（可选，国内访问更快）

1. 在 [gitee.com](https://gitee.com) 创建同名空仓库；
2. 在本地添加 Gitee 远程并推送：

```bash
git remote add gitee https://gitee.com/<你的用户名>/FIDAC-financial-dashboard.git
git push -u gitee main
```

之后每次提交可 `git push origin main`（GitHub）与 `git push gitee main`（Gitee）双推。

---

## 四、部署到 Streamlit Community Cloud

1. 打开 [share.streamlit.io](https://share.streamlit.io) 或 [streamlit.io/cloud](https://streamlit.io/cloud)，用 **GitHub 账号登录**；
2. 点击 **New app**；
3. 按提示选择：
   - **Repository**：`<你的用户名>/FIDAC-financial-dashboard`（GitHub）；
   - **Branch**：`main`；
   - **Main file path**：`streamlit_app.py`（默认已识别）；
   - **App URL**：可自定义子域名，例如 `fidac-financial-dashboard`；
4. 点击 **Advanced settings**，在 **Requirements file** 处填写 `requirements-app.txt`
   （精简依赖，构建更快更稳；如不填写则默认使用 `requirements.txt`）；
5. 点击 **Deploy**，等待 2~5 分钟构建完成。

### 部署成功后

- 看板在线地址：`https://<自定义子域名>.streamlit.app`；
- 在 Cloud 控制台可查看构建日志、重启应用、设置访问权限；
- 之后每次 `git push origin main`，Cloud 会自动重新部署（可与 GitHub 仓库的
  **Settings → Branches → 保护规则** 或 **Webhooks** 配合实现自动发布）。

---

## 五、常见问题

| 问题 | 解决方案 |
| ---- | ---- |
| 云端构建失败 / 超时 | 使用 `requirements-app.txt`（Advanced Settings），避免安装 akshare/matplotlib/prophet 等重依赖 |
| 看板显示"文件不存在" | 确认 `data/`、`reports/`、`lib/` 目录已提交到 GitHub（检查仓库文件列表） |
| 中文字体乱码（静态 PNG） | 图表库页面的 PNG 由本地 Notebook 生成时嵌入字体，无需改动；Plotly 动态图为前端渲染，无字体问题 |
| Prophet 未安装 | `lib/financial_metrics.py` 会自动回退到线性回归，看板不受影响 |
| 想私有部署（内网/服务器） | 可用 `streamlit run streamlit_app.py --server.port 8501` 自行启动，或使用 Docker 部署 |

---

## 六、文件清单（看板相关）

```
streamlit_app.py        # ★ 看板主入口（单文件多页面，内置「蓝黑暗黑」主题）
.streamlit/config.toml  # Streamlit 主题配置（深色蓝黑配色，需随仓库提交）
requirements-app.txt    # 云端精简依赖（Advanced Settings 指向它）
requirements.txt        # 完整依赖（含 streamlit/plotly）
data/                   # 财务 + 行业 + 销量结构数据（xlsx）
lib/financial_metrics.py# 指标计算 / 预测 / 评分函数库
reports/                # 预生成 PNG 图表
```

> 💡 **主题说明**：看板默认采用「蓝黑暗黑」深色主题，配色在
> `.streamlit/config.toml`（全局组件）+ `streamlit_app.py` 顶部 `THEME`/`THEME_CSS`（自定义 CSS）
> 与 `FIDAC_DARK`（Plotly 图表模板）中定义，可自行调整。

---

*部署文档 · 重庆上市车企财务智能预警研究 · 2026*
