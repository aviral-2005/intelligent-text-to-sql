import json
from pathlib import Path

from backend.baseline import generate_baseline_sql
from backend.validator import validate_sql
from backend.executor import execute_sql


INPUT = Path("evaluation/benchmark_verified.json")
OUTPUT = Path("evaluation/baseline_results.json")


data = json.loads(INPUT.read_text(encoding="utf-8"))

results = []

for item in data["benchmark"]:

    print(f"Running Q{item['id']:02d}: {item['question']}")

    result = {
        "id": item["id"],
        "question": item["question"],
        "category": item["category"],
        "expected_behavior": item["expected_behavior"],
        "generated_sql": None,
        "execution_result": None,
        "status": None,
        "error": None,
    }

    try:
        # Generate SQL
        response = generate_baseline_sql(item["question"])

        result["generated_sql"] = response.sql

        # Validate generated SQL
        is_valid, message = validate_sql(response.sql)

        if not is_valid:
            result["status"] = "invalid_sql"
            result["error"] = message
            results.append(result)
            print(f"  -> INVALID SQL: {message}")
            continue

        # Execute generated SQL
        execution_result = execute_sql(response.sql)

        result["execution_result"] = execution_result
        result["status"] = "executed"

        print("  -> EXECUTED")

    except Exception as exc:
        result["status"] = "failed"
        result["error"] = str(exc)

        print(f"  -> FAILED: {exc}")

    results.append(result)


output = {
    "total_questions": len(results),
    "results": results
}

OUTPUT.write_text(
    json.dumps(output, indent=2, default=str),
    encoding="utf-8"
)

print("\nBaseline evaluation completed.")
print(f"Results saved to: {OUTPUT}")