// ============================================================================
// final2.js — 端到端验收：开箱 → 拿第2格 → 丢弃（含服务端权威验证）
//
// 需要：一个本地 BDS（1.26.52）+ 一个可发控制台命令的通道（tmux）。
//
// 用法（在 prismarine-bedrock 根目录执行）：
//   BDS_PORT=19132 \
//   TMUX_SOCK=/tmp/bds.sock TMUX_SESSION=bds BDS_LOG=/tmp/bds.log \
//   node final2.js
//
// 环境变量：
//   BDS_HOST     默认 127.0.0.1
//   BDS_PORT     默认 19132
//   TMUX_SOCK    tmux socket 路径（用于发控制台命令）
//   TMUX_SESSION tmux 会话名
//   TMUX_RUNAS   运行 BDS 的用户（默认空 = 当前用户）
//   BDS_LOG      BDS 日志路径（服务端权威探测用）
// ============================================================================
const BotState = require('./src/state');
const { execSync } = require('child_process');
const { Vec3 } = require('vec3');
const log = (...a) => console.log('[FIN]', ...a);
const sleep = ms => new Promise(r => setTimeout(r, ms));

const HOST = process.env.BDS_HOST || '127.0.0.1';
const PORT = Number(process.env.BDS_PORT || 19132);
const SOCK = process.env.TMUX_SOCK || '';
const SESS = process.env.TMUX_SESSION || '';
const RUNAS = process.env.TMUX_RUNAS ? `sudo -u ${process.env.TMUX_RUNAS} ` : '';
const BDS_LOG = process.env.BDS_LOG || '';

const con = c => {
  if (!SOCK || !SESS) { log('  (未配置 TMUX_SOCK/SESSION，跳过控制台命令)'); return; }
  try { execSync(`${RUNAS}tmux -S ${SOCK} send-keys -t ${SESS} ${JSON.stringify(c)} Enter`); } catch (e) {}
};
const tailLog = n => {
  if (!BDS_LOG) return '';
  try { return execSync(`tail -${n} ${BDS_LOG}`).toString(); } catch (e) { return ''; }
};
const items = bot => (bot.inventory?.slots || []).map((it, i) => it ? `[${i}]${it.name}x${it.count}` : null).filter(Boolean);
async function waitItem (bot, name, timeout = 12000) {
  const t0 = Date.now();
  while (Date.now() - t0 < timeout) {
    if ((bot.inventory?.slots || []).some(it => it && it.name === name)) return true;
    await sleep(400);
  }
  return false;
}

(async () => {
  const NAME = 'KIRA_FIN_' + Math.random().toString(36).slice(2, 4).toUpperCase();
  const bot = new BotState({
    host: HOST, port: PORT, username: NAME, offline: true, version: '1.26.52',
    transport: 'raknet', skipPing: true, worldDecodeEnabled: true, physicsEnabled: true, chunkRadius: 6,
  });
  let ok = 0, fail = 0;
  const check = (n, c, d = '') => { c ? ok++ : fail++; log(`${c ? 'PASS' : 'FAIL'} ${n}${d ? ' :: ' + d : ''}`); };

  bot.start();
  bot.client.on('item_stack_response', pp => { const r = pp?.responses?.[0]; log(`   <- resp status=${JSON.stringify(r?.status)}`); });
  await new Promise((res) => {
    const to = setTimeout(res, 30000);
    bot.client.once('spawn', () => { clearTimeout(to); res(); });
    bot.client.once('close', () => { clearTimeout(to); res(); });
  });
  for (let i = 0; i < 20; i++) { await sleep(1000); const y = bot.self?.position?.y; if (y > -64 && y < 400) break; }
  await sleep(2500);

  const p = bot.self.position;
  log(`bot=${NAME} pos=${p.x.toFixed(1)},${p.y.toFixed(1)},${p.z.toFixed(1)}`);
  const bx = Math.floor(p.x), by = Math.floor(p.y), bz = Math.floor(p.z) + 2;

  con(`clear "${NAME}"`);
  con('kill @e[type=item,r=300]');
  await sleep(1200);
  con(`setblock ${bx} ${by} ${bz} chest`);
  await sleep(800);
  con(`replaceitem block ${bx} ${by} ${bz} slot.container 0 diamond 3`);
  con(`replaceitem block ${bx} ${by} ${bz} slot.container 1 emerald 1`);
  await sleep(2000);

  // 1) 开箱
  log('--- 1) 开箱 ---');
  let chest = null;
  for (let t = 0; t < 3 && !chest; t++) { try { chest = await bot.openContainer(new Vec3(bx, by, bz)); } catch (e) { await sleep(2500); } }
  check('开箱', !!chest, chest ? `slots=${chest.containerSlotCount}` : 'fail');
  if (!chest) { log(`结果 ${ok}/${fail}`); process.exit(1); }
  check('读到钻石+翡翠', chest.getItem(0)?.name === 'diamond' && chest.getItem(1)?.name === 'emerald',
    `${chest.getItem(0)?.name}x${chest.getItem(0)?.count} ${chest.getItem(1)?.name}x${chest.getItem(1)?.count}`);

  // 2) 拿第 2 格
  log('--- 2) 拿第 2 格（翡翠）---');
  await chest.takeContainerSlot(1);
  await sleep(2500);
  chest.close();
  await sleep(1000);
  const afterTake = items(bot);
  check('拿到翡翠', afterTake.some(s => s.includes('emerald')), afterTake.join(' '));

  // 3) 丢弃
  log('--- 3) 丢掉翡翠 ---');
  const idx = (bot.inventory?.slots || []).findIndex(it => it && it.name === 'emerald');
  let dropStatus = null;
  bot.client.once('item_stack_response', pp => { dropStatus = pp?.responses?.[0]?.status; });
  await bot.dropInventorySlot(idx);
  await sleep(2500);
  check('丢弃被接受', dropStatus === 'ok', `status=${JSON.stringify(dropStatus)}`);
  check('连接存活', bot.client?.status === 4, 'status=' + bot.client?.status);

  // 4) 服务端权威
  log('--- 4) 服务端权威 ---');
  con(`clear "${NAME}" emerald 0`);
  await sleep(2000);
  const t = tailLog(6);
  check('服务端确认背包无翡翠', /no items to remove/i.test(t), t.trim().split('\n').slice(-1)[0].slice(0, 80));

  log(`结果: 通过 ${ok} / 失败 ${fail}`);
  try { bot.disconnect('done'); } catch (e) {}
  process.exit(fail === 0 ? 0 : 2);
})();
setTimeout(() => process.exit(3), 160000);