# SPDX-FileCopyrightText: 2026 The maskingtape Authors
# SPDX-License-Identifier: Apache-2.0

"""웹 하이브리드 모드의 이름 판단기 약속(#545·#546).

규칙으로 먼저 가린 글(LabelAnonymizer 결과)을 받아 아직 가려지지 않은 사람 이름만
돌려준다. API 쪽(#545)은 이 모양만 알고, 실제 판단기(OpenAI, #546)나 테스트용 가짜
판단기를 갈아 끼운다.
"""

from typing import Protocol


class NameJudgeError(RuntimeError):
    """시간 초과·네트워크·응답 형식 오류.

    메시지와 `code`에는 원문·가린 글·모델 응답을 넣지 않는다. `code`는 화면과 응답의
    실패 사유로 그대로 써도 되는 짧은 영문 코드다(예: "timeout", "refused").
    """

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


class NameJudge(Protocol):
    def find_names(self, masked_text: str) -> list[str]:
        """규칙으로 먼저 가린 글에서 사람 이름만 돌려준다."""
