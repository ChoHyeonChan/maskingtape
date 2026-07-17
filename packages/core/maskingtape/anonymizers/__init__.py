"""마스킹 전략 모음. 새 전략을 만들면 여기서 export한다."""

from maskingtape.anonymizers.base import Anonymizer
from maskingtape.anonymizers.mask import MaskAnonymizer

__all__ = ["Anonymizer", "MaskAnonymizer"]
