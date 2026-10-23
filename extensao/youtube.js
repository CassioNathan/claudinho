// Aba do YouTube: acorda o fundo da extensão e, quando o Claudinho pesquisou algo pra tocar
// (#claudinho-tocar no fim do endereço), abre o primeiro vídeo do resultado.
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
