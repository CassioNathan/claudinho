"""Converte um checkpoint do Piper salvo no Linux pra carregar no Windows com o torch novo.

O checkpoint do Faber (rhasspy/piper-checkpoints) guarda um `pathlib.PosixPath` nos hiperparâmetros: o torch recusa
por segurança no modo seguro (`weights_only=True`), e nem dá pra criar um PosixPath no Windows. Aqui o arquivo é lido
NO MODO SEGURO do próprio torch, que só monta tensores e tipos simples; a única coisa liberada a mais é o caminho,
lido como `PurePosixPath` (que só guarda texto) e gravado de volta como texto. Nada do arquivo vira código.

    python converter_checkpoint.py entrada.ckpt saida.ckpt
"""
import pathlib
import sys

import torch

# os nomes que o pickle usa pro caminho do Linux (Python até 3.12 e 3.13+) → um tipo que só guarda texto
CAMINHOS = [(pathlib.PurePosixPath, nome) for nome in (
    "pathlib.PosixPath", "pathlib.PurePosixPath", "pathlib._local.PosixPath", "pathlib._local.PurePosixPath")]


def sem_caminhos(o):
    if isinstance(o, pathlib.PurePath):
        return str(o)
    if isinstance(o, dict):
        return {k: sem_caminhos(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return type(o)(sem_caminhos(v) for v in o)
    return o


def ler(entrada):
    """O checkpoint lido no modo seguro do torch (weights_only=True), com os caminhos liberados como texto."""
    with torch.serialization.safe_globals(CAMINHOS):
        return torch.load(entrada, map_location="cpu", weights_only=True)


if __name__ == "__main__":
    entrada, saida = sys.argv[1], sys.argv[2]
    torch.save(sem_caminhos(ler(entrada)), saida)
    torch.load(saida, map_location="cpu", weights_only=True)   # conferência: o convertido carrega sem nada liberado
    print("convertido:", saida)
