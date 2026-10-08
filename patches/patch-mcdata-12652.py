#!/usr/bin/env python3
"""
patch-mcdata-12652.py — 给 minecraft-data 添加 Bedrock 1.26.52 数据

问题：minecraft-data 没有 1.26.52（npm 3.117.0 与 GitHub master 都没有）
做法：
  1. 新建 data/bedrock/1.26.52/
     - protocol.json / proto.yml / types.yml  ← 复制自 1.26.51（协议号相同：2193）
     - blocks*.json / items.json              ← 复制自 1.26.30（最后一个有方块数据的版本）
  2. 改索引（注意：versions.json / protocolVersions.json 是【数组】）：
     - data/bedrock/common/versions.json          ← 数组（字符串列表）
     - data/bedrock/common/protocolVersions.json  ← 数组（对象列表，幂等）
     - data/dataPaths.json                        ← 对象
     - <pkg>/data.js                              ← 运行时真正加载的入口

用法：
  python3 patch-mcdata-12652.py [MCDATA_PKG_DIR]
  默认 MCDATA_PKG_DIR=./node_modules/minecraft-data
"""
import json, os, shutil, sys, re

MD = sys.argv[1] if len(sys.argv) > 1 else './node_modules/minecraft-data'
DATA = os.path.join(MD, 'minecraft-data', 'data')
BEDROCK = os.path.join(DATA, 'bedrock')
COMMON = os.path.join(BEDROCK, 'common')
DATAJS = os.path.join(MD, 'data.js')

if not os.path.isdir(BEDROCK):
    print('ERROR: 找不到', BEDROCK, '（MCDATA_PKG_DIR 是否正确？）'); sys.exit(1)

VER = '1.26.52'
PROTO = 2193

# ── 1) 数据目录 ──
new_dir = os.path.join(BEDROCK, VER)
if os.path.isdir(new_dir):
    print('ALREADY EXISTS:', new_dir)
else:
    os.makedirs(new_dir)
    src_dir = os.path.join(BEDROCK, '1.26.51')
    for f in os.listdir(src_dir):
        p = os.path.join(src_dir, f)
        if os.path.isfile(p):
            shutil.copy2(p, os.path.join(new_dir, f))
    for f in ['blocks.json', 'blocksB2J.json', 'blocksJ2B.json',
              'blockStates.json', 'blockCollisionShapes.json', 'items.json']:
        p = os.path.join(BEDROCK, '1.26.30', f)
        if os.path.isfile(p):
            shutil.copy2(p, os.path.join(new_dir, f))
    vj = os.path.join(new_dir, 'version.json')
    if os.path.isfile(vj):
        v = json.load(open(vj, encoding='utf-8'))
        v['version'] = PROTO
        v['minecraftVersion'] = VER
        json.dump(v, open(vj, 'w', encoding='utf-8'), indent=2)
    print('CREATED:', new_dir)

# ── 2) versions.json（数组：字符串列表）──
vp = os.path.join(COMMON, 'versions.json')
if os.path.isfile(vp):
    d = json.load(open(vp, encoding='utf-8'))
    if isinstance(d, list):
        if VER not in d:
            d.append(VER)
            json.dump(d, open(vp, 'w', encoding='utf-8'), indent=2)
            print('  PATCHED (versions):', vp)
        else:
            print('  ALREADY PATCHED (versions)')
    else:
        print('  WARN (versions 不是数组):', type(d).__name__)
else:
    print('  SKIP (missing versions.json)')

# ── 3) protocolVersions.json（数组：对象列表）──
pp = os.path.join(COMMON, 'protocolVersions.json')
if os.path.isfile(pp):
    d = json.load(open(pp, encoding='utf-8'))
    if isinstance(d, list):
        if not any(isinstance(x, dict) and x.get('minecraftVersion') == VER for x in d):
            d.insert(0, {'version': PROTO, 'minecraftVersion': VER,
                         'majorVersion': '1.26', 'releaseType': 'release'})
            json.dump(d, open(pp, 'w', encoding='utf-8'), indent=2)
            print('  PATCHED (protocolVersions):', pp)
        else:
            print('  ALREADY PATCHED (protocolVersions)')
    else:
        print('  WARN (protocolVersions 不是数组):', type(d).__name__)
else:
    print('  SKIP (missing protocolVersions.json)')

# ── 4) dataPaths.json（对象）──
dp = os.path.join(DATA, 'dataPaths.json')
if os.path.isfile(dp):
    d = json.load(open(dp, encoding='utf-8'))
    b = d.setdefault('bedrock', {})
    if VER not in b:
        b[VER] = dict(b.get('1.26.51', {}))
        json.dump(d, open(dp, 'w', encoding='utf-8'), indent=2)
        print('  PATCHED (dataPaths):', dp)
    else:
        print('  ALREADY PATCHED (dataPaths)')
else:
    print('  SKIP (missing dataPaths.json)')

# ── 5) data.js（运行时入口）──
if os.path.isfile(DATAJS):
    s = open(DATAJS, encoding='utf-8').read()
    if "'%s'" % VER in s:
        print('  ALREADY PATCHED (data.js)')
    else:
        m = re.search(r"(\s*)('1\.26\.51':\s*\{.*?\n\s*\},)", s, re.S) or \
            re.search(r"(\s*)('1\.26\.51':\s*\{.*?\n\s*\})", s, re.S)
        if m:
            indent, block = m.group(1), m.group(2)
            s = s.replace(block, block + ',\n' + indent + block.replace("'1.26.51'", "'%s'" % VER), 1)
            open(DATAJS, 'w', encoding='utf-8').write(s)
            print('  PATCHED (data.js):', DATAJS)
        else:
            print('  WARN: data.js 里找不到 1.26.51 块')
else:
    print('  SKIP (missing data.js)')

print('DONE')