"""
enhance/ai — AI-based enhancement decision models.

Fase 27F: Mock CNN Architecture.

Exports:
    EnhanceModel  — Abstract base class (interface.py)
    MockCNN       — Sigmoid-based mock model (mock_cnn.py) [added in 27F-B]
"""

from .interface import EnhanceModel
from .mock_cnn import MockCNN

__all__ = ["EnhanceModel", "MockCNN"]
