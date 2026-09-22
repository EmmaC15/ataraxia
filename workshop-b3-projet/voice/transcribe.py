from faster_whisper import WhisperModel
from audio_device import record_audio


model = WhisperModel(
    "small",
    device="cpu"
)


def transcrire_audio():
    audio_file = record_audio(
        "audio.wav",
        duration=10
    )

    segments, info = model.transcribe(
        audio_file,
        language="fr"
    )

    text = ""

    for segment in segments:
        text += segment.text

    return text


#test d'affichage du texte dans le terminal
print(transcrire_audio())
