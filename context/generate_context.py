#!/usr/bin/env python3
"""Build a bounded, sanitized context package outside the repository."""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

EXTENSIONS = {
    ".py", ".pyi", ".jsx", ".tsx", ".js", ".ts", ".html", ".css", ".scss",
    ".yml", ".yaml", ".json", ".jsonc", ".md", ".sql", ".sh", ".toml", ".ini",
}
IGNORED_DIRS = {
    ".git", "node_modules", "dist", "build", ".venv", "venv", "env", "__pycache__",
    ".pytest_cache", ".mypy_cache", ".ruff_cache", "coverage", "htmlcov", ".idea",
    ".vscode", ".wrangler", "vendor", "media", "static_collected", "volumes", "tmp",
    ".engram", "reports", "data", "datasets",
}
CRITICAL_NAMES = {
    ".dockerignore", ".env.example", ".gitignore", "nginx.conf", "wrangler.json",
    "wrangler.jsonc", "package.json", "vite.config.js", "vite.config.ts",
    "requirements.txt", "pyproject.toml", "AGENTS.md", "CLAUDE.md", "Dockerfile",
}
SECRET_PATTERNS = [
    (re.compile(r"-----BEGIN [^-]+ PRIVATE KEY-----.*?-----END [^-]+ PRIVATE KEY-----", re.I | re.S), "[REDACTED_PRIVATE_KEY]"),
    (re.compile(r"(?i)(bearer\s+)[A-Za-z0-9._~+/=-]{16,}"), r"\1[REDACTED]"),
    (re.compile(r"(?i)https?://[^\s/@]+:[^\s/@]+@"), "[REDACTED_URL_CREDENTIALS]@"),
    (re.compile(r'''(?i)(["']?(?:password|passwd|secret|token|api[_-]?key|access[_-]?key|private[_-]?key)["']?\s*[:=]\s*["']?)([^\s,"'}]+)'''), r"\1[REDACTED]"),
    (re.compile(r"\beyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9._-]{10,}\.[A-Za-z0-9._-]{10,}\b"), "[REDACTED_JWT]"),
    (re.compile(r"\b(?:ghp|github_pat|sk|xox[baprs])_[A-Za-z0-9_-]{12,}\b"), "[REDACTED_TOKEN]"),
    (re.compile(r"(?i)(?:Admin123!|Temporal2026\*Clave)"), "[REDACTED_PASSWORD]"),
]

def git_value(root: Path, *args: str) -> str:
    try:
        return subprocess.check_output(["git", "-C", str(root), *args], text=True, stderr=subprocess.DEVNULL).strip() or "unknown"
    except (OSError, subprocess.SubprocessError):
        return "unknown"

def sanitize(text: str) -> tuple[str, int]:
    text, count = re.subn(r"(?im)^.*(?:password|contraseña|credential|credencial).*$", "[REDACTED_CREDENTIAL_LINE]", text)
    for pattern, replacement in SECRET_PATTERNS:
        text, found = pattern.subn(replacement, text)
        count += found
    return text, count

def ignored(path: Path, root: Path) -> bool:
    relative = path.relative_to(root)
    if any(part in IGNORED_DIRS for part in relative.parts):
        return True
    name, lower = path.name, path.name.lower()
    if name == ".cloudflared_token" or lower == ".env" or (lower.startswith(".env.") and lower != ".env.example"):
        return True
    if name in {"package-lock.json", "yarn.lock", "pnpm-lock.yaml", "poetry.lock", "Pipfile.lock"}:
        return True
    if name.startswith(("contexto_", "contexto-web-")):
        return True
    if lower.endswith((".parquet", ".joblib", ".sqlite", ".db", ".dump", ".sql.gz")):
        return True
    return False

def critical(path: Path) -> bool:
    name, lower = path.name, path.name.lower()
    return (
        name in CRITICAL_NAMES or lower.startswith(("dockerfile", "docker-compose", "nginx"))
        or path.parts[-2:] == (".github", "workflows") or path.parent.name == ".github"
    )

def collect(root: Path, max_file_chars: int) -> list[Path]:
    result = []
    for directory, directories, filenames in os.walk(root, followlinks=False):
        current = Path(directory)
        directories[:] = [name for name in directories if not ignored(current / name, root)]
        for filename in filenames:
            path = current / filename
            if ignored(path, root) or not (critical(path) or path.suffix.lower() in EXTENSIONS):
                continue
            try:
                if not path.is_symlink() and path.stat().st_size <= max_file_chars:
                    result.append(path)
            except OSError:
                pass
    return sorted(set(result), key=lambda item: item.relative_to(root).as_posix())

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, help="Repository root; inferred from this script when omitted.")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--manifest", action="store_true", help="Also write a sidecar checksum manifest.")
    parser.add_argument("--overwrite", action="store_true", help="Allow replacing an explicitly selected output.")
    parser.add_argument("--max-chars", type=int, default=900_000)
    parser.add_argument("--max-file-chars", type=int, default=80_000)
    args = parser.parse_args()
    root = (args.root or Path(__file__).resolve().parents[1]).resolve()
    if args.output:
        output = args.output.resolve()
        if output.exists() and not args.overwrite:
            raise SystemExit(f"Output already exists: {output}. Use --overwrite only when intentional.")
    else:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        output = (Path("/tmp") / "honeymetrics_context" / root.name / f"contexto_{root.name}_{stamp}.txt").resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    chunks = [
        "# HONEYMETRICS — CONTEXTO SANITIZADO PARA AUDITORÍA",
        f"# Repositorio: {root.name}",
        f"# Rama: {git_value(root, 'branch', '--show-current')}",
        f"# Commit: {git_value(root, 'rev-parse', '--short', 'HEAD')}",
        "# Evidencia: generado fuera del repositorio; secretos y artefactos pesados fueron excluidos.",
        "",
    ]
    used, included, skipped, redactions = sum(map(len, chunks)), [], [], 0
    for path in collect(root, args.max_file_chars):
        relative = path.relative_to(root).as_posix()
        try:
            clean, count = sanitize(path.read_text(encoding="utf-8", errors="replace"))
        except OSError:
            continue
        block = f"\n{'=' * 80}\n## FILE: {relative}\n{'=' * 80}\n{clean}\n"
        if used + len(block) > args.max_chars:
            skipped.append(relative)
            continue
        chunks.append(block)
        used += len(block)
        included.append(relative)
        redactions += count
    content = "".join(chunks)
    content += f"\n{'=' * 80}\n## GENERATION SUMMARY\n{'=' * 80}\n"
    content += f"Included files: {len(included)}\nSkipped by total budget: {len(skipped)}\nRedaction replacements: {redactions}\nOutput characters: {len(content)}\n"
    if skipped:
        content += "Skipped paths:\n" + "\n".join(f"- {item}" for item in skipped[:100]) + "\n"
    output.write_text(content, encoding="utf-8")
    print(f"Generated {output} ({len(content):,} chars, {len(included)} files)")
    if args.manifest:
        digest = hashlib.sha256(content.encode()).hexdigest()
        manifest = output.with_suffix(".manifest.txt")
        manifest.write_text(f"output={output}\nsha256={digest}\nchars={len(content)}\nincluded={len(included)}\nskipped_by_budget={len(skipped)}\nredactions={redactions}\n", encoding="utf-8")
        print(f"Manifest: {manifest}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
