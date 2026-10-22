"""Content skills: reusable recipes for a kind of post (structure, tone, visuals).

Built-in skills are YAML files in config/skills/; skills people create on the website are stored
in the database. A skill targets one pipeline ("kind"): story videos, short reels, explainer
diagrams, carousels, photos or text images.
"""

import re
from typing import Literal

import yaml
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.config import settings
from app.services.gemini import generate_json
from bot.db.models import Skill
from bot.settings import CONFIG_DIR

SKILLS_DIR = CONFIG_DIR / "skills"
SkillKind = Literal["story", "reel", "explainer", "carousel", "photo", "image"]


class SkillSpec(BaseModel):
    id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{1,58}$")
    name: str = Field(max_length=60)
    description: str = Field(max_length=300)
    kind: SkillKind
    instructions: str = Field(max_length=4000)
    visual_guidance: str = Field(default="", max_length=1500)
    default_seconds: int = Field(default=60, ge=20, le=120)
    voice: str | None = None
    builtin: bool = False


class GeneratedSkill(BaseModel):
    """What the model fills in when it designs a new skill (no defaults: response schema)."""

    name: str = Field(max_length=60, description="Short, friendly name, 2-4 words.")
    description: str = Field(max_length=300, description="One sentence shown to users.")
    kind: SkillKind
    instructions: str = Field(
        max_length=4000,
        description="Concrete writing guidance: structure, beats, pacing, tone, hook, ending.",
    )
    visual_guidance: str = Field(
        max_length=1500, description="How the visuals should look and move; empty for text-only."
    )
    default_seconds: int = Field(ge=20, le=120)


class SkillError(Exception):
    pass


def builtin_skills() -> list[SkillSpec]:
    skills = []
    for path in sorted(SKILLS_DIR.glob("*.yaml")):
        data = yaml.safe_load(path.read_text())
        skills.append(SkillSpec.model_validate({**data, "builtin": True}))
    return skills


def list_skills(session: Session) -> list[SkillSpec]:
    custom = [SkillSpec.model_validate(row.spec) for row in session.query(Skill).all()]
    return [*builtin_skills(), *sorted(custom, key=lambda s: s.name.lower())]


def get_skill(session: Session, skill_id: str | None) -> SkillSpec | None:
    if not skill_id:
        return None
    for skill in builtin_skills():
        if skill.id == skill_id:
            return skill
    row = session.get(Skill, skill_id)
    if row is None:
        raise SkillError("That skill no longer exists.")
    return SkillSpec.model_validate(row.spec)


def create_skill(session: Session, description: str) -> SkillSpec:
    """Design a new skill from a plain-language description and save it."""
    generated = generate_json(
        settings.gemini_model,
        f"Design a content skill for this request: {description!r}",
        GeneratedSkill,
        system_instruction=SKILL_DESIGNER,
        temperature=0.6,
    )
    taken = {s.id for s in list_skills(session)}
    base = re.sub(r"[^a-z0-9]+", "-", generated.name.lower()).strip("-")[:50] or "skill"
    skill_id, n = base, 2
    while skill_id in taken:
        skill_id, n = f"{base}-{n}", n + 1
    spec = SkillSpec(id=skill_id, **generated.model_dump())
    session.add(Skill(id=spec.id, spec=spec.model_dump()))
    session.commit()
    return spec


def delete_skill(session: Session, skill_id: str) -> None:
    if any(s.id == skill_id for s in builtin_skills()):
        raise SkillError("Built-in skills can't be deleted.")
    row = session.get(Skill, skill_id)
    if row is None:
        raise SkillError("That skill no longer exists.")
    session.delete(row)
    session.commit()


def skill_prompt(skill: SkillSpec | None) -> str:
    if skill is None:
        return ""
    visual = f"\nVisual guidance: {skill.visual_guidance}" if skill.visual_guidance else ""
    return f"\n\nSKILL: {skill.name}\n{skill.instructions}{visual}"


SKILL_DESIGNER = """You design reusable "skills" for an Instagram content studio. A skill is a \
recipe that tells a writer how to make one kind of post well, for any topic a user gives later.

Pick the kind that fits the request:
- story: a narrated video of 20 seconds to 2 minutes made of many shots (stories of any genre, \
mini-documentaries, recipes, countdowns, travel diaries, history tales, testimonials...)
- reel: a short 20-40 second narrated reel of 3-6 scenes
- explainer: an animated diagram video for processes, cycles and systems
- carousel: swipeable text slides
- photo: one generated photo with an optional headline
- image: one text-led graphic (quote, announcement, myth vs fact)

Write instructions that are specific and practical: the structure or beats, how to hook in the \
first two seconds, pacing, tone, how to end, and what to avoid. Write them for any topic in that \
category, not for one example. Keep them accurate and safe: no invented facts about real people, \
no medical or financial guarantees, nothing hateful or graphic. visual_guidance describes framing, \
lighting, color and motion that suit the category (empty for text-only kinds). default_seconds is \
a sensible length for story videos (20-120)."""
