"""Explainer reels: a flow diagram that builds up step by step, with voiceover and captions."""

from dataclasses import dataclass
from pathlib import Path

from bot.media.reel import (
    REEL_SIZE,
    cleanup_work,
    concat_clips,
    prepare_voiceovers,
    render_overlays,
    render_scene,
)
from bot.settings import BrandKit, Voiceover, load_brand_kit
from bot.writer.schemas import ExplainerDraft

# Diagram area inside the 1080x1920 frame: below the on-screen title pill (which can wrap to
# two lines), above the captions; both stay clear of Instagram's own top and bottom UI.
AREA_LEFT, AREA_RIGHT = 60, 1020
AREA_TOP, AREA_BOTTOM = 420, 1400
COVER_TOP = 500
CAPTION_BOTTOM = 380
MAX_PER_ROW = 3
ROW_GAP = 36


@dataclass
class Box:
    id: str
    label: str
    detail: str
    x: float  # center
    y: float  # center
    w: float
    h: float
    font: int


@dataclass
class Arrow:
    source: str
    target: str
    path: str
    label: str
    label_x: float
    label_y: float


def layout(draft: ExplainerDraft, top: float = AREA_TOP) -> tuple[dict[str, Box], list[Arrow]]:
    """Layered top-to-bottom layout: each node sits one row below its furthest predecessor."""
    ids = [n.id for n in draft.nodes]
    succ: dict[str, list[str]] = {i: [] for i in ids}
    indeg = dict.fromkeys(ids, 0)
    for edge in draft.edges:
        succ[edge.source].append(edge.target)
        indeg[edge.target] += 1

    layer = dict.fromkeys(ids, 0)
    queue = [i for i in ids if indeg[i] == 0] or ids[:1]
    done: set[str] = set()
    while queue:
        node = queue.pop(0)
        if node in done:
            continue
        done.add(node)
        for nxt in succ[node]:
            layer[nxt] = max(layer[nxt], layer[node] + 1)
            indeg[nxt] -= 1
            if indeg[nxt] <= 0 and nxt not in done:
                queue.append(nxt)
    for node in ids:  # nodes on a cycle: put them below everything else
        if node not in done:
            layer[node] = max(layer.values()) + 1
            done.add(node)

    rows: list[list[str]] = []
    for level in sorted(set(layer.values())):
        members = [i for i in ids if layer[i] == level]
        rows += [members[k : k + MAX_PER_ROW] for k in range(0, len(members), MAX_PER_ROW)]

    height = AREA_BOTTOM - top
    row_h = min(280.0, height / len(rows))
    box_h = min(160.0, row_h - 70)
    start = top + (height - row_h * len(rows)) / 2
    nodes = {n.id: n for n in draft.nodes}
    boxes: dict[str, Box] = {}
    for r, row in enumerate(rows):
        width = AREA_RIGHT - AREA_LEFT
        w = min(760.0, (width - ROW_GAP * (len(row) - 1)) / len(row))
        total = w * len(row) + ROW_GAP * (len(row) - 1)
        left = AREA_LEFT + (width - total) / 2
        font = 46 if len(row) == 1 else 36 if len(row) == 2 else 30
        for c, node_id in enumerate(row):
            node = nodes[node_id]
            boxes[node_id] = Box(
                node_id,
                node.label,
                node.detail,
                left + c * (w + ROW_GAP) + w / 2,
                start + row_h * (r + 0.5),
                w,
                box_h,
                font,
            )

    arrows = [_arrow(boxes[e.source], boxes[e.target], e.label) for e in draft.edges]
    return boxes, arrows


def _arrow(a: Box, b: Box, label: str) -> Arrow:
    if b.y > a.y + 1:  # downward: bottom of a to top of b
        x1, y1, x2, y2 = a.x, a.y + a.h / 2, b.x, b.y - b.h / 2 - 6
        mid = (y1 + y2) / 2
        path = f"M{x1:.0f},{y1:.0f} C{x1:.0f},{mid:.0f} {x2:.0f},{mid:.0f} {x2:.0f},{y2:.0f}"
        return Arrow(a.id, b.id, path, label, (x1 + x2) / 2, mid)
    if abs(b.y - a.y) <= 1:  # same row: side to side
        sign = 1 if b.x > a.x else -1
        x1, x2 = a.x + sign * a.w / 2, b.x - sign * (b.w / 2 + 6)
        path = f"M{x1:.0f},{a.y:.0f} L{x2:.0f},{b.y:.0f}"
        return Arrow(a.id, b.id, path, label, (x1 + x2) / 2, a.y - 18)
    # upward (a loop back): swing out around the right side
    x1, y1 = a.x + a.w / 2, a.y
    x2, y2 = b.x + b.w / 2 + 6, b.y
    out = max(x1, x2) + 70
    path = f"M{x1:.0f},{y1:.0f} C{out:.0f},{y1:.0f} {out:.0f},{y2:.0f} {x2:.0f},{y2:.0f}"
    return Arrow(a.id, b.id, path, label, out - 10, (y1 + y2) / 2)


def frame_html(
    draft: ExplainerDraft,
    brand: BrandKit,
    visible: set[str],
    focus: set[str],
    cover: bool = False,
) -> str:
    from bot.media.render import TEMPLATES, _font_faces

    boxes, arrows = layout(draft, COVER_TOP if cover else AREA_TOP)
    return TEMPLATES.get_template("diagram_frame.html").render(
        brand=brand,
        font_faces=_font_faces(brand),
        boxes=[b for b in boxes.values() if b.id in visible],
        arrows=[a for a in arrows if a.source in visible and a.target in visible],
        focus=focus,
        title=draft.title,
        cover_title=draft.hook if cover else None,
    )


def render_explainer(
    draft: ExplainerDraft,
    out_dir: Path,
    brand: BrandKit | None = None,
    voice: Voiceover | None = None,
) -> list[Path]:
    """Render `video.mp4` and `cover.jpg` for an explainer reel."""
    from playwright.sync_api import sync_playwright

    brand = brand or load_brand_kit()
    work = out_dir / "reel_work"
    work.mkdir(parents=True, exist_ok=True)
    voices = prepare_voiceovers([s.voiceover for s in draft.steps], work, brand, voice)

    frames, visible = [], set()
    all_ids = {n.id for n in draft.nodes}
    cover = out_dir / "cover.jpg"
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        try:
            page = browser.new_page(viewport=REEL_SIZE)
            for i, step in enumerate(draft.steps):
                visible |= set(step.reveal)
                page.set_content(frame_html(draft, brand, set(visible), set(step.focus)))
                path = work / f"frame_{i}.png"
                page.screenshot(path=path)
                frames.append(path)
            page.set_content(frame_html(draft, brand, all_ids, set(), cover=True))
            page.screenshot(path=cover, type="jpeg", quality=92)
        finally:
            browser.close()

    overlays = render_overlays(
        [(s.on_screen_text, s.voiceover, d) for s, (_, d) in zip(draft.steps, voices)],
        work,
        brand,
        caption_bottom=CAPTION_BOTTOM,
    )
    clips = []
    for i, (frame, (audio, duration), scene_overlays) in enumerate(zip(frames, voices, overlays)):
        clip = work / f"scene_{i}.mp4"
        render_scene(frame, audio, duration, scene_overlays, clip, zoom_amount=0)
        clips.append(clip)

    video = out_dir / "video.mp4"
    concat_clips(clips, work, video)
    cleanup_work(work)
    return [video, cover]
