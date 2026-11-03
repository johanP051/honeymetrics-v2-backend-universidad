#!/usr/bin/env python3
"""Create the local orchestrator state without overwriting existing files."""
import argparse, json
from pathlib import Path

def main():
    p = argparse.ArgumentParser()
    p.add_argument("project", type=Path)
    args = p.parse_args()
    root = args.project / ".agents" / "orchestrator"
    root.mkdir(parents=True, exist_ok=True)
    state = root / "project_state.json"
    if not state.exists():
        state.write_text(json.dumps({"current_gate": "G0", "status": "not_started", "production_promotion": False}, indent=2) + "\n", encoding="utf-8")
    for name in ("phase_reports", "decisions", "generated_prompts"):
        (root / name).mkdir(exist_ok=True)
    print(root)

if __name__ == "__main__":
    main()
