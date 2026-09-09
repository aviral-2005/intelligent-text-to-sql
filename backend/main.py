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
from backend.ambiguity import detect_ambiguity
from backend.answer_generator import generate_human_readable_answer

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

            # Step 1: Detect ambiguity before generating SQL
            ambiguity = detect_ambiguity(request.question)

            if ambiguity.is_ambiguous:

                if not ambiguity.clarification_question:
                    return {
                        "status": "error",
                        "message": "Question was detected as ambiguous but no clarification was provided."
                    }

                save_conversation(
                    request.conversation_id,
                    request.question,
                    ambiguity.clarification_question
                )

                return {
                    "status": "clarification_needed",
                    "clarification_question": ambiguity.clarification_question
                }

            # Step 2: Question is clear → generate SQL
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

            answer = generate_human_readable_answer(
                request.question,
                response.sql,
                result
            )

            return {
                "status": "ready",
                "answer": answer,
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

            answer = generate_human_readable_answer(
                conversation.original_question,
                response.sql,
                result
            )

            delete_conversation(request.conversation_id)

            return {
                "status": "ready",
                "answer": answer,
                "sql": response.sql,
                "result": result
            }

    except Exception as e:
        return {
            "status": "error",
            "message": "An unexpected error occurred while processing the query."
        }