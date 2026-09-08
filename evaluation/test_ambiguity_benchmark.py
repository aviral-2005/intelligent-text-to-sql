import json
from pathlib import Path

from backend.ambiguity import detect_ambiguity


BENCHMARK = Path("evaluation/benchmark_verified.json")


data = json.loads(
    BENCHMARK.read_text(encoding="utf-8")
)

correct = 0
incorrect = 0


for item in data["benchmark"]:

    question = item["question"]

    expected_ambiguous = (
        item["expected_behavior"] == "clarification"
    )

    result = detect_ambiguity(question)

    actual_ambiguous = result.is_ambiguous

    is_correct = (
        expected_ambiguous == actual_ambiguous
    )

    if is_correct:
        correct += 1
        status = "PASS"
    else:
        incorrect += 1
        status = "FAIL"

    print(
        f"Q{item['id']:02d} | "
        f"{status} | "
        f"Expected: {expected_ambiguous} | "
        f"Actual: {actual_ambiguous} | "
        f"{question}"
    )


total = correct + incorrect
accuracy = correct / total * 100


print("\n========== AMBIGUITY EVALUATION ==========")
print(f"Total:       {total}")
print(f"Correct:     {correct}")
print(f"Incorrect:   {incorrect}")
print(f"Accuracy:    {accuracy:.2f}%")
print("==========================================")