import json
import os
import time
from decimal import Decimal, InvalidOperation
from math import isclose

from dotenv import load_dotenv
from groq import Groq


# =========================================================
# Configuration
# =========================================================

BENCHMARK = "evaluation/benchmark_verified.json"
PREVIOUS_RESULTS = "evaluation/clarification_results.json"
OUTPUT = "evaluation/clarification_evaluation_v3.json"

load_dotenv()

client = Groq(
    api_key=os.getenv("GROQ_API_KEY")
)

JUDGE_MODEL = os.getenv(
    "GROQ_SMALL_MODEL",
    "openai/gpt-oss-20b"
)

# Keep AI evidence small so Groq TPM limits are not exceeded.
MAX_SAMPLE_ROWS = 5
MAX_EXAMPLE_ROWS = 5
MAX_STRING_LENGTH = 300
MAX_SQL_LENGTH = 6000


# =========================================================
# Load existing benchmark + existing generated results
# =========================================================
#
# IMPORTANT:
#
# This script DOES NOT call /query.
# It DOES NOT generate SQL again.
#
# It only evaluates the results that already exist in:
#
# evaluation/clarification_results.json
#
# =========================================================

with open(BENCHMARK, "r", encoding="utf-8") as f:
    benchmark_data = json.load(f)

with open(PREVIOUS_RESULTS, "r", encoding="utf-8") as f:
    previous_data = json.load(f)


expected_by_id = {
    item["id"]: item
    for item in benchmark_data["benchmark"]
}


# =========================================================
# Numeric comparison
# =========================================================

def to_decimal(value):
    """
    Convert common numeric representations to Decimal.

    Handles:
        int
        float
        Decimal
        numeric strings

    Returns None for non-numeric values.
    """

    if isinstance(value, bool):
        return None

    if isinstance(value, Decimal):
        return value

    if isinstance(value, (int, float)):
        try:
            return Decimal(str(value))
        except (InvalidOperation, ValueError):
            return None

    if isinstance(value, str):
        try:
            return Decimal(value.strip())
        except (InvalidOperation, ValueError):
            return None

    return None


def values_equal(a, b):
    """
    Compare SQL values.

    Numeric values are compared numerically rather than
    requiring identical Python types or formatting.
    """

    if a is None or b is None:
        return a == b

    # Do not treat True/False as 1/0.
    if isinstance(a, bool) or isinstance(b, bool):
        return a == b

    a_number = to_decimal(a)
    b_number = to_decimal(b)

    if a_number is not None and b_number is not None:

        try:
            return isclose(
                float(a_number),
                float(b_number),
                rel_tol=1e-9,
                abs_tol=1e-9
            )
        except (OverflowError, ValueError):
            return a_number == b_number

    return a == b


# =========================================================
# Row comparison
# =========================================================

def exact_row_equal(expected_row, actual_row):
    """
    Strict comparison.

    Requires:
      - same number of columns
      - same column order
      - equivalent values
    """

    if not isinstance(expected_row, dict):
        return expected_row == actual_row

    if not isinstance(actual_row, dict):
        return False

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


def projection_row_equal(expected_row, actual_row):
    """
    Projection-tolerant comparison.

    Extra columns in the actual result are acceptable when
    every expected column exists and contains the expected value.
    """

    if not isinstance(expected_row, dict):
        return False

    if not isinstance(actual_row, dict):
        return False

    expected_columns = {
        str(key).strip().lower(): value
        for key, value in expected_row.items()
    }

    actual_columns = {
        str(key).strip().lower(): value
        for key, value in actual_row.items()
    }

    for column, expected_value in expected_columns.items():

        if column not in actual_columns:
            return False

        if not values_equal(
            expected_value,
            actual_columns[column]
        ):
            return False

    return True


# =========================================================
# Result comparison
# =========================================================

def results_equal(
    expected,
    actual,
    order_matters=False
):
    """
    Deterministic SQL result comparison.

    Returns:

        exact
            Exact result match.

        projection_match
            Expected columns/values are present, but generated
            SQL returned additional harmless columns.

        mismatch
            Deterministic comparison could not establish
            correctness.
    """

    if expected is None or actual is None:

        if expected == actual:
            return "exact"

        return "mismatch"

    if not isinstance(expected, list):
        return (
            "exact"
            if expected == actual
            else "mismatch"
        )

    if not isinstance(actual, list):
        return "mismatch"

    # SQL result must contain the same number of rows.
    if len(expected) != len(actual):
        return "mismatch"

    # -----------------------------------------------------
    # Order-sensitive comparison
    # -----------------------------------------------------

    if order_matters:

        all_exact = True

        for expected_row, actual_row in zip(
            expected,
            actual
        ):

            if not exact_row_equal(
                expected_row,
                actual_row
            ):
                all_exact = False
                break

        if all_exact:
            return "exact"

        all_projection_match = True

        for expected_row, actual_row in zip(
            expected,
            actual
        ):

            if not projection_row_equal(
                expected_row,
                actual_row
            ):
                all_projection_match = False
                break

        if all_projection_match:
            return "projection_match"

        return "mismatch"

    # -----------------------------------------------------
    # Order-independent comparison
    # -----------------------------------------------------

    unmatched_actual = list(actual)

    # First try exact matching.
    exact_match = True

    for expected_row in expected:

        found_index = None

        for index, actual_row in enumerate(
            unmatched_actual
        ):

            if exact_row_equal(
                expected_row,
                actual_row
            ):
                found_index = index
                break

        if found_index is None:
            exact_match = False
            break

        unmatched_actual.pop(found_index)

    if exact_match:
        return "exact"

    # Try projection-tolerant matching.
    unmatched_actual = list(actual)

    for expected_row in expected:

        found_index = None

        for index, actual_row in enumerate(
            unmatched_actual
        ):

            if projection_row_equal(
                expected_row,
                actual_row
            ):
                found_index = index
                break

        if found_index is None:
            return "mismatch"

        unmatched_actual.pop(found_index)

    return "projection_match"


# =========================================================
# Ordering
# =========================================================

def question_requires_order(question):
    """
    Determine whether result ordering is semantically important.
    """

    q = question.lower()

    keywords = [
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
        keyword in q
        for keyword in keywords
    )


# =========================================================
# Compact evidence helpers
# =========================================================

def compact_value(value):
    """
    Convert a value into a small JSON-safe representation.
    """

    if isinstance(value, Decimal):
        return str(value)

    if isinstance(value, str):
        if len(value) > MAX_STRING_LENGTH:
            return value[:MAX_STRING_LENGTH] + "...[truncated]"
        return value

    if isinstance(value, (int, float, bool)) or value is None:
        return value

    text = str(value)

    if len(text) > MAX_STRING_LENGTH:
        return text[:MAX_STRING_LENGTH] + "...[truncated]"

    return text


def compact_row(row):
    """
    Keep a single result row small.
    """

    if not isinstance(row, dict):
        return compact_value(row)

    return {
        str(key): compact_value(value)
        for key, value in row.items()
    }


def compact_rows(rows, limit=MAX_SAMPLE_ROWS):
    """
    Return only a small sample of rows.
    """

    if not isinstance(rows, list):
        return compact_value(rows)

    return [
        compact_row(row)
        for row in rows[:limit]
    ]


def column_names(rows):
    """
    Return distinct column names found in result rows.
    """

    columns = []

    if not isinstance(rows, list):
        return columns

    for row in rows:

        if not isinstance(row, dict):
            continue

        for key in row.keys():

            key_text = str(key)

            if key_text not in columns:
                columns.append(key_text)

    return columns


def row_match_index(
    expected_row,
    actual_rows,
    matcher
):
    """
    Find one matching actual row.

    Returns the index or None.
    """

    for index, actual_row in enumerate(actual_rows):

        if matcher(
            expected_row,
            actual_row
        ):
            return index

    return None


def build_mismatch_evidence(
    expected,
    actual,
    order_matters
):
    """
    Build compact evidence for the AI judge.

    IMPORTANT:
    This function intentionally does NOT send the full result
    sets to Groq.

    It calculates:
      - row counts
      - column names
      - sample rows
      - positional mismatches for ordered results
      - missing/extra row counts
      - a few mismatch examples
    """

    evidence = {
        "expected_row_count": (
            len(expected)
            if isinstance(expected, list)
            else None
        ),

        "actual_row_count": (
            len(actual)
            if isinstance(actual, list)
            else None
        ),

        "expected_columns":
            column_names(expected),

        "actual_columns":
            column_names(actual),

        "order_matters":
            order_matters,

        "expected_sample":
            compact_rows(expected),

        "actual_sample":
            compact_rows(actual),

        "comparison_notes": []
    }

    if not isinstance(expected, list):
        evidence["comparison_notes"].append(
            "Expected result is not a row list."
        )
        return evidence

    if not isinstance(actual, list):
        evidence["comparison_notes"].append(
            "Actual result is not a row list."
        )
        return evidence

    if len(expected) != len(actual):

        evidence["comparison_notes"].append(
            "Row counts differ."
        )

    # -----------------------------------------------------
    # Ordered mismatch evidence
    # -----------------------------------------------------

    if order_matters:

        positional_mismatches = 0
        mismatch_examples = []

        common_length = min(
            len(expected),
            len(actual)
        )

        for index in range(common_length):

            expected_row = expected[index]
            actual_row = actual[index]

            if projection_row_equal(
                expected_row,
                actual_row
            ):
                continue

            positional_mismatches += 1

            if len(mismatch_examples) < MAX_EXAMPLE_ROWS:

                mismatch_examples.append({
                    "position": index,
                    "expected": compact_row(
                        expected_row
                    ),
                    "actual": compact_row(
                        actual_row
                    )
                })

        evidence["positional_mismatches"] = (
            positional_mismatches
        )

        evidence["positional_mismatch_examples"] = (
            mismatch_examples
        )

        return evidence

    # -----------------------------------------------------
    # Unordered mismatch evidence
    # -----------------------------------------------------

    # Projection matching is the most useful comparison
    # for semantic result equality.
    unmatched_actual = list(actual)

    matched_count = 0
    missing_examples = []

    for expected_row in expected:

        index = row_match_index(
            expected_row,
            unmatched_actual,
            projection_row_equal
        )

        if index is None:

            if len(missing_examples) < MAX_EXAMPLE_ROWS:
                missing_examples.append(
                    compact_row(expected_row)
                )

        else:

            matched_count += 1
            unmatched_actual.pop(index)

    evidence["projection_matched_rows"] = matched_count

    evidence["missing_expected_rows"] = (
        len(expected) - matched_count
    )

    evidence["extra_actual_rows"] = (
        len(unmatched_actual)
    )

    evidence["missing_row_examples"] = (
        missing_examples
    )

    evidence["extra_row_examples"] = [
        compact_row(row)
        for row in unmatched_actual[
            :MAX_EXAMPLE_ROWS
        ]
    ]

    if matched_count == len(expected):

        evidence["comparison_notes"].append(
            "All expected rows matched by projection."
        )

    else:

        evidence["comparison_notes"].append(
            "Some expected rows did not match actual rows."
        )

    return evidence


# =========================================================
# AI semantic judge
# =========================================================

JUDGE_SCHEMA = {
    "type": "object",
    "properties": {
        "verdict": {
            "type": "string",
            "enum": [
                "correct",
                "incorrect",
                "uncertain"
            ]
        },
        "reason": {
            "type": "string"
        }
    },
    "required": [
        "verdict",
        "reason"
    ],
    "additionalProperties": False
}


def ai_judge(
    question,
    generated_sql,
    expected_result,
    actual_result,
    order_matters,
    clarification_question=None,
    clarification_answer=None
):
    """
    Semantic fallback evaluator.

    Only compact evidence is sent to Groq.
    """

    evidence = build_mismatch_evidence(
        expected=expected_result,
        actual=actual_result,
        order_matters=order_matters
    )

    # Keep SQL bounded too.
    sql_for_judge = generated_sql or ""

    if len(sql_for_judge) > MAX_SQL_LENGTH:
        sql_for_judge = (
            sql_for_judge[:MAX_SQL_LENGTH]
            + "\n...[SQL truncated]"
        )

    prompt = f"""
You are a strict evaluator for a Text-to-SQL benchmark.

Determine whether the generated SQL correctly answers the
user's question.

Evaluate SEMANTIC correctness, not SQL text equality.

Rules:

1. The generated SQL must answer the user's actual question.
2. Correct joins, filters, grouping, aggregation and calculations
   are required.
3. Wrong calculations are incorrect.
4. Wrong filters are incorrect.
5. Wrong joins are incorrect.
6. Wrong time periods are incorrect.
7. Wrong ranking criteria are incorrect.
8. Missing requested information is incorrect.
9. Extra harmless columns can be acceptable.
10. Column aliases do not matter.
11. Small numeric representation differences are acceptable.
12. If the question explicitly requires ranking or ordering,
    ordering must be respected.
13. Do not mark a result correct merely because some expected
    values happen to appear in it.
14. Be conservative.
15. Return "uncertain" only when the supplied evidence genuinely
    does not allow a decision.
16. A different column order is harmless when the same requested
    information and values are present.
17. If row counts differ, treat that as incorrect unless the
    evidence clearly shows the difference is only an artifact
    of harmless representation.

IMPORTANT BUSINESS DEFINITION FOR THIS PROJECT:

Revenue is calculated as:

unitprice * qty * (1 - discount)

This definition must be respected whenever revenue is involved.

"""

    if clarification_question:
        prompt += f"""
ORIGINAL CLARIFICATION QUESTION:
{clarification_question}

USER'S CLARIFICATION ANSWER:
{clarification_answer}
"""

    prompt += f"""

USER QUESTION:
{question}

GENERATED SQL:
{sql_for_judge}

COMPACT RESULT EVIDENCE:
{json.dumps(
    evidence,
    default=str,
    indent=2
)}

The evidence contains samples and deterministic comparison
statistics. It intentionally does not contain every row.

ORDER MATTERS:
{order_matters}

Return:
- correct
- incorrect
- uncertain

Also provide a short reason.
"""

    response = client.chat.completions.create(
        model=JUDGE_MODEL,
        temperature=0,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a strict Text-to-SQL "
                    "benchmark evaluator. "
                    "Return only structured JSON."
                )
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "sql_result_judge",
                "strict": True,
                "schema": JUDGE_SCHEMA
            }
        }
    )

    content = response.choices[0].message.content

    return json.loads(content)


# =========================================================
# Metrics
# =========================================================

total = len(previous_data["results"])

correct = 0
incorrect = 0
invalid_sql = 0
execution_failed = 0
ai_uncertain = 0

direct_total = 0
direct_correct = 0

clarification_total = 0
clarification_correct = 0

true_positive = 0
true_negative = 0
false_positive = 0
false_negative = 0

deterministic_exact = 0
deterministic_projection = 0

ai_judged = 0
ai_correct = 0
ai_incorrect = 0
ai_uncertain_count = 0

details = []


# =========================================================
# Re-evaluate existing results
# =========================================================

for item in previous_data["results"]:

    qid = item["id"]
    question = item["question"]

    benchmark = expected_by_id[qid]

    expected_behavior = benchmark[
        "expected_behavior"
    ]

    expected_result = benchmark[
        "expected_result"
    ]

    actual_result = item.get(
        "final_result"
    )

    generated_sql = item.get(
        "final_sql"
    )

    old_status = item.get(
        "status"
    )

    print(
        f"\nQ{qid:02d}: {question}"
    )

    # -----------------------------------------------------
    # System failures
    # -----------------------------------------------------

    if old_status == "INVALID_SQL":

        invalid_sql += 1

        details.append({
            "id": qid,
            "question": question,
            "expected_behavior": expected_behavior,
            "status": "INVALID_SQL",
            "correct": False,
            "evaluation_method": "system_failure",
            "reason": item.get("reason")
        })

        print("   INVALID_SQL")

        continue


    if old_status == "FAIL_EXECUTION":

        execution_failed += 1

        details.append({
            "id": qid,
            "question": question,
            "expected_behavior": expected_behavior,
            "status": "FAIL_EXECUTION",
            "correct": False,
            "evaluation_method": "system_failure",
            "reason": item.get("reason")
        })

        print("   FAIL_EXECUTION")

        continue


    # -----------------------------------------------------
    # Ambiguity detector metrics
    # -----------------------------------------------------

    if expected_behavior == "clarification":

        clarification_total += 1

        if item.get(
            "detection_correct"
        ):
            true_positive += 1
        else:
            false_negative += 1

    else:

        direct_total += 1

        if item.get(
            "detection_correct"
        ):
            true_negative += 1
        else:
            false_positive += 1


    # -----------------------------------------------------
    # Missing result
    # -----------------------------------------------------

    if actual_result is None:

        incorrect += 1

        details.append({
            "id": qid,
            "question": question,
            "expected_behavior": expected_behavior,
            "status": "NO_RESULT",
            "correct": False,
            "evaluation_method": "system_failure",
            "reason": "No final result was stored."
        })

        print("   NO_RESULT")

        continue


    # -----------------------------------------------------
    # Deterministic comparison
    # -----------------------------------------------------

    order_matters = question_requires_order(
        question
    )

    comparison = results_equal(
        expected_result,
        actual_result,
        order_matters=order_matters
    )


    # -----------------------------------------------------
    # Exact deterministic PASS
    # -----------------------------------------------------

    if comparison == "exact":

        deterministic_exact += 1
        correct += 1

        if expected_behavior == "clarification":
            clarification_correct += 1
        else:
            direct_correct += 1

        status = "PASS"
        evaluation_method = "deterministic_exact"
        judge_result = None
        evidence = None

        print(
            "   PASS "
            "(deterministic exact)"
        )


    # -----------------------------------------------------
    # Projection-tolerant deterministic PASS
    # -----------------------------------------------------

    elif comparison == "projection_match":

        deterministic_projection += 1
        correct += 1

        if expected_behavior == "clarification":
            clarification_correct += 1
        else:
            direct_correct += 1

        status = "PASS_EXTRA_COLUMNS"
        evaluation_method = (
            "deterministic_projection"
        )
        judge_result = None
        evidence = None

        print(
            "   PASS "
            "(deterministic - extra columns)"
        )


    # -----------------------------------------------------
    # Deterministic mismatch → AI judge
    # -----------------------------------------------------

    else:

        ai_judged += 1

        # Build compact evidence once for saving/debugging.
        evidence = build_mismatch_evidence(
            expected=expected_result,
            actual=actual_result,
            order_matters=order_matters
        )

        # Stay safely below Groq RPM.
        time.sleep(2.1)

        try:

            judge_result = ai_judge(
                question=question,
                generated_sql=generated_sql,
                expected_result=expected_result,
                actual_result=actual_result,
                order_matters=order_matters,
                clarification_question=item.get(
                    "clarification_question"
                ),
                clarification_answer=item.get(
                    "clarification_answer"
                )
            )

        except Exception as exc:

            judge_result = {
                "verdict": "uncertain",
                "reason": (
                    "AI judge failed: "
                    f"{exc}"
                )
            }

        verdict = judge_result.get(
            "verdict"
        )

        evaluation_method = "ai_judge"


        if verdict == "correct":

            ai_correct += 1
            correct += 1

            if expected_behavior == "clarification":
                clarification_correct += 1
            else:
                direct_correct += 1

            status = "PASS_AI_JUDGE"

            print(
                "   PASS "
                "(AI judge): "
                f"{judge_result.get('reason')}"
            )


        elif verdict == "incorrect":

            ai_incorrect += 1
            incorrect += 1

            status = "FAIL_AI_JUDGE"

            print(
                "   FAIL "
                "(AI judge): "
                f"{judge_result.get('reason')}"
            )


        else:

            ai_uncertain_count += 1
            ai_uncertain += 1
            incorrect += 1

            status = "UNCERTAIN_AI_JUDGE"

            print(
                "   UNCERTAIN "
                "(AI judge): "
                f"{judge_result.get('reason')}"
            )


    # -----------------------------------------------------
    # Save detailed result
    # -----------------------------------------------------

    details.append({

        "id": qid,

        "question": question,

        "category": benchmark.get(
            "category"
        ),

        "expected_behavior":
            expected_behavior,

        "clarification_question":
            item.get(
                "clarification_question"
            ),

        "clarification_answer":
            item.get(
                "clarification_answer"
            ),

        "generated_sql":
            generated_sql,

        "expected_result":
            expected_result,

        "actual_result":
            actual_result,

        "order_matters":
            order_matters,

        "deterministic_comparison":
            comparison,

        "compact_mismatch_evidence":
            evidence,

        "evaluation_method":
            evaluation_method,

        "ai_judge":
            judge_result,

        "status":
            status,

        "correct":
            status in [
                "PASS",
                "PASS_EXTRA_COLUMNS",
                "PASS_AI_JUDGE"
            ]
    })


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
    clarification_correct
    / clarification_total
    * 100
    if clarification_total
    else 0
)

detection_accuracy = (
    (
        true_positive
        + true_negative
    )
    / total
    * 100
    if total
    else 0
)

ambiguous_recall = (
    true_positive
    / clarification_total
    * 100
    if clarification_total
    else 0
)

false_positive_rate = (
    false_positive
    / direct_total
    * 100
    if direct_total
    else 0
)

false_negative_rate = (
    false_negative
    / clarification_total
    * 100
    if clarification_total
    else 0
)

invalid_rate = (
    invalid_sql
    / total
    * 100
    if total
    else 0
)

execution_failure_rate = (
    execution_failed
    / total
    * 100
    if total
    else 0
)


# =========================================================
# Save evaluation
# =========================================================

output = {

    "evaluation_version":
        "v3_compact_hybrid",

    "important_note":
        (
            "This evaluation reuses the existing "
            "clarification_results.json. "
            "It does not regenerate benchmark queries. "
            "AI judge receives compact mismatch evidence "
            "instead of complete result sets."
        ),

    "summary": {

        "total_questions":
            total,

        "correct":
            correct,

        "incorrect":
            incorrect,

        "invalid_sql":
            invalid_sql,

        "execution_failed":
            execution_failed,

        "ai_uncertain":
            ai_uncertain,

        "overall_accuracy_percent":
            round(
                overall_accuracy,
                2
            ),

        "direct_questions": {

            "total":
                direct_total,

            "correct":
                direct_correct,

            "accuracy_percent":
                round(
                    direct_accuracy,
                    2
                )
        },

        "clarification_questions": {

            "total":
                clarification_total,

            "end_to_end_correct":
                clarification_correct,

            "accuracy_percent":
                round(
                    clarification_accuracy,
                    2
                )
        },

        "ambiguity_detection": {

            "true_positive":
                true_positive,

            "true_negative":
                true_negative,

            "false_positive":
                false_positive,

            "false_negative":
                false_negative,

            "accuracy_percent":
                round(
                    detection_accuracy,
                    2
                ),

            "ambiguous_recall_percent":
                round(
                    ambiguous_recall,
                    2
                ),

            "false_positive_rate_percent":
                round(
                    false_positive_rate,
                    2
                ),

            "false_negative_rate_percent":
                round(
                    false_negative_rate,
                    2
                )
        },

        "evaluation_method": {

            "deterministic_exact":
                deterministic_exact,

            "deterministic_projection":
                deterministic_projection,

            "ai_judged":
                ai_judged,

            "ai_judge_correct":
                ai_correct,

            "ai_judge_incorrect":
                ai_incorrect,

            "ai_judge_uncertain":
                ai_uncertain_count
        },

        "invalid_sql_rate_percent":
            round(
                invalid_rate,
                2
            ),

        "execution_failure_rate_percent":
            round(
                execution_failure_rate,
                2
            )
    },

    "details":
        details
}


OUTPUT = "evaluation/clarification_evaluation_v3.json"

with open(
    OUTPUT,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        output,
        f,
        indent=2,
        default=str
    )


# =========================================================
# Print summary
# =========================================================

print()
print("==========================================")
print(" COMPACT HYBRID CLARIFICATION EVALUATION V3")
print("==========================================")

print(
    f"Total questions:          {total}"
)

print(
    f"Correct:                  {correct}"
)

print(
    f"Incorrect:                {incorrect}"
)

print(
    f"Invalid SQL:              {invalid_sql}"
)

print(
    f"Execution failed:         {execution_failed}"
)

print(
    f"AI uncertain:             {ai_uncertain}"
)

print(
    f"Overall accuracy:         "
    f"{overall_accuracy:.2f}%"
)

print()
print("----- Direct Questions -----")

print(
    f"Total:                    "
    f"{direct_total}"
)

print(
    f"Correct:                  "
    f"{direct_correct}"
)

print(
    f"Accuracy:                 "
    f"{direct_accuracy:.2f}%"
)

print()
print("----- Clarification Questions -----")

print(
    f"Total:                    "
    f"{clarification_total}"
)

print(
    f"End-to-end correct:       "
    f"{clarification_correct}"
)

print(
    f"Accuracy:                 "
    f"{clarification_accuracy:.2f}%"
)

print()
print("----- Ambiguity Detection -----")

print(
    f"True positives:           "
    f"{true_positive}"
)

print(
    f"True negatives:           "
    f"{true_negative}"
)

print(
    f"False positives:          "
    f"{false_positive}"
)

print(
    f"False negatives:          "
    f"{false_negative}"
)

print(
    f"Detection accuracy:       "
    f"{detection_accuracy:.2f}%"
)

print(
    f"Ambiguous recall:         "
    f"{ambiguous_recall:.2f}%"
)

print(
    f"False-positive rate:      "
    f"{false_positive_rate:.2f}%"
)

print()
print("----- Evaluation Method -----")

print(
    f"Deterministic exact:      "
    f"{deterministic_exact}"
)

print(
    f"Deterministic projection: "
    f"{deterministic_projection}"
)

print(
    f"AI judged:                "
    f"{ai_judged}"
)

print(
    f"AI judge correct:         "
    f"{ai_correct}"
)

print(
    f"AI judge incorrect:       "
    f"{ai_incorrect}"
)

print(
    f"AI judge uncertain:       "
    f"{ai_uncertain_count}"
)

print()
print("----- Error Rates -----")

print(
    f"Invalid SQL rate:         "
    f"{invalid_rate:.2f}%"
)

print(
    f"Execution failure rate:   "
    f"{execution_failure_rate:.2f}%"
)

print()
print(
    f"Detailed results saved to: "
    f"{OUTPUT}"
)

print("==========================================")