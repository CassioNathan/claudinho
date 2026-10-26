// Rotinas: você mostra o caminho num site que liberou (gravar), e o Claudinho repete quando você pede (rodar).
// A gravação fica no storage da sessão (o fundo da extensão pode dormir no meio); cada passo da repetição roda
// na página pelo chrome.scripting, então página nova no meio do caminho não perde o fio.
(function (raiz) {
  const CHAVE = "gravacao";  // {tabId, origem, inicio, passos}
  let cancelado = false;     // ⏹ parar no Claudinho: a rotina em andamento para no próximo passo
  const dormir = ms => new Promise(r => setTimeout(r, ms));
  const base = () => `http://127.0.0.1:${self.CLAUDINHO.porta}`;

  async function gravacao() { return (await chrome.storage.session.get(CHAVE))[CHAVE] || null; }
  async function guardar(g) { await chrome.storage.session.set({[CHAVE]: g}); }

  async function porGravador(tabId) {
    try { await chrome.scripting.executeScript({target: {tabId}, files: ["gravador.js"]}); } catch (e) { /* aba fechou */ }
  }

  // página nova na aba que está gravando: o gravador vai junto
  chrome.tabs.onUpdated.addListener(async (tabId, info) => {
    if (info.status !== "complete") return;
    const g = await gravacao();
    if (g && g.tabId === tabId) await porGravador(tabId);
  });

  async function comecar(tabId) {
    const aba = await chrome.tabs.get(tabId);
    const origem = new URL(aba.url).origin;
    if (!(await chrome.permissions.contains({origins: [origem + "/*"]}))) return {ok: false, erro: "site não liberado"};
    await guardar({tabId, origem, inicio: aba.url, passos: []});
    await porGravador(tabId);
    return {ok: true};
  }

  async function anotar(passo, remetente) {
    const g = await gravacao();
    if (!g || !remetente.tab || remetente.tab.id !== g.tabId) return;
    if (new URL(remetente.tab.url).origin !== g.origem) return;  // saiu do site liberado: não anota
    if (passo.tipo === "digitar") {
      // o mesmo campo com o mesmo texto (Enter e depois "change"): fica um só; texto novo no mesmo campo seguido: troca
      const recente = g.passos.slice(-3).find(p => p.tipo === "digitar" && p.alvo.css === passo.alvo.css);
      if (recente && recente.valor === passo.valor) return;
      const ult = g.passos[g.passos.length - 1];
      if (ult && ult.tipo === "digitar" && ult.alvo.css === passo.alvo.css) g.passos.pop();
    }
    g.passos.push(passo);
    await guardar(g);
  }

  async function terminar(nome) {
    const g = await gravacao();
    await chrome.storage.session.remove(CHAVE);
    if (g) chrome.tabs.sendMessage(g.tabId, {tipo: "gravador_parar"}).catch(() => {});
    if (!g || !nome) return {ok: true, cancelado: true};
    if (!g.passos.length) return {ok: false, erro: "nenhum passo gravado"};
    try {
      const r = await fetch(`${base()}/ext/rotina_salvar`, {
        method: "POST",
        headers: {"Content-Type": "application/json", "X-Claudinho-Ext": self.CLAUDINHO.token},
        body: JSON.stringify({nome, site: g.origem, inicio: g.inicio, passos: g.passos}),
      });
      return r.ok ? {ok: true} : {ok: false, erro: `o Claudinho respondeu ${r.status}`};
    } catch (e) {
      return {ok: false, erro: "o Claudinho está fechado: abra ele e salve de novo"};
    }
  }

  async function mensagem(msg, remetente) {
    if (msg.tipo === "gravador_passo") return anotar(msg.passo, remetente);
    if (msg.tipo === "rotina_estado") return gravacao();
    if (msg.tipo === "rotina_comecar") return comecar(msg.tabId);
    if (msg.tipo === "rotina_ler") {
      const g = await gravacao();
      if (g) await chrome.tabs.sendMessage(g.tabId, {tipo: "gravador_ler"}).catch(() => {});
      return {ok: !!g};
    }
    if (msg.tipo === "rotina_ler_pagina") {  // ler o texto da página inteira (quando marcar a área não dá certo)
      const g = await gravacao();
      if (!g) return {ok: false};
      g.passos.push({tipo: "ler", alvo: {pagina: true}, rotulo: "a página toda"});
      await guardar(g);
      return {ok: true};
    }
    if (msg.tipo === "rotina_terminar") return terminar(msg.nome);
    return null;
  }

  // ---------------------------------------------------------------- repetir
  async function carregada(tabId) {
    for (let i = 0; i < 80; i++) {
      const t = await chrome.tabs.get(tabId);
      if (t.status === "complete") return t;
      await dormir(250);
    }
    return chrome.tabs.get(tabId);
  }

  // roda dentro da página: precisa ser autossuficiente (vai serializada pro chrome.scripting)
  async function fazerPasso(p, valor) {
    const dormir = ms => new Promise(r => setTimeout(r, ms));
    const visivel = el => !!(el && (el.offsetParent || el.getClientRects().length));
    const limpa = s => (s || "").replace(/\s+/g, " ").trim().toLowerCase();
    const a = p.alvo || {};
    function achar() {
      if (a.css) {
        try {
          const el = document.querySelector(a.css);
          // no clique, o texto confere (lista que mudou de ordem não clica no item errado)
          if (visivel(el) && (p.tipo !== "clique" || !a.texto || limpa(el.innerText || el.value) === limpa(a.texto))) return el;
        } catch (e) { /* seletor inválido nesta página */ }
      }
      if (a.texto) {
        const iguais = [...document.querySelectorAll(a.tag || "*")].filter(e => visivel(e) && limpa(e.innerText) === limpa(a.texto));
        const mais_dentro = iguais.filter(e => !iguais.some(o => o !== e && e.contains(o)));
        if (mais_dentro.length) return mais_dentro[0];
      }
      if (a.rotulo) {
        const r = limpa(a.rotulo);
        const el = [...document.querySelectorAll("[aria-label], [placeholder], [name], [title]")].find(e => visivel(e) &&
          [e.getAttribute("aria-label"), e.getAttribute("placeholder"), e.getAttribute("name"), e.getAttribute("title")]
            .some(v => limpa(v) === r));
        if (el) return el;
      }
      return null;
    }
    const lerTexto = area => (area.innerText || "").replace(/[ \t]+/g, " ").replace(/\n{3,}/g, "\n\n").trim().slice(0, 15000);
    // site que monta a lista depois de carregar (kanban busca os cards à parte): lê quando o texto PARA de mudar,
    // no máximo 20 s. A moldura (filtros, colunas vazias) chega antes dos cards e fica parada um tempo: página que
    // acabou de abrir espera 4 s de texto igual; página aberta há tempo (já carregada) só 1,5 s
    async function lerQuandoAssentar(area) {
      const precisa = performance.now() < 20000 ? 8 : 3;  // amostras iguais seguidas, de 0,5 s
      let antes = -1, iguais = 0;
      for (let i = 0; i < 40; i++) {
        const agora = lerTexto(area).length;
        iguais = agora === antes && agora > 0 ? iguais + 1 : 0;
        if (iguais >= precisa) break;
        antes = agora;
        await dormir(500);
      }
      return lerTexto(area);
    }
    if (p.tipo === "ler" && a.pagina) return {ok: true, texto: await lerQuandoAssentar(document.body)};
    let el = null;
    const tentativas = p.tipo === "ler" ? 60 : 40;  // até 15 s pra área de leitura (kanban demora a montar), 10 s pro resto
    for (let i = 0; i < tentativas && !el; i++) {
      el = achar();
      if (!el) await dormir(250);
    }
    if (p.tipo === "ler") {
      if (!el)  // a área mudou de jeito: lê a página toda em vez de falhar (o chat ainda acha o que ele pediu)
        return {ok: true, texto: "(não achei a área marcada; li a página toda)\n" + await lerQuandoAssentar(document.body)};
      return {ok: true, texto: await lerQuandoAssentar(el)};
    }
    if (!el) return {ok: false, erro: `não achei "${p.rotulo || a.texto || a.rotulo || a.css}" na página`};
    el.scrollIntoView({block: "center"});
    if (p.tipo === "clique") {
      for (const t of ["pointerdown", "mousedown", "pointerup", "mouseup"])
        el.dispatchEvent(new MouseEvent(t, {bubbles: true, cancelable: true, view: window}));
      el.click();
    } else if (p.tipo === "digitar") {
      el.focus();
      if (el.isContentEditable) el.innerText = valor;
      else {
        const proto = el.tagName === "TEXTAREA" ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
        Object.getOwnPropertyDescriptor(proto, "value").set.call(el, valor);  // React e afins só veem pelo setter nativo
      }
      el.dispatchEvent(new Event("input", {bubbles: true}));
      el.dispatchEvent(new Event("change", {bubbles: true}));
    } else if (p.tipo === "selecionar") {
      el.value = valor;
      el.dispatchEvent(new Event("change", {bubbles: true}));
    } else if (p.tipo === "tecla") {
      el.focus();
      const opcoes = {key: "Enter", code: "Enter", keyCode: 13, which: 13, bubbles: true, cancelable: true};
      const seguiu = el.dispatchEvent(new KeyboardEvent("keydown", opcoes));
      el.dispatchEvent(new KeyboardEvent("keyup", opcoes));
      if (seguiu && el.form) el.form.requestSubmit();  // formulário comum: o Enter de verdade enviaria
    }
    return {ok: true};
  }

  function descrever(p) {
    const nome = p.rotulo || (p.alvo || {}).texto || (p.alvo || {}).rotulo || "?";
    return {clique: `clicar em "${nome}"`, digitar: `digitar em "${nome}"`, selecionar: `escolher em "${nome}"`,
            tecla: "apertar Enter", ler: `ler "${nome}"`}[p.tipo] || p.tipo;
  }

  function cancelar() { cancelado = true; }

  async function rodar(c) {
    cancelado = false;
    const r = c.rotina || {};
    const valores = c.valores || {};
    if (!(await chrome.permissions.contains({origins: [r.site + "/*"]})))
      throw new Error(`o site ${r.site} não está liberado na extensão (ícone do Claudinho → Liberar este site)`);
    // aba do site já aberta no mesmo endereço: usa como está (recarregar perde o quadro aberto e demora);
    // em outro endereço do site, vai pro início da rotina; sem aba, abre uma
    const semHash = u => (u || "").split("#")[0].replace(/\/$/, "");
    const abas = await chrome.tabs.query({url: r.site + "/*"});
    let aba = abas.find(t => semHash(t.url) === semHash(r.inicio)) || abas[0];
    if (aba && semHash(aba.url) === semHash(r.inicio)) aba = await chrome.tabs.update(aba.id, {active: true});
    else aba = aba ? await chrome.tabs.update(aba.id, {url: r.inicio, active: true})
                   : await chrome.tabs.create({url: r.inicio, active: true});
    await chrome.windows.update(aba.windowId, {focused: true});
    await dormir(500);
    await carregada(aba.id);
    const lidos = [];
    for (const [i, p] of (r.passos || []).entries()) {
      if (cancelado) throw new Error(`parei no passo ${i + 1}: ele mandou parar`);
      const valor = p.variavel && valores[p.variavel] !== undefined ? String(valores[p.variavel]) : (p.valor || "");
      let saida = null;
      for (let tentativa = 0; tentativa < 2 && !saida; tentativa++) {
        try {
          const [res] = await chrome.scripting.executeScript({target: {tabId: aba.id}, func: fazerPasso, args: [p, valor]});
          saida = res && res.result;
        } catch (e) {  // a página trocou bem na hora: espera a nova e tenta de novo
          await dormir(800);
          await carregada(aba.id);
        }
      }
      if (!saida || !saida.ok)
        throw new Error(`parei no passo ${i + 1} (${descrever(p)}): ${saida ? saida.erro : "a página não respondeu"}`);
      if (saida.texto !== undefined) lidos.push({area: p.rotulo || "", texto: saida.texto});
      await dormir(400);
      await carregada(aba.id);
    }
    return {passos: (r.passos || []).length, lidos};
  }

  raiz.rotinasClaudinho = {mensagem, rodar, cancelar};
})(self);
