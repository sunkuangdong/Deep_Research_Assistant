from typing import Iterable

from src.tools.lib.prompts import (
    SKILL_WEB_RESEARCH_PROMPT,
    SKILL_REPORT_WRITER_PROMPT,
)

VALID_SKILLS = {"web-research", "report-writer"}

DEFAULT_ENABLED_SKILLS = ("web-research", "report-writer")

SKILL_PROMPT_MAP = {
    "web-research": SKILL_WEB_RESEARCH_PROMPT,
    "report-writer": SKILL_REPORT_WRITER_PROMPT,
}

def resolve_enabled_skills(
    requested_skills: Iterable[str] | None,
    use_defaults: bool = True,
) -> list[str]:
    base = list(requested_skills or [])
    if not base and use_defaults:
        base = list(DEFAULT_ENABLED_SKILLS)

    seen = set()
    result = []
    for skill in base:
        name = (skill or "").strip()
        if not name or name not in VALID_SKILLS:
            continue
        if name in seen:
            continue
        seen.add(name)
        result.append(name)
    return result

def build_skills_guard(enabled_skills: Iterable[str]) -> str:
    prompts = []

    for skill in enabled_skills:
        p = SKILL_PROMPT_MAP.get(skill)
        if p:
            prompts.append(p)
    if not prompts:
        return ""
        
    return "[Skills]\n" + "\n\n".join(prompts)
