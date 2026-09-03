import json
from pathlib import Path

from backend.executor import execute_sql

INPUT = Path("evaluation/benchmark_with_expected_sql.json")
OUTPUT = Path("evaluation/benchmark_verified.json")

data = json.loads(INPUT.read_text(encoding="utf-8"))

for item in data["benchmark"]:
    try:
        item["expected_result"] = execute_sql(item["expected_sql"])
        item["result_verification"] = "verified"
        item.pop("verification_error", None)
        print(f"Q{item['id']:02d}: VERIFIED")
    except Exception as exc:
        item["expected_result"] = None
        item["result_verification"] = "failed"
        item["verification_error"] = str(exc)
        print(f"Q{item['id']:02d}: FAILED -> {exc}")

OUTPUT.write_text(
    json.dumps(data, indent=2, default=str),
    encoding="utf-8"
)

failed = [
    item["id"]
    for item in data["benchmark"]
    if item["result_verification"] != "verified"
]

print(f"\nVerified: {50 - len(failed)}/50")
if failed:
    print("Failed questions:", failed)
else:
    print("All 50 expected SQL queries executed successfully.")
