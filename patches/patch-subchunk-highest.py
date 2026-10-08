#!/usr/bin/env python3
"""
patch-subchunk-highest.py — 用 highest_subchunk_count 加载整列

问题：levelChunkPollingSectionYs() 只在 sub_chunk_count === -2 时用
      highest_subchunk_count，导致 sub_chunk_count=0 时只请求 origin±1（薄薄一层）。

改法（只改条件，不动调用方）：
  packet.sub_chunk_count === -2 &&
      → packet.sub_chunk_count <= 0 &&
          ... && packet.highest_subchunk_count >= 0

⚠️ 注意：**不要**改 `if (packet.sub_chunk_count === -2) { markChunkSectionsLoadedAbove(...) }`
   那处的守卫 —— 工作版保持 `=== -2`（只对 -2 标记"以上全加载"）。

用法：
  python3 patch-subchunk-highest.py [WORLD_JS]
  默认 WORLD_JS=./src/builtins/world.js
"""
import sys, re

f = sys.argv[1] if len(sys.argv) > 1 else './src/builtins/world.js'
s = open(f, encoding='utf-8').read()

if re.search(r'packet\.sub_chunk_count <= 0 &&\s*\n\s*Number\.isInteger\(packet\.highest_subchunk_count\)', s) \
   or 'packet.sub_chunk_count <= 0 && Number.isInteger(packet.highest_subchunk_count)' in s:
    print('ALREADY PATCHED'); sys.exit(0)

# 多行条件（原始形态）
pat = re.compile(
    r'packet\.sub_chunk_count === -2 &&\s*\n\s*Number\.isInteger\(packet\.highest_subchunk_count\)'
)
if pat.search(s):
    s = pat.sub(
        'packet.sub_chunk_count <= 0 &&\n'
        '      Number.isInteger(packet.highest_subchunk_count) &&\n'
        '      packet.highest_subchunk_count >= 0',
        s, count=1)
    open(f, 'w', encoding='utf-8').write(s)
    print(f'PATCHED: {f} (multi-line condition)')
    sys.exit(0)

# 单行变体
pat2 = re.compile(
    r'packet\.sub_chunk_count === -2 && Number\.isInteger\(packet\.highest_subchunk_count\)'
)
if pat2.search(s):
    s = pat2.sub(
        'packet.sub_chunk_count <= 0 && Number.isInteger(packet.highest_subchunk_count) '
        '&& packet.highest_subchunk_count >= 0',
        s, count=1)
    open(f, 'w', encoding='utf-8').write(s)
    print(f'PATCHED: {f} (single-line condition)')
    sys.exit(0)

print('PATTERN NOT FOUND'); sys.exit(1)