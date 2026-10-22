from typing import Literal

from pydantic import BaseModel, Field

# These models double as Gemini response schemas, so they avoid defaults and keep
# constraints to what the structured-output API understands.


class DraftBase(BaseModel):
    caption: str = Field(max_length=2000, description="Hook line, value, then a call to action.")
    hashtags: list[str] = Field(min_length=5, max_length=15)
    alt_text: str = Field(max_length=500)
    suggested_collaborators: list[str] = Field(
        max_length=3, description="Instagram usernames worth inviting as collaborators."
    )


class Slide(BaseModel):
    kind: Literal["title", "content", "cta"]
    heading: str = Field(max_length=90)
    body: str = Field(max_length=300)


class CarouselDraft(DraftBase):
    slides: list[Slide] = Field(min_length=7, max_length=10)


class ImageDraft(DraftBase):
    headline: str = Field(max_length=90)
    subline: str = Field(max_length=160)
    layout: Literal["bold", "split", "quote"]


class ReelScene(BaseModel):
    voiceover: str = Field(max_length=300)
    on_screen_text: str = Field(max_length=60)
    image_prompt: str = Field(
        max_length=400, description="Vertical background image for this scene; no text in it."
    )
    seconds: float = Field(ge=1, le=12)


class ReelDraft(DraftBase):
    hook: str = Field(max_length=80, description="What is said and shown in the first 1-2 seconds.")
    visual_style: str = Field(max_length=200, description="The look that suits this subject.")
    scenes: list[ReelScene] = Field(min_length=3, max_length=6)
    needs_trending_sound: bool


class PhotoDraft(DraftBase):
    visual_style: str = Field(max_length=200, description="The look that suits this subject.")
    image_prompt: str = Field(max_length=500, description="The photo to generate; no text in it.")
    headline: str = Field(max_length=60, description="Short overlay text, or empty for none.")
    text_position: Literal["top", "bottom", "none"]


class DiagramNode(BaseModel):
    id: str = Field(max_length=24, description="Short lowercase slug, unique.")
    label: str = Field(max_length=28, description="At most 3 words.")
    detail: str = Field(max_length=48, description="Optional clarifier, at most 6 words.")


class DiagramEdge(BaseModel):
    source: str = Field(max_length=24)
    target: str = Field(max_length=24)
    label: str = Field(max_length=20, description="Optional 1-2 word label, or empty.")


class ExplainerStep(BaseModel):
    voiceover: str = Field(max_length=300)
    on_screen_text: str = Field(max_length=60)
    reveal: list[str] = Field(max_length=9, description="Node ids that first appear in this step.")
    focus: list[str] = Field(max_length=9, description="Node ids to highlight in this step.")


class ExplainerDraft(DraftBase):
    hook: str = Field(max_length=80, description="What is said and shown in the first 1-2 seconds.")
    title: str = Field(max_length=48, description="Diagram title, at most 6 words.")
    nodes: list[DiagramNode] = Field(min_length=3, max_length=9)
    edges: list[DiagramEdge] = Field(max_length=14)
    steps: list[ExplainerStep] = Field(min_length=3, max_length=6)


NARRATOR = "Narrator"


class Character(BaseModel):
    name: str = Field(max_length=40)
    gender: Literal["female", "male"] = Field(description="Used to cast the speaking voice.")
    age: Literal["child", "teen", "adult", "elderly"]
    look: str = Field(
        max_length=300,
        description="Fixed visual description reused in every shot: age, build, face, hair, "
        "clothing, distinctive details.",
    )


class StoryBeat(BaseModel):
    name: str = Field(max_length=40)
    summary: str = Field(max_length=300)
    seconds: float = Field(ge=2, le=60)


class StoryPlan(BaseModel):
    title: str = Field(max_length=80)
    logline: str = Field(max_length=240)
    genre: str = Field(max_length=40)
    narration_language: str = Field(
        max_length=10, description="BCP-47 code of the narration language, e.g. en-IN or hi-IN."
    )
    visual_style: str = Field(max_length=240)
    setting: str = Field(max_length=300)
    characters: list[Character] = Field(max_length=4)
    beats: list[StoryBeat] = Field(min_length=3, max_length=8)


Camera = Literal["slow_push_in", "slow_pull_out", "pan_left", "pan_right", "tilt_up", "static"]


class Line(BaseModel):
    speaker: str = Field(description='"Narrator" or the exact name of a character from the plan.')
    text: str = Field(
        description="What is said aloud: one or two natural sentences, no quotation marks, "
        "speaker labels or stage directions."
    )


class StoryShot(BaseModel):
    # No length limits here: long shot lists with per-field limits exceed what the structured
    # output engine accepts; write_story enforces sizes after parsing.
    lines: list[Line] = Field(description="Spoken lines in this shot, in order (usually 1-3).")
    on_screen_text: str = Field(description="Optional short title, at most 6 words, or empty.")
    scene: str = Field(
        description="Exactly what the frame shows while the narration is spoken: action, "
        "characters by name, setting, framing, emotion. In English."
    )
    characters: list[str] = Field(description="Names of characters in frame.")
    camera: Camera
    key_moment: bool = Field(description="True for the hook and the climax only.")

    @property
    def narration(self) -> str:
        """Everything said in the shot, for word counts and summaries."""
        return " ".join(line.text for line in self.lines)


class StoryScript(DraftBase):
    hook: str = Field(max_length=100)
    shots: list[StoryShot] = Field(description="The shot list, in order.")


class StoryReview(BaseModel):
    score: int = Field(ge=1, le=10)
    strengths: list[str] = Field(max_length=4)
    problems: list[str] = Field(max_length=8)
    fixes: str = Field(max_length=1200, description="Concrete instructions for the rewrite.")


class StoryDraft(StoryScript):
    title: str = Field(max_length=80)
    logline: str = Field(max_length=240)
    genre: str = Field(max_length=40)
    narration_language: str = Field(max_length=10)
    visual_style: str = Field(max_length=240)
    setting: str = Field(max_length=300)
    characters: list[Character] = Field(max_length=4)
    target_seconds: int = Field(ge=20, le=120)


Draft = CarouselDraft | ImageDraft | ReelDraft | PhotoDraft | ExplainerDraft | StoryDraft

VIDEO_FORMATS = ("reel", "explainer", "story")


def load_draft(fmt: str, script: dict) -> Draft:
    """Validate a stored script, filling fields that drafts saved by older versions lack."""
    data = dict(script)
    if fmt in ("reel", "photo"):
        data.setdefault("visual_style", "")
    if fmt == "story":
        # Stories made before characters could speak: narration only, no voice casting info.
        data["shots"] = [
            {**shot, "lines": [{"speaker": NARRATOR, "text": shot["narration"]}]}
            if "lines" not in shot
            else shot
            for shot in data.get("shots", [])
        ]
        data["characters"] = [
            {"gender": "male", "age": "adult", **c} for c in data.get("characters", [])
        ]
    return FORMAT_SCHEMAS[fmt].model_validate(data)


FORMAT_SCHEMAS: dict[str, type[DraftBase]] = {
    "carousel": CarouselDraft,
    "image": ImageDraft,
    "reel": ReelDraft,
    "photo": PhotoDraft,
    "explainer": ExplainerDraft,
    "story": StoryDraft,
}
