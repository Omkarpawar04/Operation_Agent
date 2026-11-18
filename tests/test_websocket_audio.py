
"""Tests for the WebSocket audio processor."""

import pytest

from audio.websocket_audio import (
    WebSocketAudioProcessor,
    WebSocketAudioError,
)


class FakeVAD:
    """Returns predefined speech/silence classifications."""

    def __init__(self, sequence):
        self.sequence = list(sequence)

    def is_speech(self, frame, sample_rate):
        if not self.sequence:
            return False

        return self.sequence.pop(0)


@pytest.fixture
def processor():
    instance = WebSocketAudioProcessor(
        sample_rate=16000,
        frame_duration_ms=20,
        silence_duration_ms=40,
    )

    return instance


def test_process_speech_utterance(processor):
    processor.vad.vad = FakeVAD([True, True, False, False])

    result = processor.process_audio(bytes(640 * 4))

    assert result.speech_started is True
    assert result.speech_ended is True
    assert result.completed_audio is not None
    assert len(result.completed_utterances) == 1


def test_pre_roll_preserves_audio_before_vad_detects_first_word():
    processor = WebSocketAudioProcessor(
        sample_rate=16000,
        frame_duration_ms=20,
        silence_duration_ms=40,
    )
    processor.vad.vad = FakeVAD([False, True, False, False])
    frames = [bytes([value]) * 640 for value in (1, 2, 3, 4)]

    result = processor.process_audio(b"".join(frames))

    assert result.completed_audio is not None
    assert result.completed_audio.startswith(frames[0] + frames[1])


def test_preserve_multiple_utterances_in_one_chunk(processor):
    processor.vad.vad = FakeVAD([
        True, False, False,
        True, False, False,
    ])

    result = processor.process_audio(bytes(640 * 6))

    assert result.speech_started is True
    assert result.speech_ended is True

    assert len(result.completed_utterances) == 2

    assert all(
        isinstance(audio, bytes)
        for audio in result.completed_utterances
    )

    assert result.completed_audio == result.completed_utterances[0]


def test_preserve_partial_frame(processor):
    processor.process_audio(bytes(320))

    assert processor.get_frame_buffer_size() == 320

    processor.process_audio(bytes(320))

    assert processor.get_frame_buffer_size() == 0


def test_reject_invalid_pcm(processor):
    with pytest.raises(WebSocketAudioError):
        processor.process_audio(bytes(101))


def test_reset_processor(processor):
    processor.process_audio(bytes(320))

    processor.reset()

    assert processor.get_frame_buffer_size() == 0
    assert processor.get_buffer_size() == 0
    assert processor.is_speaking is False


def test_default_answer_buffer_allows_long_answers():
    instance = WebSocketAudioProcessor()

    assert instance.max_buffer_seconds == 120


def test_configured_answer_buffer_limit_is_enforced():
    instance = WebSocketAudioProcessor(max_buffer_seconds=1)

    with pytest.raises(WebSocketAudioError, match="buffer limit"):
        instance.process_audio(bytes(instance.sample_rate * 2 * 2))

