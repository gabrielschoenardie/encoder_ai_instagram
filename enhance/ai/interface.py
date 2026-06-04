"""
enhance/ai/interface.py
=======================
Abstract base class for enhancement decision models.

Fase 27F — Mock CNN Architecture.

Contract:
    - predict() receives 13-dim float32 feature vector
    - predict() returns 3 continuous weights [0.0, 1.0]
      Order: [denoise_weight, sharpen_weight, deband_weight]
    - Implementations MUST NOT have side effects
    - Implementations MUST be thread-safe (stateless predict)

Swap path: MockCNN → OnnxModel → TorchModel via single import change.
"""

from abc import ABC, abstractmethod

import numpy as np


class EnhanceModel(ABC):
    """
    Abstract base class for enhancement decision models.

    Input:  13-dim feature vector (noise + banding + detail metrics)
    Output: 3-dim weight vector [denoise, sharpen, deband] in [0.0, 1.0]
    """

    FEATURE_DIM = 13
    OUTPUT_DIM = 3

    @abstractmethod
    def predict(self, features: np.ndarray) -> np.ndarray:
        """
        Map 13-dim feature vector to 3-dim enhancement weights.

        Args:
            features: shape (13,), dtype float32
                [0]  noise.sigma
                [1]  noise.low_freq_ratio
                [2]  noise.uniformity
                [3]  banding.severity
                [4]  banding.gradient_score
                [5]  banding.flat_region_pct
                [6]  detail.sharpness
                [7]  detail.texture_complexity
                [8]  detail.edge_density
                [9]  detail.freq_low
                [10] detail.freq_mid
                [11] detail.freq_high
                [12] detail.detail_score

        Returns:
            shape (3,), dtype float32, values clamped to [0.0, 1.0]
                [0] denoise_weight
                [1] sharpen_weight
                [2] deband_weight
        """
        ...

    @abstractmethod
    def name(self) -> str:
        """Human-readable model name for logging."""
        ...
