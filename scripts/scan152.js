// ============================================================================
// scan152.js — 世界解码验证（Bedrock 1.26.52）
//
// 用法（在 prismarine-bedrock 根目录执行）：
//   BDS_HOST=127.0.0.1 BDS_PORT=19132 node scan152.js
// ============================================================================
const BotState = require('./src/state');
const { Vec3 } = require('vec3');
const log = (...a) => console.log('[S]', ...a);
const sleep = ms => new Promise(r => setTimeout(r, ms));

const HOST = process.env.BDS_HOST || '127.0.0.1';
const PORT = Number(process.env.BDS_PORT || 19132);
const VER = process.env.MC_VERSION || '1.26.52';
const NAME = process.env.BOT_NAME || 'KIRA_SCAN';

const bot = new BotState({
  host: HOST, port: PORT, username: NAME, offline: true,
  version: VER, transport: 'raknet', skipPing: true,
  worldDecodeEnabled: true, physicsEnabled: false, chunkRadius: 4,
});

(async () => {
  bot.start();
  await new Promise((res) => {
    const to = setTimeout(res, 25000);
    bot.client.once('spawn', () => { clearTimeout(to); res(); });
    bot.client.once('close', () => { clearTimeout(to); res(); });
  });
  await sleep(8000);

  const cols = bot.world?.columns ? Object.keys(bot.world.columns) : [];
  log('columns =', cols.length);
  const c0 = cols.length ? bot.world.columns[cols[0]] : null;
  log('sections len =', c0?.sections?.length || 0);

  // 连不上 / 解码失败 → 非零退出（供 CI 与自动化判定）
  if (cols.length === 0 || !c0 || (c0.sections?.length || 0) === 0) {
    log('FAIL: 世界解码为空（连接失败或补丁未生效）');
    process.exit(2);
  }

  // 扫 6 列，每列沿 Y 采样
  const found = {};
  let total = 0;
  for (const k of cols.slice(0, 6)) {
    const [cx, cz] = k.split(',').map(Number);
    for (let y = -64; y <= 200; y += 1) {
      try {
        const b = await bot.getBlock(new Vec3(cx * 16 + 8, y, cz * 16 + 8));
        if (b && b.name && b.name !== 'air' && b.name !== 'void_air') {
          total++; found[b.name] = (found[b.name] || 0) + 1;
        }
      } catch (e) {}
    }
  }
  log('non-air total =', total);
  log('block types:', Object.entries(found).sort((a, b) => b[1] - a[1]).slice(0, 12)
    .map(([n, c]) => `${n}:${c}`).join(' '));
  process.exit(0);
})();
bot.client.on('error', e => log('error:', e.message));
setTimeout(() => process.exit(0), 60000);