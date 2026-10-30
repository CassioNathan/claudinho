// Fundo da extensão: pergunta ao Claudinho (servidor local) se tem pedido e executa no navegador.
// Quem pergunta é o fundo, e não as abas: aba em segundo plano tem os timers congelados pelo navegador.
//   YouTube Music: toca no player da barra lateral do Opera, se ele estiver aberto; senão troca a música na aba que
//                  já está aberta, sem roubar o foco (sem aba: abre uma em segundo plano)
//   YouTube: sempre numa aba nova, trazida pra frente
//   Rotinas: nos sites que você liberou, repete o caminho que você gravou (rotinas.js)
//   Abas: lista as abas abertas (título e site) e troca ou fecha uma, pelo id que o Claudinho escolheu
importScripts("config.js", "consultas.js", "rotinas.js");  // self.CLAUDINHO = {porta, token} (gerado na instalação)

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

// as abas abertas, pro Claudinho achar "a aba da Strandberg" pelo título sem tirar print da tela
async function listarAbas() {
  const abas = await chrome.tabs.query({});
  return abas.filter(a => a.id >= 0).map(a => ({id: a.id, titulo: a.title || "", site: (() => {
    try { return new URL(a.url).hostname; } catch (e) { return ""; } })(), ativa: a.active, tocando: !!a.audible,
    janela: a.windowId}));
}

async function executar(c) {
  if (c.acao === "aba") {   // trocar pra uma aba ou fechar (o Claudinho escolheu pelo título)
    const [ativa] = await chrome.tabs.query({active: true, lastFocusedWindow: true});
    const id = c.id === "ativa" ? (ativa && ativa.id) : Number(c.id);
    if (!id && id !== 0) return;
    if (c.qual === "focar") await trazerPraFrente(await chrome.tabs.get(id));
    else if (c.qual === "fechar") await chrome.tabs.remove(id);
    return;
  }
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
  } else if (["curtir", "descurtir", "controle"].includes(c.acao)) {
    // cliques e controles do player: quem faz é o script da página (na aba que está tocando ou foi usada por último)
    const aba = escolher(await abasDe(c.site));
    if (aba) chrome.tabs.sendMessage(aba.id, c).catch(() => {});
  }
}

// consulta ("o que tem no YouTube?"): a extensão olha e devolve pro Claudinho, sem mexer na tela do usuário;
// rotina: repete o que ele gravou num site liberado e devolve o que leu (essa mexe na tela: foi ele que pediu)
async function consultar(c) {
  let resultado;
  try {
    const rotina = c.acao === "rotina";
    if (c.modo === "abas") {   // não abre nem mexe em nada: só a lista
      await responder(c, {ok: true, dados: await listarAbas()});
      return;
    }
    const limite = new Promise((_, falhou) => setTimeout(() => falhou(new Error(rotina ? "a rotina passou de 3 minutos" :
      "a consulta travou em: " + (self.consultasClaudinho.andamento.etapa || "início"))), rotina ? 170000 : 35000));
    const trabalho = rotina ? self.rotinasClaudinho.rodar(c) : self.consultasClaudinho.consultar(c);
    resultado = {ok: true, dados: await Promise.race([trabalho, limite])};
  } catch (e) {
    resultado = {ok: false, erro: String((e && e.message) || e)};
  }
  await responder(c, resultado);
}

async function responder(c, resultado) {
  try {
    await fetch(`${BASE}/ext/resultado`, {
      method: "POST",
      headers: {"Content-Type": "application/json", "X-Claudinho-Ext": self.CLAUDINHO.token},
      body: JSON.stringify({id: c.id, resultado}),
    });
  } catch (e) { /* Claudinho fechou */ }
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
      for (const c of dados.comandos || []) {
        if (c.acao === "consultar" || c.acao === "rotina") consultar(c);  // sem await: demora e não pode travar o ciclo
        else if (c.acao === "cancelar") self.rotinasClaudinho.cancelar();  // ⏹ parar no Claudinho
        else await executar(c);
      }
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
  // gravação de rotina (o botão da extensão e o gravador na página)
  if (msg.tipo && (msg.tipo.startsWith("rotina_") || msg.tipo === "gravador_passo")) {
    self.rotinasClaudinho.mensagem(msg, remetente).then(responder, e => responder({ok: false, erro: String(e)}));
    return true;  // resposta assíncrona
  }
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
