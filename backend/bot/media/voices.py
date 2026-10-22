"""Cast a distinct speaking voice for each story character."""

from bot.settings import Voiceover
from bot.writer.schemas import Character

# Natural voices available in every supported language, in order of preference per role.
FEMALE = {
    "child": ["Leda", "Kore", "Zephyr"],
    "teen": ["Kore", "Leda", "Aoede", "Zephyr"],
    "adult": ["Aoede", "Despina", "Callirrhoe", "Autonoe", "Erinome", "Laomedeia", "Achernar"],
    "elderly": ["Gacrux", "Sulafat", "Vindemiatrix", "Pulcherrima"],
}
MALE = {
    "child": ["Puck", "Fenrir"],
    "teen": ["Puck", "Fenrir", "Orus"],
    "adult": ["Orus", "Iapetus", "Umbriel", "Algenib", "Enceladus", "Sadaltager", "Alnilam"],
    "elderly": ["Charon", "Rasalgethi", "Schedar", "Sadachbia"],
}
ALL = {
    "female": [v for voices in FEMALE.values() for v in voices],
    "male": [v for voices in MALE.values() for v in voices],
}
SPEAKING_RATE = {"child": 1.06, "teen": 1.03, "adult": 1.0, "elderly": 0.92}


def cast_voices(characters: list[Character], narrator: Voiceover) -> dict[str, Voiceover]:
    """Map character name -> voice in the narrator's language, never reusing the narrator's."""
    locale = "-".join(narrator.voice.split("-")[:2])
    used = {narrator.voice.split("-")[-1]}
    cast = {}
    for character in characters:
        table = FEMALE if character.gender == "female" else MALE
        options = table[character.age] + ALL[character.gender]
        name = next((v for v in options if v not in used), options[0])
        used.add(name)
        cast[character.name] = Voiceover(
            voice=f"{locale}-Chirp3-HD-{name}", speaking_rate=SPEAKING_RATE[character.age]
        )
    return cast
