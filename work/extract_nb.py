"""Extract all code cells from the FIDAC notebook and save them sequentially."""
import json
import os
import re

NB_PATH = r'D:\CodingEmber\FIDAC\基于K-Means聚类与多模型时序预测的重庆上市车企财务智能预警研究.ipynb'
OUT_DIR = r'D:\CodingEmber\FIDAC\dosc'
os.makedirs(OUT_DIR, exist_ok=True)

with open(NB_PATH, encoding='utf-8') as f:
    nb = json.load(f)

cells = nb['cells']
code_cells = [(i, c) for i, c in enumerate(cells) if c['cell_type'] == 'code']

print(f"Total cells: {len(cells)} | Code cells: {len(code_cells)}")

# Dump each code cell to a single file with marker headers
combined_path = os.path.join(OUT_DIR, '_nb_all_code.py')
with open(combined_path, 'w', encoding='utf-8') as out:
    out.write(f"# Auto-extracted from {os.path.basename(NB_PATH)}\n")
    out.write(f"# Total code cells: {len(code_cells)}\n\n")
    for idx, (orig_idx, cell) in enumerate(code_cells, 1):
        src = ''.join(cell['source'])
        out.write(f"\n# ============================================================\n")
        out.write(f"# Cell {idx} (notebook index {orig_idx})\n")
        out.write(f"# ============================================================\n")
        out.write(src)
        if not src.endswith('\n'):
            out.write('\n')

print(f"Saved to: {combined_path}")
print(f"Lines: {sum(sum(1 for _ in c['source']) for _, c in code_cells)}")
