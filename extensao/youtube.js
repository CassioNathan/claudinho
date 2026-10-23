// Aba do YouTube: acorda o fundo da extensão; quando o Claudinho pesquisou algo pra tocar (#claudinho-tocar no
// fim do endereço), abre o primeiro vídeo do resultado; e obedece os controles do vídeo (pausar, velocidade…).
chrome.runtime.sendMessage({oi: "youtube"}).catch(() => {});

function tocarPrimeiro() {
  if (location.pathname !== "/results" || location.hash !== "#claudinho-tocar") return;
  let tentativas = 0;
  const procurar = setInterval(() => {
    // primeiro vídeo normal da lista (pula anúncio, shorts e canais)
    const link = document.querySelector("ytd-search ytd-video-renderer a#video-title[href^='/watch']");
    if (link || ++tentativas > 40) {
      clearInterval(procurar);
      if (link) location.assign(link.href);
    }
  }, 250);
}
tocarPrimeiro();

function controle(qual, valor) {
  const video = document.querySelector("video.html5-main-video") || document.querySelector("video");
  const clicar = seletor => { const b = document.querySelector(seletor); if (b) b.click(); };
  if (!video) return;
  if (qual === "pausar" && !video.paused) clicar(".ytp-play-button");
  else if (qual === "tocar" && video.paused) clicar(".ytp-play-button");
  else if (qual === "velocidade") video.playbackRate = Math.max(0.25, Math.min(2.5, parseFloat(valor) || 1));
  else if (qual === "avancar") video.currentTime += parseFloat(valor) || 10;
  else if (qual === "voltar") video.currentTime = Math.max(0, video.currentTime - (parseFloat(valor) || 10));
  else if (qual === "legenda") clicar(".ytp-subtitles-button");
  else if (qual === "cinema") clicar(".ytp-size-button");
}

chrome.runtime.onMessage.addListener(msg => {
  if (msg.acao === "controle") controle(msg.qual, msg.valor);
});
