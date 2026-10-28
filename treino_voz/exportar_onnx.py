"""Exporta o checkpoint do Piper pra ONNX no torch novo: o exportador novo (dynamo) não aguenta o modelo, então
força o exportador clássico (dynamo=False). Uso: python exportar_onnx.py --checkpoint x.ckpt --output-file voz.onnx"""
import runpy
import sys

import torch

_exportar = torch.onnx.export
torch.onnx.export = lambda *a, **k: _exportar(*a, **{**k, "dynamo": False})
sys.argv[0] = "piper.train.export_onnx"
runpy.run_module("piper.train.export_onnx", run_name="__main__")
