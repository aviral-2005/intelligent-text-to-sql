from backend.baseline import generate_baseline_sql


question = "Show me the top customers."

response = generate_baseline_sql(question)

print("Generated SQL:")
print(response.sql)