#!/usr/bin/env python3
"""
staruml_export_all.py — Extractor Universal de Diagramas StarUML (.mdj -> SVG + PNG)
====================================================================================
Abre un archivo .mdj en StarUML vía API REST (localhost:12345), descubre todos los
diagramas del árbol JSON, exporta cada uno a SVG (inyectando viewBox para que no se
corte en PDF) y a PNG de alta resolución con nombres de archivo ASCII limpios.

Uso:
  python3 staruml_export_all.py "/ruta/archivo.mdj" "/ruta/carpeta_salida"
"""

import os
import sys
import re
import json
import base64
import unicodedata
import urllib.parse
from pathlib import Path
import requests

BASE_URL = "http://localhost:12345/api"
HEADERS = {"Authorization": "Bearer secret", "Content-Type": "application/json"}

DIAGRAM_TYPES = {
    "UMLSequenceDiagram": "SD",
    "UMLUseCaseDiagram": "CU",
    "UMLActivityDiagram": "AD",
    "UMLClassDiagram": "CD",
    "ERDDiagram": "MER",
}


def sanitize_filename(name: str) -> str:
    """Convierte un nombre de diagrama en un nombre de archivo ASCII limpio sin espacios."""
    nfkd = unicodedata.normalize("NFKD", name)
    ascii_str = "".join([c for c in nfkd if not unicodedata.combining(c)])
    clean = re.sub(r"[^a-zA-Z0-9_-]+", "_", ascii_str).strip("_")
    return clean or "Diagrama"


def find_all_diagrams(node, acc=None):
    """Recorre recursivamente el JSON del .mdj y lista todos los diagramas con vistas."""
    if acc is None:
        acc = []
    if isinstance(node, dict):
        t = node.get("_type")
        if t in DIAGRAM_TYPES:
            views = node.get("ownedViews", [])
            acc.append({
                "_id": node.get("_id"),
                "_type": t,
                "category": DIAGRAM_TYPES[t],
                "name": node.get("name", "Untitled"),
                "views_count": len(views),
            })
        for v in node.values():
            if isinstance(v, (dict, list)):
                find_all_diagrams(v, acc)
    elif isinstance(node, list):
        for item in node:
            find_all_diagrams(item, acc)
    return acc


def ensure_svg_viewbox(svg_text: str) -> str:
    """Inyecta viewBox='0 0 W H' en el tag <svg> si no existe para evitar recortes en PDF."""
    if "viewBox=" in svg_text:
        return svg_text
    m_w = re.search(r'<svg[^>]*\bwidth=["\']([0-9.]+)(?:px)?["\']', svg_text)
    m_h = re.search(r'<svg[^>]*\bheight=["\']([0-9.]+)(?:px)?["\']', svg_text)
    if m_w and m_h:
        w, h = m_w.group(1), m_h.group(1)
        svg_text = re.sub(
            r"<svg\b",
            f'<svg viewBox="0 0 {w} {h}"',
            svg_text,
            count=1,
        )
    return svg_text


def main():
    if len(sys.argv) < 3:
        print("Uso: python3 staruml_export_all.py <ruta_archivo.mdj> <carpeta_salida>")
        sys.exit(1)

    mdj_path = Path(sys.argv[1]).resolve()
    out_dir = Path(sys.argv[2]).resolve()
    svg_dir = out_dir / "svg"
    png_dir = out_dir / "png"
    svg_dir.mkdir(parents=True, exist_ok=True)
    png_dir.mkdir(parents=True, exist_ok=True)

    if not mdj_path.exists():
        print(f"❌ No existe el archivo: {mdj_path}")
        sys.exit(1)

    # 1. Leer el JSON del .mdj directamente para inventariar los diagramas
    mdj_data = json.loads(mdj_path.read_text(encoding="utf-8"))
    diagrams = [d for d in find_all_diagrams(mdj_data) if d["views_count"] > 0]
    print(f"🔍 Detectados {len(diagrams)} diagramas no vacíos en {mdj_path.name}")

    # 2. Abrir el archivo en StarUML vía API REST
    try:
        r_open = requests.post(
            f"{BASE_URL}/project/open",
            json={"path": str(mdj_path)},
            headers=HEADERS,
            timeout=15,
        )
        print(f"📂 Proyecto cargado en StarUML API: HTTP {r_open.status_code}")
    except Exception as e:
        print(f"⚠️ Error al llamar a /project/open (verifica que no haya un modal bloqueando StarUML): {e}")
        sys.exit(1)

    manifest = []
    seen_names = {}

    for d in diagrams:
        d_id = d["_id"]
        raw_name = d["name"]
        base_clean = sanitize_filename(raw_name)
        if base_clean in seen_names:
            seen_names[base_clean] += 1
            clean_name = f"{base_clean}_{seen_names[base_clean]}"
        else:
            seen_names[base_clean] = 1
            clean_name = base_clean

        enc_id = urllib.parse.quote(d_id, safe="")

        # Exportar SVG
        svg_path = svg_dir / f"{clean_name}.svg"
        r_svg = requests.post(
            f"{BASE_URL}/diagrams/{enc_id}/export",
            json={"format": "svg"},
            headers=HEADERS,
            timeout=15,
        ).json()
        svg_content = r_svg.get("data", {}).get("file", {}).get("content", "")
        if svg_content:
            try:
                decoded = base64.b64decode(svg_content).decode("utf-8")
                if "<svg" in decoded:
                    svg_content = decoded
            except Exception:
                pass
            svg_content = ensure_svg_viewbox(svg_content)
            svg_path.write_text(svg_content, encoding="utf-8")

        # Exportar PNG
        png_path = png_dir / f"{clean_name}.png"
        r_png = requests.post(
            f"{BASE_URL}/diagrams/{enc_id}/export",
            json={"format": "png"},
            headers=HEADERS,
            timeout=15,
        ).json()
        png_content = r_png.get("data", {}).get("file", {}).get("content", "")
        if png_content:
            png_path.write_bytes(base64.b64decode(png_content))

        print(f"  ✅ [{d['category']}] {raw_name} -> {clean_name}.png ({png_path.stat().st_size // 1024 if png_path.exists() else 0} KB)")
        manifest.append({
            "id": d_id,
            "category": d["category"],
            "type": d["_type"],
            "original_name": raw_name,
            "clean_name": clean_name,
            "svg_path": str(svg_path),
            "png_path": str(png_path),
        })

    manifest_path = out_dir / "export_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n🎉 Exportación completada: {len(manifest)} diagramas en {out_dir}")
    print(f"📄 Manifiesto guardado en: {manifest_path}")


if __name__ == "__main__":
    main()
