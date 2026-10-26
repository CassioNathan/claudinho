// Consultas do Claudinho ao YouTube e ao YouTube Music: ele pergunta, a extensão olha e devolve os dados, SEM mexer na
// tela do usuário (nada de trazer janela pra frente).
//   YouTube:       lê o HTML da página (pesquisa, início, inscrições, canal, vídeo) com o login do navegador; não abre aba
//   YouTube Music: abre uma aba em segundo plano, lê a lista que a própria página montou e fecha a aba
(function (raiz) {
  const IDIOMA = "hl=pt-BR&gl=BR";

  // ---------------------------------------------------------------- utilidades
  function extrairJSON(html, marcador, serve) {
    // `marcador = {...}`: casa as chaves respeitando textos. O nome aparece em mais de um lugar da página;
    // devolve o primeiro objeto que passa em `serve` (sem ele, o primeiro que ler).
    const re = new RegExp(marcador + "\\s*=\\s*\\{", "g");
    let achado;
    while ((achado = re.exec(html))) {
      const i = achado.index + achado[0].length - 1;
      let fundo = 0, dentro = false, escape = false;
      for (let j = i; j < html.length; j++) {
        const c = html[j];
        if (dentro) {
          if (escape) escape = false;
          else if (c === "\\") escape = true;
          else if (c === '"') dentro = false;
        } else if (c === '"') dentro = true;
        else if (c === "{") fundo++;
        else if (c === "}" && --fundo === 0) {
          try {
            const o = JSON.parse(html.slice(i, j + 1));
            if (!serve || serve(o)) return o;
          } catch (e) { /* tenta a próxima */ }
          break;
        }
      }
    }
    return null;
  }

  const texto = o => !o ? "" : (o.simpleText !== undefined ? o.simpleText : (o.runs || []).map(r => r.text).join(""));

  function andar(o, aoAchar) {
    if (Array.isArray(o)) { for (const x of o) if (andar(x, aoAchar) === false) return false; return true; }
    if (o && typeof o === "object") {
      if (aoAchar(o) === false) return false;
      for (const k in o) if (andar(o[k], aoAchar) === false) return false;
    }
    return true;
  }

  async function pegarHTML(url) {
    const r = await fetch(url, {credentials: "include", headers: {"Accept-Language": "pt-BR,pt;q=0.9"}});
    if (!r.ok) throw new Error(`o YouTube respondeu ${r.status}`);
    return r.text();
  }

  // ---------------------------------------------------------------- YouTube: leitura dos vídeos de uma página
  function videoDeRenderer(v) {
    const dono = (v.ownerText || v.longBylineText || v.shortBylineText || {}).runs || [{}];
    const insignias = (v.badges || []).map(b => (b.metadataBadgeRenderer || {}).label || "");
    const aoVivo = insignias.some(t => /ao vivo|live/i.test(t)) || (v.thumbnailOverlays || []).some(o =>
      (o.thumbnailOverlayTimeStatusRenderer || {}).style === "LIVE");
    return {
      id: v.videoId, titulo: texto(v.title), canal: dono[0].text || "",
      duracao: texto(v.lengthText) || (aoVivo ? "AO VIVO" : ""),
      views: texto(v.viewCountText) || texto(v.shortViewCountText), publicado: texto(v.publishedTimeText),
      resumo: texto(v.descriptionSnippet) || ((v.detailedMetadataSnippets || [{}])[0].snippetText ? texto(v.detailedMetadataSnippets[0].snippetText) : ""),
    };
  }

  function videoDeLockup(l) {
    // o layout novo do YouTube (início, recomendados): lockupViewModel
    const m = ((l.metadata || {}).lockupMetadataViewModel) || {};
    const partes = [];
    andar((m.metadata || {}).contentMetadataViewModel || {}, o => {
      if (o.metadataParts) for (const p of o.metadataParts) if (p.text && p.text.content) partes.push(p.text.content);
    });
    let duracao = "";
    andar(l.contentImage || {}, o => {
      if (o.thumbnailBadgeViewModel && o.thumbnailBadgeViewModel.text) duracao = duracao || o.thumbnailBadgeViewModel.text;
    });
    const publicado = partes.find(p => /atrás|ago|há |streamed|transmitido|estreia/i.test(p)) || "";
    const views = partes.find(p => /visualiza|views|assistindo|watching/i.test(p))
      || partes.find(p => p !== publicado && /^\d[\d.,]*\s*(mil|mi|bi|k|m)?$/i.test(p.trim())) || "";
    const canal = partes.find(p => p !== publicado && p !== views) || "";
    return {id: l.contentId, titulo: (m.title || {}).content || "", canal, duracao, views, publicado, resumo: ""};
  }

  function videosDe(dados, n) {
    const lista = [], vistos = new Set();
    andar(dados, o => {
      let v = null;
      if (o.videoRenderer && o.videoRenderer.videoId) v = videoDeRenderer(o.videoRenderer);
      else if (o.lockupViewModel && (o.lockupViewModel.contentType === "LOCKUP_CONTENT_TYPE_VIDEO"
        || (!o.lockupViewModel.contentType && /^[\w-]{11}$/.test(o.lockupViewModel.contentId || "")))) v = videoDeLockup(o.lockupViewModel);
      if (v && v.id && v.titulo && !vistos.has(v.id)) { vistos.add(v.id); lista.push(v); }
      return lista.length < n;
    });
    return lista;
  }

  async function paginaDeVideos(url, n) {
    const dados = extrairJSON(await pegarHTML(url), "ytInitialData");
    if (!dados) throw new Error("não consegui ler a página do YouTube");
    return videosDe(dados, n);
  }

  // Roda DENTRO da página do vídeo (mundo MAIN): lê o que o próprio YouTube montou e para o vídeo.
  async function lerVideoNaPagina() {
    const esperar = ms => new Promise(r => setTimeout(r, ms));
    let jogador = null;
    for (let t = 0; t < 40 && !(jogador && jogador.videoDetails); t++) {
      jogador = window.ytInitialPlayerResponse;
      if (!(jogador && jogador.videoDetails)) await esperar(250);
    }
    const v = document.querySelector("video");
    if (v) { v.pause(); v.muted = true; }
    const d = jogador && jogador.videoDetails;
    if (!d) return null;
    const mf = (jogador.microformat || {}).playerMicroformatRenderer || {};
    const seg = parseInt(d.lengthSeconds || "0", 10);
    return {
      id: d.videoId, titulo: d.title, canal: d.author, publicado: mf.publishDate || mf.uploadDate || "",
      duracao: seg ? `${Math.floor(seg / 60)}:${String(seg % 60).padStart(2, "0")}` : "AO VIVO",
      views: d.viewCount ? `${Number(d.viewCount).toLocaleString("pt-BR")} visualizações` : "",
      ao_vivo: !!d.isLiveContent, descricao: d.shortDescription || "",
    };
  }

  // espera a aba carregar e roda a função nela; se a página trocou de quadro no meio (o YouTube redireciona), tenta de novo
  async function rodarNaAba(tabId, opcoes) {
    let ultimo;
    for (let tentativa = 0; tentativa < 3; tentativa++) {
      try {
        await new Promise(r => setTimeout(r, tentativa ? 1500 : 500));
        await esperarCarga(tabId, 5000);
        return await chrome.scripting.executeScript({target: {tabId}, world: "MAIN", ...opcoes});
      } catch (e) {
        ultimo = e;
      }
    }
    throw ultimo;
  }

  const andamento = {etapa: ""};   // onde a consulta está (pra dizer onde travou, se travar)

  async function videoPelaAba(id) {
    andamento.etapa = "criando a aba do vídeo";
    const aba = await chrome.tabs.create({url: `https://www.youtube.com/watch?v=${encodeURIComponent(id)}&${IDIOMA}`, active: false});
    try {
      andamento.etapa = "aba criada, lendo a página";
      chrome.tabs.update(aba.id, {muted: true}).catch(() => {});
      const [r] = await rodarNaAba(aba.id, {func: lerVideoNaPagina});
      andamento.etapa = "página lida";
      return r.result || null;
    } finally {
      chrome.tabs.remove(aba.id).catch(() => {});
    }
  }

  // ---------------------------------------------------------------- YouTube: consultas
  const youtube = {
    async pesquisa(c) {
      return paginaDeVideos(`https://www.youtube.com/results?search_query=${encodeURIComponent(c.termo)}&${IDIOMA}`, c.n || 8);
    },
    async inicio(c) { return paginaDeVideos(`https://www.youtube.com/?${IDIOMA}`, c.n || 12); },
    async inscricoes(c) { return paginaDeVideos(`https://www.youtube.com/feed/subscriptions?${IDIOMA}`, c.n || 12); },
    async historico(c) { return paginaDeVideos(`https://www.youtube.com/feed/history?${IDIOMA}`, c.n || 12); },
    async canal(c) {
      // acha o canal pelo nome (filtro "canais" da pesquisa) e lê a aba de vídeos dele
      const busca = extrairJSON(await pegarHTML(
        `https://www.youtube.com/results?search_query=${encodeURIComponent(c.termo)}&sp=EgIQAg%253D%253D&${IDIOMA}`), "ytInitialData");
      let canal = null;
      andar(busca || {}, o => { if (o.channelRenderer && !canal) canal = o.channelRenderer; return !canal; });
      if (!canal) throw new Error(`não achei um canal chamado ${c.termo}`);
      const videos = await paginaDeVideos(`https://www.youtube.com/channel/${canal.channelId}/videos?${IDIOMA}`, c.n || 10);
      const nome = texto(canal.title);
      videos.forEach(v => { v.canal = nome; });
      return {canal: nome, inscritos: texto(canal.videoCountText) || texto(canal.subscriberCountText), videos};
    },
    async video(c) {
      const html = await pegarHTML(`https://www.youtube.com/watch?v=${encodeURIComponent(c.id)}&${IDIOMA}`);
      const jogador = extrairJSON(html, "ytInitialPlayerResponse", o => o.videoDetails);
      const d = jogador && jogador.videoDetails;
      if (!d && typeof chrome !== "undefined" && chrome.tabs) {
        // o YouTube não entrega o jogador pra um pedido de fundo: abre a página numa aba muda e em segundo plano, lê e fecha
        const lido = await videoPelaAba(c.id);
        if (lido) return lido;
      }
      if (!d) {
        // sem o jogador (às vezes o YouTube só entrega a página "crua"): lê título, canal, data e descrição do que a página mostra
        const dados = extrairJSON(html, "ytInitialData");
        const achar = {};
        andar(dados || {}, o => {
          for (const k of ["videoPrimaryInfoRenderer", "videoSecondaryInfoRenderer", "attributedDescription"]) if (o[k] && !achar[k]) achar[k] = o[k];
          return true;
        });
        const p = achar.videoPrimaryInfoRenderer;
        if (!p) {
          const ps = (extrairJSON(html, "ytInitialPlayerResponse") || {}).playabilityStatus || {};
          throw new Error(`não consegui ler esse vídeo (${ps.status || "?"}: ${ps.reason || "sem motivo"})`);
        }
        const dono = (((achar.videoSecondaryInfoRenderer || {}).owner || {}).videoOwnerRenderer || {}).title;
        const visu = ((p.viewCount || {}).videoViewCountRenderer || {}).viewCount;
        return {
          id: c.id, titulo: texto(p.title), canal: texto(dono), publicado: texto(p.dateText), duracao: "?",
          views: texto(visu), ao_vivo: false, descricao: (achar.attributedDescription || {}).content || "",
        };
      }
      const mf = (jogador.microformat || {}).playerMicroformatRenderer || {};
      const seg = parseInt(d.lengthSeconds || "0", 10);
      return {
        id: d.videoId, titulo: d.title, canal: d.author,
        publicado: mf.publishDate || mf.uploadDate || "", duracao: seg ? `${Math.floor(seg / 60)}:${String(seg % 60).padStart(2, "0")}` : "AO VIVO",
        views: d.viewCount ? `${Number(d.viewCount).toLocaleString("pt-BR")} visualizações` : "",
        ao_vivo: !!d.isLiveContent, descricao: d.shortDescription || "",
      };
    },
  };

  // ---------------------------------------------------------------- YouTube Music: leitura da página (roda DENTRO da aba)
  // Auto-contida: é serializada e executada na página (mundo MAIN), onde cada item tem o `.data` que o YouTube Music montou.
  async function varrerYTMusic(max, rolar) {
    const texto = r => !r ? "" : (r.simpleText !== undefined ? r.simpleText : (r.runs || []).map(x => x.text).join(""));
    const primeiro = (o, chave) => {
      if (!o || typeof o !== "object") return null;
      if (o[chave]) return o[chave];
      for (const k in o) { const r = primeiro(o[k], chave); if (r) return r; }
      return null;
    };
    const referencia = (ep, dados) => {
      const w = ep && (ep.watchEndpoint || ep.watchPlaylistEndpoint);
      if (w && w.videoId) return {ref: "m:" + w.videoId, tipo: "música"};
      if (w && w.playlistId) return {ref: "p:" + w.playlistId.replace(/^VL/, ""), tipo: "playlist"};
      const b = ep && ep.browseEndpoint && ep.browseEndpoint.browseId;
      if (b) {
        if (b.startsWith("UC")) return {ref: "c:" + b, tipo: "artista/canal"};
        if (b.startsWith("MPRE") || b.startsWith("OLAK")) return {ref: "a:" + b, tipo: "álbum"};
        if (b.startsWith("VL")) return {ref: "p:" + b.slice(2), tipo: "playlist"};
        return {ref: "b:" + b, tipo: "página"};
      }
      return null;
    };
    const secaoDe = el => {
      const s = el.closest("ytmusic-carousel-shelf-renderer, ytmusic-shelf-renderer, ytmusic-immersive-carousel-shelf-renderer");
      const h = s && s.data && s.data.header;
      const r = h && Object.values(h)[0];
      return r ? texto(r.title) : "";
    };
    const colher = () => {
      const itens = [];
      for (const el of document.querySelectorAll("ytmusic-two-row-item-renderer, ytmusic-responsive-list-item-renderer")) {
        const d = el.data;
        if (!d) continue;
        let titulo, sub, ep;
        if (d.flexColumns) {
          const cols = d.flexColumns.map(c => Object.values(c)[0].text);
          titulo = texto(cols[0]);
          sub = cols.slice(1).map(texto).filter(Boolean).join(" • ");
          const dado = d.playlistItemData && d.playlistItemData.videoId;
          ep = (cols[0].runs && cols[0].runs[0] && cols[0].runs[0].navigationEndpoint) || d.navigationEndpoint
            || primeiro(d.overlay, "watchEndpoint") && {watchEndpoint: primeiro(d.overlay, "watchEndpoint")};
          if (dado && !(ep && ep.watchEndpoint)) ep = {watchEndpoint: {videoId: dado}};
        } else {
          titulo = texto(d.title);
          sub = texto(d.subtitle);
          ep = d.navigationEndpoint || (d.title && d.title.runs && d.title.runs[0] && d.title.runs[0].navigationEndpoint);
        }
        const r = referencia(ep);
        if (titulo && r) itens.push({titulo, detalhe: sub, ref: r.ref, tipo: r.tipo, secao: secaoDe(el)});
      }
      return itens;
    };
    const esperar = ms => new Promise(r => setTimeout(r, ms));
    let itens = [];
    for (let t = 0; t < 40 && !itens.length; t++) { itens = colher(); if (!itens.length) await esperar(300); }
    for (let k = 0; k < (rolar ? 3 : 0) && itens.length < max; k++) {   // início: vai carregando mais prateleiras
      window.scrollTo(0, document.body.scrollHeight);
      document.querySelectorAll("ytmusic-app-layout #contents, ytmusic-browse-response #contents").forEach(e => e.scrollTo && e.scrollTo(0, 99999));
      await esperar(1200);
      itens = colher();
    }
    const vistos = new Set();
    const unicos = itens.filter(i => !vistos.has(i.ref + i.secao) && vistos.add(i.ref + i.secao)).slice(0, max);
    const conta = s => document.querySelectorAll(s).length;
    return {itens: unicos, info: `estado=${document.readyState} titulo="${document.title}" url=${location.href} ` +
      `linhas=${conta("ytmusic-responsive-list-item-renderer")} cards=${conta("ytmusic-two-row-item-renderer")} ` +
      `oculta=${document.hidden}`};
  }

  const URL_YTMUSIC = {
    inicio: () => "https://music.youtube.com/",
    explorar: () => "https://music.youtube.com/explore",
    pesquisa: c => `https://music.youtube.com/search?q=${encodeURIComponent(c.termo)}`,
    musicas: () => "https://music.youtube.com/library/songs",
    playlists: () => "https://music.youtube.com/library/playlists",
    albuns: () => "https://music.youtube.com/library/albums",
    artistas: () => "https://music.youtube.com/library/artists",
    curtidas: () => "https://music.youtube.com/playlist?list=LM",
    historico: () => "https://music.youtube.com/history",
    pagina: c => urlDeReferencia(c.ref),
  };

  function urlDeReferencia(ref) {
    const [tipo, id] = String(ref).split(":");
    if (!/^[A-Za-z0-9_-]{3,60}$/.test(id || "")) throw new Error("referência inválida");
    if (tipo === "m") return `https://music.youtube.com/watch?v=${id}&list=RDAMVM${id}`;
    if (tipo === "p") return `https://music.youtube.com/playlist?list=${id}`;
    return `https://music.youtube.com/browse/${id}`;   // álbum, artista, canal, página
  }

  async function esperarCarga(tabId, limite) {
    const fim = Date.now() + limite;
    while (Date.now() < fim) {
      const aba = await chrome.tabs.get(tabId);
      if (aba.status === "complete") return;
      await new Promise(r => setTimeout(r, 250));
    }
  }

  async function ytmusic(c) {
    const montar = URL_YTMUSIC[c.modo];
    if (!montar) throw new Error(`consulta '${c.modo}' não existe no YouTube Music`);
    const url = montar(c);
    // aba em segundo plano (não rouba o foco); fecha no fim
    const aba = await chrome.tabs.create({url, active: false});
    try {
      const [r] = await rodarNaAba(aba.id, {func: varrerYTMusic, args: [c.n || 15, c.modo === "inicio" || c.modo === "explorar"]});
      const res = r.result || {itens: [], info: "sem retorno"};
      if (!res.itens.length) throw new Error("não achei nada na página do YouTube Music (" + res.info + ")");
      return res.itens;
    } finally {
      chrome.tabs.remove(aba.id).catch(() => {});
    }
  }

  async function consultar(c) {
    if (c.site === "youtube") {
      const f = youtube[c.modo];
      if (!f) throw new Error(`consulta '${c.modo}' não existe no YouTube`);
      return f(c);
    }
    if (c.site === "ytmusic") return ytmusic(c);
    throw new Error("site desconhecido");
  }

  raiz.consultasClaudinho = {andamento, consultar, extrairJSON, videosDe, youtube, urlDeReferencia};
  if (typeof module !== "undefined") module.exports = raiz.consultasClaudinho;
})(typeof self !== "undefined" ? self : globalThis);
