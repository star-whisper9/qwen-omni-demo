import io
import logging
import tempfile
import time
from pathlib import Path
from typing import Optional, Tuple

import numpy as np
import soundfile as sf

logger = logging.getLogger(__name__)


class AudioHandler:
    def __init__(self, sample_rate: int = 24000):
        self.sample_rate = sample_rate
        self.temp_dir = Path(tempfile.gettempdir()) / "qwen_audio"
        self.temp_dir.mkdir(parents=True, exist_ok=True)

    def save_audio(self, audio_data: bytes, client_id: str) -> Tuple[str, np.ndarray]:
        """安全地保存音频数据并返回文件路径和数组"""
        try:
            # 转换音频数据
            audio_array = np.frombuffer(audio_data, dtype=np.float32)
            audio_array = np.clip(audio_array, -1.0, 1.0)

            # 生成唯一文件名
            timestamp = int(time.time() * 1000)
            temp_path = self.temp_dir / f"input_{client_id}_{timestamp}.wav"

            # 写入文件
            sf.write(
                str(temp_path),
                audio_array,
                self.sample_rate,
                format='WAV',
                subtype='FLOAT'
            )

            # 验证文件写入
            if not temp_path.exists():
                raise IOError(f"Failed to write audio file: {temp_path}")

            # 确保文件完整性
            with sf.SoundFile(str(temp_path)) as f:
                if f.frames == 0:
                    raise IOError("Written audio file is empty")

            return str(temp_path), audio_array

        except Exception as e:
            logger.error(f"Error saving audio: {str(e)}")
            raise

    def load_audio(self, file_path: str) -> Optional[np.ndarray]:
        """安全地加载音频文件"""
        try:
            audio_array, _ = sf.read(file_path)
            return audio_array
        except Exception as e:
            logger.error(f"Error loading audio: {str(e)}")
            return None

    def save_response(self, audio_array: np.ndarray) -> bytes:
        """将模型响应转换为音频字节"""
        try:
            buffer = io.BytesIO()
            sf.write(
                buffer,
                audio_array,
                self.sample_rate,
                format='WAV',
                subtype='FLOAT'
            )
            return buffer.getvalue()
        except Exception as e:
            logger.error(f"Error saving response: {str(e)}")
            raise

    def cleanup_temp_files(self, max_age: int = 300):
        """清理过期的临时文件"""
        try:
            current_time = time.time()
            for temp_file in self.temp_dir.glob("*.wav"):
                if current_time - temp_file.stat().st_mtime > max_age:
                    temp_file.unlink(missing_ok=True)
        except Exception as e:
            logger.error(f"Error cleaning up temp files: {str(e)}")
