#!/usr/bin/env node
/**
 * patch-dynamic-container-id.js — 只在非零时带 dynamic_container_id
 *
 * 问题：fullContainerName 总是带 dynamic_container_id:0，
 *      但 proto 里该字段是【可选】(FullContainerName.dynamic_container_id?: u32)，
 *      非动态容器（背包/热栏/箱子）带上它会导致 BDS 返回 status 49
 *      (FailedToValidateSrcSlot)，item_stack_request 被拒。
 *
 * 用法：
 *   node patch-dynamic-container-id.js [INVENTORY_JS]
 *   默认 INVENTORY_JS=./src/utils/inventory.js
 */
const fs = require('fs');

const f = process.argv[2] || './src/utils/inventory.js';

if (!fs.existsSync(f)) { console.log('SKIP (missing):', f); process.exit(1); }

let s = fs.readFileSync(f, 'utf8');

if (s.includes('if (dynamicContainerId) name.dynamic_container_id')) {
  console.log('ALREADY PATCHED:', f); process.exit(0);
}

const before = `function fullContainerName (containerId = 'inventory', dynamicContainerId = 0) {
  return {
    container_id: containerId,
    dynamic_container_id: dynamicContainerId
  }
}`;

const after = `function fullContainerName (containerId = 'inventory', dynamicContainerId = 0) {
  const name = { container_id: containerId }
  if (dynamicContainerId) name.dynamic_container_id = dynamicContainerId
  return name
}`;

if (s.includes(before)) {
  fs.writeFileSync(f, s.replace(before, after));
  console.log('PATCHED:', f);
} else {
  console.log('PATTERN NOT FOUND:', f);
  process.exit(1);
}