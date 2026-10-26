// Gravador de rotina: enquanto você grava, anota cada clique, o que você digita e as áreas que você marca pra ler.
// Vai pra página pelo fundo da extensão (só nos sites que você liberou) e é posto de novo a cada página nova.
// Campo de senha nunca é anotado.
(() => {
  if (window.__gravadorClaudinho) { window.__gravadorClaudinho(); return; }  // já está na página: só volta a gravar
  let parado = false, modoLer = false, ultimoEnter = 0;

  const faixa = document.createElement("div");
  faixa.style.cssText = "position:fixed;top:8px;left:50%;transform:translateX(-50%);z-index:2147483647;" +
    "background:#c0392b;color:#fff;font:600 13px Segoe UI,sans-serif;padding:6px 14px;border-radius:999px;" +
    "box-shadow:0 2px 10px #0006;pointer-events:none";
  const textoNormal = "● Gravando rotina do Claudinho: clique no ícone da extensão pra salvar";
  faixa.textContent = textoNormal;
  document.documentElement.appendChild(faixa);

  const escapar = s => (window.CSS && CSS.escape) ? CSS.escape(s) : s.replace(/[^\w-]/g, "\\$&");
  const idBom = id => id && !/\d{3,}|^\d|:/.test(id);
  const unico = s => { try { return document.querySelectorAll(s).length === 1; } catch (e) { return false; } };

  // o jeito mais estável de achar o elemento de novo: id, atributos de teste/nome, e por último o caminho
  function seletor(el) {
    if (idBom(el.id) && unico("#" + escapar(el.id))) return "#" + escapar(el.id);
    const tag = el.tagName.toLowerCase();
    for (const at of ["data-testid", "data-test", "data-cy", "name", "aria-label", "placeholder"]) {
      const v = el.getAttribute(at);
      if (v) {
        const s = `${tag}[${at}="${v.replace(/"/g, '\\"')}"]`;
        if (unico(s)) return s;
      }
    }
    const partes = [];
    let e = el;
    while (e && e.nodeType === 1 && e !== document.body) {
      if (idBom(e.id)) { partes.unshift("#" + escapar(e.id)); break; }
      const irmaos = [...e.parentNode.children].filter(x => x.tagName === e.tagName);
      partes.unshift(e.tagName.toLowerCase() + (irmaos.length > 1 ? `:nth-of-type(${irmaos.indexOf(e) + 1})` : ""));
      e = e.parentElement;
    }
    return (e === document.body ? "body > " : "") + partes.join(" > ");
  }

  function rotuloDe(el) {
    const lbl = el.labels && el.labels[0] ? el.labels[0].innerText : "";
    return (el.getAttribute("aria-label") || el.getAttribute("placeholder") || lbl || el.getAttribute("name") ||
            el.getAttribute("title") || "").trim().slice(0, 60);
  }

  function alvo(el) {
    const texto = (el.innerText || (el.type === "submit" || el.type === "button" ? el.value : "") || "")
      .replace(/\s+/g, " ").trim().slice(0, 80);
    return {css: seletor(el), texto, tag: el.tagName.toLowerCase(), rotulo: rotuloDe(el)};
  }

  const ehCampo = el => el.matches && el.matches(
    "input:not([type=button]):not([type=submit]):not([type=checkbox]):not([type=radio]):not([type=reset])" +
    ":not([type=image]), textarea, select, [contenteditable=''], [contenteditable=true]");
  const ehSenha = el => el.type === "password" || /senha|password/i.test(el.getAttribute("autocomplete") || "");
  const mandar = passo => { if (!parado) chrome.runtime.sendMessage({tipo: "gravador_passo", passo}).catch(() => {}); };
  const valorDe = el => el.isContentEditable ? el.innerText : el.value;

  function piscar(el) {
    const antes = el.style.outline;
    el.style.outline = "3px solid #2ecc71";
    setTimeout(() => { el.style.outline = antes; }, 900);
  }

  // marcar a área pra ler: o que está sob o mouse fica destacado; ↑ pega a área de fora (o quadro inteiro em vez
  // do título da coluna), ↓ volta; clique escolhe; Esc desiste
  const moldura = document.createElement("div");
  moldura.style.cssText = "position:fixed;z-index:2147483646;pointer-events:none;border:3px solid #2ecc71;" +
    "background:#2ecc7122;border-radius:4px;display:none";
  document.documentElement.appendChild(moldura);
  let marcado = null, caminhoAcima = [];
  function mostrarMoldura() {
    if (!marcado) { moldura.style.display = "none"; return; }
    const r = marcado.getBoundingClientRect();
    Object.assign(moldura.style, {display: "block", left: r.left + "px", top: r.top + "px",
                                  width: r.width + "px", height: r.height + "px"});
    const linhas = (marcado.innerText || "").split("\n").filter(l => l.trim()).length;
    faixa.textContent = `📖 ${linhas} linha${linhas === 1 ? "" : "s"} de texto · ↑ área maior · ↓ menor · clique pra escolher · Esc sai`;
  }
  document.addEventListener("mousemove", e => {
    if (!modoLer || parado) return;
    if (caminhoAcima.length && marcado && marcado.contains(e.target)) return;  // já subiu com ↑: não desfaz ao mexer
    marcado = e.target; caminhoAcima = [];
    mostrarMoldura();
  }, true);
  document.addEventListener("keydown", e => {
    if (!modoLer || parado) return;
    if (e.key === "ArrowUp" && marcado && marcado.parentElement && marcado.parentElement !== document.documentElement) {
      caminhoAcima.push(marcado); marcado = marcado.parentElement;
    } else if (e.key === "ArrowDown" && caminhoAcima.length) {
      marcado = caminhoAcima.pop();
    } else if (e.key === "Escape") {
      modoLer = false; marcado = null; faixa.textContent = textoNormal;
    } else return;
    e.preventDefault(); e.stopPropagation();
    mostrarMoldura();
  }, true);

  document.addEventListener("click", e => {
    if (parado) return;
    if (modoLer) {  // a área que ele deve ler na hora de repetir (ex.: o quadro do kanban)
      e.preventDefault(); e.stopPropagation();
      modoLer = false;
      const el = marcado || e.target;
      marcado = null; caminhoAcima = []; moldura.style.display = "none";
      faixa.textContent = textoNormal;
      piscar(el);
      const inicio = (el.innerText || "").replace(/\s+/g, " ").trim();
      mandar({tipo: "ler", alvo: alvo(el),
              rotulo: rotuloDe(el) || (inicio ? `a área "${inicio.slice(0, 30)}${inicio.length > 30 ? "…" : ""}"` : "a área marcada")});
      return;
    }
    // Enter num campo de formulário faz o navegador "clicar" sozinho no botão de enviar: esse clique não é seu
    if (e.detail === 0 && Date.now() - ultimoEnter < 800) return;
    const el = e.target.closest("a, button, [role=button], [role=menuitem], [role=tab], [role=option], [role=link], " +
                                "[role=checkbox], input, label, summary, select, [onclick], [tabindex]") || e.target;
    if ((ehCampo(el) && el.tagName !== "SELECT") || ehSenha(el)) return;  // clicar pra digitar: o "digitar" anota
    if (el.tagName === "SELECT") return;  // a escolha vem no "change"
    const a = alvo(el);
    mandar({tipo: "clique", alvo: a, rotulo: a.texto || a.rotulo});
  }, true);

  document.addEventListener("change", e => {
    const el = e.target;
    if (parado || !ehCampo(el) || ehSenha(el)) return;
    const a = alvo(el);
    if (el.tagName === "SELECT") mandar({tipo: "selecionar", alvo: a, valor: el.value, rotulo: a.rotulo});
    else mandar({tipo: "digitar", alvo: a, valor: valorDe(el), rotulo: a.rotulo});
  }, true);

  document.addEventListener("keydown", e => {
    const el = e.target;
    if (parado || e.key !== "Enter" || !ehCampo(el) || el.tagName === "TEXTAREA" || ehSenha(el)) return;
    const a = alvo(el);
    ultimoEnter = Date.now();
    mandar({tipo: "digitar", alvo: a, valor: valorDe(el), rotulo: a.rotulo});
    mandar({tipo: "tecla", tecla: "Enter", alvo: a, rotulo: a.rotulo});
  }, true);

  window.__gravadorClaudinho = () => {
    parado = false; modoLer = false;
    faixa.textContent = textoNormal;
    document.documentElement.append(faixa, moldura);
  };

  chrome.runtime.onMessage.addListener(m => {
    if (m.tipo === "gravador_parar") { parado = true; faixa.remove(); moldura.remove(); }
    if (m.tipo === "gravador_ler") { modoLer = true; faixa.textContent = "📖 Passe o mouse na área que o Claudinho deve ler (↑ pega a área de fora)"; }
  });
})();
