"""Movie style: every shot is a generated clip with its own sound and lip-synced dialogue.

Dialogue shots ask the video model to have the character speak their lines (described voice,
lip sync, ambience). Narration shots get natural ambience from the clip with the narrator's
consistent voice laid over it. A shot whose clip can't be made falls back to a moving still with
the cast voices, so the movie always finishes.
"""

import logging
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from app.config import settings
from bot.media.ai_images import MediaError, generate_image
from bot.media.reel import (
    FPS,
    Caption,
    caption_chunks,
    cleanup_work,
    concat_clips,
    ffmpeg_exe,
    render_caption_overlays,
    render_scene,
)
from bot.media.story_video import (
    Progress,
    _existing,
    _render_cover,
    narration_voice,
    prepare_dialogue,
    shot_prompt,
)
from bot.media.video_gen import animate_image, clip_length
from bot.media.voices import cast_voices
from bot.settings import BrandKit, load_brand_kit
from bot.writer.schemas import NARRATOR, StoryDraft, StoryShot

logger = logging.getLogger(__name__)

SPEECH_WORDS_PER_SECOND = 2.4
AMBIENT_UNDER_NARRATION = 0.35
PARALLEL_CLIPS = 3


def is_dialogue(shot: StoryShot) -> bool:
    return any(line.speaker != NARRATOR for line in shot.lines)


def speech_seconds(shot: StoryShot) -> float:
    words = sum(len(line.text.split()) for line in shot.lines)
    return words / SPEECH_WORDS_PER_SECOND + 1.0


def clip_prompt(draft: StoryDraft, shot: StoryShot) -> str:
    base = shot_prompt(draft, shot) + f"\nCamera: {shot.camera.replace('_', ' ')}."
    if not is_dialogue(shot):
        return base + "\nNo one speaks. Natural ambient sound of the scene only."
    voices = {c.name: c.voice for c in draft.characters}
    spoken = []
    for line in shot.lines:
        if line.speaker == NARRATOR:
            continue
        voice = f" ({voices[line.speaker]})" if voices.get(line.speaker) else ""
        spoken.append(f'{line.speaker}{voice} says: "{line.text}"')
    return (
        base + "\nDialogue, spoken on camera with lips moving precisely in sync with each word, "
        "facing the camera with the mouth clearly visible:\n"
        + "\n".join(spoken)
        + "\nOnly these words are spoken. Natural ambient sound."
    )


def render_movie(
    draft: StoryDraft,
    out_dir: Path,
    brand: BrandKit | None = None,
    progress: Progress | None = None,
    language: str | None = None,
) -> tuple[list[Path], int]:
    """Render the movie; returns (video and cover, number of shots that fell back to stills)."""
    brand = brand or load_brand_kit()
    report = progress or (lambda *_: None)
    work = out_dir / "reel_work"
    work.mkdir(parents=True, exist_ok=True)
    total = len(draft.shots)

    report("voiceover", 32, "Recording the narrator")
    narrator = narration_voice(draft, brand, language)
    # Every line gets a consistent recorded take too: narration uses it, and dialogue shots
    # fall back to it if their clip can't be made.
    audio = prepare_dialogue(
        draft, work, narrator, cast_voices(draft.characters, narrator), brand.voiceover
    )

    reference = None
    if draft.characters:
        report("characters", 36, "Casting the characters")
        reference = _existing(work, "characters") or generate_image(
            "Character reference sheet: each character shown full body and face, side by side, "
            "neutral plain background, even lighting.\n"
            + "\n".join(f"{c.name}: {c.look}" for c in draft.characters),
            "3:4",
            work / "characters",
            draft.visual_style,
            brand.image_style,
        )

    stills = []
    for i, shot in enumerate(draft.shots):
        report("pictures", 38 + round(20 * i / total), f"Setting up shot {i + 1} of {total}")
        stills.append(
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

    done = {"count": 0}

    def film(i: int) -> tuple[int, Path | None]:
        shot = draft.shots[i]
        clip = work / f"clip_{i}.mp4"
        if not clip.is_file():
            seconds = clip_length(speech_seconds(shot) if is_dialogue(shot) else audio[i][1])
            try:
                animate_image(
                    stills[i],
                    clip_prompt(draft, shot),
                    seconds,
                    clip,
                    with_audio=True,
                    model=settings.movie_video_model,
                )
            except MediaError:
                logger.warning("Shot %s falls back to a still with recorded voices", i)
                return i, None
        done["count"] += 1
        report(
            "filming",
            58 + round(30 * done["count"] / total),
            f"Filmed {done['count']} of {total} shots",
        )
        return i, clip

    report("filming", 58, f"Filming {total} shots")
    with ThreadPoolExecutor(max_workers=PARALLEL_CLIPS) as pool:
        clips = dict(pool.map(film, range(total)))

    report("editing", 90, "Editing the movie")
    timings = []
    for i, shot in enumerate(draft.shots):
        clip = clips.get(i)
        if clip and is_dialogue(shot):
            length = _duration(clip) or clip_length(speech_seconds(shot))
            timings.append((length, _dialogue_captions(shot, length)))
        else:
            timings.append((audio[i][1], audio[i][2]))
    overlays = render_caption_overlays(
        [(shot.on_screen_text, captions) for shot, (_, captions) in zip(draft.shots, timings)],
        work,
        brand,
    )

    parts = []
    for i, shot in enumerate(draft.shots):
        part = work / f"part_{i}.mp4"
        clip = clips.get(i)
        length, _ = timings[i]
        if clip is None:
            render_scene(stills[i], audio[i][0], audio[i][1], overlays[i], part, motion=shot.camera)
        elif is_dialogue(shot):
            _render_clip_part(clip, length, overlays[i], part, narration=None)
        else:
            _render_clip_part(clip, length, overlays[i], part, narration=audio[i][0])
        parts.append(part)

    video = out_dir / "video.mp4"
    concat_clips(parts, work, video)
    cover = out_dir / "cover.jpg"
    _render_cover(draft, stills[0], cover, brand)
    cleanup_work(work)
    report("done", 100, "Ready")
    return [video, cover], sum(1 for clip in clips.values() if clip is None)


def _dialogue_captions(shot: StoryShot, length: float) -> list[Caption]:
    """Spread each spoken line's captions over the clip, roughly where it is said."""
    lines = [line for line in shot.lines if line.speaker != NARRATOR]
    start, end = 0.3, max(length - 0.3, 0.6)
    weights = [len(line.text) for line in lines]
    total = sum(weights) or 1
    captions, cursor = [], start
    for line, weight in zip(lines, weights):
        span = (end - start) * weight / total
        for caption in caption_chunks(line.text, span):
            captions.append(
                Caption(
                    caption.text,
                    cursor + caption.start,
                    cursor + caption.end,
                    caption.highlight,
                    line.speaker,
                )
            )
        cursor += span
    return captions


def _render_clip_part(
    clip: Path,
    duration: float,
    overlays: list[tuple[Path, Caption]],
    out: Path,
    narration: Path | None,
) -> None:
    """A clip with its own sound (dialogue/ambience), optionally with narration over it."""
    duration = max(duration, 1.0)
    clip_has_audio = _has_audio(clip)
    inputs = ["-i", str(clip)]
    for path, _ in overlays:
        inputs += ["-loop", "1", "-t", f"{duration:.3f}", "-i", str(path)]
    graph = [
        (
            "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,"
            f"fps={FPS},setsar=1,tpad=stop_mode=clone:stop_duration={duration:.3f},"
            f"trim=duration={duration:.3f}[v0]"
        )
    ]
    for k, (_, caption) in enumerate(overlays, 1):
        end = duration if k == len(overlays) else caption.end
        graph.append(
            f"[v{k - 1}][{k}:v]overlay=0:0:enable='between(t,{caption.start:.3f},{end:.3f})'[v{k}]"
        )
    narration_index = len(overlays) + 1
    if narration is not None:
        inputs += ["-i", str(narration)]
    ambient = (
        f"[0:a]aresample=44100,volume={AMBIENT_UNDER_NARRATION if narration else 1.0},apad[amb]"
        if clip_has_audio
        else f"anullsrc=r=44100:cl=stereo,atrim=0:{duration:.3f}[amb]"
    )
    graph.append(ambient)
    if narration is not None:
        graph.append(f"[{narration_index}:a]aresample=44100,apad[nar]")
        graph.append("[amb][nar]amix=inputs=2:duration=longest:normalize=0[mix]")
        graph.append(f"[mix]atrim=0:{duration:.3f}[a]")
    else:
        graph.append(f"[amb]atrim=0:{duration:.3f}[a]")
    _ffmpeg(
        [
            *inputs,
            "-filter_complex", ";".join(graph),
            "-map", f"[v{len(overlays)}]", "-map", "[a]",
            "-t", f"{duration:.3f}", "-r", str(FPS),
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "160k", "-ac", "2", "-ar", "44100",
            str(out),
        ]
    )  # fmt: skip


def _ffmpeg(args: list[str]) -> None:
    command = [ffmpeg_exe(), "-y", "-hide_banner", "-loglevel", "error", *args]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        logger.error("Movie editing failed: %s", result.stderr.strip()[-2000:])
        raise MediaError("We couldn't put the movie together. Please try again.")


def _probe(path: Path) -> str:
    return subprocess.run(
        [ffmpeg_exe(), "-hide_banner", "-i", str(path)], capture_output=True, text=True, check=False
    ).stderr


def _has_audio(path: Path) -> bool:
    return "Audio:" in _probe(path)


def _duration(path: Path) -> float | None:
    for line in _probe(path).splitlines():
        if "Duration:" in line:
            h, m, s = line.split("Duration:")[1].split(",")[0].strip().split(":")
            return int(h) * 3600 + int(m) * 60 + float(s)
    return None


def estimate_cost(style: str, seconds: int) -> float:
    """Rough USD for one video, shown to users before they create it."""
    rate = (
        settings.movie_price_per_second if style == "movie" else settings.cinematic_price_per_second
    )
    return round(seconds * rate + 0.1, 2)
