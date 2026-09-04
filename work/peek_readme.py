import sys
p = r'D:\CodingEmber\FIDAC\README.md'
with open(p, encoding='utf-8') as f:
    s = f.read()
print(repr(s[:300]))
