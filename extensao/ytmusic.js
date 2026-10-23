// Página do YouTube Music: numa aba normal ou no player da barra lateral do Opera (que não é aba).
// Fica avisando o fundo da extensão que está aqui; quando é o player, recebe os pedidos por essa conversa
// (o fundo não consegue mandar nada pra ele por conta própria, porque ele não é uma aba).

function botao(tipo) {
  // botões de curtir/não curtir da barra do player (o YouTube Music muda a estrutura às vezes: tenta alguns)
  const barra = document.querySelector("ytmusic-player-bar");
  if (!barra) return null;
  const rotulos = tipo === "curtir" ? ["Gostei", "Like", "Curtir"] : ["Não gostei", "Dislike", "Descurtir"];
  return [...barra.querySelectorAll("button, tp-yt-paper-icon-button")]
    .find(b => rotulos.some(r => (b.getAttribute("aria-label") || "").toLowerCase().startsWith(r.toLowerCase())));
}

// controles do player (botões da barra de baixo do YouTube Music)
function controle(qual, valor) {
  const barra = document.querySelector("ytmusic-player-bar");
  const video = document.querySelector("video");
  const clicar = seletor => { const b = barra && barra.querySelector(seletor); if (b) b.click(); };
  if (qual === "pausar" && video && !video.paused) clicar("#play-pause-button");
  else if (qual === "tocar" && video && video.paused) clicar("#play-pause-button");
  else if (qual === "proxima") clicar(".next-button");
  else if (qual === "anterior") clicar(".previous-button");
  else if (qual === "aleatorio") clicar(".shuffle");
  else if (qual === "repetir") clicar(".repeat");
  else if (qual === "volume") {
    const n = Math.max(0, Math.min(100, parseInt(valor, 10) || 0));
    const slider = document.querySelector("#volume-slider");
    if (slider) { slider.value = n; slider.dispatchEvent(new Event("change", {bubbles: true})); }
    if (video) video.volume = n / 100;
  }
}

function fazer(msg) {
  if (msg.acao === "controle") {
    controle(msg.qual, msg.valor);
  } else if (msg.acao === "abrir") {
    const url = new URL(msg.url);
    if (url.hostname === "music.youtube.com") location.assign(msg.url);  // só dentro do YouTube Music
  } else if (msg.acao === "curtir" || msg.acao === "descurtir") {
    const b = botao(msg.acao);
    if (b && b.getAttribute("aria-pressed") !== "true") b.click();  // já curtida: não desfaz
  }
}

chrome.runtime.onMessage.addListener(fazer);  // aba normal: o fundo manda direto

setInterval(() => {
  chrome.runtime.sendMessage({tipo: "ytmusic"}, resposta => {
    if (chrome.runtime.lastError || !resposta) return;
    for (const c of resposta.comandos || []) fazer(c);  // player do Opera: pedidos chegam por aqui
  });
}, 1200);
