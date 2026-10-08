#!/usr/bin/env bash
# ============================================================================
# apply-all.sh — 一键应用全部 7 个补丁
#
# 用法：
#   # 在 prismarine-bedrock 仓库根目录（含 src/ 和 node_modules/）执行：
#   bash apply-all.sh
#
#   # 或指定路径：
#   bash apply-all.sh /path/to/prismarine-bedrock
# ============================================================================
set -uo pipefail

ROOT="${1:-.}"
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ ! -d "$ROOT/src" ]; then
  echo "ERROR: $ROOT 不是 prismarine-bedrock 根目录（缺 src/）" >&2
  exit 1
fi

cd "$ROOT" || exit 1
echo "==> 目标: $(pwd)"
echo

echo "[1/7] patch-mcdata-12652      (minecraft-data 数据层)"
python3 "$DIR/patch-mcdata-12652.py" "${MCDATA_DIR:-./node_modules/minecraft-data}"

echo "[2/7] patch-subchunk-polling  (count==0 走轮询)"
python3 "$DIR/patch-subchunk-polling.py" ./src/builtins/world.js

echo "[3/7] patch-subchunk-highest  (用 highest 加载整列)"
python3 "$DIR/patch-subchunk-highest.py" ./src/builtins/world.js

echo "[4/7] patch-subchunk-order    (entry 位置按请求顺序)"
python3 "$DIR/patch-subchunk-order.py" ./src/builtins/world.js

echo "[5/7] patch-dynamic-container-id (容器可选字段)"
node "$DIR/patch-dynamic-container-id.js" ./src/utils/inventory.js

echo "[6/7] patch-legacy-type-id    (action legacy_type_id)"
python3 "$DIR/patch-legacy-type-id.py" ./src/builtins/inventory-actions.js

echo "[7/7] patch-empty-slot-guard  (空槽保护)"
python3 "$DIR/patch-empty-slot-guard.py" ./src/builtins/inventory-actions.js

echo
echo "==> 语法自检"
node --check ./src/builtins/world.js && echo "  OK world.js"
node --check ./src/builtins/inventory-actions.js && echo "  OK inventory-actions.js"
node --check ./src/utils/inventory.js && echo "  OK utils/inventory.js"

echo
echo "DONE. 全部补丁已应用（幂等，可重复执行）。"