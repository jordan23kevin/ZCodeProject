// 生成一张模拟"竞品主图"的测试 PNG：暖黄厨房感背景 + 棕色猫粮袋 + 白色标签 + 草地绿底边
const zlib = require('zlib');
const fs = require('fs');

const W = 640, H = 640;
const px = Buffer.alloc(W * H * 3);
function rect(x0, y0, w, h, r, g, b) {
  for (let y = y0; y < y0 + h; y++) for (let x = x0; x < x0 + w; x++) {
    if (x < 0 || y < 0 || x >= W || y >= H) continue;
    const i = (y * W + x) * 3; px[i] = r; px[i + 1] = g; px[i + 2] = b;
  }
}
rect(0, 0, W, H, 245, 226, 180);        // 暖黄背景
rect(0, 520, W, 120, 210, 190, 150);    // 木桌台面
rect(230, 180, 180, 320, 139, 90, 43);  // 棕色猫粮袋
rect(230, 180, 180, 40, 110, 68, 30);   // 袋口深色
rect(250, 280, 140, 120, 255, 255, 255);// 白色标签
rect(262, 292, 116, 20, 200, 60, 60);   // 标签红条(模拟卖点字)
rect(262, 322, 116, 12, 90, 90, 90);    // 标签灰条1
rect(262, 344, 80, 12, 90, 90, 90);     // 标签灰条2
rect(80, 380, 60, 90, 255, 200, 200);   // 左侧粉色玩具球
rect(500, 400, 70, 70, 120, 180, 120);  // 右侧绿色元素
// 猫粮颗粒
for (const [x, y] of [[180, 560], [220, 580], [420, 570], [460, 550], [380, 590]]) rect(x, y, 22, 16, 160, 110, 60);

// PNG 编码（无依赖）
function crc32(buf) {
  let c, table = crc32.t;
  if (!table) { table = crc32.t = []; for (let n = 0; n < 256; n++) { c = n; for (let k = 0; k < 8; k++) c = c & 1 ? 0xEDB88320 ^ (c >>> 1) : c >>> 1; table[n] = c >>> 0; } }
  c = 0xFFFFFFFF; for (const b of buf) c = table[(c ^ b) & 0xFF] ^ (c >>> 8);
  return (c ^ 0xFFFFFFFF) >>> 0;
}
function chunk(type, data) {
  const len = Buffer.alloc(4); len.writeUInt32BE(data.length);
  const body = Buffer.concat([Buffer.from(type), data]);
  const crc = Buffer.alloc(4); crc.writeUInt32BE(crc32(body));
  return Buffer.concat([len, body, crc]);
}
const raw = Buffer.alloc(H * (1 + W * 3));
for (let y = 0; y < H; y++) { raw[y * (1 + W * 3)] = 0; px.copy(raw, y * (1 + W * 3) + 1, y * W * 3, (y + 1) * W * 3); }
const ihdr = Buffer.alloc(13);
ihdr.writeUInt32BE(W, 0); ihdr.writeUInt32BE(H, 4); ihdr[8] = 8; ihdr[9] = 2;
const png = Buffer.concat([
  Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]),
  chunk('IHDR', ihdr), chunk('IDAT', zlib.deflateSync(raw)), chunk('IEND', Buffer.alloc(0))
]);
fs.writeFileSync(__dirname + '/test-ref.png', png);
console.log('test-ref.png written,', png.length, 'bytes');
