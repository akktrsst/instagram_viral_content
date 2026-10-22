"""Languages people can choose for a post, and which narration voice reads each one."""

from dataclasses import dataclass

from bot.settings import Voiceover

VOICE_NAME = "Chirp3-HD-Achird"


@dataclass(frozen=True)
class Language:
    code: str
    name: str
    native: str
    locale: str  # text-to-speech locale that reads it
    instruction: str  # how the writer should write it


LANGUAGES: dict[str, Language] = {
    lang.code: lang
    for lang in [
        Language(
            "en-IN", "English (India)", "English", "en-IN", "English, in natural Indian English."
        ),
        Language(
            "en-US", "English (US)", "English", "en-US", "English, in natural American English."
        ),
        Language("hi", "Hindi", "हिन्दी", "hi-IN", "Hindi, written in Devanagari script."),
        Language(
            "hinglish",
            "Hinglish",
            "Hinglish",
            "en-IN",
            "Hinglish: everyday Hindi-English mix written only in Roman (English) letters.",
        ),
        Language(
            "bho",
            "Bhojpuri",
            "भोजपुरी",
            "hi-IN",
            "Bhojpuri, written in Devanagari script. Use authentic Bhojpuri vocabulary and "
            "grammar (e.g. बा, बानी, रहल, हमनी के, तोहार, का हो), not Hindi with a few words "
            "swapped. Keep it natural and warm, as spoken in Bihar and eastern Uttar Pradesh.",
        ),
        Language("bn", "Bengali", "বাংলা", "bn-IN", "Bengali, written in Bengali script."),
        Language("mr", "Marathi", "मराठी", "mr-IN", "Marathi, written in Devanagari script."),
        Language("ta", "Tamil", "தமிழ்", "ta-IN", "Tamil, written in Tamil script."),
        Language("te", "Telugu", "తెలుగు", "te-IN", "Telugu, written in Telugu script."),
        Language("gu", "Gujarati", "ગુજરાતી", "gu-IN", "Gujarati, written in Gujarati script."),
        Language("kn", "Kannada", "ಕನ್ನಡ", "kn-IN", "Kannada, written in Kannada script."),
        Language("ml", "Malayalam", "മലയാളം", "ml-IN", "Malayalam, written in Malayalam script."),
        Language("pa", "Punjabi", "ਪੰਜਾਬੀ", "pa-IN", "Punjabi, written in Gurmukhi script."),
        Language("ur", "Urdu", "اردو", "ur-IN", "Urdu, written in Urdu (Perso-Arabic) script."),
    ]
}

# Locales with a natural voice, and close relatives that borrow one.
VOICE_LOCALES = {lang.locale for lang in LANGUAGES.values()}
BORROWED_VOICES = {"bho": "hi-IN", "mai": "hi-IN", "awa": "hi-IN", "raj": "hi-IN", "bh": "hi-IN"}

# Unicode script blocks -> locale, to pick a voice from the text itself.
SCRIPT_LOCALES = [
    (0x0900, 0x097F, "hi-IN"),  # Devanagari (Hindi, Marathi, Bhojpuri...)
    (0x0980, 0x09FF, "bn-IN"),
    (0x0A00, 0x0A7F, "pa-IN"),
    (0x0A80, 0x0AFF, "gu-IN"),
    (0x0B80, 0x0BFF, "ta-IN"),
    (0x0C00, 0x0C7F, "te-IN"),
    (0x0C80, 0x0CFF, "kn-IN"),
    (0x0D00, 0x0D7F, "ml-IN"),
    (0x0600, 0x06FF, "ur-IN"),
]


def get_language(code: str | None) -> Language | None:
    return LANGUAGES.get(code) if code else None


def language_instruction(language: Language | None) -> str:
    if language is None:
        return ""
    return (
        f"\n\nLANGUAGE: Write everything a viewer reads or hears (caption, slide and on-screen "
        f"text, headlines, narration, alt text) in {language.instruction} Hashtags may mix "
        "English and this language. Descriptions of images, scenes and visual style stay in "
        "English. This overrides the language of the brief."
    )


def locale_from_text(text: str) -> str | None:
    counts: dict[str, int] = {}
    for char in text:
        point = ord(char)
        for start, end, locale in SCRIPT_LOCALES:
            if start <= point <= end:
                counts[locale] = counts.get(locale, 0) + 1
    return max(counts, key=counts.get) if counts else None


def voice_for(
    brand_voice: Voiceover,
    *,
    language: str | None = None,
    locale_hint: str | None = None,
    sample_text: str = "",
) -> Voiceover:
    """The narration voice: chosen language > story's stated locale > the text's script."""
    locale = None
    if chosen := get_language(language):
        locale = chosen.locale
    elif locale_hint:
        prefix = locale_hint.split("-")[0].lower()
        normalized = f"{prefix}-{locale_hint.split('-')[1].upper()}" if "-" in locale_hint else ""
        locale = normalized if normalized in VOICE_LOCALES else BORROWED_VOICES.get(prefix)
    if locale is None:
        locale = locale_from_text(sample_text)
    brand_locale = "-".join(brand_voice.voice.split("-")[:2])
    if locale is None or locale.lower() == brand_locale.lower():
        return brand_voice
    return Voiceover(voice=f"{locale}-{VOICE_NAME}", speaking_rate=1.0)
