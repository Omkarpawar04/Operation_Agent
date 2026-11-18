
"""
Tests for Voice Activity Detection (VAD).

Uses a fake VAD engine to test speech and silence
without requiring a real microphone.
"""

import pytest

from audio.vad import VoiceActivityDetector


class FakeVAD:
    """Simulates WebRTC VAD speech detection."""

    def __init__(self, speech_sequence):
        self.speech_sequence = list(speech_sequence)

    def is_speech(self, frame, sample_rate):
        if not self.speech_sequence:
            return False

        return self.speech_sequence.pop(0)


@pytest.fixture
def detector():
    """Create a VAD detector with a 20ms frame size."""

    instance = VoiceActivityDetector(
        sample_rate=16000,
        frame_duration_ms=20,
        silence_duration_ms=40,
    )

    return instance


def test_detect_speech_started(detector):
    """First speech frame should emit speech_started."""

    detector.vad = FakeVAD([True])

    frame = bytes(640)

    result = detector.process_frame(frame)

    assert result.event == "speech_started"
    assert result.is_speech is True
    assert result.speech_duration_ms == 20


def test_detect_continuous_speech(detector):
    """Subsequent speech frames should emit speech."""

    detector.vad = FakeVAD([True, True])

    frame = bytes(640)

    first_result = detector.process_frame(frame)
    second_result = detector.process_frame(frame)

    assert first_result.event == "speech_started"
    assert second_result.event == "speech"
    assert second_result.is_speech is True
    assert second_result.speech_duration_ms == 40


def test_detect_silence(detector):
    """Silence below the threshold should emit silence."""

    detector.vad = FakeVAD([True, False])

    frame = bytes(640)

    detector.process_frame(frame)
    result = detector.process_frame(frame)

    assert result.event == "silence"
    assert result.is_speech is False
    assert result.silence_duration_ms == 20


def test_detect_speech_ended(detector):
    """Silence reaching the threshold should end speech."""

    detector.vad = FakeVAD([True, False, False])

    frame = bytes(640)

    detector.process_frame(frame)

    detector.process_frame(frame)

    result = detector.process_frame(frame)

    assert result.event == "speech_ended"
    assert result.is_speech is False

    # The detector should preserve the duration
    # of the completed speech segment.
    assert result.speech_duration_ms == 20


def test_450ms_endpoint_ends_after_460ms_at_20ms_frame_granularity():
    """The 450 ms threshold is applied on complete 20 ms VAD frames."""
    detector = VoiceActivityDetector(
        sample_rate=16000,
        frame_duration_ms=20,
        silence_duration_ms=450,
    )
    detector.vad = FakeVAD([True] + [False] * 23)

    result = None
    for _ in range(24):
        result = detector.process_frame(bytes(640))
        if result.event == "speech_ended":
            break

    assert result is not None
    assert result.event == "speech_ended"
    # VAD only checks every 20 ms, so 450 ms is crossed at 460 ms.
    assert result.silence_duration_ms == 460


def test_reject_invalid_frame_size(detector):
    """Incorrect audio frame sizes should be rejected."""

    invalid_frame = bytes(100)

    with pytest.raises(ValueError):
        detector.process_frame(invalid_frame)


def test_reset_detector(detector):
    """Reset should clear the current speech state."""

    detector.vad = FakeVAD([True, False])

    frame = bytes(640)

    first_result = detector.process_frame(frame)

    assert first_result.event == "speech_started"

    detector.reset()

    result = detector.process_frame(frame)

    assert result.event == "silence"
