import json
from pathlib import Path
from math import isclose


BENCHMARK = Path("evaluation/benchmark_verified.json")
BASELINE = Path("evaluation/baseline_results.json")
OUTPUT = Path("evaluation/baseline_evaluation.json")


# ---------------------------------------------------------
# Load data
# ---------------------------------------------------------

benchmark_data = json.loads(
    BENCHMARK.read_text(encoding="utf-8")
)

baseline_data = json.loads(
    BASELINE.read_text(encoding="utf-8")
)

expected_by_id = {
    item["id"]: item
    for item in benchmark_data["benchmark"]
}


# ---------------------------------------------------------
# Value comparison
# ---------------------------------------------------------

def values_equal(a, b):
    """
    Compare two SQL result values.

    Numeric values are compared with a small tolerance.
    Everything else is compared normally.
    """

    if a is None or b is None:
        return a == b

    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return isclose(
            float(a),
            float(b),
            rel_tol=1e-9,
            abs_tol=1e-9
        )

    return a == b


# ---------------------------------------------------------
# Row comparison
# ---------------------------------------------------------

def rows_equal(expected_row, actual_row):
    """
    Compare rows by column position.

    Column names / aliases are intentionally ignored.
    Column order is preserved.
    """

    expected_values = list(expected_row.values())
    actual_values = list(actual_row.values())

    if len(expected_values) != len(actual_values):
        return False

    return all(
        values_equal(expected, actual)
        for expected, actual in zip(
            expected_values,
            actual_values
        )
    )


# ---------------------------------------------------------
# Result comparison
# ---------------------------------------------------------

def results_equal(expected, actual, order_matters=False):
    """
    Compare complete SQL results.

    For most questions, row order does not matter.

    For ranking/trend/ordered questions, row order matters.
    """

    if expected is None or actual is None:
        return expected == actual

    if len(expected) != len(actual):
        return False

    # -----------------------------------------------------
    # Order-sensitive comparison
    # -----------------------------------------------------

    if order_matters:
        return all(
            rows_equal(expected_row, actual_row)
            for expected_row, actual_row
            in zip(expected, actual)
        )

    # -----------------------------------------------------
    # Order-independent comparison
    # -----------------------------------------------------
    #
    # We cannot simply use sets because duplicate rows matter.
    # Instead, match each actual row to one unused expected row.
    # -----------------------------------------------------

    unmatched_expected = list(expected)

    for actual_row in actual:
        match_found = False

        for index, expected_row in enumerate(
            unmatched_expected
        ):
            if rows_equal(expected_row, actual_row):
                unmatched_expected.pop(index)
                match_found = True
                break

        if not match_found:
            return False

    return len(unmatched_expected) == 0


# ---------------------------------------------------------
# Decide whether ordering matters
# ---------------------------------------------------------

def question_requires_order(question):
    """
    Determine whether the question explicitly requires
    a meaningful result order.
    """

    question_lower = question.lower()

    order_keywords = [
        "top ",
        "bottom ",
        "highest",
        "lowest",
        "rank",
        "ranking",
        "ranked",
        "most ",
        "least ",
        "trend",
        "trends",
        "chronological",
        "over time",
        "month-over-month",
        "monthly trend",
        "by date",
        "latest",
        "earliest",
    ]

    return any(
        keyword in question_lower
        for keyword in order_keywords
    )


# ---------------------------------------------------------
# Evaluation
# ---------------------------------------------------------

correct = 0
incorrect = 0
invalid = 0
failed = 0

direct_total = 0
direct_correct = 0

ambiguous_total = 0
ambiguous_correct = 0

details = []


for item in baseline_data["results"]:

    question_id = item["id"]
    question = item["question"]

    expected = expected_by_id[question_id]

    expected_behavior = expected["expected_behavior"]

    status = item["status"]


    # -----------------------------------------------------
    # Separate direct vs clarification questions
    # -----------------------------------------------------

    if expected_behavior == "clarification":
        ambiguous_total += 1
    else:
        direct_total += 1


    # -----------------------------------------------------
    # Invalid SQL
    # -----------------------------------------------------

    if status == "invalid_sql":

        invalid += 1

        details.append({
            "id": question_id,
            "question": question,
            "category": expected["category"],
            "expected_behavior": expected_behavior,
            "status": "invalid_sql",
            "correct": False,
            "reason": item["error"]
        })

        continue


    # -----------------------------------------------------
    # Execution failure
    # -----------------------------------------------------

    if status == "failed":

        failed += 1

        details.append({
            "id": question_id,
            "question": question,
            "category": expected["category"],
            "expected_behavior": expected_behavior,
            "status": "execution_failed",
            "correct": False,
            "reason": item["error"]
        })

        continue


    # -----------------------------------------------------
    # Compare results
    # -----------------------------------------------------

    expected_result = expected["expected_result"]
    actual_result = item["execution_result"]

    order_matters = question_requires_order(question)

    is_correct = results_equal(
        expected_result,
        actual_result,
        order_matters=order_matters
    )


    # -----------------------------------------------------
    # Update counters
    # -----------------------------------------------------

    if is_correct:

        correct += 1

        if expected_behavior == "clarification":
            ambiguous_correct += 1
        else:
            direct_correct += 1

        result_status = "correct"

    else:

        incorrect += 1
        result_status = "incorrect"


    # -----------------------------------------------------
    # Save detailed result
    # -----------------------------------------------------

    details.append({
        "id": question_id,
        "question": question,
        "category": expected["category"],
        "expected_behavior": expected_behavior,
        "status": result_status,
        "correct": is_correct,
        "order_matters": order_matters,
        "generated_sql": item["generated_sql"],
        "expected_result": expected_result,
        "actual_result": actual_result
    })


# ---------------------------------------------------------
# Calculate metrics
# ---------------------------------------------------------

total = len(baseline_data["results"])

accuracy = (
    correct / total * 100
    if total
    else 0
)

direct_accuracy = (
    direct_correct / direct_total * 100
    if direct_total
    else 0
)

ambiguous_accuracy = (
    ambiguous_correct / ambiguous_total * 100
    if ambiguous_total
    else 0
)

invalid_rate = (
    invalid / total * 100
    if total
    else 0
)

execution_failure_rate = (
    failed / total * 100
    if total
    else 0
)


# ---------------------------------------------------------
# Save evaluation
# ---------------------------------------------------------

output = {
    "total_questions": total,

    "correct": correct,
    "incorrect": incorrect,
    "invalid_sql": invalid,
    "execution_failed": failed,

    "accuracy_percent": round(accuracy, 2),

    "direct_questions": {
        "total": direct_total,
        "correct": direct_correct,
        "accuracy_percent": round(direct_accuracy, 2)
    },

    "clarification_questions": {
        "total": ambiguous_total,
        "correct": ambiguous_correct,
        "accuracy_percent": round(ambiguous_accuracy, 2)
    },

    "invalid_sql_rate_percent": round(
        invalid_rate,
        2
    ),

    "execution_failure_rate_percent": round(
        execution_failure_rate,
        2
    ),

    "details": details
}


OUTPUT.write_text(
    json.dumps(
        output,
        indent=2,
        default=str
    ),
    encoding="utf-8"
)


# ---------------------------------------------------------
# Print summary
# ---------------------------------------------------------

print("\n========== BASELINE EVALUATION ==========")

print(f"Total questions:       {total}")
print(f"Correct:               {correct}")
print(f"Incorrect:             {incorrect}")
print(f"Invalid SQL:           {invalid}")
print(f"Execution failed:      {failed}")

print(f"\nOverall accuracy:      {accuracy:.2f}%")

print("\n----- Direct Questions -----")
print(f"Total:                 {direct_total}")
print(f"Correct:               {direct_correct}")
print(f"Accuracy:              {direct_accuracy:.2f}%")

print("\n----- Clarification Questions -----")
print(f"Total:                 {ambiguous_total}")
print(f"Correct:               {ambiguous_correct}")
print(f"Accuracy:              {ambiguous_accuracy:.2f}%")

print("\n----- Error Rates -----")
print(f"Invalid SQL rate:       {invalid_rate:.2f}%")
print(f"Execution failure:      {execution_failure_rate:.2f}%")

print("\n=========================================")

print(
    f"\nDetailed results saved to: {OUTPUT}"
)