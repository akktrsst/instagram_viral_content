"""Story videos: consistent characters, one picture per narration line, real clips for key moments."""

import logging
import wave
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from bot.languages import voice_for
from bot.media.ai_images import MediaError, generate_image
from bot.media.reel import (
    REEL_SIZE,
    SCENE_TAIL,
    Caption,
    caption_chunks,
    cleanup_work,
    concat_clips,
    render_caption_overlays,
    render_scene,
)
from bot.media.tts import synthesize
from bot.media.video_gen import animate_image, clip_length, video_enabled
from bot.media.voices import cast_voices
from bot.settings import BrandKit, Voiceover, load_brand_kit
from bot.writer.schemas import NARRATOR, Line, StoryDraft, StoryShot

logger = logging.getLogger(__name__)

Progress = Callable[[str, int, str], None]


def narration_voice(draft: StoryDraft, brand: BrandKit, language: str | None = None) -> Voiceover:
    return voice_for(
        brand.voiceover,
        language=language,
        locale_hint=draft.narration_language,
        sample_text=" ".join(s.narration for s in draft.shots[:3]),
    )


def shot_prompt(draft: StoryDraft, shot: StoryShot) -> str:
    cast = [c for c in draft.characters if c.name in shot.characters]
    who = "".join(f"\n{c.name}: {c.look}" for c in cast)
    return f"A single frame from a film. {shot.scene}\nSetting: {draft.setting}" + (
        f"\nCharacters in frame (keep exactly this appearance):{who}" if who else ""
    )


def render_story(
    draft: StoryDraft,
    out_dir: Path,
    brand: BrandKit | None = None,
    progress: Progress | None = None,
    language: str | None = None,
) -> list[Path]:
    """Render `video.mp4` and `cover.jpg`; reuses assets left by an interrupted attempt."""
    brand = brand or load_brand_kit()
    report = progress or (lambda *_: None)
    work = out_dir / "reel_work"
    work.mkdir(parents=True, exist_ok=True)
    total = len(draft.shots)

    report("voiceover", 35, "Recording the voices")
    narrator = narration_voice(draft, brand, language)
    cast = cast_voices(draft.characters, narrator)
    audio = prepare_dialogue(draft, work, narrator, cast, brand.voiceover)
    voices = [(path, duration) for path, duration, _ in audio]

    reference = None
    if draft.characters:
        report("characters", 40, "Designing the characters")
        reference = _existing(work, "characters") or generate_image(
            "Character reference sheet: each character shown full body, side by side, neutral "
            "plain background, even lighting.\n"
            + "\n".join(f"{c.name}: {c.look}" for c in draft.characters),
            "3:4",
            work / "characters",
            draft.visual_style,
            brand.image_style,
        )

    images = []
    for i, shot in enumerate(draft.shots):
        report("pictures", 42 + round(38 * i / total), f"Creating picture {i + 1} of {total}")
        images.append(
            _existing(work, f"scene_{i}")
            or generate_image(
                shot_prompt(draft, shot),
                "9:16",
                work / f"scene_{i}",
                draft.visual_style,
                brand.image_style,
                reference=reference if shot.characters else None,
            )
        )

    clips: dict[int, Path] = {}
    key_shots = [i for i, shot in enumerate(draft.shots) if shot.key_moment]
    if key_shots and video_enabled():
        for n, i in enumerate(key_shots, 1):
            report("motion", 80 + 4 * n, f"Filming key moment {n} of {len(key_shots)}")
            clip = work / f"clip_{i}.mp4"
            if clip.is_file():
                clips[i] = clip
                continue
            try:
                seconds = clip_length(voices[i][1])
                clips[i] = animate_image(
                    images[i], shot_prompt(draft, draft.shots[i]), seconds, clip
                )
            except MediaError:
                logger.warning("Shot %s falls back to a still image", i)

    report("editing", 90, "Editing the video")
    overlays = render_caption_overlays(
        [(shot.on_screen_text, captions) for shot, (_, _, captions) in zip(draft.shots, audio)],
        work,
        brand,
    )
    parts = []
    for i, (shot, (audio, duration), shot_overlays) in enumerate(
        zip(draft.shots, voices, overlays)
    ):
        part = work / f"part_{i}.mp4"
        if i in clips:
            render_scene(clips[i], audio, duration, shot_overlays, part, motion="video")
        else:
            render_scene(images[i], audio, duration, shot_overlays, part, motion=shot.camera)
        parts.append(part)

    video = out_dir / "video.mp4"
    concat_clips(parts, work, video)
    cover = out_dir / "cover.jpg"
    _render_cover(draft, images[0], cover, brand)
    cleanup_work(work)
    report("done", 100, "Ready")
    return [video, cover]


LINE_GAP = 0.25  # pause between two spoken lines in the same shot


def prepare_dialogue(
    draft: StoryDraft,
    work: Path,
    narrator: Voiceover,
    cast: dict[str, Voiceover],
    fallback: Voiceover,
) -> list[tuple[Path, float, list[Caption]]]:
    """Record every line in its speaker's voice and join each shot's lines into one track.

    Returns, per shot: (audio file, shot seconds, captions timed within the shot). Line
    recordings are reused if a previous attempt made them."""

    def record(item: tuple[int, int, Line]) -> tuple[int, int, Path, float]:
        i, j, line = item
        path = work / f"line_{i}_{j}.wav"
        if not path.is_file():
            voice = cast.get(line.speaker, narrator)
            candidates = list({v.voice: v for v in (voice, narrator, fallback)}.values())
            for candidate in candidates:
                try:
                    synthesize(line.text, path, candidate)
                    break
                except MediaError:
                    logger.warning("Voice %s failed for a line; trying the next", candidate.voice)
            else:
                raise MediaError("We couldn't record the voices. Please try again.")
        return i, j, path, _wav_seconds(path)

    items = [
        (i, j, line) for i, shot in enumerate(draft.shots) for j, line in enumerate(shot.lines)
    ]
    with ThreadPoolExecutor(max_workers=4) as pool:
        recorded = list(pool.map(record, items))

    result = []
    for i, shot in enumerate(draft.shots):
        takes = [(path, seconds) for si, _, path, seconds in recorded if si == i]
        track = work / f"shot_{i}.wav"
        captions, cursor = [], 0.0
        for (path, seconds), line in zip(takes, shot.lines):
            label = "" if line.speaker == NARRATOR else line.speaker
            for caption in caption_chunks(line.text, seconds):
                captions.append(
                    Caption(
                        caption.text,
                        cursor + caption.start,
                        cursor + caption.end,
                        caption.highlight,
                        label,
                    )
                )
            cursor += seconds + LINE_GAP
        _join_wavs([path for path, _ in takes], track, LINE_GAP)
        result.append((track, cursor - LINE_GAP + SCENE_TAIL, captions))
    return result


def _join_wavs(paths: list[Path], out: Path, gap: float) -> None:
    with wave.open(str(paths[0])) as first:
        params = first.getparams()
    silence = b"\x00" * int(params.framerate * gap) * params.sampwidth * params.nchannels
    with wave.open(str(out), "wb") as joined:
        joined.setparams(params)
        for n, path in enumerate(paths):
            with wave.open(str(path)) as part:
                if n:
                    joined.writeframes(silence)
                joined.writeframes(part.readframes(part.getnframes()))


def _wav_seconds(path: Path) -> float:
    with wave.open(str(path)) as audio:
        return audio.getnframes() / audio.getframerate()


def _existing(work: Path, stem: str) -> Path | None:
    found = [p for p in work.glob(f"{stem}.*") if p.suffix in (".png", ".jpg", ".jpeg", ".webp")]
    return found[0] if found else None


def _render_cover(draft: StoryDraft, background: Path, out: Path, brand: BrandKit) -> None:
    from playwright.sync_api import sync_playwright

    from bot.media.render import TEMPLATES, _data_uri, _font_faces

    html = TEMPLATES.get_template("reel_frame.html").render(
        brand=brand,
        font_faces=_font_faces(brand),
        background_uri=_data_uri(background),
        cover_title=draft.title,
    )
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        try:
            page = browser.new_page(viewport=REEL_SIZE)
            page.set_content(html, wait_until="load")
            page.screenshot(path=out, type="jpeg", quality=92)
        finally:
            browser.close()
