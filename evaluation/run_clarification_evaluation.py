import json
from pathlib import Path
from math import isclose

from fastapi.testclient import TestClient

from backend.main import app


BENCHMARK = Path("evaluation/benchmark_verified.json")
OUTPUT = Path("evaluation/clarification_results.json")

client = TestClient(app)

data = json.loads(
    BENCHMARK.read_text(encoding="utf-8")
)


# =========================================================
# Result comparison
# =========================================================

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


def rows_equal(expected_row, actual_row):
    """
    Compare rows by column position.

    Column names / aliases are ignored.
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


def results_equal(expected, actual, order_matters=False):
    """
    Compare complete SQL results.

    For most questions, row order does not matter.

    For ranking/trend/ordered questions, row order matters.
    """

    if expected is None or actual is None:
        return expected == actual

    if not isinstance(expected, list) or not isinstance(actual, list):
        return expected == actual

    if len(expected) != len(actual):
        return False

    # -----------------------------------------------------
    # Order-sensitive comparison
    # -----------------------------------------------------

    if order_matters:
        return all(
            rows_equal(expected_row, actual_row)
            for expected_row, actual_row in zip(
                expected,
                actual
            )
        )

    # -----------------------------------------------------
    # Order-independent comparison
    # -----------------------------------------------------
    #
    # Do not use sets because duplicate rows matter.
    # Instead, match every actual row to one unused
    # expected row.
    # -----------------------------------------------------

    unmatched_expected = list(expected)

    for actual_row in actual:

        match_found = False

        for index, expected_row in enumerate(
            unmatched_expected
        ):

            if rows_equal(
                expected_row,
                actual_row
            ):
                unmatched_expected.pop(index)
                match_found = True
                break

        if not match_found:
            return False

    return len(unmatched_expected) == 0


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


# =========================================================
# Helpers
# =========================================================

def is_invalid_sql_error(response):
    """
    Determine whether an API error represents invalid SQL.
    """

    if response.get("status") != "error":
        return False

    message = response.get("message", "")

    return "Only SELECT queries are allowed" in message


def classify_error(response):
    """
    Classify an unsuccessful API response.
    """

    if is_invalid_sql_error(response):
        return "INVALID_SQL"

    return "FAIL_EXECUTION"


# =========================================================
# Counters
# =========================================================

total = 0

correct = 0
incorrect = 0
invalid = 0
failed = 0

# Direct questions
direct_total = 0
direct_correct = 0

# Expected ambiguous questions
ambiguous_total = 0
ambiguous_end_to_end_correct = 0

# Detection confusion matrix
true_positive = 0
true_negative = 0
false_positive = 0
false_negative = 0

# Detection / clarification statistics
clarification_detected = 0
clarification_not_detected = 0

# False-positive direct questions
unnecessary_clarifications = 0

results = []


# =========================================================
# Evaluation
# =========================================================

for item in data["benchmark"]:

    qid = item["id"]
    question = item["question"]
    expected_behavior = item["expected_behavior"]
    expected_result = item["expected_result"]

    conversation_id = f"evaluation-{qid}"

    total += 1

    print(f"\nQ{qid:02d}: {question}")

    # -----------------------------------------------------
    # First turn
    # -----------------------------------------------------

    first_response = client.post(
        "/query",
        json={
            "conversation_id": conversation_id,
            "question": question,
        },
    )

    first = first_response.json()

    first_status = first.get("status")

    detection_correct = False
    final_result_correct = False

    second = None
    clarification_answer = None
    final_sql = None
    final_result = None

    status = None
    reason = None

    # =====================================================
    # EXPECTED CLARIFICATION
    # =====================================================

    if expected_behavior == "clarification":

        ambiguous_total += 1

        # -------------------------------------------------
        # Detector correctly detected ambiguity
        # -------------------------------------------------

        if first_status == "clarification_needed":

            true_positive += 1
            clarification_detected += 1
            detection_correct = True

            clarification_question = first.get(
                "clarification_question"
            )

            clarification_answer = item.get(
                "clarification_answer"
            )

            # ---------------------------------------------
            # Second turn
            # ---------------------------------------------

            second_response = client.post(
                "/query",
                json={
                    "conversation_id": conversation_id,
                    "clarification_answer": clarification_answer,
                },
            )

            second = second_response.json()

            if second.get("status") == "ready":

                final_sql = second.get("sql")
                final_result = second.get("result")

                order_matters = question_requires_order(
                    question
                )

                final_result_correct = results_equal(
                    expected_result,
                    final_result,
                    order_matters=order_matters
                )

                if final_result_correct:

                    ambiguous_end_to_end_correct += 1
                    correct += 1

                    status = "PASS"

                else:

                    incorrect += 1
                    status = "FAIL_RESULT"

                    reason = (
                        "Clarification was detected correctly, "
                        "but the final SQL result did not match "
                        "the benchmark result."
                    )

            else:

                error_type = classify_error(second)

                if error_type == "INVALID_SQL":

                    invalid += 1
                    status = "INVALID_SQL"
                    reason = second.get("message")

                else:

                    failed += 1
                    status = "FAIL_EXECUTION"
                    reason = second.get("message")

        # -------------------------------------------------
        # Detector missed ambiguity
        # -------------------------------------------------

        else:

            false_negative += 1
            clarification_not_detected += 1

            detection_correct = False

            incorrect += 1

            status = "FAIL_NO_CLARIFICATION"

            reason = (
                "Question was expected to require "
                "clarification, but the system did not "
                "request clarification."
            )

    # =====================================================
    # EXPECTED DIRECT
    # =====================================================

    else:

        direct_total += 1

        # -------------------------------------------------
        # Correctly went directly to SQL
        # -------------------------------------------------

        if first_status == "ready":

            true_negative += 1
            detection_correct = True

            final_sql = first.get("sql")
            final_result = first.get("result")

            order_matters = question_requires_order(
                question
            )

            final_result_correct = results_equal(
                expected_result,
                final_result,
                order_matters=order_matters
            )

            if final_result_correct:

                direct_correct += 1
                correct += 1

                status = "PASS"

            else:

                incorrect += 1
                status = "FAIL_RESULT"

                reason = (
                    "Question was correctly treated as direct, "
                    "but the SQL result did not match the "
                    "benchmark result."
                )

        # -------------------------------------------------
        # False-positive clarification
        # -------------------------------------------------

        elif first_status == "clarification_needed":

            false_positive += 1
            unnecessary_clarifications += 1

            detection_correct = False

            incorrect += 1

            status = "FAIL_UNEXPECTED"

            reason = (
                "Question was expected to be direct, "
                "but the ambiguity detector requested "
                "clarification."
            )

        # -------------------------------------------------
        # Error
        # -------------------------------------------------

        elif first_status == "error":

            # The detector did not successfully produce
            # a usable direct SQL response.
            false_negative += 0

            error_type = classify_error(first)

            if error_type == "INVALID_SQL":

                invalid += 1
                status = "INVALID_SQL"
                reason = first.get("message")

            else:

                failed += 1
                status = "FAIL_EXECUTION"
                reason = first.get("message")

        # -------------------------------------------------
        # Unexpected API state
        # -------------------------------------------------

        else:

            incorrect += 1

            status = "FAIL_UNEXPECTED"

            reason = (
                f"Unexpected first response status: "
                f"{first_status}"
            )

    # -----------------------------------------------------
    # Print result
    # -----------------------------------------------------

    print(f"   {status}")

    # -----------------------------------------------------
    # Save detailed result
    # -----------------------------------------------------

    result_record = {
        "id": qid,
        "question": question,
        "category": item.get("category"),
        "expected_behavior": expected_behavior,

        "clarification_question": (
            first.get("clarification_question")
            if first_status == "clarification_needed"
            else None
        ),

        "clarification_answer": clarification_answer,

        "first_response": first,

        "second_response": second,

        "final_sql": final_sql,

        "expected_result": expected_result,

        "final_result": final_result,

        "detection_correct": detection_correct,

        "final_result_correct": final_result_correct,

        "status": status,

        "reason": reason,
    }

    results.append(result_record)


# =========================================================
# Calculate metrics
# =========================================================

overall_accuracy = (
    correct / total * 100
    if total
    else 0
)

direct_accuracy = (
    direct_correct / direct_total * 100
    if direct_total
    else 0
)

clarification_accuracy = (
    ambiguous_end_to_end_correct / ambiguous_total * 100
    if ambiguous_total
    else 0
)

# Recall for genuinely ambiguous questions
clarification_detection_recall = (
    true_positive / ambiguous_total * 100
    if ambiguous_total
    else 0
)

# False-positive rate among genuinely direct questions
false_positive_rate = (
    false_positive / direct_total * 100
    if direct_total
    else 0
)

# False-negative rate among genuinely ambiguous questions
false_negative_rate = (
    false_negative / ambiguous_total * 100
    if ambiguous_total
    else 0
)

# Overall detector classification accuracy
detection_accuracy = (
    (true_positive + true_negative) / total * 100
    if total
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


# =========================================================
# Summary
# =========================================================

summary = {

    "total_questions": total,

    "correct": correct,
    "incorrect": incorrect,
    "invalid_sql": invalid,
    "execution_failed": failed,

    "overall_accuracy_percent": round(
        overall_accuracy,
        2
    ),

    "direct_questions": {
        "total": direct_total,
        "correct": direct_correct,
        "accuracy_percent": round(
            direct_accuracy,
            2
        )
    },

    "clarification_questions": {
        "total": ambiguous_total,
        "end_to_end_correct": ambiguous_end_to_end_correct,
        "accuracy_percent": round(
            clarification_accuracy,
            2
        )
    },

    "ambiguity_detection": {

        "true_positive": true_positive,
        "true_negative": true_negative,
        "false_positive": false_positive,
        "false_negative": false_negative,

        "accuracy_percent": round(
            detection_accuracy,
            2
        ),

        "ambiguous_recall_percent": round(
            clarification_detection_recall,
            2
        ),

        "false_positive_rate_percent": round(
            false_positive_rate,
            2
        ),

        "false_negative_rate_percent": round(
            false_negative_rate,
            2
        ),

        "unnecessary_clarifications": (
            unnecessary_clarifications
        )
    },

    "invalid_sql_rate_percent": round(
        invalid_rate,
        2
    ),

    "execution_failure_rate_percent": round(
        execution_failure_rate,
        2
    )
}


# =========================================================
# Save results
# =========================================================

output = {
    "summary": summary,
    "results": results
}

OUTPUT.write_text(
    json.dumps(
        output,
        indent=2,
        default=str
    ),
    encoding="utf-8"
)


# =========================================================
# Print summary
# =========================================================

print("\n==========================================")
print(" CLARIFICATION-AWARE EVALUATION")
print("==========================================")

print(f"Total questions:          {total}")
print(f"Correct:                  {correct}")
print(f"Incorrect:                {incorrect}")
print(f"Invalid SQL:              {invalid}")
print(f"Execution failed:         {failed}")

print(
    f"Overall accuracy:        "
    f"{overall_accuracy:.2f}%"
)

print()
print("----- Direct Questions -----")
print(f"Total:                    {direct_total}")
print(f"Correct:                  {direct_correct}")
print(
    f"Accuracy:                "
    f"{direct_accuracy:.2f}%"
)

print()
print("----- Clarification Questions -----")
print(f"Total:                    {ambiguous_total}")
print(
    f"End-to-end correct:      "
    f"{ambiguous_end_to_end_correct}"
)
print(
    f"Accuracy:                "
    f"{clarification_accuracy:.2f}%"
)

print()
print("----- Ambiguity Detection -----")
print(
    f"True positives:          "
    f"{true_positive}"
)
print(
    f"True negatives:          "
    f"{true_negative}"
)
print(
    f"False positives:         "
    f"{false_positive}"
)
print(
    f"False negatives:         "
    f"{false_negative}"
)
print(
    f"Detection accuracy:      "
    f"{detection_accuracy:.2f}%"
)
print(
    f"Ambiguous recall:        "
    f"{clarification_detection_recall:.2f}%"
)
print(
    f"False-positive rate:     "
    f"{false_positive_rate:.2f}%"
)

print()
print("----- Error Rates -----")
print(
    f"Invalid SQL rate:        "
    f"{invalid_rate:.2f}%"
)
print(
    f"Execution failure:       "
    f"{execution_failure_rate:.2f}%"
)

print()
print(
    f"Detailed results saved to: "
    f"{OUTPUT}"
)

print("==========================================")