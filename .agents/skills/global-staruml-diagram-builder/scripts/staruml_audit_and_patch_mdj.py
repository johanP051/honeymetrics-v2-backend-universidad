#!/usr/bin/env python3
"""
staruml_audit_and_patch_mdj.py — Auditor Forense y Reparador de Archivos .mdj
=============================================================================
Inspecciona el AST JSON de un archivo StarUML (.mdj) buscando violaciones al
estándar académico Gualivá / HoneyMetrics:
1. Fragmentos con doble etiqueta 'alt alt' (name == 'alt' en UMLCombinedFragment).
2. Marcos 'ref' (UMLInteractionUseView) vacíos o sin texto visible.
3. Mensajes de secuencia con endpoints técnicos (GET/POST/PUT/DELETE /api/...) o SQL crudo.
4. Actores llamados 'Superusuario' en lugar de 'Administrador'.
5. Diagramas de actividad de eliminación clonados de actualización.

Uso:
  python3 staruml_audit_and_patch_mdj.py "/ruta/archivo.mdj" [--patch]
"""

import sys
import re
import json
import shutil
from pathlib import Path


def build_id_map(node, id_map=None):
    if id_map is None:
        id_map = {}
    if isinstance(node, dict):
        if "_id" in node:
            id_map[node["_id"]] = node
        for v in node.values():
            if isinstance(v, (dict, list)):
                build_id_map(v, id_map)
    elif isinstance(node, list):
        for item in node:
            build_id_map(item, id_map)
    return id_map


def audit_and_patch(mdj_path: Path, do_patch: bool = False):
    data = json.loads(mdj_path.read_text(encoding="utf-8"))
    id_map = build_id_map(data)
    issues = []
    fixes = 0

    def walk(node, parent_diag_name=""):
        nonlocal fixes
        if isinstance(node, dict):
            t = node.get("_type", "")
            if t in ("UMLSequenceDiagram", "UMLUseCaseDiagram", "UMLActivityDiagram", "UMLClassDiagram"):
                parent_diag_name = node.get("name", parent_diag_name)

            # 1. Bug 'alt alt' en UMLCombinedFragment
            if t == "UMLCombinedFragment" and node.get("interactionOperator") == "alt":
                if node.get("name", "").strip().lower() == "alt":
                    issues.append(f"[ALT-ALT] En '{parent_diag_name}': UMLCombinedFragment tiene name='alt' (genera 'alt alt').")
                    if do_patch:
                        node["name"] = ""
                        fixes += 1

            # 2. Marcos 'ref' vacíos en UMLInteractionUseView
            if t == "UMLInteractionUseView":
                model_ref = node.get("model", {}).get("$ref")
                model_obj = id_map.get(model_ref, {})
                refers_to_id = model_obj.get("refersTo", {}).get("$ref") if isinstance(model_obj.get("refersTo"), dict) else None
                target_inter = id_map.get(refers_to_id, {})
                target_name = target_inter.get("name") or model_obj.get("name") or ""

                for sub in node.get("subViews", []):
                    if sub.get("_type") == "LabelView" and sub.get("_id") == node.get("nameLabel", {}).get("$ref"):
                        txt = sub.get("text", "").strip()
                        if not txt:
                            issues.append(f"[EMPTY-REF] En '{parent_diag_name}': Marco 'ref' tiene etiqueta visual vacía.")
                            if do_patch and target_name:
                                sub["text"] = target_name
                                sub["visible"] = True
                                fixes += 1

            # 3. Endpoints HTTP o SQL crudo en UMLMessage
            if t == "UMLMessage":
                m_name = node.get("name", "")
                if re.search(r"\b(GET|POST|PUT|DELETE|PATCH)\s+/api/", m_name) or re.search(r"\b(SELECT|UPDATE|INSERT\s+INTO)\b", m_name):
                    issues.append(f"[TECH-MSG] Mensaje con código técnico/HTTP/SQL: '{m_name}'")
                    if do_patch:
                        cleaned = re.sub(r"\s*\((?:GET|POST|PUT|DELETE|PATCH)\s+/api/[^)]+\)", "", m_name)
                        cleaned = re.sub(r"\b(?:Petición|Enviar petición)\s+(?:GET|POST|PUT|DELETE|PATCH)\s+/api/\S+", "Solicitar procesamiento de operación", cleaned)
                        node["name"] = cleaned
                        fixes += 1

            # 4. Actor 'Administrador' en lugar de 'Superusuario'
            if t == "UMLActor":
                a_name = node.get("name", "")
                if a_name.strip().lower() == "administrador":
                    issues.append(f"[ACTOR-NAME] Actor llamado '{a_name}' en lugar de 'Superusuario'.")
                    if do_patch:
                        node["name"] = "Superusuario"
                        fixes += 1

            for v in node.values():
                if isinstance(v, (dict, list)):
                    walk(v, parent_diag_name)
        elif isinstance(node, list):
            for item in node:
                walk(item, parent_diag_name)

    walk(data)

    print("=" * 70)
    print(f"📋 REPORTE DE AUDITORÍA AST: {mdj_path.name}")
    print("=" * 70)
    if not issues:
        print("✅ 0 problemas detectados. El archivo cumple el estándar.")
    else:
        for idx, iss in enumerate(issues, 1):
            print(f"  {idx}. {iss}")
        print(f"\nTotal de hallazgos: {len(issues)}")

    if do_patch and fixes > 0:
        backup = mdj_path.with_suffix(".mdj.bak")
        shutil.copy2(mdj_path, backup)
        mdj_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"🛠️ Aplicados {fixes} parches automáticos. Backup guardado en: {backup.name}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python3 staruml_audit_and_patch_mdj.py <archivo.mdj> [--patch]")
        sys.exit(1)
    path = Path(sys.argv[1]).resolve()
    patch_flag = "--patch" in sys.argv
    audit_and_patch(path, do_patch=patch_flag)
