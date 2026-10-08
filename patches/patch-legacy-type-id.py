#!/usr/bin/env python3
"""
patch-legacy-type-id.py — 修 ItemStackRequest action 的 legacy_type_id

问题：drop 一发，BDS 1.26.52 直接断开连接（无日志、无响应）。
根因：协议是 [varint variant][u8 legacy_id][payload] 两段式
      （见 gophertunnel writer.go 的 StackRequestAction）。
      prismarine 只填了 varint type_id，legacy_type_id 默认写 0：
        take 的原始 id 恰好是 0 → 碰巧正确
        drop=3 / destroy=4 / create=6 … 全错 → BDS 断连

改法：发送前按 action 原始 id 表补 legacy_type_id（覆盖 3 个发送点）。

用法：
  python3 patch-legacy-type-id.py [INVENTORY_ACTIONS_JS]
  默认 INVENTORY_ACTIONS_JS=./src/builtins/inventory-actions.js
"""
import sys

f = sys.argv[1] if len(sys.argv) > 1 else './src/builtins/inventory-actions.js'
t = open(f, encoding='utf-8').read()

if 'STACK_REQUEST_ACTION_IDS' in t:
    print('ALREADY PATCHED'); sys.exit(0)

anchor = "  function dropAction (count, source, randomly = false) {"
if anchor not in t:
    print('ANCHOR NOT FOUND'); sys.exit(1)

inject = '''  // ── ItemStackRequest action ids (order per protocol; place_in_container/take_out_container
  //    are never sent, but keep their ids so the table matches the wire enum) ──
  const STACK_REQUEST_ACTION_IDS = {
    take: 0, place: 1, swap: 2, drop: 3, destroy: 4, consume: 5, create: 6,
    place_in_container: 7, take_out_container: 8, lab_table_combine: 9,
    beacon_payment: 10, mine_block: 11, craft_recipe: 12, craft_recipe_auto: 13,
    craft_creative: 14, optional: 15, craft_grindstone_request: 16,
    craft_loom_request: 17, non_implemented: 18, results_deprecated: 19
  }
  // The wire format carries both a varint type id and a legacy u8 id; the u8 must be the
  // action's raw id, otherwise BDS (1.26.52) drops the connection on non-take actions.
  function normalizeRequestActions (request) {
    if (!request || !Array.isArray(request.actions)) return request
    for (const action of request.actions) {
      if (action && action.legacy_type_id === undefined && STACK_REQUEST_ACTION_IDS[action.type_id] !== undefined) {
        action.legacy_type_id = STACK_REQUEST_ACTION_IDS[action.type_id]
      }
    }
    return request
  }

'''
t = t.replace(anchor, inject + anchor, 1)

# 3 个发送点
t = t.replace(
    "      botState.setAuthInputFlag(packet, 'item_stack_request', true)\n      packet.item_stack_request = request",
    "      botState.setAuthInputFlag(packet, 'item_stack_request', true)\n      packet.item_stack_request = normalizeRequestActions(request)", 1)
t = t.replace(
    "  function sendItemStackRequests (requests) {\n    client.queue('item_stack_request', {\n      requests\n    })",
    "  function sendItemStackRequests (requests) {\n    for (const request of requests) normalizeRequestActions(request)\n    client.queue('item_stack_request', {\n      requests\n    })", 1)
t = t.replace(
    "  function sendStandaloneItemStackRequest (request) {\n    client.queue('item_stack_request', {\n      requests: [request]\n    })",
    "  function sendStandaloneItemStackRequest (request) {\n    normalizeRequestActions(request)\n    client.queue('item_stack_request', {\n      requests: [request]\n    })", 1)

open(f, 'w', encoding='utf-8').write(t)
print('PATCHED:', f)