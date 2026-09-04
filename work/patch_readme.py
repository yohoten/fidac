"""Insert resource link block into README.md just before the first '---' divider."""
p = r'D:\CodingEmber\FIDAC\README.md'
with open(p, encoding='utf-8') as f:
    text = f.read()

needle = '> 核心研究问题：**代工协同模式（赛力斯）与自主研发模式（长安），谁的财务风险更高、更不稳定？**'
assert needle in text, 'anchor not found'

insert = '''

### 🔗 资源链接

- 完整代码仓库：[github.com/yohoten/fidac](https://github.com/yohoten/fidac)
- 研究 Notebook：[`基于K-Means聚类与多模型时序预测的重庆上市车企财务智能预警研究.ipynb`](./基于K-Means聚类与多模型时序预测的重庆上市车企财务智能预警研究.ipynb)
- 代码附录（关键代码逻辑梳理）：[`dosc/代码附录_关键代码逻辑.md`](./dosc/代码附录_关键代码逻辑.md)
- 研究论文 PDF：[`基于K-Means聚类与多模型时序预测的重庆上市车企财务智能预警研究.pdf`](./基于K-Means聚类与多模型时序预测的重庆上市车企财务智能预警研究.pdf)'''

# Insert right after the core-question line
new_text = text.replace(needle, needle + insert, 1)
with open(p, 'w', encoding='utf-8') as f:
    f.write(new_text)
print('done; new length:', len(new_text))
