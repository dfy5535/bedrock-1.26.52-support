#!/usr/bin/env python3
"""
patch-subchunk-order.py — subchunk entry 位置按「请求顺序」映射

问题：BDS 1.26.52 返回的 subchunk entry 的 dx/dy/dz 全是 0（逐字节相同），
      无法用 offset 定位 section。若用 sectionY = originY + entryIndex，
      在「请求 offsets 非从 0 连续」时会算错（例：请求 [4,5,6]，offsets [-1,0,1]）。

改法（精确复刻已验证的工作版）：
  1. 在 subchunk handler 里插入 allEntryOffsetsZero / pendingReq / reqSectionYs / useRequestOrder
  2. for 循环改成带索引形态
  3. 循环体内**新增** `const entry = pkt.entries[entryIndex];`
  4. cx / sectionY / cz 三行改为条件表达式

用法：
  python3 patch-subchunk-order.py [WORLD_JS]
  默认 WORLD_JS=./src/builtins/world.js
"""
import sys

f = sys.argv[1] if len(sys.argv) > 1 else './src/builtins/world.js'
lines = open(f, encoding='utf-8').read().split('\n')

if any('useRequestOrder' in l for l in lines):
    print('ALREADY PATCHED'); sys.exit(0)

# 定位 subchunk handler 的 for 行
i_for = -1
for i, l in enumerate(lines):
    if 'for (let entryIndex = 0; entryIndex < pkt.entries.length; entryIndex++)' in l:
        i_for = i; break
if i_for < 0:
    for i, l in enumerate(lines):
        if l.strip() == 'for (const entry of pkt.entries) {':
            i_for = i; break
if i_for < 0:
    print('FOR NOT FOUND'); sys.exit(1)

# 替换 for 行（含前置计算）
lines[i_for] = (
    "    // BDS 1.26.52 answers a subchunk_request with entries whose dx/dy/dz are all zero,\n"
    "    // so position must come from the remembered request: response entry[i] corresponds\n"
    "    // to the i-th section we asked for. Falls back to entry.dy when offsets are present.\n"
    "    const allEntryOffsetsZero = pkt.entries.length > 0 && pkt.entries.every(e => e.dx === 0 && e.dy === 0 && e.dz === 0);\n"
    "    const pendingReq = botState.pendingSubchunkRequests?.get(chunkKey(originSectionX, originSectionZ));\n"
    "    const reqSectionYs = pendingReq ? [...pendingReq.sectionYs] : null;\n"
    "    const useRequestOrder = !!(allEntryOffsetsZero && reqSectionYs && reqSectionYs.length === pkt.entries.length);\n"
    "    for (let entryIndex = 0; entryIndex < pkt.entries.length; entryIndex++) {"
)

# 找 cx / sectionY / cz 行 + 确认/插入 entry 定义
i_cx = i_sy = i_cz = i_ent = -1
for i in range(i_for, min(i_for + 14, len(lines))):
    st = lines[i].strip()
    if st.startswith('const cx = originSectionX +'): i_cx = i
    if st.startswith('const sectionY ='): i_sy = i
    if st.startswith('const cz = originSectionZ +'): i_cz = i
    if st.startswith('const entry = pkt.entries['): i_ent = i

if min(i_cx, i_sy, i_cz) < 0:
    print(f'OFFSET LINES NOT FOUND cx={i_cx} sy={i_sy} cz={i_cz}'); sys.exit(1)

lines[i_cx] = "      const cx = originSectionX + (useRequestOrder ? 0 : entry.dx);"
lines[i_sy] = "      const sectionY = useRequestOrder ? reqSectionYs[entryIndex] : (originSectionY + entry.dy);"
lines[i_cz] = "      const cz = originSectionZ + (useRequestOrder ? 0 : entry.dz);"

# 若没有 entry 定义（原来是 for..of 形态），插在循环体第一行
if i_ent < 0:
    lines.insert(i_for + 1, "      const entry = pkt.entries[entryIndex];")

open(f, 'w', encoding='utf-8').write('\n'.join(lines))
print(f'PATCHED: {f} (for@{i_for + 1}, entry_def={i_ent >= 0})')