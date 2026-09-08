import json
from pathlib import Path


BENCHMARK = Path("evaluation/benchmark_verified.json")
BASELINE = Path("evaluation/baseline_evaluation.json")


benchmark_data = json.loads(
    BENCHMARK.read_text(encoding="utf-8")
)

baseline_data = json.loads(
    BASELINE.read_text(encoding="utf-8")
)


benchmark_by_id = {
    item["id"]: item
    for item in benchmark_data["benchmark"]
}


print("\n========== BASELINE FAILURES ==========\n")

for item in baseline_data["details"]:

    if item["correct"]:
        continue

    question_id = item["id"]
    benchmark = benchmark_by_id[question_id]

    print(f"Q{question_id:02d}")
    print(f"Question: {item['question']}")
    print(f"Category: {benchmark['category']}")
    print(f"Expected behavior: {benchmark['expected_behavior']}")
    print(f"Status: {item['status']}")

    if item.get("reason"):
        print(f"Reason: {item['reason']}")

    if item.get("generated_sql"):
        print(f"Generated SQL:\n{item['generated_sql']}")

    print("-" * 70)


print("\n========== END ==========\n")