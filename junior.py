"""Os olhos do modo Júnior: lê o texto da janela em foco com o OCR do próprio Windows (local, de graça, nada sai do PC)
e percebe quando aparece um erro novo ou quando você está empacado no mesmo erro há um tempo. Só aí ele chama a IA.

Só lê: não clica nem digita nada. Respeita a faixa nos olhos, os programas bloqueados no painel e pula as janelas do
próprio Claudinho. O texto lido é dado da tela, nunca ordem."""
import asyncio
import io
import re
import threading
import time

from PIL import ImageGrab

import janelas
import programas
import tela

INTERVALO = 15            # de quanto em quanto tempo ele lê a janela em foco (s)
EMPACADO = 8 * 60         # o mesmo erro na tela por esse tempo: você deve estar empacado
LARGURA_IA = 1568         # a janela vai nítida pra IA, só encolhe se passar disso
# palavras de erro (português e inglês) que valem a pena olhar; o resto da tela ele ignora
ERRO = re.compile(r"\w*exception|\w*error\b|\berro\b|failed|falhou|\bfalha\b|traceback|\bfatal\b|cannot |"
                  r"não foi possível|undefined|not found|não encontrad|build failed|tests? failed|assertion|"
                  r"permission denied|acesso negado|connection refused|timed? ?out|\bpanic\b|segmentation fault|"
                  r"\bnull ?pointer|stack ?trace|\bwarning\b", re.I)


def _motor():
    from winrt.windows.media.ocr import OcrEngine
    return OcrEngine.try_create_from_user_profile_languages()


async def _ler(png):
    from winrt.windows.graphics.imaging import BitmapDecoder
    from winrt.windows.storage.streams import DataWriter, InMemoryRandomAccessStream
    fluxo = InMemoryRandomAccessStream()
    escritor = DataWriter(fluxo)
    escritor.write_bytes(png)
    await escritor.store_async()
    escritor.detach_stream()
    fluxo.seek(0)
    imagem = await (await BitmapDecoder.create_async(fluxo)).get_software_bitmap_async()
    resultado = await _motor().recognize_async(imagem)
    return "\n".join(linha.text for linha in resultado.lines)


def ler(img):
    """O texto da imagem pelo OCR do Windows ("" se não der: Windows sem o pacote de idioma, por exemplo)."""
    buffer = io.BytesIO()
    img.convert("RGB").save(buffer, "PNG")
    try:
        return asyncio.run(_ler(buffer.getvalue()))
    except Exception:
        return ""


def erros(texto):
    """As linhas do texto que parecem erro (no máximo 6, sem repetir)."""
    achadas = []
    for linha in texto.splitlines():
        linha = linha.strip()
        if 6 <= len(linha) and ERRO.search(linha) and linha not in achadas:
            achadas.append(linha[:200])
    return achadas[:6]


def chave(linha):
    """O mesmo erro com outro número de linha, hora ou id continua sendo o mesmo erro."""
    return re.sub(r"\d+", "#", linha.lower())[:120]


def foto():
    """A janela em foco, nítida: {"janela", "nome", "imagem", "texto", "erros"} ou None (sem janela, do próprio
    Claudinho ou de programa bloqueado no painel)."""
    janela = tela.janela_da_frente()
    if (not janela or janela["exe"] in janelas.IGNORAR or programas.exe_bloqueado(janela["exe"])
            or janela["titulo"].startswith("Claudinho ·")):   # o painel e a conversa dele abrem no Edge
        return None
    esq, topo, dir_, base = janela["rect"]
    mon = tela.monitor_de((esq + dir_) / 2, (topo + base) / 2)
    caixa = (max(esq, mon[0]), max(topo, mon[1]), min(dir_, mon[2]), min(base, mon[3]))
    if caixa[2] - caixa[0] < 200 or caixa[3] - caixa[1] < 120:
        return None
    img = ImageGrab.grab(bbox=caixa, all_screens=True)
    texto = ler(img)
    if img.width > LARGURA_IA:
        img = img.resize((LARGURA_IA, round(img.height * LARGURA_IA / img.width)))
    return {"janela": janela, "nome": f"{janela['titulo'] or janela['exe']} ({janela['exe']})", "imagem": img,
            "texto": texto, "erros": erros(texto)}


class Vigia:
    """Lê a janela em foco a cada INTERVALO s enquanto `pode()` deixar e chama `avisar(evento)` quando aparece um
    erro novo (motivo "erro") ou quando o mesmo erro fica na tela por EMPACADO s (motivo "empacado")."""

    def __init__(self, pode, avisar):
        self.pode, self.avisar = pode, avisar
        self.vistos = {}       # chave do erro -> quando apareceu pela primeira vez (na sessão)
        self.na_tela = {}      # chave -> desde quando está na tela sem sair
        self.avisados = set()  # empacado já avisado (uma vez por erro)
        threading.Thread(target=self.rodar, daemon=True).start()

    def rodar(self):
        while True:
            time.sleep(INTERVALO)
            try:
                if self.pode():
                    self.olhar()
            except Exception:
                pass

    def olhar(self):
        f = foto()
        if not f:
            return
        agora = time.time()
        atuais = {chave(e): e for e in f["erros"]}
        self.na_tela = {c: self.na_tela.get(c, agora) for c in atuais}
        novos = [e for c, e in atuais.items() if c not in self.vistos]
        for c in atuais:
            self.vistos.setdefault(c, agora)
        if len(self.vistos) > 500:   # sessão longa: esquece os mais velhos
            self.vistos = dict(sorted(self.vistos.items(), key=lambda kv: kv[1])[-300:])
        parados = [atuais[c] for c, desde in self.na_tela.items() if agora - desde >= EMPACADO and c not in self.avisados]
        if novos:
            self.avisar(dict(f, motivo="erro", erros=novos))
        elif parados:
            self.avisados.update(chave(e) for e in parados)
            self.avisar(dict(f, motivo="empacado", erros=parados, minutos=int(EMPACADO / 60)))
