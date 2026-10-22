import base64
import mimetypes
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from bot.settings import BrandKit, load_brand_kit, resolve_asset
from bot.writer.schemas import (
    CarouselDraft,
    Draft,
    ExplainerDraft,
    ImageDraft,
    PhotoDraft,
    ReelDraft,
)

FEED_SIZE = {"width": 1080, "height": 1350}
TEMPLATES = Environment(
    loader=FileSystemLoader(Path(__file__).parent / "templates"),
    autoescape=select_autoescape(["html"]),
)
FONT_FORMATS = {".ttf": "truetype", ".otf": "opentype", ".woff": "woff", ".woff2": "woff2"}


def build_pages(draft: Draft, brand: BrandKit, photo_uri: str | None = None) -> list[str]:
    """Return the HTML for each feed image in the post. Photos need their generated image."""
    context = {"brand": brand, "font_faces": _font_faces(brand), "logo_uri": _logo_uri(brand)}

    if isinstance(draft, CarouselDraft):
        template = TEMPLATES.get_template("slide.html")
        total = len(draft.slides)
        return [
            template.render(
                **context,
                slide=slide,
                index=i,
                total=total,
                heading_size=_heading_size(slide.heading, title=slide.kind == "title"),
            )
            for i, slide in enumerate(draft.slides, 1)
        ]

    if isinstance(draft, PhotoDraft):
        return [
            TEMPLATES.get_template("photo.html").render(
                **context,
                photo_uri=photo_uri,
                headline=draft.headline.strip(),
                text_position=draft.text_position,
                heading_size=_heading_size(draft.headline, title=False),
            )
        ]

    if not isinstance(draft, ImageDraft):
        raise TypeError(f"Unsupported draft type: {type(draft).__name__}")
    headline, subline, layout = draft.headline, draft.subline, draft.layout

    template = TEMPLATES.get_template("image.html")
    return [
        template.render(
            **context,
            headline=headline,
            subline=subline,
            layout=layout,
            heading_size=_heading_size(headline, title=True),
        )
    ]


def render_post(
    draft: Draft, out_dir: Path, brand: BrandKit | None = None, language: str | None = None
) -> list[Path]:
    """Render the post's media: JPEG slides/photo, or video.mp4 + cover.jpg for a reel."""
    from playwright.sync_api import sync_playwright

    brand = brand or load_brand_kit()
    out_dir.mkdir(parents=True, exist_ok=True)
    if isinstance(draft, ReelDraft):
        from bot.media.reel import render_reel

        return render_reel(draft, out_dir, brand, _voice(draft, brand, language))
    if isinstance(draft, ExplainerDraft):
        from bot.media.diagram import render_explainer

        return render_explainer(draft, out_dir, brand, _voice(draft, brand, language))

    photo_uri = None
    if isinstance(draft, PhotoDraft):
        from bot.media.ai_images import generate_image

        photo = generate_image(
            draft.image_prompt, "3:4", out_dir / "ai_photo", draft.visual_style, brand.image_style
        )
        photo_uri = _data_uri(photo)
    pages = build_pages(draft, brand, photo_uri)
    prefix = "slide"

    paths = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        try:
            page = browser.new_page(viewport=FEED_SIZE)
            for i, html in enumerate(pages, 1):
                page.set_content(html, wait_until="load")
                # Instagram's publishing API only accepts JPEG images.
                path = out_dir / (f"{prefix}.jpg" if len(pages) == 1 else f"{prefix}_{i:02d}.jpg")
                page.screenshot(path=path, type="jpeg", quality=95)
                paths.append(path)
        finally:
            browser.close()
    return paths


def _voice(draft: ReelDraft | ExplainerDraft, brand: BrandKit, language: str | None):
    from bot.languages import voice_for

    lines = draft.scenes if isinstance(draft, ReelDraft) else draft.steps
    return voice_for(
        brand.voiceover, language=language, sample_text=" ".join(x.voiceover for x in lines[:3])
    )


def _heading_size(text: str, *, title: bool) -> str:
    length = len(text)
    if title and length <= 28:
        return "h-xl"
    if length <= 45:
        return "h-lg"
    if length <= 70:
        return "h-md"
    return "h-sm"


def _data_uri(path: Path) -> str:
    mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    return f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode()}"


def _logo_uri(brand: BrandKit) -> str | None:
    if not brand.logo:
        return None
    path = resolve_asset(brand.logo)
    return _data_uri(path) if path.is_file() else None


def _font_faces(brand: BrandKit) -> str:
    rules = []
    for family, file, weight in (
        (brand.fonts.heading, brand.fonts.heading_file, 800),
        (brand.fonts.body, brand.fonts.body_file, 400),
    ):
        if not file:
            continue
        path = resolve_asset(file)
        if not path.is_file():
            continue
        fmt = FONT_FORMATS.get(path.suffix.lower(), "truetype")
        rules.append(
            f'@font-face {{ font-family: "{family}"; font-weight: {weight}; '
            f'src: url("{_data_uri(path)}") format("{fmt}"); }}'
        )
    return "\n".join(rules)
