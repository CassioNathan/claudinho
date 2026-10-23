// Aba do YouTube Music: acorda o fundo da extensão e faz os cliques que a API de abas não faz (curtir).
chrome.runtime.sendMessage({oi: "ytmusic"}).catch(() => {});

function botao(tipo) {
  // botões de curtir/não curtir da barra do player (o YouTube Music muda a estrutura às vezes: tenta alguns)
  const barra = document.querySelector("ytmusic-player-bar");
  if (!barra) return null;
  const rotulos = tipo === "curtir" ? ["Gostei", "Like", "Curtir"] : ["Não gostei", "Dislike", "Descurtir"];
  return [...barra.querySelectorAll("button, tp-yt-paper-icon-button")]
    .find(b => rotulos.some(r => (b.getAttribute("aria-label") || "").toLowerCase().startsWith(r.toLowerCase())));
}

chrome.runtime.onMessage.addListener(msg => {
  if (msg.acao === "curtir" || msg.acao === "descurtir") {
    const b = botao(msg.acao);
    if (b && b.getAttribute("aria-pressed") !== "true") b.click();  // já curtida: não desfaz
  }
});
