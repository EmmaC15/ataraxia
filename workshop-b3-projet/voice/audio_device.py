import sounddevice as sd
import soundfile as sf

_current_device = None
SAMPLE_RATE = 16000


def get_input_devices():
    devices = sd.query_devices()

    return [
        (i, device["name"])
        for i, device in enumerate(devices)
        if device["max_input_channels"] > 0
    ]


def set_input_device(device_id):
    global _current_device
    _current_device = device_id


def record_audio(filename, duration):
    audio = sd.rec(
        int(duration * SAMPLE_RATE),
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype="float32",
        device=_current_device
    )

    sd.wait()

    sf.write(filename, audio, SAMPLE_RATE)

    return filename
