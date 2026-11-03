#!/usr/bin/env python3
"""Render a deterministic delegation prompt from a phase contract JSON."""
import argparse, json
from pathlib import Path

def main():
    p = argparse.ArgumentParser()
    p.add_argument("contract", type=Path)
    args = p.parse_args()
    c = json.loads(args.contract.read_text(encoding="utf-8"))
    sections = ["CONTEXTO", "OBJETIVO", "ALCANCE", "NO HACER", "ARCHIVOS PERMITIDOS", "ARCHIVOS PROTEGIDOS", "CRITERIOS DE ACEPTACIÓN", "PRUEBAS", "FORMATO DE ENTREGA", "CONDICIONES DE DETENCIÓN"]
    for key in sections:
        value = c.get(key.lower().replace(" ", "_"), c.get(key, ""))
        print(f"\n## {key}\n{value}")

if __name__ == "__main__":
    main()
