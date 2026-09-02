from backend.llm import generate_sql_from_clarification


original_question = "Show me the top customers."
clarification_answer = "By number of orders."


response = generate_sql_from_clarification(
    original_question,
    clarification_answer
)

print(response)
print(response.model_dump())