"""Validate the repository-local used-oil skill and routing rules."""

from __future__ import annotations

from pathlib import Path
import re
import subprocess
import sys


NAME = "used-oil-soap-pilot"
HEADINGS = [f"## {index}. {title}" for index, title in enumerate((
    "Назначение skill",
    "Условия автоматического запуска",
    "Когда skill не использовать",
    "Необходимые входные данные",
    "Какие файлы проекта сначала изучать",
    "Пошаговый рабочий процесс",
    "Команды и инструменты",
    "Обработка ошибок и откат",
    "Обязательные проверки",
    "Критерии готовности",
    "Формат итогового отчёта пользователю",
    "Правила накопления подтверждённого опыта",
    "Запрещённые действия",
), start=1)]


def main() -> int:
    script = Path(__file__).resolve()
    skill = script.parents[1]
    root = script.parents[4]
    errors: list[str] = []
    required = [
        skill / "SKILL.md",
        skill / "agents" / "openai.yaml",
        skill / "references" / "lessons-learned.md",
        skill / "references" / "activation-cases.md",
        skill / "references" / "source-index.md",
        skill / "assets" / "used-oil-batch.template.json",
        skill / "scripts" / "prepare_used_oil_batch.py",
        root / "AGENTS.md",
    ]
    for path in required:
        if not path.is_file():
            errors.append(f"missing file: {path.relative_to(root)}")
    if errors:
        return report(errors)

    body = (skill / "SKILL.md").read_text(encoding="utf-8")
    agents = (root / "AGENTS.md").read_text(encoding="utf-8")
    meta = re.match(r"\A---\n(.*?)\n---\n", body, re.DOTALL)
    if not meta or f"name: {NAME}" not in meta.group(1):
        errors.append("frontmatter name is missing or does not match the folder")
    if not meta or "description:" not in meta.group(1) or "TODO" in meta.group(1):
        errors.append("frontmatter description is missing or unfinished")
    for heading in HEADINGS:
        if heading not in body:
            errors.append(f"missing heading: {heading}")

    for phrase in (f"${NAME}", "до внесения изменений", "другими словами", "не применять", "провер"):
        if phrase.lower() not in agents.lower():
            errors.append(f"AGENTS.md lacks routing phrase: {phrase}")
    if "$soap-data-catalog" not in agents or "оба" not in agents.lower():
        errors.append("AGENTS.md does not explain dual-skill routing")

    cases = (skill / "references" / "activation-cases.md").read_text(encoding="utf-8")
    if "## Должен активироваться" not in cases or "## Не должен активироваться" not in cases:
        errors.append("activation cases lack positive or negative section")
    if len(re.findall(r"^\d+\.", cases, re.MULTILINE)) < 4:
        errors.append("activation cases do not cover enough simulated prompts")

    prepare = skill / "scripts" / "prepare_used_oil_batch.py"
    run = subprocess.run([sys.executable, str(prepare), "--self-test"], capture_output=True, text=True)
    if run.returncode != 0:
        errors.append(f"prepare script self-test failed: {run.stderr.strip()}")
    blocked = subprocess.run(
        [sys.executable, str(prepare), str(skill / "assets" / "used-oil-batch.template.json")],
        capture_output=True,
        text=True,
    )
    if blocked.returncode == 0 or "BLOCKED:" not in blocked.stderr:
        errors.append("placeholder template is not blocked")

    ui = (skill / "agents" / "openai.yaml").read_text(encoding="utf-8")
    if f"${NAME}" not in ui:
        errors.append("agents/openai.yaml does not invoke the skill")
    return report(errors)


def report(errors: list[str]) -> int:
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print("OK: used-oil skill metadata, routing, cases, converter, and fail-closed template are valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
