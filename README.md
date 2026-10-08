# Bedrock 1.26.52 支持补丁集（prismarine-bedrock / bedrock-protocol）

> 让**无头 Bot**（`prismarine-bedrock` + `bedrock-protocol`）完整支持 **Minecraft Bedrock 1.26.52 / protocol 2193**。
>
> 状态：**连接 / 世界解码（整列）/ 实体 / 背包 / 配方 / 容器 / 物品操作** 全部可用，并经**服务端权威验证**。

---

## 为什么需要这个

上游（PrismarineJS）**没有 1.26.52**：

| 组件 | 上游状态 |
|---|---|
| `bedrock-protocol` | 最高 **1.26.51**（protocol **2193**） |
| `minecraft-data` | **无 1.26.52**（npm 3.117.0 与 GitHub master 都没有） |
| `prismarine-bedrock` | 只处理「全量 `count>=0`」或「轮询 `count<0`」两种区块 |

**关键事实：1.26.52 的协议号 = 2193 = 1.26.51。**
→ 协议层不用改，只需补**数据** + 修**解码逻辑**。

---

## 快速开始

```bash
# 1) 准备 prismarine-bedrock 源码 + 依赖
git clone https://github.com/PrismarineJS/prismarine-bedrock
cd prismarine-bedrock
npm install --ignore-scripts && npm rebuild raknet-native

# 2) 应用全部补丁（幂等，可重复执行）
bash /path/to/this-repo/patches/apply-all.sh

# 3) 起一个 Bedrock 1.26.52 服务端（BDS），然后跑验证
BDS_PORT=19132 node /path/to/this-repo/scripts/scan152.js
```

> `apply-all.sh` 会就地修改 `src/builtins/world.js`、`src/builtins/inventory-actions.js`、
> `src/utils/inventory.js` 和 `node_modules/minecraft-data`。

---

## 七个补丁

| # | 补丁 | 修的问题 |
|---|---|---|
| 1 | `patch-mcdata-12652.py` | `minecraft-data` 缺 1.26.52 数据（含数组型索引） |
| 2 | `patch-subchunk-polling.py` | `sub_chunk_count==0` 落进了错误分支 |
| 3 | `patch-subchunk-highest.py` | 只加载 origin±1（薄薄一层），两处守卫 |
| 4 | `patch-subchunk-order.py` | subchunk entry 的 offset 全是 0，无法定位 |
| 5 | `patch-dynamic-container-id.js` | `dynamic_container_id:0` 导致 `status 49` |
| 6 | `patch-legacy-type-id.py` | `drop` 一发 BDS 就断连（缺 `legacy_type_id`） |
| 7 | `patch-empty-slot-guard.py` | 空槽操作崩溃（`reading 'count'`） |

**全部参数化**：接受目标文件路径参数，不依赖任何本地路径；全部**幂等**。

---

## 五个核心发现

### 发现 1：协议号 2193（= 1.26.51）
```json
{ "protocol": 2193, "gameVersion": "1.26.52" }
```
→ 协议层零改动。

### 发现 2：raknet 仍可用
服务端自报 `NetherNet is the only supported transport type`，
但 `transport=raknet` 实测**仍可连接**（`SPAWN_OK`）。

### 发现 3：区块走独立 sub-chunk 包
```
level_chunk: sub_chunk_count=0, cache_enabled=false, highest_subchunk_count=10
```
→ 方块数据走 `subchunk` 包，需客户端主动请求。

### 发现 4：subchunk entry 的 offset 全是 (0,0,0)
15 个 entry **逐字节相同**，间距恒定。
→ 位置必须按「记住的请求顺序」映射，**不能**用 `originY + index`。

### 发现 5：action 的 `legacy_type_id`
```
gophertunnel writer.go:
  w.Varuint32(&variant)   // varint 变体索引
  w.Uint8(&id)            // u8 原始 id  ← prismarine 从不设置，默认 0
```
- `take` 原始 id = **0** → 碰巧正确
- `drop` 原始 id = **3** → 写 0 → **BDS 直接断开连接**

> ⚠️ **`take` 能过 ≠ 结构正确** —— 它的 id 恰好是 0，掩盖了字段缺失。

---

## 实测结果

### 世界解码
```
columns = 113 | sections = 15
non-air = 1440（Y 全高度剖面）
```

### 容器 + 物品操作（服务端权威验证）
```
PASS 开箱                 :: slots=27
PASS 读到 3 格             :: diamondx3 emeraldx1 gold_ingotx5
PASS 拿到翡翠              :: status="ok"
PASS 丢弃                  :: status="ok" + add_item_entity
PASS 服务端确认背包无翡翠   :: "no items to remove"   ← 权威
结果: 通过 12 / 失败 0（连跑 3 次稳定）
```

---

## 排错手册（真实踩过的坑）

| 现象 | 原因 | 补丁 |
|---|---|---|
| `sections len = 0` | `count==0` 落错分支 | 2 |
| `sections len = 1` | 只请求 origin±1 | 3 |
| 物理检查超时 `missing block data for 9 of 9 chunks` | `sectionY = originY + index` 算错 | 4 |
| `Timed out waiting for container_open` | 物理未就绪 → 位置没同步 | 3+4 |
| `status 49`（`FailedToValidateSrcSlot`） | `dynamic_container_id:0` 不该带 | 5 |
| **`drop` 一发就断连** | `legacy_type_id` 默认 0，但 drop 是 3 | 6 |
| `Cannot read properties of null (reading 'count')` | 空槽操作 | 7 |
| **「丢完还在」** | **不是 bug** —— 物品丢在脚下被自动拾回 | — |

> **判别技巧**：服务端**无日志、无响应**直接断开 = **包结构错**（不是语义拒绝）。

---

## 验证方法论

**三层证据法**（不要只信客户端）：

| 层 | 证据 |
|---|---|
| 协议响应 | `item_stack_response { status: "ok" }` |
| 世界实体 | `add_item_entity`（物品真的落地） |
| **服务端权威** | `/clear <item> 0` → `no items to remove` |

> ⚠️ **判定要用「请求被接受 + 副作用发生」，不要用「某个状态最终值」** ——
> 后者受时序影响（自动拾取是竞态）。

---

## 文件结构

```
patches/                 # 7 个补丁（全部参数化 + 幂等）
├── apply-all.sh
├── patch-mcdata-12652.py
├── patch-subchunk-polling.py
├── patch-subchunk-highest.py
├── patch-subchunk-order.py
├── patch-dynamic-container-id.js
├── patch-legacy-type-id.py
└── patch-empty-slot-guard.py

scripts/                 # 验证脚本（环境变量驱动，无硬编码路径）
├── scan152.js           # 世界解码
├── final2.js            # 开箱→拿→丢（含服务端权威）
└── proof.js             # 地面掉落物证明

data/1.26.52/            # 可直接使用的数据文件（10 个，~16 MB）
```

### 环境变量（脚本通用）

| 变量 | 默认 | 说明 |
|---|---|---|
| `BDS_HOST` | `127.0.0.1` | 服务端地址 |
| `BDS_PORT` | `19132` | 服务端端口 |
| `TMUX_SOCK` | — | tmux socket（发控制台命令） |
| `TMUX_SESSION` | — | tmux 会话名 |
| `TMUX_RUNAS` | — | 以哪个用户运行 tmux（可空） |
| `BDS_LOG` | — | BDS 日志路径（服务端权威探测） |
| `MCDATA_DIR` | `./node_modules/minecraft-data` | minecraft-data 路径（patch 1） |

---

## 许可

补丁代码为原创（MIT）。
`data/` 目录中的协议/方块数据源自 **Mojang 官方公开 schema**（`bedrock-samples` / `minecraft-data`），
遵循其原始许可。

---

*基于真机实测（Bedrock 1.26.52.3 + BDS + raknet）· 服务端权威验证*