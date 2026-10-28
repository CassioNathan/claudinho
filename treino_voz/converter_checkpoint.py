"""Converte um checkpoint do Piper salvo no Linux pra carregar no Windows com o torch novo (weights_only=True).

O checkpoint do Faber (rhasspy/piper-checkpoints) guarda um `pathlib.PosixPath` nos hiperparâmetros, que o torch
recusa por segurança e que nem dá pra criar no Windows. Em vez de liberar tudo (`weights_only=False` roda código do
arquivo), o arquivo é lido por um leitor restrito: só tensores e tipos simples; o caminho vira texto.

    python converter_checkpoint.py entrada.ckpt saida.ckpt
"""
import pathlib
import pickle
import sys
import types

import torch

PERMITIDOS = ("torch", "collections", "numpy", "_codecs", "lightning", "pytorch_lightning", "piper")
PERMITIDOS_BUILTINS = {"set", "frozenset", "dict", "list", "tuple", "int", "float", "str", "bool", "bytes", "slice",
                       "complex", "bytearray", "range", "object", "getattr", "type"}


class Leitor(pickle.Unpickler):
    def find_class(self, modulo, nome):
        if modulo == "pathlib" and nome in ("PosixPath", "PurePosixPath", "WindowsPath", "PureWindowsPath"):
            return pathlib.PurePosixPath
        if modulo == "builtins" and nome in PERMITIDOS_BUILTINS:
            return super().find_class(modulo, nome)
        if modulo.split(".")[0] in PERMITIDOS:
            return super().find_class(modulo, nome)
        raise pickle.UnpicklingError(f"bloqueado: {modulo}.{nome}")


# o torch.load pede um "módulo pickle": este é o do Python com o leitor restrito no lugar do padrão
leitor_seguro = types.ModuleType("leitor_seguro")
leitor_seguro.Unpickler = Leitor
leitor_seguro.load = lambda f, **kw: Leitor(f, **kw).load()
leitor_seguro.UnpicklingError = pickle.UnpicklingError
leitor_seguro.dumps, leitor_seguro.loads = pickle.dumps, pickle.loads


def sem_caminhos(o):
    if isinstance(o, pathlib.PurePath):
        return str(o)
    if isinstance(o, dict):
        return {k: sem_caminhos(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return type(o)(sem_caminhos(v) for v in o)
    return o


if __name__ == "__main__":
    entrada, saida = sys.argv[1], sys.argv[2]
    ckpt = torch.load(entrada, map_location="cpu", weights_only=False, pickle_module=leitor_seguro)
    torch.save(sem_caminhos(ckpt), saida)
    torch.load(saida, map_location="cpu", weights_only=True)   # conferência: agora carrega no modo seguro
    print("convertido:", saida)
