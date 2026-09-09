from backend.answer_generator import generate_human_readable_answer
from backend.llm import generate_sql
from backend.executor import execute_sql

questions = [
    "How many customers do we have in total?",
    "Show me our top customers.",
    "What was our total revenue in 2007?",
    "Which customers placed an order in Antarctica?",
    "List all customers.",
]


for question in questions:
    print("\n" + "=" * 70)
    print("QUESTION:")
    print(question)
    print("=" * 70)

    try:
        sql_response = generate_sql(question)

        print("\nGENERATED SQL:")
        print(sql_response.sql)

        if sql_response.status != "ready":
            print("\nSTATUS:")
            print(sql_response.status)

            if sql_response.clarification_question:
                print("CLARIFICATION:")
                print(sql_response.clarification_question)

            continue

        results = execute_sql(sql_response.sql)

        print("\nDATABASE RESULT:")
        print(results)

        answer = generate_human_readable_answer(
            question=question,
            sql=sql_response.sql,
            results=results,
        )

        print("\nHUMAN-READABLE ANSWER:")
        print(answer)

    except Exception as e:
        print("\nERROR:")
        print(type(e).__name__, str(e))
