// O botão da extensão: liberar o site da aba, gravar uma rotina nele e salvar no Claudinho.
const caixa = document.getElementById("conteudo");
const pedir = msg => chrome.runtime.sendMessage(msg);

function descrever(p) {
  const nome = p.rotulo || (p.alvo || {}).texto || (p.alvo || {}).rotulo || "?";
  if (p.tipo === "digitar") return `digitar "${p.valor}" em ${nome}`;
  return {clique: `clicar em ${nome}`, selecionar: `escolher "${p.valor}" em ${nome}`, tecla: "apertar Enter",
          ler: `📖 ler ${nome}`}[p.tipo] || p.tipo;
}

function html(texto) { const d = document.createElement("div"); d.textContent = texto; return d.innerHTML; }

async function montar() {
  const [aba] = await chrome.tabs.query({active: true, currentWindow: true});
  let origem = null;
  try { const u = new URL(aba.url); if (/^https?:$/.test(u.protocol)) origem = u.origin; } catch (e) { /* página interna */ }
  document.getElementById("site").textContent = origem || "";
  if (!origem) {
    caixa.innerHTML = "<p>Abra o site onde quer gravar a rotina e clique aqui de novo.</p>";
    return;
  }
  const g = await pedir({tipo: "rotina_estado"});
  if (g && g.tabId !== aba.id) {
    caixa.innerHTML = `<p class="gravando">● Gravando em outra aba (${html(g.origem)}).</p>` +
      `<button id="cancelar">Cancelar aquela gravação</button>`;
    document.getElementById("cancelar").onclick = async () => { await pedir({tipo: "rotina_terminar"}); montar(); };
    return;
  }
  if (g) {
    const ultimos = g.passos.slice(-8);
    caixa.innerHTML = `<p class="gravando">● Gravando: ${g.passos.length} passo${g.passos.length === 1 ? "" : "s"}</p>` +
      (ultimos.length ? `<ol start="${g.passos.length - ultimos.length + 1}">` +
        ultimos.map(p => `<li>${html(descrever(p))}</li>`).join("") + "</ol>" : "<p>Faça o caminho no site: cada clique e o que você digitar entra.</p>") +
      `<button id="ler">📖 Marcar área pra ler</button>` +
      `<button id="pagina">📄 Ler a página toda</button>` +
      `<input id="nome" placeholder="nome da rotina (ex.: ler meu kanban)" maxlength="60">` +
      `<button class="forte" id="salvar">Salvar rotina</button>` +
      `<button class="fraco" id="cancelar">Cancelar</button><p class="erro" id="erro"></p>`;
    document.getElementById("ler").onclick = async () => { await pedir({tipo: "rotina_ler"}); window.close(); };
    document.getElementById("pagina").onclick = async () => { await pedir({tipo: "rotina_ler_pagina"}); montar(); };
    document.getElementById("cancelar").onclick = async () => { await pedir({tipo: "rotina_terminar"}); montar(); };
    document.getElementById("salvar").onclick = async () => {
      const nome = document.getElementById("nome").value.trim();
      if (!nome) { document.getElementById("erro").textContent = "Dê um nome pra rotina."; return; }
      const r = await pedir({tipo: "rotina_terminar", nome});
      if (r && r.ok) caixa.innerHTML = `<p>✓ Rotina <b>${html(nome)}</b> salva no Claudinho. Peça no chat: "${html(nome)}".</p>`;
      else document.getElementById("erro").textContent = (r && r.erro) || "não deu pra salvar";
    };
    return;
  }
  const liberado = await chrome.permissions.contains({origins: [origem + "/*"]});
  if (!liberado) {
    caixa.innerHTML = "<p>O Claudinho ainda não mexe neste site. Liberando, você pode gravar rotinas aqui e ele " +
      "repete quando você pedir (só o que você gravar).</p><button class='forte' id='liberar'>Liberar este site</button>";
    document.getElementById("liberar").onclick = async () => {
      await chrome.permissions.request({origins: [origem + "/*"]});
      montar();
    };
    return;
  }
  caixa.innerHTML = "<p>Site liberado ✓. Grave o caminho que o Claudinho deve repetir: cliques, o que digitar e as " +
    "áreas pra ler (ex.: o quadro do kanban).</p><button class='forte' id='gravar'>⏺ Gravar rotina</button>" +
    "<button class='fraco' id='tirar'>Tirar a liberação deste site</button>";
  document.getElementById("gravar").onclick = async () => {
    const r = await pedir({tipo: "rotina_comecar", tabId: aba.id});
    if (r && r.ok) window.close(); else caixa.insertAdjacentHTML("beforeend", `<p class="erro">${html((r && r.erro) || "não deu")}</p>`);
  };
  document.getElementById("tirar").onclick = async () => {
    await chrome.permissions.remove({origins: [origem + "/*"]});
    montar();
  };
}
montar();
