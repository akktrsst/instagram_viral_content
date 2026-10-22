import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from bot.db.models import Base, Post
from bot.media.render import build_pages
from bot.settings import load_bot_settings, load_brand_kit
from bot.writer import writer
from bot.writer.schemas import CarouselDraft, ImageDraft


@pytest.fixture
def brand():
    return load_brand_kit().model_copy(
        update={"banned_words": ["guaranteed"], "hashtags_always": ["#MyBrand"]}
    )


def carousel(**overrides) -> CarouselDraft:
    data = {
        "caption": "Stop wasting your mornings.",
        "hashtags": ["AI Tools", "#productivity", "productivity", "#study-tips", "#notion"],
        "alt_text": "Dark slides with tips",
        "suggested_collaborators": ["@someone"],
        "slides": [{"kind": "title", "heading": "5 AI tools <for> students", "body": "Save hours"}]
        + [{"kind": "content", "heading": f"Tool {i}", "body": "Why it helps"} for i in range(5)]
        + [{"kind": "cta", "heading": "Save this", "body": "Follow for more"}],
    }
    data.update(overrides)
    return CarouselDraft.model_validate(data)


def test_config_files_load():
    assert load_bot_settings().niche.name
    assert load_brand_kit().colors.background.startswith("#")


def test_finalize_normalizes_hashtags_collaborators_and_disclosure(brand):
    draft = writer.finalize(carousel(), brand)
    assert draft.hashtags == ["#mybrand", "#aitools", "#productivity", "#studytips", "#notion"]
    assert draft.suggested_collaborators == ["someone"]
    assert draft.caption.endswith(brand.ai_disclosure)
    assert writer.finalize(draft, brand).caption.count(brand.ai_disclosure) == 1


def test_write_post_retries_then_rejects_banned_words(monkeypatch, brand):
    calls = []

    def fake_generate(model, prompt, schema, system_instruction=None):
        calls.append(prompt)
        return carousel(caption="A guaranteed win.")

    monkeypatch.setattr(writer, "generate_json", fake_generate)
    with pytest.raises(writer.BannedWordsError):
        writer.write_post("topic", "carousel", brand=brand)
    assert len(calls) == 2
    assert "guaranteed" in calls[1]


def test_write_post_uses_clean_retry(monkeypatch, brand):
    drafts = iter([carousel(caption="A guaranteed win."), carousel()])
    monkeypatch.setattr(writer, "generate_json", lambda *a, **k: next(drafts))
    draft = writer.write_post("topic", "carousel", brand=brand)
    assert "guaranteed" not in draft.caption


def test_banned_words_match_whole_words_only():
    draft = carousel(caption="This is unguaranteed territory")
    assert writer.find_banned_words(draft, ["guaranteed"]) == []


def test_build_pages_escapes_text_and_renders_each_slide(brand):
    pages = build_pages(carousel(), brand)
    assert len(pages) == 7
    assert "&lt;for&gt;" in pages[0]
    assert "1/7" in pages[0]


def test_build_pages_single_image(brand):
    draft = ImageDraft.model_validate(
        {
            **carousel().model_dump(exclude={"slides"}),
            "headline": "Hi",
            "subline": "There",
            "layout": "split",
        }
    )
    (page,) = build_pages(draft, brand)
    assert 'class="split"' in page


def test_post_model_roundtrip():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add(Post(topic="t", format="carousel", script={}, caption="c", model="m"))
        session.commit()
        post = session.scalars(select(Post)).one()
        assert post.status == "draft"
        assert post.created_at is not None


def test_caption_chunks_cover_the_whole_line_in_order():
    from itertools import pairwise

    from bot.media.reel import MAX_CHUNK_WORDS, caption_chunks

    captions = caption_chunks("Stop guessing what to build and start with one clear prompt", 4.0)
    assert captions[0].start == 0
    assert captions[-1].end == pytest.approx(4.0)
    assert all(a.end == pytest.approx(b.start) for a, b in pairwise(captions))
    assert all(len(c.text.split()) <= MAX_CHUNK_WORDS for c in captions)
    assert " ".join(c.text for c in captions) == (
        "Stop guessing what to build and start with one clear prompt"
    )


def test_build_pages_photo_uses_generated_image(brand):
    from bot.writer.schemas import PhotoDraft

    draft = PhotoDraft.model_validate(
        {
            **carousel().model_dump(exclude={"slides"}),
            "image_prompt": "a desk",
            "visual_style": "warm morning light",
            "headline": "Ship <it>",
            "text_position": "bottom",
        }
    )
    (page,) = build_pages(draft, brand, photo_uri="data:image/png;base64,AAAA")
    assert "data:image/png;base64,AAAA" in page
    assert "Ship &lt;it&gt;" in page
    assert 'class="overlay bottom"' in page


def test_system_prompt_puts_the_brief_before_the_niche(brand):
    bot = load_bot_settings()
    prompt = writer.build_system_prompt(bot, brand, "reel")
    assert "The user's brief decides what the post is about" in prompt
    assert "the post is about X itself" in prompt
    assert "Only if it names no subject at all" in prompt
    assert "visual_style" in prompt
    assert "visual_style" not in writer.build_system_prompt(bot, brand, "carousel")


def test_brief_is_sent_as_data(monkeypatch, brand):
    seen = {}

    def fake_generate(model, prompt, schema, system_instruction=None):
        seen["prompt"] = prompt
        return carousel()

    monkeypatch.setattr(writer, "generate_json", fake_generate)
    writer.write_post("Diwali greetings for my bakery's customers", "carousel", brand=brand)
    assert seen["prompt"].startswith('Brief: "Diwali greetings for my bakery')


def test_load_draft_accepts_scripts_saved_before_visual_style():
    from bot.writer.schemas import load_draft

    old = {
        **carousel().model_dump(exclude={"slides"}),
        "image_prompt": "a desk",
        "headline": "",
        "text_position": "none",
    }
    assert load_draft("photo", old).visual_style == ""


def explainer(**overrides):
    from bot.writer.schemas import ExplainerDraft

    data = {
        **carousel().model_dump(exclude={"slides"}),
        "hook": "How transformers read",
        "title": "Transformer flow",
        "nodes": [
            {"id": "in", "label": "Input tokens", "detail": ""},
            {"id": "emb", "label": "Embeddings", "detail": "words to vectors"},
            {"id": "att", "label": "Self-attention", "detail": ""},
            {"id": "ffn", "label": "Feed-forward", "detail": ""},
            {"id": "out", "label": "Next token", "detail": ""},
        ],
        "edges": [
            {"source": "in", "target": "emb", "label": ""},
            {"source": "emb", "target": "att", "label": ""},
            {"source": "att", "target": "ffn", "label": ""},
            {"source": "ffn", "target": "out", "label": ""},
            {"source": "ffn", "target": "att", "label": "x N"},
        ],
        "steps": [
            {"voiceover": "a", "on_screen_text": "a", "reveal": ["in", "emb"], "focus": ["emb"]},
            {"voiceover": "b", "on_screen_text": "b", "reveal": ["att"], "focus": ["att"]},
            {"voiceover": "c", "on_screen_text": "c", "reveal": ["ffn"], "focus": []},
        ],
    }
    data.update(overrides)
    return ExplainerDraft.model_validate(data)


def test_clean_explainer_reveals_every_node_and_drops_bad_edges():
    draft = explainer(
        edges=[
            {"source": "in", "target": "emb", "label": ""},
            {"source": "ghost", "target": "emb", "label": ""},
            {"source": "att", "target": "att", "label": ""},
        ]
    )
    cleaned = writer.clean_explainer(draft)
    assert [(e.source, e.target) for e in cleaned.edges] == [("in", "emb")]
    revealed = [i for step in cleaned.steps for i in step.reveal]
    assert sorted(revealed) == sorted(n.id for n in cleaned.nodes)
    assert cleaned.steps[2].focus == ["ffn", "out"]


def test_layout_places_nodes_top_to_bottom_within_the_frame():
    from bot.media.diagram import AREA_BOTTOM, AREA_LEFT, AREA_RIGHT, AREA_TOP, layout

    boxes, arrows = layout(explainer())
    order = ["in", "emb", "att", "ffn", "out"]
    ys = [boxes[i].y for i in order]
    assert ys == sorted(ys)
    for box in boxes.values():
        assert AREA_LEFT <= box.x - box.w / 2 and box.x + box.w / 2 <= AREA_RIGHT
        assert AREA_TOP <= box.y - box.h / 2 and box.y + box.h / 2 <= AREA_BOTTOM
    assert len(arrows) == 5  # including the loop back from ffn to att


def test_frame_html_shows_only_visible_nodes(brand):
    from bot.media.diagram import frame_html

    html = frame_html(explainer(), brand, visible={"in", "emb"}, focus={"emb"})
    assert "Embeddings" in html and "Self-attention" not in html
    assert 'class="node focus"' in html


def test_local_store_keeps_paths_inside_output(tmp_path, monkeypatch):
    from app.config import PROJECT_ROOT
    from bot import storage

    monkeypatch.setattr(storage.settings, "media_store", "local")
    out = PROJECT_ROOT / "output" / "pytest-storage"
    out.mkdir(parents=True, exist_ok=True)
    image = out / "slide.jpg"
    image.write_bytes(b"jpeg")
    try:
        (stored,) = storage.store_media(1, [image])
        assert stored == "output/pytest-storage/slide.jpg"
        assert storage.media_bytes(stored) == (b"jpeg", "image/jpeg")
        with pytest.raises(storage.MediaMissing):
            storage.media_bytes("backend/app/config.py")  # outside output/: refused
    finally:
        image.unlink()
        out.rmdir()


def test_cloud_runner_starts_a_job_per_post(monkeypatch):
    from bot import jobs

    calls = []
    monkeypatch.setattr(jobs.settings, "job_runner", "cloudrun")
    monkeypatch.setattr(
        jobs,
        "_start_cloud_run_job",
        lambda post_id, render_only: calls.append((post_id, render_only)),
    )
    jobs.submit(7, render_only=True)
    assert calls == [(7, True)]


def test_hashtags_keep_indic_vowel_signs():
    assert writer.normalize_hashtags(["गांव का मेला", "#छठ-पूजा", "தமிழ்நாடு", "#AI Tools!"]) == [
        "#गांवकामेला",
        "#छठपूजा",
        "#தமிழ்நாடு",
        "#aitools",
    ]
