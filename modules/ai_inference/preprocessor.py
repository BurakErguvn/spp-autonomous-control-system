"""Görüntü ön işleme yardımcı fonksiyonları.

YOLO26 inference öncesi termal ve RGB görüntüleri normalize eder,
yeniden boyutlandırır ve tensor'a dönüştürür.
"""

from __future__ import annotations

import cv2
import numpy as np


# YOLO26'nın beklediği varsayılan giriş boyutu
DEFAULT_INPUT_SIZE: tuple[int, int] = (640, 640)


class Preprocessor:
    """Termal / RGB görüntüleri YOLO26 girişine hazırlar.

    Args:
        input_size: Model giriş boyutu (genişlik, yükseklik). Varsayılan (640, 640).
    """

    def __init__(self, input_size: tuple[int, int] = DEFAULT_INPUT_SIZE) -> None:
        self.input_size = input_size

    def process(self, frame: np.ndarray) -> np.ndarray:
        """Ham görüntüyü model girişi için hazırlar.

        Args:
            frame: BGR veya gri tonlamalı numpy dizisi.

        Returns:
            Yeniden boyutlandırılmış ve normalize edilmiş numpy dizisi [0, 1].

        Raises:
            ValueError: frame boş veya geçersizse.
        """
        if frame is None or frame.size == 0:
            raise ValueError("Geçersiz frame: boş veya None.")

        # Gri tonlamalı görüntüyü 3 kanala çevir (termal kamera için)
        if frame.ndim == 2:
            frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)

        resized = cv2.resize(frame, self.input_size, interpolation=cv2.INTER_LINEAR)
        normalized = resized.astype(np.float32) / 255.0
        return normalized

    def normalize_thermal(self, frame: np.ndarray) -> np.ndarray:
        """Termal görüntüye özel normalize: min-max ölçekleme.

        Termal kamera görüntülerinde sıcaklık değerleri geniş aralıkta
        dağılabilir; min-max normalize kontrast kaybını önler.

        Args:
            frame: Ham termal görüntü dizisi.

        Returns:
            [0, 255] aralığına normalize edilmiş uint8 dizi.
        """
        if frame is None or frame.size == 0:
            raise ValueError("Geçersiz frame: boş veya None.")

        f_min, f_max = frame.min(), frame.max()
        if f_max == f_min:
            return np.zeros_like(frame, dtype=np.uint8)

        normalized = (frame - f_min) / (f_max - f_min) * 255.0
        return normalized.astype(np.uint8)
