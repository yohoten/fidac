import json, sys
nb = json.load(open(r'D:\CodingEmber\FIDAC\基于K-Means聚类与多模型时序预测的重庆上市车企财务智能预警研究.ipynb',encoding='utf-8'))
md_cells = [c for c in nb['cells'] if c['cell_type']=='markdown']
print('md cells:', len(md_cells))
for i, c in enumerate(md_cells):
    src = ''.join(c['source']).strip()
    if src:
        first = src.split('\n')[0][:120]
        print(f'-- md[{i}] -- {first}')
