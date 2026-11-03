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

// ---------- WhatsApp Web (habilidade de vendedor): lê a conversa aberta como texto e escreve no campo, sem enviar ----------
// as duas funções rodam DENTRO da página do WhatsApp (chrome.scripting): não enxergam nada daqui de fora
function lerWhatsapp(n) {
  const main = document.querySelector("#main");
  if (!main) {   // sem conversa aberta (ou o WhatsApp mudou a página): devolve só a estrutura, nada de texto
    const conta = sel => document.querySelectorAll(sel).length;
    return {aberta: false, contato: "", mensagens: [], estrutura: {
      main: conta("#main"), app: conta("#app"), pre: conta("[data-pre-plain-text]"), dataId: conta("[data-id]"),
      editaveis: conta("div[contenteditable='true']"), footer: conta("footer"), header: conta("header"),
      msgIn: conta(".message-in"), msgOut: conta(".message-out"), mainIds: [...document.querySelectorAll("[id]")]
        .map(e => e.id).filter(i => /^(main|pane|app|side)/i.test(i)).slice(0, 10)}};
  }
  const nome = main.querySelector("header span[dir='auto']");
  const contato = ((nome && (nome.getAttribute("title") || nome.textContent)) || "").trim().slice(0, 80);
  // cada linha de mensagem tem o data-id; a de texto tem, dentro, o data-pre-plain-text ("[10:32, 31/10/2026] Fulano: ").
  // Foto, vídeo, áudio e figurinha sem legenda não têm texto: entram como "[foto]", "[vídeo]"… pra ele saber que existem.
  // Quem mandou: o rótulo "Você:" / "Fulano:" da própria mensagem, o id antigo ("true_…"), a classe antiga
  // (.message-out) ou a cauda do balão ("tail-out" / "tail-in", só na primeira de cada bloco); o resto herda do
  // remetente ou da anterior
  const lados = {};   // remetente (do data-pre-plain-text) -> "eu" | "cliente", aprendido pelas que têm sinal
  let anterior = "cliente";
  const quemPeloRotulo = linha => {
    const r = linha.querySelector("[aria-label$=':']");
    const t = r ? (r.getAttribute("aria-label") || "").trim() : "";
    return !t ? null : /^(você|voce|you):$/i.test(t) ? "eu" : "cliente";
  };
  const midiaDe = linha => {
    const rotulos = [...linha.querySelectorAll("[aria-label]")].map(e => (e.getAttribute("aria-label") || "").toLowerCase()).join("|");
    const icones = [...linha.querySelectorAll("[data-icon]")].map(e => e.getAttribute("data-icon")).join("|");
    const tudo = rotulos + "|" + icones;
    if (/vídeo|video|media-play|video-pip/.test(tudo)) return "[vídeo]";
    if (/mensagem de voz|voice message|audio-play|ptt/.test(tudo)) return "[áudio]";
    if (/figurinha|sticker/.test(rotulos)) return "[figurinha]";
    if (/abrir imagem|open image|open photo|abrir foto/.test(rotulos)) return "[foto]";
    if (/documento|document|doc-/.test(tudo)) return "[arquivo]";
    return "";
  };
  const mensagens = [...main.querySelectorAll("[data-id]")].map(linha => {
    const id = linha.getAttribute("data-id") || "";
    const el = linha.querySelector("[data-pre-plain-text]");
    const pre = el ? el.getAttribute("data-pre-plain-text") || "" : "";
    const remetente = ((pre.match(/\]\s*([^:]+):/) || [])[1] || "").trim();
    const icone = sel => !!linha.querySelector(`[data-icon${sel}]`);
    let lado = quemPeloRotulo(linha) || (id.startsWith("true_") || linha.querySelector(".message-out") || icone('="tail-out"') ? "eu"
      : id.startsWith("false_") || linha.querySelector(".message-in") || icone('="tail-in"') ? "cliente" : null);
    if (lado && remetente) lados[remetente] = lado;
    lado = lado || lados[remetente] || anterior;
    const hora = (pre.match(/\[([^\]]+)\]/) || [])[1] || ((linha.innerText || "").match(/\d{1,2}:\d{2}/) || [""])[0];
    let texto = "";
    if (el) {   // blocos de texto sem repetir nem vazios; a citação de uma resposta fica num botão (role=button)
      const blocos = [...new Set([...el.querySelectorAll(".selectable-text")].map(b => (b.innerText || "").trim()).filter(Boolean))];
      const cita = el.querySelector("[role='button'] .selectable-text");
      const citada = cita ? (cita.innerText || "").trim() : "";
      const propria = blocos.filter(b => b !== citada);
      texto = citada && propria.length ? `(respondendo a "${citada.slice(0, 80)}") ${propria.join(" ")}`
        : blocos.join(" ") || (el.innerText || "");
    }
    if (!texto.trim()) texto = midiaDe(linha);
    if (texto.trim()) anterior = lado;
    return {de: lado, texto: texto.trim().slice(0, 1000), hora, id};
  }).filter(m => m.texto).slice(-n);
  return {aberta: true, contato, mensagens};
}

// a lista de conversas (painel da esquerda): quem tem mensagem não lida e a prévia da última, sem abrir (nem marcar como
// lida) nenhuma conversa. Olha as `n` primeiras linhas (as mais recentes, o WhatsApp ordena assim)
function lerListaWhatsapp(n, todas) {   // todas: também as já lidas (as recentes, do jeito que a lista mostra)
  const lado = document.querySelector("#pane-side");
  if (!lado) return {ok: false, erro: "não achei a lista de conversas (o WhatsApp ainda está carregando, pede o QR code ou mudou a página)"};
  let linhas = [...lado.querySelectorAll("[role='row']")];
  if (!linhas.length) linhas = [...lado.querySelectorAll("[role='listitem']")];
  if (!linhas.length) linhas = [...lado.querySelectorAll("[data-testid='cell-frame-container']")];
  if (!linhas.length) return {ok: false, erro: "a lista de conversas veio vazia (o WhatsApp mudou a página?)"};
  const quando = /^\d{1,2}:\d{2}(\s?[ap]m)?$|^(hoje|ontem|today|yesterday)$|^\d{1,2}\/\d{1,2}(\/\d{2,4})?$/i;
  const conversas = [];
  for (const el of linhas.slice(0, n)) {
    const nomeEl = el.querySelector("span[title]");
    const nome = ((nomeEl && (nomeEl.getAttribute("title") || nomeEl.textContent)) || "").trim();
    const badge = el.querySelector("[aria-label*='não lida' i], [aria-label*='unread' i]");
    if (!nome || (!badge && !todas)) continue;   // sem bolinha de não lida: nem entra na conta (a não ser em "todas")
    const rotulo = (badge && badge.getAttribute("aria-label")) || "";
    const num = badge ? (parseInt(rotulo, 10) || parseInt((badge.textContent || "").trim(), 10) || 1) : 0;
    const textos = (el.innerText || "").split("\n").map(t => t.trim()).filter(Boolean);
    const hora = textos.find(t => quando.test(t)) || "";
    const previa = textos.filter(t => t !== nome && t !== hora && !/^\d{1,3}$/.test(t)).pop() || "";
    const silenciada = !!el.querySelector("[data-icon='muted'], [data-icon='mute']");
    conversas.push({nome: nome.slice(0, 80), previa: previa.slice(0, 200), hora, n: num, silenciada});
  }
  return {ok: true, vistas: Math.min(linhas.length, n), conversas};
}

async function escreverWhatsapp(texto, enviar) {
  const caixa = document.querySelector("#main footer div[contenteditable='true']");
  if (!caixa) return {ok: false, erro: "nenhuma conversa aberta no WhatsApp"};
  if ((caixa.innerText || "").trim()) return {ok: false, erro: "o campo já tem texto seu", ocupado: true};
  caixa.focus();
  document.execCommand("insertText", false, texto);   // o WhatsApp só "vê" o texto se vier como digitação
  if (!enviar) return {ok: true, enviada: false};
  await new Promise(r => setTimeout(r, 300));   // o botão de enviar aparece depois que o campo tem texto
  const icone = document.querySelector("#main footer [data-icon='send'], #main footer [data-icon='wds-ic-send-filled']");
  const botao = (icone && icone.closest("button")) ||
    document.querySelector("#main footer button[aria-label='Enviar'], #main footer button[aria-label='Send']");
  if (botao) botao.click();
  else caixa.dispatchEvent(new KeyboardEvent("keydown", {key: "Enter", code: "Enter", keyCode: 13, which: 13, bubbles: true}));
  await new Promise(r => setTimeout(r, 600));
  const foi = !(caixa.innerText || "").trim();   // enviada: o campo esvazia
  return foi ? {ok: true, enviada: true} : {ok: false, erro: "preenchi, mas o envio não foi: aperta Enter você"};
}

async function whatsapp(c) {
  const abas = await chrome.tabs.query({url: "https://web.whatsapp.com/*"});
  const aba = abas.find(a => a.active) || abas[0];
  if (!aba) throw new Error("o WhatsApp Web não está aberto no navegador");
  const ler = c.modo === "whatsapp_ler", lista = c.modo === "whatsapp_lista";
  const [r] = await chrome.scripting.executeScript({target: {tabId: aba.id},
    func: lista ? lerListaWhatsapp : ler ? lerWhatsapp : escreverWhatsapp,
    args: lista ? [Number(c.n) || 30, !!c.todas] : ler ? [Number(c.n) || 20] : [String(c.texto || ""), !!c.enviar]});
  if (!ler && !lista && r.result && r.result.ok) await trazerPraFrente(aba);
  return r.result;
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
    if (["whatsapp_ler", "whatsapp_escrever", "whatsapp_lista"].includes(c.modo)) {   // habilidade de vendedor
      await responder(c, {ok: true, dados: await whatsapp(c)});
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
