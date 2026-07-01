"""실습 - Pydantic 기반 도구 인자 검증 (템플릿)

메모를 생성하는 create_memo 도구에 두 겹의 입력 검증을 적용합니다.
  - 스키마 검증 : 타입/길이/필수 여부는 Pydantic 모델 정의만으로 함수 실행 전에 자동 적용
  - 비즈니스 검증 : 스키마로 표현하기 어려운 규칙(중복 제목 등)은 함수 안에서 ToolError로 처리

검증 실패 메시지는 그대로 모델(AI)에게 전달되어, 모델이 인수를 고쳐 재시도하는 단서가 됩니다.
모델은 함수 본문을 보지 못하므로, 필드 description과 에러 메시지가 곧 AI가 읽는 명세입니다.

과제: 아래 TODO 3곳을 채워 검증을 완성하세요.
  [검증 1] 스키마 제약   - title/content에 길이 제약과 description 부여
  [검증 2] 비즈니스 규칙 - 공백만으로 이루어진 제목을 field_validator로 차단
  [검증 3] 명확한 에러   - 중복 제목일 때 모델이 고칠 수 있는 ToolError 메시지 작성
"""

from typing import Annotated

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from pydantic import BaseModel, Field, field_validator

mcp = FastMCP("Memo Server")

# 생성된 메모를 보관하는 임시 저장소 (서버 프로세스 메모리)
_MEMOS: dict[str, str] = {}


# ── 참고 예시 (완성본) ──────────────────────────────────────────────
# 메모와 도메인만 다른 '연락처' 도구입니다. 구현 구조는 아래 과제와 똑같습니다.
#   Field 길이·description 제약 + field_validator(공백 차단) + 중복 시 ToolError
# 이 예시를 그대로 따라 MemoInput / create_memo를 완성하세요.
_CONTACTS: dict[str, str] = {}


class ContactInput(BaseModel):
    name: Annotated[
        str, Field(min_length=1, max_length=30, description="연락처 이름 (1~30자)")
    ]
    phone: Annotated[
        str, Field(min_length=1, max_length=20, description="전화번호 (1~20자)")
    ]

    @field_validator("name")
    @classmethod
    def name_not_blank(cls, v: str) -> str:
        # 공백만으로 이루어진 이름은 min_length는 통과하지만 의미가 없으므로 차단
        stripped = v.strip()
        if not stripped:
            raise ValueError("이름은 공백만으로 채울 수 없습니다. 실제 이름을 입력하세요.")
        return stripped


@mcp.tool
def add_contact(contact: ContactInput) -> dict:
    """이름과 전화번호를 받아 연락처를 저장합니다. (참고 예시)"""
    # 같은 이름이 이미 있으면 거부 (스키마로 표현할 수 없는 규칙 -> ToolError)
    if contact.name in _CONTACTS:
        raise ToolError(
            f"'{contact.name}' 연락처가 이미 있습니다. "
            "다른 이름을 쓰거나 기존 연락처를 수정하세요."
        )
    _CONTACTS[contact.name] = contact.phone
    return {"status": "created", "name": contact.name}


# ── 여기부터 과제: 위 예시를 참고해 MemoInput / create_memo를 완성하세요 ──
class MemoInput(BaseModel):
    """create_memo 도구의 입력 스키마.

    각 필드에 단 제약(타입·길이·description)은 그대로 도구의 inputSchema가 되어
    모델에게 노출되고, 위반 시 함수가 실행되기 전에 검증 에러가 반환됩니다.
    """

    # TODO [검증 1 · 스키마 제약]: title은 1~50자, content는 1~2000자로 제한하고
    #     각각 description을 달아 모델이 무엇을 넣어야 하는지 알 수 있게 하세요.
    #     예) Annotated[str, Field(min_length=1, max_length=50, description="...")]
    title: Annotated[
        str,
        Field(description="제목",min_length=1,max_length=50)
    ]
    content: Annotated[
        str,
        Field(description="내용",min_length=1,max_length=2000)
    ]

    @field_validator("title")
    @classmethod
    def title_not_blank(cls, v: str) -> str:
        # TODO [검증 2 · 비즈니스 규칙]: 공백만으로 이루어진 제목(min_length는 통과)을 차단하세요.
        #     v.strip() 결과가 비어 있으면 ValueError를 던지고, 아니면 정리된 값을 반환합니다.
        #     ValueError 메시지는 그대로 모델에게 전달되므로 "어떻게 고쳐야 하는지"까지 적으세요.
        splited = v.split
        if not splited:
            raise ValueError("공백의 제목은 안돼요.")
        return splited


@mcp.tool
def create_memo(memo: MemoInput) -> dict:
    """제목과 내용을 받아 메모를 저장하고, 저장 결과를 반환합니다."""
    # TODO [검증 3 · 명확한 에러]: 같은 제목의 메모가 이미 있으면(memo.title in _MEMOS)
    #     ToolError를 던지세요. 모델이 다음 행동(다른 제목/수정)을 고를 수 있는 메시지여야 합니다.
    if memo.title in _MEMOS:
        raise ToolError("이미 같은 제목의 메모가 있습니다.")


    _MEMOS[memo.title] = memo.content
    return {
        "status": "created",
        "title": memo.title,
        "content_length": len(memo.content),
    }


@mcp.tool
def list_memos() -> list[str]:
    """저장된 메모의 제목 목록을 반환합니다."""
    return list(_MEMOS.keys())


if __name__ == "__main__":
    mcp.run()
