// ============================================================================
// proof.js — 证明「drop 真的把物品丢到地上」（查世界实体 + 服务端权威）
//
// 用法（在 prismarine-bedrock 根目录执行）：
//   BDS_PORT=19132 TMUX_SOCK=/tmp/bds.sock TMUX_SESSION=bds BDS_LOG=/tmp/bds.log node proof.js
// ============================================================================
const BotState = require('./src/state');
const { execSync } = require('child_process');
const log = (...a) => console.log('[PROOF]', ...a);
const sleep = ms => new Promise(r => setTimeout(r, ms));

const HOST = process.env.BDS_HOST || '127.0.0.1';
const PORT = Number(process.env.BDS_PORT || 19132);
const SOCK = process.env.TMUX_SOCK || '';
const SESS = process.env.TMUX_SESSION || '';
const RUNAS = process.env.TMUX_RUNAS ? `sudo -u ${process.env.TMUX_RUNAS} ` : '';
const BDS_LOG = process.env.BDS_LOG || '';

const con = c => {
  if (!SOCK || !SESS) return;
  try { execSync(`${RUNAS}tmux -S ${SOCK} send-keys -t ${SESS} ${JSON.stringify(c)} Enter`); } catch (e) {}
};
const tailLog = n => {
  if (!BDS_LOG) return '';
  try { return execSync(`tail -${n} ${BDS_LOG}`).toString().trim().split('\n').slice(-1)[0]; } catch (e) { return ''; }
};
const items = bot => (bot.inventory?.slots || []).map((it, i) => it ? `[${i}]${it.name}x${it.count}` : null).filter(Boolean);
async function waitItem (bot, name, timeout = 15000) {
  const t0 = Date.now();
  while (Date.now() - t0 < timeout) {
    if ((bot.inventory?.slots || []).some(it => it && it.name === name)) return true;
    await sleep(500);
  }
  return false;
}

(async () => {
  const NAME = 'KIRA_P_' + Math.random().toString(36).slice(2, 5).toUpperCase();
  const bot = new BotState({
    host: HOST, port: PORT, username: NAME, offline: true, version: '1.26.52',
    transport: 'raknet', skipPing: true, worldDecodeEnabled: true, physicsEnabled: true, chunkRadius: 4,
  });

  bot.start();
  bot.client.on('item_stack_response', pp => { const r = pp?.responses?.[0]; log(`   <- resp status=${JSON.stringify(r?.status)}`); });
  bot.client.on('add_item_entity', p => log(`   ★ add_item_entity（地面出现掉落物）id=${p.runtime_entity_id}`));
  bot.client.on('itemPickup', e => log(`   ★ itemPickup（被捡起）entity=${e.itemEntityId} isSelf=${e.isSelf}`));

  await new Promise((res) => {
    const to = setTimeout(res, 30000);
    bot.client.once('spawn', () => { clearTimeout(to); res(); });
    bot.client.once('close', () => { clearTimeout(to); res(); });
  });
  for (let i = 0; i < 20; i++) { await sleep(1000); const y = bot.self?.position?.y; if (y > -64 && y < 400) break; }
  await sleep(2500);

  const p0 = bot.self.position;
  log(`bot=${NAME} pos=${p0.x.toFixed(1)},${p0.y.toFixed(1)},${p0.z.toFixed(1)}`);

  con(`clear "${NAME}"`);
  await sleep(1000);
  con(`give "${NAME}" emerald 1`);
  const got = await waitItem(bot, 'emerald');
  log('本地(give后):', items(bot).join(' ') || '(空)', got ? 'OK' : 'FAIL');
  if (!got) process.exit(1);

  // 丢，然后立刻传送 20 格，让物品留在原地
  log('--- 丢翡翠 + 立刻传送（物品留原地）---');
  const idx = (bot.inventory?.slots || []).findIndex(it => it && it.name === 'emerald');
  bot.dropInventorySlot(idx);
  await sleep(200);
  con(`tp "${NAME}" ${(p0.x + 20).toFixed(1)} ${p0.y.toFixed(1)} ${p0.z.toFixed(1)}`);
  await sleep(3000);
  log('  传送后本地:', items(bot).join(' ') || '(空)');

  log('--- 原位置附近的掉落物 ---');
  con(`execute positioned ${Math.floor(p0.x)} ${Math.floor(p0.y)} ${Math.floor(p0.z)} run testfor @e[type=item,r=10]`);
  await sleep(1500);
  log('  ', tailLog(3));

  log('--- 服务端权威 ---');
  con(`clear "${NAME}" emerald 0`);
  await sleep(1500);
  log('  clear emerald:', tailLog(1));

  try { bot.disconnect('done'); } catch (e) {}
  process.exit(0);
})();
setTimeout(() => process.exit(3), 120000);