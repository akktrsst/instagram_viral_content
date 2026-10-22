"""Story agent: plan -> shot list -> editor review -> revision -> length check.

Each step is one structured model call; the editor scores the script against the brief and the
target length, and the writer revises once when the score is low. The result is a StoryDraft whose
shots each pair a narration line with the exact picture shown while it is spoken.
"""

import json
from collections.abc import Callable

from app.config import settings
from app.schemas import ModelTier
from app.services.gemini import GenerationUnavailable, generate_json, model_for_tier
from bot.languages import get_language, language_instruction
from bot.settings import BotSettings, BrandKit, load_bot_settings, load_brand_kit
from bot.skills import SkillSpec, skill_prompt
from bot.writer.schemas import NARRATOR, Line, StoryDraft, StoryPlan, StoryReview, StoryScript
from bot.writer.writer import BannedWordsError, finalize, find_banned_words

Progress = Callable[[str, int, str], None]

WORDS_PER_SECOND = 2.5  # comfortable narration pace for the voiceover
SECONDS_PER_SHOT = 4.5  # a new picture roughly every 4-5 seconds
SHOT_TAIL = 0.3  # pause added after each narration line
PASSING_SCORE = 8


def shot_budget(target_seconds: int) -> tuple[int, int]:
    """(number of shots, total narration words) that fill target_seconds."""
    shots = max(4, min(30, round(target_seconds / SECONDS_PER_SHOT)))
    words = round((target_seconds - shots * SHOT_TAIL) * WORDS_PER_SECOND)
    return shots, words


def max_video_clips(target_seconds: int) -> int:
    return 1 if target_seconds <= 30 else settings.video_clips_per_story


def write_story(
    brief: str,
    target_seconds: int,
    *,
    skill: SkillSpec | None = None,
    tier: ModelTier | None = None,
    language: str | None = None,
    progress: Progress | None = None,
    bot: BotSettings | None = None,
    brand: BrandKit | None = None,
) -> StoryDraft:
    bot = bot or load_bot_settings()
    brand = brand or load_brand_kit()
    report = progress or (lambda *_: None)
    model = model_for_tier(tier) or settings.gemini_model
    editor_model = settings.gemini_model_pro
    chosen = get_language(language)
    system = story_system_prompt(bot, brand, skill) + language_instruction(chosen)
    shots, words = shot_budget(target_seconds)
    brief_json = json.dumps(brief, ensure_ascii=False)

    report("planning", 5, "Planning the story")
    plan = generate_json(
        model,
        f"Brief: {brief_json}\nTarget length: {target_seconds} seconds.\n"
        "Plan the story: title, logline, genre, narration language, a visual style that suits "
        "it, the setting, up to 4 characters (each with gender, age group and a fixed look), "
        "and 3-8 beats whose seconds add "
        f"up to about {target_seconds}.",
        StoryPlan,
        system_instruction=system,
    )

    report("writing", 12, "Writing the script")
    script_request = (
        f"Brief: {brief_json}\nPlan:\n{plan.model_dump_json(indent=1)}\n\n"
        f"Write the shot list: about {shots} shots and about {words} spoken words in total "
        f"(the video must run about {target_seconds} seconds). Follow the beats in order. "
        "Each shot has 1-3 spoken lines. Let the characters speak: give them real dialogue "
        "(roughly a third to a half of all lines when the story has characters) and use the "
        f'"{NARRATOR}" for scene-setting and transitions. A line\'s speaker is "{NARRATOR}" or '
        "a character's exact name. Shot 1's first line is the hook and works in the first 2 "
        "seconds. Each shot's scene shows exactly what is being said at that moment; when a "
        "character speaks, show them speaking (in frame and listed in characters). Use "
        "character names from the plan, and vary framing (wide, medium, close-up) and camera "
        "move. Mark key_moment "
        f"true on at most {max_video_clips(target_seconds)} shots: the hook and the climax."
    )
    script = generate_json(model, script_request, StoryScript, system_instruction=system)

    report("reviewing", 20, "Editor is reviewing the story")
    review = generate_json(
        editor_model,
        _review_request(brief_json, plan, script, target_seconds, words),
        StoryReview,
        system_instruction=EDITOR,
        temperature=0.3,
    )
    if review.score < PASSING_SCORE:
        report("revising", 26, f"Improving the script (editor score {review.score}/10)")
        script = generate_json(
            model,
            f"{script_request}\n\nYour previous draft:\n{script.model_dump_json(indent=1)}\n\n"
            f"Editor feedback (score {review.score}/10):\nProblems: {review.problems}\n"
            f"Fixes: {review.fixes}\nRewrite the whole shot list applying the feedback.",
            StoryScript,
            system_instruction=system,
        )

    narration_words = sum(len(shot.narration.split()) for shot in script.shots)
    # Dialogue lines are short and voices brisk, so hold the word count close to target.
    if not 0.9 * words <= narration_words <= 1.2 * words:
        report("adjusting", 30, "Adjusting the length")
        direction = "Expand" if narration_words < words else "Tighten"
        script = generate_json(
            model,
            f"{script_request}\n\nCurrent draft ({narration_words} words, needs about {words}):\n"
            f"{script.model_dump_json(indent=1)}\n\n{direction} it to about {words} narration "
            "words, keeping the same story, characters and ending.",
            StoryScript,
            system_instruction=system,
        )

    hits = find_banned_words(script, brand.banned_words)
    if hits:
        script = generate_json(
            model,
            f"{script_request}\n\nRewrite this draft without the words {hits}:\n"
            f"{script.model_dump_json(indent=1)}",
            StoryScript,
            system_instruction=system,
        )
        if find_banned_words(script, brand.banned_words):
            raise BannedWordsError("The story still uses words your brand avoids. Try again.")

    draft = StoryDraft(
        **tidy_shots(script, [c.name for c in plan.characters]).model_dump(),
        title=plan.title,
        logline=plan.logline,
        genre=plan.genre,
        narration_language=chosen.locale if chosen else plan.narration_language,
        visual_style=(
            f"{plan.visual_style}. {skill.visual_guidance}"
            if skill and skill.visual_guidance
            else plan.visual_style
        )[:240],
        setting=plan.setting,
        characters=plan.characters,
        target_seconds=target_seconds,
    )
    return finalize(limit_key_moments(draft), brand)


MAX_SHOTS = 40


def tidy_shots(script: StoryScript, cast: list[str]) -> StoryScript:
    """Enforce what the response schema can't: valid speakers, spoken lines, a sane shot count."""
    shots = []
    for shot in script.shots[:MAX_SHOTS]:
        lines = []
        for line in shot.lines:
            text = line.text.strip().strip("\"“”‘’'").strip()
            if not text:
                continue
            speaker = next(
                (name for name in cast if name.lower() == line.speaker.strip().lower()), NARRATOR
            )
            lines.append(Line(speaker=speaker, text=text))
        if not lines:
            continue
        speakers = [l.speaker for l in lines if l.speaker != NARRATOR]
        in_frame = list(dict.fromkeys([*shot.characters, *speakers]))[:4]
        shots.append(
            shot.model_copy(
                update={
                    "lines": lines,
                    "on_screen_text": shot.on_screen_text[:60],
                    "characters": in_frame,
                }
            )
        )
    if len(shots) < 3:
        raise GenerationUnavailable("We couldn't write this story. Please try again.")
    return script.model_copy(update={"shots": shots})


def limit_key_moments(draft: StoryDraft) -> StoryDraft:
    """Keep real-video clips to the budget: the hook first, then the latest flagged climax."""
    budget = max_video_clips(draft.target_seconds)
    flagged = [i for i, shot in enumerate(draft.shots) if shot.key_moment]
    keep = set(([0] if budget else []) + flagged[::-1][: max(budget - 1, 0)])
    shots = [
        shot.model_copy(update={"key_moment": i in keep}) for i, shot in enumerate(draft.shots)
    ]
    return draft.model_copy(update={"shots": shots})


def _review_request(
    brief_json: str, plan: StoryPlan, script: StoryScript, target_seconds: int, words: int
) -> str:
    narration_words = sum(len(shot.narration.split()) for shot in script.shots)
    return (
        f"Brief: {brief_json}\nTarget: {target_seconds} seconds (about {words} narration words; "
        f"the draft has {narration_words}).\nPlan:\n{plan.model_dump_json(indent=1)}\n"
        f"Shot list:\n{script.model_dump_json(indent=1)}"
    )


def story_system_prompt(bot: BotSettings, brand: BrandKit, skill: SkillSpec | None) -> str:
    banned = ", ".join(brand.banned_words) or "none"
    return (
        f"You are an award-winning short-form storyteller and film director making a narrated "
        f"Instagram video for {brand.brand_name} ({brand.handle}).\n\n"
        "THE BRIEF COMES FIRST\n"
        "Tell the story the brief asks for, in its genre, mood, audience and language. It can be "
        "any kind of story: motivational, horror, romance, comedy, mystery, fable, mythology, "
        "slice of life, history, or a narrated non-fiction piece (documentary, recipe, "
        "countdown). If the brief is a request ('make a story about X'), the story is about X. "
        "If it is vague, choose the most gripping specific take. Only if it gives no subject "
        f"at all, draw on: {bot.niche.name}.\n\n"
        "STORYTELLING\n"
        "Hook in the first 2 seconds with intrigue, conflict or a striking image. Give viewers "
        "someone to follow and something at stake, a turn, and an ending that pays off "
        "(resolution, twist, or lesson) without rushing. Show, don't tell. Characters speak "
        "for themselves in natural, in-character dialogue that reveals who they are and moves "
        "the story; a narrator bridges scenes. Everything is spoken aloud: natural rhythm, "
        "short sentences, no quotation marks, labels or stage directions.\n\n"
        "PICTURE MATCHES WORDS\n"
        "Each shot's scene depicts exactly what its narration says at that moment, as a single "
        "filmable frame: who is in it, what they are doing, where, framing (wide, medium, "
        "close-up), lighting and emotion. Characters keep the same look in every shot. Scenes "
        "are written in English even if the narration is not. Never ask for text, captions, "
        "logos, brand names, watermarks, copyrighted characters or real people's likeness.\n\n"
        f"VOICE: {brand.voice} Adapt energy to the genre.\n"
        "Write the narration in the brief's language unless it asks for another.\n\n"
        "CAPTION AND HASHTAGS\n"
        "Caption: a hook line, a one-line teaser of the story (no spoilers), then a call to "
        "action that fits. No hashtags in it. Hashtags: 5-15 about this story's genre and "
        "subject. Alt text describes the video.\n\n"
        "SAFETY\n"
        "Keep it PG-13: suspense not gore, romance not explicit. Don't present invented events as "
        "true or make claims about real people; non-fiction must be accurate. "
        f"Never use: {banned}.{skill_prompt(skill)}"
    )


EDITOR = """You are a demanding story editor for short vertical videos. Score the draft 1-10 \
against the brief and target length. Check: does it deliver what the brief asks (subject, genre, \
mood, language)? Is the first shot a real hook? Is there a clear character, stakes, a turn and a \
satisfying ending? Do the characters speak in natural, distinct, in-character dialogue (not \
everything narrated), with valid speakers? Is pacing right for the length, with narration words close to the target? \
Does every shot's scene show exactly what its narration says, with consistent characters? Is it \
accurate and safe? List concrete problems and give specific fixes. Score 8+ only if it is ready \
to publish."""
