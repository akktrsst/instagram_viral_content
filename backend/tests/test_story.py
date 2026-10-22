import pytest

from bot.media.reel import camera_move
from bot.media.video_gen import clip_length
from bot.skills import SkillError, builtin_skills, delete_skill, skill_prompt
from bot.writer import story
from bot.writer.schemas import StoryPlan, StoryReview, StoryScript


def plan() -> StoryPlan:
    return StoryPlan.model_validate(
        {
            "title": "The Last Lamp",
            "logline": "A boy keeps his village's last lamp burning.",
            "genre": "fable",
            "narration_language": "en-IN",
            "visual_style": "warm painterly",
            "setting": "a hill village at dusk",
            "characters": [
                {
                    "name": "Ravi",
                    "gender": "male",
                    "age": "child",
                    "voice": "bright, quick boy's voice",
                    "look": "a 10-year-old boy in a red kurta",
                }
            ],
            "beats": [
                {"name": "Hook", "summary": "s", "seconds": 5},
                {"name": "Middle", "summary": "s", "seconds": 15},
                {"name": "End", "summary": "s", "seconds": 10},
            ],
        }
    )


def script(
    words_per_shot: int = 12, shots: int = 7, key: tuple[int, ...] = (0, 3, 6)
) -> StoryScript:
    return StoryScript.model_validate(
        {
            "caption": "A story about light.",
            "hashtags": ["#story", "#fable", "#kids", "#moral", "#village"],
            "alt_text": "A boy with a lamp",
            "suggested_collaborators": [],
            "hook": "The whole village went dark.",
            "shots": [
                {
                    "lines": [{"speaker": "Narrator", "text": " ".join(["word"] * words_per_shot)}],
                    "on_screen_text": "",
                    "scene": f"Ravi in shot {i}",
                    "characters": ["Ravi"],
                    "camera": "pan_left",
                    "key_moment": i in key,
                }
                for i in range(shots)
            ],
        }
    )


@pytest.fixture
def scripted(monkeypatch):
    """Feed the agent canned plan/script/review responses in call order."""

    def install(*responses):
        calls = []
        queue = list(responses)

        def fake(model, prompt, schema, system_instruction=None, temperature=0.7):
            calls.append((schema.__name__, prompt))
            return queue.pop(0)

        monkeypatch.setattr(story, "generate_json", fake)
        return calls

    return install


def review(score: int) -> StoryReview:
    return StoryReview(score=score, strengths=[], problems=["weak ending"], fixes="Sharper twist.")


def test_shot_budget_scales_with_length():
    assert story.shot_budget(30) == (7, 70)
    shots, words = story.shot_budget(120)
    assert 25 <= shots <= 30 and 250 <= words <= 290


def test_good_review_skips_revision_and_limits_video_clips(scripted):
    calls = scripted(plan(), script(), review(9))
    draft = story.write_story("A fable about light", 30)
    assert [name for name, _ in calls] == ["StoryPlan", "StoryScript", "StoryReview"]
    assert draft.title == "The Last Lamp" and draft.target_seconds == 30
    assert [i for i, s in enumerate(draft.shots) if s.key_moment] == [0]  # 30s: one clip


def test_low_review_triggers_one_revision_with_feedback(scripted):
    calls = scripted(plan(), script(), review(5), script())
    story.write_story("A fable about light", 30)
    assert [name for name, _ in calls][-1] == "StoryScript"
    assert "Sharper twist." in calls[-1][1]


def test_too_short_script_is_expanded(scripted):
    calls = scripted(plan(), script(words_per_shot=3), review(9), script())
    story.write_story("A fable", 30)
    assert "Expand it to about 70 narration words" in calls[-1][1]


def test_longer_story_keeps_hook_and_climax_clips(scripted):
    scripted(plan(), script(words_per_shot=10, shots=14, key=(0, 5, 12)), review(9))
    draft = story.write_story("A fable", 60)
    assert [i for i, s in enumerate(draft.shots) if s.key_moment] == [0, 12]


def test_clip_length_covers_narration():
    assert clip_length(3.2) == 4
    assert clip_length(5.5) == 6
    assert clip_length(11) == 8


@pytest.mark.parametrize(
    "move", ["slow_push_in", "slow_pull_out", "pan_left", "pan_right", "tilt_up", "static"]
)
def test_camera_moves_produce_zoompan_expressions(move):
    z, x, y = camera_move(move, 120)
    assert z and x and y


def test_builtin_skills_load_and_shape_prompts():
    skills = {s.id: s for s in builtin_skills()}
    assert {"story", "horror-story", "recipe-video"} <= skills.keys()
    assert all(s.builtin for s in skills.values())
    assert "SKILL: Horror story" in skill_prompt(skills["horror-story"])


def test_builtin_skills_cannot_be_deleted():
    with pytest.raises(SkillError):
        delete_skill(None, "story")


def test_voice_follows_chosen_language_and_script():
    from bot.languages import voice_for
    from bot.settings import Voiceover

    brand = Voiceover(voice="en-IN-Chirp3-HD-Achird")
    assert voice_for(brand, language="hi").voice == "hi-IN-Chirp3-HD-Achird"
    assert (
        voice_for(brand, language="bho").voice == "hi-IN-Chirp3-HD-Achird"
    )  # Bhojpuri: Hindi voice
    assert voice_for(brand, language="hinglish") is brand
    assert voice_for(brand, locale_hint="bho-IN").voice.startswith("hi-IN")
    assert voice_for(brand, sample_text="வணக்கம் நண்பர்களே").voice.startswith("ta-IN")
    assert voice_for(brand, sample_text="Hello friends") is brand


def test_language_instruction_overrides_brief_language():
    from bot.languages import get_language, language_instruction

    text = language_instruction(get_language("bho"))
    assert "Bhojpuri" in text and "overrides the language of the brief" in text
    assert language_instruction(None) == ""


def test_tidy_shots_fixes_speakers_and_puts_speakers_in_frame():
    from bot.writer.schemas import StoryScript

    raw = script(shots=4).model_dump()
    raw["shots"][1]["lines"] = [
        {"speaker": "ravi", "text": '"I can keep it lit!"'},
        {"speaker": "Mystery voice", "text": "Nobody believed him."},
        {"speaker": "Narrator", "text": "   "},
    ]
    raw["shots"][1]["characters"] = []
    tidy = story.tidy_shots(StoryScript.model_validate(raw), ["Ravi"])
    lines = tidy.shots[1].lines
    assert [(l.speaker, l.text) for l in lines] == [
        ("Ravi", "I can keep it lit!"),
        ("Narrator", "Nobody believed him."),
    ]
    assert tidy.shots[1].characters == ["Ravi"]


def test_voices_are_distinct_and_fit_the_character():
    from bot.media.voices import cast_voices
    from bot.settings import Voiceover
    from bot.writer.schemas import Character

    narrator = Voiceover(voice="hi-IN-Chirp3-HD-Achird")
    cast = cast_voices(
        [
            Character(name="Anaya", gender="female", age="child", voice="v", look="x"),
            Character(name="Dadi", gender="female", age="elderly", voice="v", look="x"),
            Character(name="Raju", gender="male", age="adult", voice="v", look="x"),
            Character(name="Sonu", gender="male", age="adult", voice="v", look="x"),
        ],
        narrator,
    )
    voices = [v.voice for v in cast.values()]
    assert len(set(voices)) == 4 and narrator.voice not in voices
    assert all(v.startswith("hi-IN-Chirp3-HD-") for v in voices)
    assert cast["Anaya"].speaking_rate > 1 > cast["Dadi"].speaking_rate


def test_old_narration_only_stories_still_load():
    from bot.writer.schemas import load_draft

    old = {
        **script().model_dump(),
        "title": "t",
        "logline": "l",
        "genre": "g",
        "narration_language": "en-IN",
        "visual_style": "v",
        "setting": "s",
        "target_seconds": 30,
        "characters": [{"name": "Ravi", "look": "boy"}],
    }
    for shot in old["shots"]:
        shot["narration"] = shot.pop("lines")[0]["text"]
    loaded = load_draft("story", old)
    assert loaded.shots[0].lines[0].speaker == "Narrator"
    assert loaded.characters[0].age == "adult"


def test_dialogue_track_joins_lines_and_times_captions(tmp_path, monkeypatch):
    import wave

    from bot.media import story_video
    from bot.settings import Voiceover
    from bot.writer.schemas import StoryDraft

    def fake_tts(text, path, voice):
        seconds = 1.0 if "Narrator" not in voice.voice else 2.0
        with wave.open(str(path), "wb") as out:
            out.setnchannels(1)
            out.setsampwidth(2)
            out.setframerate(8000)
            out.writeframes(b"\x00\x00" * int(8000 * seconds))
        return seconds

    monkeypatch.setattr(story_video, "synthesize", fake_tts)
    data = {
        **script(shots=4).model_dump(),
        "title": "t",
        "logline": "l",
        "genre": "g",
        "narration_language": "en-IN",
        "visual_style": "v",
        "setting": "s",
        "target_seconds": 30,
        "characters": [
            {"name": "Ravi", "gender": "male", "age": "child", "voice": "bright", "look": "boy"}
        ],
    }
    data["shots"][0]["lines"] = [
        {"speaker": "Narrator", "text": "The lights went out across the whole village"},
        {"speaker": "Ravi", "text": "I will fix it"},
    ]
    draft = StoryDraft.model_validate(data)
    narrator = Voiceover(voice="en-IN-Narrator")
    track, seconds, captions = story_video.prepare_dialogue(
        draft, tmp_path, narrator, {"Ravi": Voiceover(voice="en-IN-Ravi")}, narrator
    )[0]
    assert seconds == pytest.approx(2.0 + story_video.LINE_GAP + 1.0 + story_video.SCENE_TAIL)
    with wave.open(str(track)) as joined:
        assert joined.getnframes() / joined.getframerate() == pytest.approx(3.25)
    ravi = [c for c in captions if c.speaker == "Ravi"]
    assert ravi and ravi[0].start == pytest.approx(2.0 + story_video.LINE_GAP)
    assert all(c.speaker == "" for c in captions if c.end <= 2.0)


def test_movie_prompt_has_dialogue_voice_and_lip_sync():
    from bot.media.movie import clip_prompt, is_dialogue
    from bot.writer.schemas import StoryDraft

    data = {
        **script(shots=4).model_dump(),
        "title": "t",
        "logline": "l",
        "genre": "g",
        "narration_language": "hi-IN",
        "visual_style": "v",
        "setting": "kitchen",
        "target_seconds": 30,
        "style": "movie",
        "characters": [
            {
                "name": "Dadi",
                "gender": "female",
                "age": "elderly",
                "voice": "warm husky voice",
                "look": "grey bun",
            }
        ],
    }
    data["shots"][1]["lines"] = [{"speaker": "Dadi", "text": "सब्र रख बेटा"}]
    data["shots"][1]["characters"] = ["Dadi"]
    draft = StoryDraft.model_validate(data)
    talk, quiet = clip_prompt(draft, draft.shots[1]), clip_prompt(draft, draft.shots[0])
    assert is_dialogue(draft.shots[1]) and not is_dialogue(draft.shots[0])
    assert 'Dadi (warm husky voice) says: "सब्र रख बेटा"' in talk and "in sync" in talk
    assert "No one speaks" in quiet


def test_dialogue_captions_fit_inside_the_clip():
    from bot.media.movie import _dialogue_captions
    from bot.writer.schemas import Line, StoryShot

    shot = StoryShot(
        lines=[
            Line(speaker="Dadi", text="Patience makes the roti round"),
            Line(speaker="Riya", text="Really?"),
        ],
        on_screen_text="",
        scene="s",
        characters=["Dadi", "Riya"],
        camera="static",
        key_moment=False,
    )
    captions = _dialogue_captions(shot, 6.0)
    assert captions[0].start >= 0.3 and captions[-1].end <= 5.7 + 1e-6
    assert {c.speaker for c in captions} == {"Dadi", "Riya"}


def test_clip_part_mixes_clip_sound_with_narration(tmp_path):
    import subprocess
    import wave

    from bot.media.movie import _duration, _has_audio, _render_clip_part
    from bot.media.reel import ffmpeg_exe

    clip = tmp_path / "clip.mp4"
    subprocess.run(
        [
            ffmpeg_exe(),
            "-y",
            "-loglevel",
            "error",
            "-f",
            "lavfi",
            "-i",
            "color=c=blue:s=360x640:d=4",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=300:duration=4",
            "-shortest",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            str(clip),
        ],
        check=True,
    )
    narration = tmp_path / "n.wav"
    with wave.open(str(narration), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(44100)
        w.writeframes(b"\x00\x00" * 44100 * 5)
    out = tmp_path / "part.mp4"
    _render_clip_part(clip, 5.0, [], out, narration=narration)
    assert _has_audio(out) and abs(_duration(out) - 5.0) < 0.2


def test_movie_with_unfilmed_scenes_leaves_a_retry_note(monkeypatch):
    from types import SimpleNamespace

    from bot import posts
    from bot.media import movie

    draft = SimpleNamespace(style="movie", shots=[1, 2, 3, 4, 5])
    monkeypatch.setattr(posts, "load_draft", lambda fmt, script: draft)
    monkeypatch.setattr(movie, "render_movie", lambda *a, **k: ([], 3))
    monkeypatch.setattr(posts, "store_media", lambda post_id, paths: [])
    post = SimpleNamespace(
        id=1,
        status="draft",
        format="story",
        script={},
        language=None,
        topic="t",
        error=None,
        media_paths=[],
    )
    session = SimpleNamespace(commit=lambda: None)
    posts.render_media(session, post)
    assert post.error.startswith("3 of 5 scenes couldn't be filmed") and "Try again" in post.error
