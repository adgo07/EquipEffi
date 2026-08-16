# -*- coding: utf-8 -*-
"""M1 POC：zip补丁写回引擎验证——改单元格值，图片/格式必须100%保留"""
import shutil, zipfile, hashlib, sys
sys.path.insert(0, r'G:\Python Project\EquipEffi')
from core.writer import patch_cells
import openpyxl

SRC = r'G:\标准  规范\02_能耗限额_终端产品\用能设备\用能设备能效分析表V1.11.xlsx'
TMP = r'G:\Python Project\EquipEffi\tests\samples\V1.11_poc.xlsx'
OUT = r'G:\Python Project\EquipEffi\tests\samples\V1.11_poc_out.xlsx'

print('== 1. 复制原文件（39MB）==')
shutil.copy2(SRC, TMP)

def media_hash(path):
    with zipfile.ZipFile(path) as z:
        names = [n for n in z.namelist() if n.startswith('xl/media/')]
        return {n: hashlib.md5(z.read(n)).hexdigest() for n in names}

h_before = media_hash(TMP)
print(f'原文件图片数: {len(h_before)}')

print('\n== 2. 执行zip补丁 ==')
result = patch_cells(TMP, OUT, {
    '变压器': {'T4': '3级', 'V4': 'POC测试：zip补丁写回'},
    '低压电动机': {'P3': '2级'},
})
print('patch结果:', result)

print('\n== 3. 验证图片100%保留 ==')
h_after = media_hash(OUT)
print('图片数量一致:', len(h_before) == len(h_after), f'({len(h_after)})')
same = h_before == h_after
print('每个图片字节hash一致:', same)
if not same:
    for k in h_before:
        if h_before[k] != h_after.get(k):
            print('  差异:', k)

print('\n== 4. openpyxl读回修改的值 ==')
wb = openpyxl.load_workbook(OUT, data_only=True)
ws = wb['变压器']
print(f'变压器 T4(能效等级) = {ws["T4"].value!r}')
print(f'变压器 V4(备注新增) = {ws["V4"].value!r}')
ws2 = wb['低压电动机']
print(f'低压电动机 P3(能效等级) = {ws2["P3"].value!r}')
wb.close()

print('\n== 5. 照片列DISPIMG公式必须原样保留 ==')
wb2 = openpyxl.load_workbook(OUT, data_only=False)
ws3 = wb2['变压器']
print(f'变压器 U4(照片) = {str(ws3["U4"].value)[:70]}')
ws4 = wb2['低压电动机']
print(f'低压电动机 Q3(照片) = {str(ws4["Q3"].value)[:70]}')
wb2.close()

print('\n== 6. zip完整性检查 ==')
bad = zipfile.ZipFile(OUT).testzip()
print('zip损坏条目:', bad if bad else '无，完整')
print('\n✅ POC全部通过' if same and bad is None else '\n❌ POC有问题')
