// Fundo da extensão: pergunta ao Claudinho (servidor local) se tem pedido e executa no navegador.
// Quem pergunta é o fundo, e não as abas: aba em segundo plano tem os timers congelados pelo navegador.
//   YouTube Music: toca no player da barra lateral do Opera, se ele estiver aberto; senão troca a música na aba que
//                  já está aberta, sem roubar o foco (sem aba: abre uma em segundo plano)
//   YouTube: sempre numa aba nova, trazida pra frente
importScripts("config.js");  // self.CLAUDINHO = {porta, token} (gerado pelo Claudinho na instalação)

const BASE = `http://127.0.0.1:${self.CLAUDINHO.porta}`;
const SITES = {ytmusic: "https://music.youtube.com/*", youtube: "https://www.youtube.com/*"};
const PERMITIDO = {ytmusic: "music.youtube.com", youtube: "www.youtube.com"};
const VERSAO = chrome.runtime.getManifest().version;

// player do YouTube Music fora de aba (barra lateral do Opera): ele mesmo pergunta se tem pedido
const player = {visto: 0, fila: []};
const playerVivo = () => Date.now() - player.visto < 5000;

async function abasDe(site) {
  return chrome.tabs.query({url: SITES[site]});
}

// a aba certa: a que está tocando; senão a que você usou por último
function escolher(abas) {
  return abas.find(a => a.audible) || [...abas].sort((a, b) => (b.lastAccessed || 0) - (a.lastAccessed || 0))[0];
}

async function trazerPraFrente(aba) {
  await chrome.tabs.update(aba.id, {active: true});
  await chrome.windows.update(aba.windowId, {focused: true});
}

async function executar(c) {
  if (c.site === "ytmusic" && playerVivo() && !c.nova) {
    player.fila.push(c);  // o player do Opera busca no próximo "oi"
    return;
  }
  if (c.acao === "abrir") {
    if (new URL(c.url).hostname !== PERMITIDO[c.site]) return;  // só navega dentro do próprio site
    const aba = c.nova ? null : escolher(await abasDe(c.site));
    if (aba) {
      await chrome.tabs.update(aba.id, {url: c.url});
      if (c.focar) await trazerPraFrente(aba);
    } else {
      const nova = await chrome.tabs.create({url: c.url, active: !!c.focar});
      if (c.focar) await trazerPraFrente(nova);
    }
  } else if (c.acao === "curtir" || c.acao === "descurtir") {
    const aba = escolher(await abasDe(c.site));
    if (aba) chrome.tabs.sendMessage(aba.id, {acao: c.acao}).catch(() => {});
  }
}

let rodando = false;
async function ciclo() {
  if (rodando) return;
  rodando = true;
  try {
    const abas = {};
    for (const site in SITES) abas[site] = (await abasDe(site)).length;
    abas.player_opera = playerVivo();
    if (abas.player_opera) abas.ytmusic += 1;
    const r = await fetch(`${BASE}/ext/buscar`, {
      method: "POST",
      headers: {"Content-Type": "application/json", "X-Claudinho-Ext": self.CLAUDINHO.token},
      body: JSON.stringify({abas, versao: VERSAO}),
    });
    if (r.ok) {
      const dados = await r.json();
      for (const c of dados.comandos || []) await executar(c);
      // o Claudinho já copiou uma versão nova dos arquivos: recarrega pra usar (atualiza sozinha)
      if (dados.versao && dados.versao !== VERSAO) chrome.runtime.reload();
    }
  } catch (e) {
    // Claudinho fechado: tenta de novo no próximo ciclo
  } finally {
    rodando = false;
  }
}

chrome.runtime.onMessage.addListener((msg, remetente, responder) => {
  // a página do YouTube Music avisando que está aí; sem aba = é o player da barra lateral
  if (msg.tipo === "ytmusic" && (!remetente.tab || remetente.tab.id < 0)) {
    player.visto = Date.now();
    responder({comandos: player.fila.splice(0)});
  } else {
    responder({comandos: []});
  }
  ciclo();
});

setInterval(ciclo, 1000);
ciclo();
// o navegador pode encerrar o fundo quando está parado: o alarme acorda ele de novo
chrome.alarms.create("acordar", {periodInMinutes: 0.5});
chrome.alarms.onAlarm.addListener(ciclo);
