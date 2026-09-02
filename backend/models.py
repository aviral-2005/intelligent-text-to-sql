from typing import Literal
from pydantic import BaseModel, model_validator


class SQLResponse(BaseModel):
    status: Literal["ready", "clarification_needed"]
    sql: str | None = None
    clarification_question: str | None = None


class QueryRequest(BaseModel):
    conversation_id: str
    question: str | None = None
    clarification_answer: str | None = None

    @model_validator(mode="after")
    def validate_request(self):
        has_question = bool(self.question and self.question.strip())
        has_answer = bool(
            self.clarification_answer
            and self.clarification_answer.strip()
        )

        if has_question == has_answer:
            raise ValueError(
                "Provide exactly one of question or clarification_answer."
            )

        return self