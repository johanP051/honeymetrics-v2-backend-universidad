#!/usr/bin/env python3
"""Check that a delegated phase report contains the required evidence headings."""
import argparse
from pathlib import Path

REQUIRED = ("archivos", "comandos", "pruebas", "riesgos", "bloqueadores")
def main():
    p = argparse.ArgumentParser(); p.add_argument("report", type=Path); args = p.parse_args()
    text = args.report.read_text(encoding="utf-8").lower()
    missing = [x for x in REQUIRED if x not in text]
    if missing:
        raise SystemExit("Missing evidence: " + ", ".join(missing))
    print("phase report valid")

if __name__ == "__main__": main()
