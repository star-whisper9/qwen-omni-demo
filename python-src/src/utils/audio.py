import io
import numpy as np
import torch
import wave
import webrtcvada
from typing import Optional


class AudioProcessor:
    def __init__(self):
        self.vad = webrtcvad.Vad(3)  # 灵敏度设置为3(最高)
        self.buffer = []
        self.sample_rate = 24000
        self.frame_duration = 30  # ms
        self.silent_chunks = 0
        self.silent_threshold = 10  # 静默帧阈值

    async def process_chunk(self, audio_data: bytes) -> Optional[bytes]:
        # 将bytes转换为numpy数组
        audio_array = np.frombuffer(audio_data, dtype=np.float32)

        # 检测是否有声音
        is_speech = self._detect_speech(audio_array)

        if is_speech:
            self.buffer.append(audio_array)
            self.silent_chunks = 0

            if len(self.buffer) >= 5:  # 积累了足够的音频数据
                return self._get_audio_segment()
        else:
            self.silent_chunks += 1
            if self.buffer and self.silent_chunks >= self.silent_threshold:
                return self._get_audio_segment()

        return None

    def _detect_speech(self, audio_array: np.ndarray) -> bool:
        # 将float32转换为int16
        audio_int16 = (audio_array * 32768).astype(np.int16)

        # 重采样到16kHz (VAD需要)
        if self.sample_rate != 16000:
            # 简单的重采样，实际项目中建议使用librosa等专业库
            audio_int16 = audio_int16[::self.sample_rate // 16000]

        # 将音频分成30ms的帧
        samples_per_frame = int(16000 * self.frame_duration / 1000)
        frames = []
        for i in range(0, len(audio_int16), samples_per_frame):
            frame = audio_int16[i:i + samples_per_frame]
            if len(frame) == samples_per_frame:
                frames.append(frame.tobytes())

        # 检测每一帧是否包含语音
        speech_frames = 0
        for frame in frames:
            try:
                if self.vad.is_speech(frame, 16000):
                    speech_frames += 1
            except Exception:
                continue

        # 如果超过30%的帧包含语音，则认为这个块包含语音
        return speech_frames / max(len(frames), 1) > 0.3

    def _get_audio_segment(self) -> bytes:
        if not self.buffer:
            return None

        # 合并缓冲区中的所有音频数据
        audio_data = np.concatenate(self.buffer)

        # 清空缓冲区
        self.buffer = []
        self.silent_chunks = 0

        # 转换为bytes
        audio_bytes = io.BytesIO()
        with wave.open(audio_bytes, 'wb') as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(4)  # float32 = 4 bytes
            wav_file.setframerate(self.sample_rate)
            wav_file.writeframes(audio_data.tobytes())

        return audio_bytes.getvalue()
