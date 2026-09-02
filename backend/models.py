from typing import Literal
from pydantic import BaseModel


class SQLResponse(BaseModel):
    status: Literal["ready", "clarification_needed"]
    sql: str | None = None
    clarification_question: str | None = None


class QueryRequest(BaseModel):
    conversation_id: str
    question: str | None = None
    clarification_answer: str | None = None