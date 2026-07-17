"""maskingtape — 한국어 개인정보 비식별화 엔진.

사용 예:
    from maskingtape import Pipeline

    result = Pipeline().anonymize("주민번호 800101-1234560 문의주세요")
    print(result.text)  # 주민번호 ************** 문의주세요
"""

from maskingtape.pipeline import AnonymizeResult, Pipeline
from maskingtape.types import Detection

__version__ = "0.1.0"
__all__ = ["AnonymizeResult", "Detection", "Pipeline", "__version__"]
