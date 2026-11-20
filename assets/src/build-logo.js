// Builds Newton's logo files. Text is converted to vector paths so the SVGs look identical everywhere.
const fs = require("fs"), path = require("path");
const sharp = require("/opt/npm-tools/node_modules/sharp");
const OUT = process.env.OUT || path.resolve(__dirname, "..");


// ---------- the mark (same design, polished) ----------
const defs = (p) => `
  <linearGradient id="${p}tile" x1="0.2" y1="0" x2="0.8" y2="1"><stop offset="0" stop-color="#1A212C"/><stop offset="0.55" stop-color="#0E131A"/><stop offset="1" stop-color="#070A0E"/></linearGradient>
  <linearGradient id="${p}rim" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#FFFFFF" stop-opacity="0.22"/><stop offset="0.35" stop-color="#FFFFFF" stop-opacity="0.05"/><stop offset="1" stop-color="#FFFFFF" stop-opacity="0.02"/></linearGradient>
  <radialGradient id="${p}halo" cx="0.66" cy="0.36" r="0.55"><stop offset="0" stop-color="#46F2A8" stop-opacity="0.20"/><stop offset="1" stop-color="#46F2A8" stop-opacity="0"/></radialGradient>
  <radialGradient id="${p}sheen" cx="0.25" cy="0.05" r="0.7"><stop offset="0" stop-color="#FFFFFF" stop-opacity="0.07"/><stop offset="1" stop-color="#FFFFFF" stop-opacity="0"/></radialGradient>
  <linearGradient id="${p}glow" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#D4FA6A"/><stop offset="0.55" stop-color="#7DF08A"/><stop offset="1" stop-color="#22DDA0"/></linearGradient>
  <radialGradient id="${p}orb" cx="0.36" cy="0.32" r="0.78"><stop offset="0" stop-color="#F2FFB8"/><stop offset="0.35" stop-color="#B9F566"/><stop offset="0.75" stop-color="#3FE39A"/><stop offset="1" stop-color="#16B97F"/></radialGradient>
  <linearGradient id="${p}leaf" x1="0" y1="1" x2="1" y2="0"><stop offset="0" stop-color="#7EE86F"/><stop offset="1" stop-color="#D8FB72"/></linearGradient>
  <linearGradient id="${p}trail" x1="0" y1="1" x2="0" y2="0"><stop offset="0" stop-color="#9BF57A" stop-opacity="0.7"/><stop offset="1" stop-color="#9BF57A" stop-opacity="0"/></linearGradient>
  <linearGradient id="${p}cursor" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#FFFFFF"/><stop offset="1" stop-color="#D5DCE6"/></linearGradient>
  <filter id="${p}blur" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="16"/></filter>
  <filter id="${p}soft" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="6"/></filter>
  <clipPath id="${p}clip"><rect x="16" y="16" width="480" height="480" rx="112"/></clipPath>`;

const mark = (p = "") => `
  <rect x="16" y="16" width="480" height="480" rx="112" fill="url(#${p}tile)"/>
  <g clip-path="url(#${p}clip)">
    <rect x="16" y="16" width="480" height="480" fill="url(#${p}halo)"/>
    <rect x="16" y="16" width="480" height="480" fill="url(#${p}sheen)"/>
    <!-- glows -->
    <circle cx="336" cy="200" r="58" fill="#3DF5A7" opacity="0.45" filter="url(#${p}blur)"/>
    <path d="M120 236 L222 318 L120 400" fill="none" stroke="#7DF08A" stroke-width="44" stroke-linecap="round" stroke-linejoin="round" opacity="0.35" filter="url(#${p}blur)"/>
  </g>
  <rect x="17.5" y="17.5" width="477" height="477" rx="110.5" fill="none" stroke="url(#${p}rim)" stroke-width="3"/>
  <!-- motion trail -->
  <rect x="300" y="64" width="10" height="56" rx="5" fill="url(#${p}trail)" opacity="0.55"/>
  <rect x="331" y="44" width="10" height="70" rx="5" fill="url(#${p}trail)" opacity="0.8"/>
  <rect x="362" y="70" width="10" height="44" rx="5" fill="url(#${p}trail)" opacity="0.45"/>
  <!-- the apple -->
  <ellipse cx="336" cy="252" rx="40" ry="6" fill="#000" opacity="0.35" filter="url(#${p}soft)"/>
  <circle cx="336" cy="196" r="54" fill="url(#${p}orb)"/>
  <ellipse cx="318" cy="174" rx="17" ry="11" transform="rotate(-35 318 174)" fill="#FFFFFF" opacity="0.55"/>
  <path d="M337 143 C 337 136, 338 130, 341 124" stroke="#2E7D57" stroke-width="5" stroke-linecap="round" fill="none"/>
  <path d="M340 140 C 346 116, 368 106, 390 110 C 386 133, 365 146, 340 140 Z" fill="url(#${p}leaf)"/>
  <path d="M344 136 C 356 126, 370 118, 384 114" stroke="#5CC56E" stroke-width="2.5" stroke-linecap="round" fill="none" opacity="0.8"/>
  <!-- the prompt -->
  <path d="M120 236 L222 318 L120 400" fill="none" stroke="url(#${p}glow)" stroke-width="44" stroke-linecap="round" stroke-linejoin="round"/>
  <rect x="262" y="372" width="126" height="40" rx="20" fill="url(#${p}cursor)"/>`;

const markSvg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" width="512" height="512"><defs>${defs("")}</defs>${mark("")}</svg>`;
fs.writeFileSync(path.join(OUT, "logo-mark.svg"), markSvg);

// ---------- wordmark ----------
const { execFileSync } = require("child_process");
const IN = "/usr/share/fonts/opentype/inter/";
const FONTS = {
  inter: IN + "Inter-Bold.otf", interMed: IN + "Inter-Medium.otf", interSemi: IN + "Inter-SemiBold.otf", interDisp: IN + "InterDisplay-Regular.otf",
  jb: "/tmp/fonts/JetBrainsMono-Medium.ttf", grotesk: "/tmp/fonts/SpaceGrotesk-Medium.ttf"
};
function textPath(font, text, x, y, size, ls = 0) {
  const job = [{ path: FONTS[font], text, x, y, size, ls }];
  return JSON.parse(execFileSync("python3", [path.join(__dirname, "text_paths.py"), JSON.stringify(job)]).toString())[0];
}
const tp = textPath;
const word = tp("inter", "newton", 330, 192, 150, -0.04);
const GRAD = "url(#tg)", GREY = "#9BA6B6", WHITE = "#F1F4F8";
const X0 = 338, Y0 = 252;
const P = (r, fill) => `<path d="${r.d}" fill="${fill}"/>`;

const taglines = {
  // 1 — a real keycap: the product's one gesture, drawn as the thing you press
  keycap() {
    const s = 40, ks = 29, kls = 0.05;
    const a = tp("interMed", "Think it.", 0, 0, s);
    const b0 = tp("interSemi", "Done.", 0, 0, s);
    const label = tp("jb", "tab", 0, 0, ks, kls);
    const lw = label.width - ks * kls;
    const kw = Math.round(lw + 54), kh = 56, ky = -43, lip = 6;
    const gap = 28, kx = a.width + gap;
    const lab = tp("jb", "tab", kx + (kw - lw) / 2, ky + kh / 2 + 9.5, ks, kls);
    const b = tp("interSemi", "Done.", kx + kw + gap, 0, s);
    return `<g transform="translate(${X0},${Y0})">
      <rect x="${kx - 2}" y="${ky}" width="${kw + 4}" height="${kh + lip}" rx="14" fill="#3FE39A" opacity="0.32" filter="url(#msoft)"/>
      <rect x="${kx}" y="${ky + lip}" width="${kw}" height="${kh}" rx="13" fill="#0B1118" stroke="#2EE6A0" stroke-opacity="0.45" stroke-width="1.4"/>
      <rect x="${kx}" y="${ky}" width="${kw}" height="${kh}" rx="13" fill="url(#key)" stroke="url(#keyedge)" stroke-width="1.8"/>
      <rect x="${kx + 8}" y="${ky + 2.5}" width="${kw - 16}" height="2" rx="1" fill="#FFFFFF" opacity="0.14"/>
      ${P(a, GREY)}${P(lab, GRAD)}${P(b, WHITE)}</g>`;
  },
  // 2 — lowercase geometric grotesk
  grotesk() {
    const s = 38; let x = 0, out = "";
    [["think it. ", GREY], ["tab it. ", GRAD], ["done.", WHITE]].forEach(([t, f]) => { const r = tp("grotesk", t, x, 0, s, 0.005); out += P(r, f); x += r.width; });
    return `<g transform="translate(${X0},${Y0})">${out}</g>`;
  },
  // 3 — small tracked caps, justified to the wordmark, green dot separators
  dots() {
    const s = 21, ls = 0.2, target = word.width - 8;
    const items = [["THINK IT", GREY], ["TAB IT", GRAD], ["DONE", GREY]].map(([t, f]) => ({ t, f, w: tp("interSemi", t, 0, 0, s, ls).width - ls * s }));
    const gap = (target - items.reduce((a, b) => a + b.w, 0)) / 2;
    let x = 0, out = "";
    items.forEach((o, i) => {
      out += P(tp("interSemi", o.t, x, 0, s, ls), o.f); x += o.w;
      if (i < 2) { out += `<circle cx="${x + gap / 2}" cy="-7.6" r="3.2" fill="url(#tg)"/>`; x += gap; }
    });
    return `<g transform="translate(${X0},${Y0})">${out}</g>`;
  },
  // 4 — the prompt itself: chevron + mono + blinking-cursor block
  terminal() {
    const s = 30; let x = 38, out = "";
    [["think it. ", GREY], ["tab it. ", GRAD], ["done.", WHITE]].forEach(([t, f]) => { const r = tp("jb", t, x, 0, s); out += P(r, f); x += r.width; });
    return `<g transform="translate(${X0},${Y0})">
      <path d="M3 -25 L18 -13.5 L3 -2" fill="none" stroke="url(#tg)" stroke-width="4.6" stroke-linecap="round" stroke-linejoin="round"/>
      ${out}<rect x="${x + 6}" y="-25" width="13" height="28" rx="2.5" fill="url(#tg)"/></g>`;
  },
  // 5 — quiet sentence case; each full stop is a green "pixel"
  periods() {
    const s = 38; let x = 0, out = "";
    [["Think it", GREY], ["Tab it", WHITE], ["Done", GREY]].forEach(([t, f]) => {
      const r = tp("interDisp", t, x, 0, s, 0.008); out += P(r, f); x += r.width - 0.008 * s;
      out += `<circle cx="${x + 5.2}" cy="-3.6" r="3.6" fill="url(#tg)"/>`; x += 22;
    });
    return `<g transform="translate(${X0},${Y0})">${out}</g>`;
  }
};

const W = 900, H = 320;
const lockupInner = (variant) => `<defs>${defs("m")}
    <radialGradient id="bg" cx="0.12" cy="0.3" r="0.9"><stop offset="0" stop-color="#101620"/><stop offset="1" stop-color="#090C11"/></radialGradient>
    <linearGradient id="tg" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#D4FA6A"/><stop offset="1" stop-color="#3FE39A"/></linearGradient>
    <linearGradient id="wm" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#FFFFFF"/><stop offset="1" stop-color="#DCE2EA"/></linearGradient>
    <linearGradient id="key" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#27313F"/><stop offset="1" stop-color="#151B25"/></linearGradient>
    <linearGradient id="keyedge" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#D4FA6A"/><stop offset="1" stop-color="#2EE6A0"/></linearGradient>
    <filter id="shadow" x="-20%" y="-20%" width="140%" height="150%"><feDropShadow dx="0" dy="14" stdDeviation="16" flood-color="#000" flood-opacity="0.55"/></filter>
  </defs>
  <rect width="${W}" height="${H}" fill="url(#bg)"/>
  <g transform="translate(40,40) scale(0.46875)" filter="url(#shadow)">${mark("m")}</g>
  <path d="${word.d}" fill="url(#wm)"/>
  ${taglines[variant]()}`;
const lockup = (variant) => `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${W} ${H}" width="${W}" height="${H}">${lockupInner(variant)}</svg>`;

(async () => {
  const V = process.env.VARIANT || "keycap";
  if (V === "sheet") {
    const names = Object.keys(taglines), cols = 2, pad = 24, lab = 34;
    const rows = Math.ceil(names.length / cols);
    const SW = cols * W + (cols + 1) * pad, SH = rows * (H + lab) + (rows + 1) * pad;
    const cells = names.map((n, i) => {
      const x = pad + (i % cols) * (W + pad), y = pad + Math.floor(i / cols) * (H + lab + pad);
      return `<svg x="${x}" y="${y}" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}">${lockupInner(n)}</svg>
        <text x="${x}" y="${y + H + 24}" font-family="DejaVu Sans, Arial" font-size="20" fill="#C7CEDA">${i + 1} · ${n}</text>`;
    }).join("");
    const sheet = `<svg xmlns="http://www.w3.org/2000/svg" width="${SW}" height="${SH}" viewBox="0 0 ${SW} ${SH}"><rect width="${SW}" height="${SH}" fill="#04060A"/>${cells}</svg>`;
    await sharp(Buffer.from(sheet), { density: 96 }).png().toFile(path.join(OUT, "sheet.png"));
    console.log("sheet");
    return;
  }
  const wordSvg = lockup(V);
  fs.writeFileSync(path.join(OUT, "logo-wordmark.svg"), wordSvg);
  fs.writeFileSync(path.join(OUT, "logo-wordmark-transparent.svg"), wordSvg.replace(`<rect width="${W}" height="${H}" fill="url(#bg)"/>`, ""));
  for (const sz of [32, 128, 256, 512, 1024]) await sharp(Buffer.from(markSvg), { density: 300 }).resize(sz, sz).png().toFile(path.join(OUT, `logo-${sz}.png`));
  await sharp(Buffer.from(wordSvg), { density: 220 }).resize(W * 2, H * 2).png().toFile(path.join(OUT, "logo-wordmark.png"));
  console.log("built", V);
})();
