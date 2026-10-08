#!/usr/bin/env python3
"""
patch-empty-slot-guard.py — 物品操作的空槽保护

问题：对空槽做 drop/split 会抛
      TypeError: Cannot read properties of null (reading 'count')，直接崩溃。

改法：加 assertItemPresent()，空槽时 fail cleanly。

用法：
  python3 patch-empty-slot-guard.py [INVENTORY_ACTIONS_JS]
  默认 INVENTORY_ACTIONS_JS=./src/builtins/inventory-actions.js
"""
import sys

f = sys.argv[1] if len(sys.argv) > 1 else './src/builtins/inventory-actions.js'
t = open(f, encoding='utf-8').read()

if 'KIRA_GUARD_EMPTY_SLOT' in t:
    print('ALREADY PATCHED'); sys.exit(0)

anchor = "  function dropInventorySlot (slot, randomly = false) {"
if anchor not in t:
    print('ANCHOR NOT FOUND'); sys.exit(1)

guard = '''  // KIRA_GUARD_EMPTY_SLOT — operating on an empty slot previously threw
  // "Cannot read properties of null (reading 'count')"; fail cleanly instead.
  function assertItemPresent (slot, op) {
    const item = itemAt(slot)
    if (!item) throw new Error(`${op}: slot ${slot} is empty`)
    return item
  }
'''
t = t.replace(anchor, guard + anchor, 1)

t = t.replace(
    "  function dropInventorySlot (slot, randomly = false) {\n    const request = makeRequest([\n      dropAction(itemAt(slot).count, playerStackRequestSlotInfo(slot, itemAt(slot)), randomly)",
    "  function dropInventorySlot (slot, randomly = false) {\n    const _item = assertItemPresent(slot, 'dropInventorySlot')\n    const request = makeRequest([\n      dropAction(_item.count, playerStackRequestSlotInfo(slot, _item), randomly)", 1)
t = t.replace(
    "  function dropOneInventoryItem (slot, randomly = false) {\n    const request = makeRequest([\n      dropAction(1, playerStackRequestSlotInfo(slot, itemAt(slot)), randomly)",
    "  function dropOneInventoryItem (slot, randomly = false) {\n    const _item = assertItemPresent(slot, 'dropOneInventoryItem')\n    const request = makeRequest([\n      dropAction(1, playerStackRequestSlotInfo(slot, _item), randomly)", 1)
t = t.replace(
    "  function splitInventorySlot (fromSlot, toSlot) {\n    const count = Math.ceil(itemAt(fromSlot).count / 2)",
    "  function splitInventorySlot (fromSlot, toSlot) {\n    const _item = assertItemPresent(fromSlot, 'splitInventorySlot')\n    const count = Math.ceil(_item.count / 2)", 1)

open(f, 'w', encoding='utf-8').write(t)
print('PATCHED:', f)