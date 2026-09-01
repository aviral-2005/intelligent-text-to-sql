from fastapi import FastAPI
from backend.database import test_connection
from backend.llm import generate_sql
from backend.schema import get_database_schema

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

    return {
        "question": question,
        "sql": sql
    }

@app.get("/schema")
def database_schema():
    return get_database_schema()