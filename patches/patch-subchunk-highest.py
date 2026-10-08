#!/usr/bin/env python3
"""
patch-subchunk-highest.py — 用 highest_subchunk_count 加载整列

问题：原代码只在 sub_chunk_count === -2 时用 highest_subchunk_count，
      导致 sub_chunk_count=0 时只请求 origin±1（薄薄一层）。涉及两处：
        A) levelChunkPollingSectionYs() 里的多行条件
        B) markChunkSectionsLoadedAbove() 的守卫条件

改法：
  A) packet.sub_chunk_count === -2 && Number.isInteger(...)  （多行）
       → packet.sub_chunk_count <= 0 && Number.isInteger(...) && ... >= 0
  B) if (packet.sub_chunk_count === -2) {
       → if (packet.sub_chunk_count <= 0) {

用法：
  python3 patch-subchunk-highest.py [WORLD_JS]
  默认 WORLD_JS=./src/builtins/world.js
"""
import sys, re

f = sys.argv[1] if len(sys.argv) > 1 else './src/builtins/world.js'
s = open(f, encoding='utf-8').read()

if 'packet.sub_chunk_count <= 0 && Number.isInteger' in s or 'packet.sub_chunk_count <= 0 &&\n' in s:
    print('ALREADY PATCHED'); sys.exit(0)

changed = []

# A) 多行条件
pat_a = re.compile(
    r'packet\.sub_chunk_count === -2 &&\s*\n\s*Number\.isInteger\(packet\.highest_subchunk_count\)'
)
if pat_a.search(s):
    s = pat_a.sub(
        'packet.sub_chunk_count <= 0 &&\n'
        '      Number.isInteger(packet.highest_subchunk_count) &&\n'
        '      packet.highest_subchunk_count >= 0',
        s, count=1)
    changed.append('A')

# A') 单行变体
pat_a2 = re.compile(
    r'packet\.sub_chunk_count === -2 && Number\.isInteger\(packet\.highest_subchunk_count\)'
)
if pat_a2.search(s):
    s = pat_a2.sub(
        'packet.sub_chunk_count <= 0 && Number.isInteger(packet.highest_subchunk_count) '
        '&& packet.highest_subchunk_count >= 0',
        s, count=1)
    changed.append("A2")

# B) 守卫条件
pat_b = re.compile(r'if \(packet\.sub_chunk_count === -2\) \{')
if pat_b.search(s):
    s = pat_b.sub('if (packet.sub_chunk_count <= 0) {', s, count=1)
    changed.append('B')

if not changed:
    print('PATTERN NOT FOUND'); sys.exit(1)

open(f, 'w', encoding='utf-8').write(s)
print(f'PATCHED: {f} (sections: {",".join(changed)})')