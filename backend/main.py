from fastapi import FastAPI
from backend.database import test_connection
from backend.llm import generate_sql
from backend.schema import get_database_schema
from backend.validator import validate_sql
from backend.executor import execute_sql

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

    return {
        "question": question,
        "sql": sql,
        "valid": is_valid,
        "message": message
    }

@app.get("/schema")
def database_schema():
    return get_database_schema()

@app.get("/query")
def query_database(question: str):
    # Step 1: Generate SQL
    sql = generate_sql(question)

    # Step 2: Validate SQL
    is_valid, message = validate_sql(sql)

    if not is_valid:
        return {
            "question": question,
            "sql": sql,
            "valid": False,
            "message": message,
            "result": None
        }

    # Step 3: Execute SQL
    result = execute_sql(sql)

    return {
        "question": question,
        "sql": sql,
        "valid": True,
        "message": message,
        "result": result
    }