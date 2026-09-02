from fastapi import FastAPI, HTTPException
from backend.database import test_connection
from backend.llm import generate_sql, generate_sql_from_clarification
from backend.schema import get_database_schema
from backend.validator import validate_sql
from backend.executor import execute_sql
from backend.models import QueryRequest
from backend.conversation import (
    save_conversation,
    get_conversation,
    update_clarification,
    delete_conversation,
)

app = FastAPI()


@app.get("/")
def root():
    return {"message": "Text-to-SQL API is running"}


@app.get("/test-db")
def test_db():
    result = test_connection()
    return {"database": "connected", "result": result}


@app.get("/generate-sql")
def generate_sql_endpoint(question: str):
    sql = generate_sql(question)

    is_valid, message = validate_sql(sql)

    return {"question": question, "sql": sql, "valid": is_valid, "message": message}


@app.get("/schema")
def database_schema():
    return get_database_schema()


@app.post("/query")
def query_database(request: QueryRequest):

    try:
        # First turn: user asks a new question
        if request.question:

            response = generate_sql(request.question)

            if response.status == "clarification_needed":

                if not response.clarification_question:
                    return {
                        "status": "error",
                        "message": "LLM requested clarification but did not provide a question."
                    }

                save_conversation(
                    request.conversation_id,
                    request.question,
                    response.clarification_question
                )

                return {
                    "status": "clarification_needed",
                    "clarification_question": response.clarification_question
                }

            # LLM says the query is ready
            if not response.sql:
                return {
                    "status": "error",
                    "message": "LLM returned ready status without SQL."
                }

            is_valid, message = validate_sql(response.sql)

            if not is_valid:
                return {
                    "status": "error",
                    "message": message
                }

            result = execute_sql(response.sql)

            return {
                "status": "ready",
                "sql": response.sql,
                "result": result
            }

        # Second turn: user provides clarification
        if request.clarification_answer:

            conversation = get_conversation(request.conversation_id)

            if not conversation:
                return {
                    "status": "error",
                    "message": "Conversation not found."
                }

            response = generate_sql_from_clarification(
                conversation.original_question,
                request.clarification_answer
            )

            if response.status == "clarification_needed":

                if not response.clarification_question:
                    return {
                        "status": "error",
                        "message": "LLM requested clarification but did not provide a question."
                    }

                update_clarification(
                    request.conversation_id,
                    response.clarification_question
                )

                return {
                    "status": "clarification_needed",
                    "clarification_question": response.clarification_question
                }

            # Clarification resolved
            if not response.sql:
                return {
                    "status": "error",
                    "message": "LLM returned ready status without SQL."
                }

            is_valid, message = validate_sql(response.sql)

            if not is_valid:
                return {
                    "status": "error",
                    "message": message
                }

            result = execute_sql(response.sql)

            delete_conversation(request.conversation_id)

            return {
                "status": "ready",
                "sql": response.sql,
                "result": result
            }

    except Exception as e:
        return {
            "status": "error",
            "message": "An unexpected error occurred while processing the query."
        }