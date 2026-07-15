"""Check repository-local skill metadata and run bundled validators."""

from __future__ import annotations

from pathlib import Path
import re
import subprocess
import sys


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    skill_root = root / ".agents" / "skills"
    errors: list[str] = []
    for directory in sorted(path for path in skill_root.iterdir() if path.is_dir()):
        skill_file = directory / "SKILL.md"
        if not skill_file.is_file():
            errors.append(f"{directory.name}: missing SKILL.md")
            continue
        text = skill_file.read_text(encoding="utf-8")
        meta = re.match(r"\A---\n(.*?)\n---\n", text, re.DOTALL)
        if not meta:
            errors.append(f"{directory.name}: invalid frontmatter")
            continue
        if f"name: {directory.name}" not in meta.group(1):
            errors.append(f"{directory.name}: name does not match directory")
        if "description:" not in meta.group(1) or "TODO" in meta.group(1):
            errors.append(f"{directory.name}: description is missing or unfinished")

        validator = directory / "scripts" / "validate_repository_skill.py"
        if validator.is_file():
            run = subprocess.run([sys.executable, str(validator)], capture_output=True, text=True)
            if run.returncode != 0:
                errors.append(f"{directory.name}: {run.stderr.strip() or run.stdout.strip()}")

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print("OK: repository-local skills are valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
