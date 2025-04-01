import io
import numpy as np
import soundfile as sf
from pydub import AudioSegment

class AudioProcessor:
    def __init__(self):
        self.sample_rate = 24000  # 模型需要的采样率

    def webm_to_float32(self, webm_bytes: bytes) -> np.ndarray:
        """将 WEBM 格式的音频数据转换为 float32 数组"""
        # 使用 pydub 读取 WEBM
        audio = AudioSegment.from_file(io.BytesIO(webm_bytes), format="webm")

        # 转换为单声道、指定采样率
        audio = audio.set_channels(1).set_frame_rate(self.sample_rate)

        # 获取原始采样数据
        samples = np.array(audio.get_array_of_samples(), dtype=np.float32)

        # 归一化到 [-1, 1] 范围
        samples = samples / 32768.0

        return samples

    def float32_to_wav(self, audio_data: np.ndarray, sample_rate: int = 24000) -> bytes:
        """将 float32 数组转换为 WAV 字节数据"""
        # 确保数据范围在 [-1, 1] 之间
        audio_data = np.clip(audio_data, -1.0, 1.0)

        # 写入 WAV 格式
        with io.BytesIO() as wav_buffer:
            sf.write(
                wav_buffer,
                audio_data,
                sample_rate,
                format='WAV',
                subtype='PCM_16'  # 16位深度
            )
            return wav_buffer.getvalue()

    def resample(self, audio_data: np.ndarray, original_rate: int, target_rate: int) -> np.ndarray:
        """重采样音频数据"""
        if original_rate == target_rate:
            return audio_data

        from scipy import signal
        duration = len(audio_data) / original_rate
        target_length = int(duration * target_rate)
        resampled = signal.resample(audio_data, target_length)

        return resampled


# 全局实例
audio_processor = AudioProcessor()