// Fundo da extensão: pergunta ao Claudinho (servidor local) se tem pedido e executa nas abas abertas.
// Quem pergunta é o fundo, e não as abas: aba em segundo plano tem os timers congelados pelo navegador.
importScripts("config.js");  // self.CLAUDINHO = {porta, token} (gerado pelo Claudinho na instalação)

const BASE = `http://127.0.0.1:${self.CLAUDINHO.porta}`;
const SITES = {ytmusic: "https://music.youtube.com/*", youtube: "https://www.youtube.com/*"};
const PERMITIDO = {ytmusic: "music.youtube.com", youtube: "www.youtube.com"};

async function abasDe(site) {
  return chrome.tabs.query({url: SITES[site]});
}

// a aba certa: a que está tocando; senão a que você usou por último
function escolher(abas) {
  return abas.find(a => a.audible) || [...abas].sort((a, b) => (b.lastAccessed || 0) - (a.lastAccessed || 0))[0];
}

async function executar(c) {
  const aba = escolher(await abasDe(c.site));
  if (!aba) return;
  if (c.acao === "abrir") {
    const url = new URL(c.url);
    if (url.hostname !== PERMITIDO[c.site]) return;  // só navega dentro do próprio site
    await chrome.tabs.update(aba.id, {url: c.url});
    if (c.focar) {
      await chrome.tabs.update(aba.id, {active: true});
      await chrome.windows.update(aba.windowId, {focused: true});
    }
  } else if (c.acao === "curtir" || c.acao === "descurtir") {
    chrome.tabs.sendMessage(aba.id, {acao: c.acao}).catch(() => {});
  }
}

let rodando = false;
async function ciclo() {
  if (rodando) return;
  rodando = true;
  try {
    const abas = {};
    for (const site in SITES) abas[site] = (await abasDe(site)).length;
    const r = await fetch(`${BASE}/ext/buscar`, {
      method: "POST",
      headers: {"Content-Type": "application/json", "X-Claudinho-Ext": self.CLAUDINHO.token},
      body: JSON.stringify({abas}),
    });
    if (r.ok) for (const c of (await r.json()).comandos || []) await executar(c);
  } catch (e) {
    // Claudinho fechado: tenta de novo no próximo ciclo
  } finally {
    rodando = false;
  }
}

setInterval(ciclo, 1000);
ciclo();
// o navegador pode encerrar o fundo quando está parado: o alarme acorda ele de novo
chrome.alarms.create("acordar", {periodInMinutes: 0.5});
chrome.alarms.onAlarm.addListener(ciclo);
chrome.runtime.onMessage.addListener(() => { ciclo(); });  // aba do YouTube abriu: acorda também
