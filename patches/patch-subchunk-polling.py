#!/usr/bin/env python3
"""
patch-subchunk-polling.py — 修 BDS 1.26.52 的 level_chunk 分支判断

问题：level_chunk 的 sub_chunk_count=0，原代码把它当「全量非缓存」，解 0 个 section。
      （0 既不满足 >=0 的语义，又落不进 <0 的轮询分支 —— 边界 bug）

改法：
  if (sectionCount >= 0 ...)  →  if (sectionCount > 0 ...)
  else if (sectionCount < 0)  →  else if (sectionCount <= 0)

用法：
  python3 patch-subchunk-polling.py [WORLD_JS]
  默认 WORLD_JS=./src/builtins/world.js
"""
import sys

f = sys.argv[1] if len(sys.argv) > 1 else './src/builtins/world.js'
s = open(f, encoding='utf-8').read()

if 'sectionCount <= 0' in s:
    print('ALREADY PATCHED'); sys.exit(0)

# 找 level_chunk 里的 sectionCount 分支
import re
pat_ge = re.compile(r'if \(sectionCount >= 0 && !packet\.cache_enabled\)')
pat_lt = re.compile(r'\} else if \(sectionCount < 0\) \{')

if not pat_ge.search(s):
    print('PATTERN NOT FOUND: "sectionCount >= 0"'); sys.exit(1)
if not pat_lt.search(s):
    print('PATTERN NOT FOUND: "sectionCount < 0"'); sys.exit(1)

s = pat_ge.sub('if (sectionCount > 0 && !packet.cache_enabled)', s, count=1)
s = pat_lt.sub('} else if (sectionCount <= 0) {', s, count=1)

open(f, 'w', encoding='utf-8').write(s)
print('PATCHED:', f)