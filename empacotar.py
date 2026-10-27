"""Gera a release do Claudinho pra Windows: dist/Claudinho/ (PyInstaller, em pasta) e o zip em release/.

    python empacotar.py

Quem baixa: descompacta onde quiser e abre o Claudinho.exe (não precisa de Python). Pra tirar, é só apagar a pasta
(e, se quiser, o ~/.claudinho com os dados dele).
"""
import subprocess
import sys
import zipfile
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
import sistema  # noqa: E402


def icone():
    """O ícone do exe é o mesmo da bandeja (desenhado pelo próprio Claudinho)."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("claudinho_app", AQUI / "claudinho.pyw")
    app = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(app)
    (AQUI / "build").mkdir(exist_ok=True)
    app.desenhar_icone(256).save(AQUI / "build/claudinho.ico", sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (256, 256)])


def main():
    icone()
    subprocess.run([sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "claudinho.spec"], cwd=AQUI, check=True)
    pasta = AQUI / "dist" / "Claudinho"
    (pasta / "LEIA-ME.txt").write_text(
        f"Claudinho {sistema.VERSAO}\r\n\r\n"
        "1. Deixe esta pasta onde quiser (ex.: Documentos\\Claudinho) e abra o Claudinho.exe.\r\n"
        "2. Na primeira vez ele abre o painel: conte quem você é em \"Meu Mestre\" e, se quiser, ligue\r\n"
        "   \"abrir junto com o Windows\" e o aviso do Claude Code.\r\n"
        "3. O chat e as piadas olhando a tela usam o Claude Code (instale e faça login com `claude`).\r\n"
        "   Sem ele, o resto funciona: banco de frases, música, esquetes, skins.\r\n\r\n"
        "Pra desinstalar: feche o Claudinho (botão direito > Sair), desligue as opções em Sistema no painel\r\n"
        "e apague esta pasta. Os dados dele ficam em %USERPROFILE%\\.claudinho.\r\n",
        encoding="utf-8")
    (AQUI / "release").mkdir(exist_ok=True)
    destino = AQUI / "release" / f"Claudinho-{sistema.VERSAO}-windows.zip"
    destino.unlink(missing_ok=True)
    with zipfile.ZipFile(destino, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for arquivo in pasta.rglob("*"):
            z.write(arquivo, Path("Claudinho") / arquivo.relative_to(pasta))
    tamanho = sum(f.stat().st_size for f in pasta.rglob("*") if f.is_file())
    print(f"\npasta: {pasta} ({tamanho / 1e6:.0f} MB)\nzip:   {destino} ({destino.stat().st_size / 1e6:.0f} MB)")


if __name__ == "__main__":
    main()
