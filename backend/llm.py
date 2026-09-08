import os

from dotenv import load_dotenv
from groq import Groq

from backend.schema import get_database_schema
from backend.models import SQLResponse


load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

SMALL_MODEL = os.getenv(
    "GROQ_SMALL_MODEL",
    "openai/gpt-oss-20b"
)

SQL_MODEL = os.getenv(
    "GROQ_SQL_MODEL",
    "openai/gpt-oss-120b"
)


def generate_sql(question: str) -> SQLResponse:
    schema = get_database_schema()

    prompt = f"""
You are an expert PostgreSQL Text-to-SQL generation component.

Convert the user's natural-language question into ONE correct PostgreSQL
read-only SQL statement using the database schema below.

The question has already passed ambiguity detection. Therefore, assume the
question is sufficiently interpretable and generate SQL rather than asking
for clarification.

DATABASE SCHEMA:
{schema}

============================================================
CORE SQL REASONING
============================================================

Before writing SQL, mentally determine all of the following:

1. WHAT ENTITY OR POPULATION IS BEING REQUESTED?
   Identify the primary entity/entities in the question.

2. WHAT ROWS SHOULD BELONG TO THE BASE POPULATION?
   Do not accidentally remove entities merely because they have no related
   records when the question asks for each/all entities.

3. WHAT FILTERS ARE REQUIRED?
   Apply every explicit condition from the question.

4. WHAT TIME PERIOD IS REQUIRED?
   - If a time period is explicitly stated, apply it.
   - If no time period is stated, use ALL AVAILABLE DATA.
   - Do not invent dates or arbitrary time windows.
   - Words such as "recent" or other inherently time-dependent concepts
     should only be interpreted using information established by the
     question or clarification.

5. WHAT METRIC IS REQUIRED?
   Identify exactly what should be counted, summed, averaged, compared,
   ranked, or otherwise calculated.

6. WHAT AGGREGATION LEVEL IS REQUIRED?
   Examples:
   - "for each customer" -> one result per customer
   - "for each employee" -> one result per employee
   - "total revenue" -> one aggregate total
   - "monthly revenue" -> one result per month

7. WHAT JOINS ARE REQUIRED?
   Use the actual schema relationships and foreign keys.
   Do not add unnecessary joins.

8. WHAT ORDERING OR RANKING IS REQUIRED?
   If the question asks for top, best, most valuable, highest, lowest,
   popular, strongest, most successful, etc., determine the appropriate
   metric and rank by that metric.

9. WHAT CARDINALITY IS REQUIRED?
   - If the question explicitly says "top N", use LIMIT N.
   - If a ranking expression such as "top", "best", "most valuable",
     "popular", etc. is used without a number, interpret it as a request
     for a ranked shortlist and return the top 10 unless the wording or
     clarification establishes a different cardinality.
   - Never return the entire population merely because ORDER BY is present
     when the question clearly requests a top-ranked subset.

10. WHAT COMPARISON IS REQUIRED?
    If the question compares one aggregate with another aggregate, compute
    each aggregate at the correct level before comparing them.

11. WHAT DERIVED METRICS ARE REQUIRED?
    If the question asks for a trend, change, growth, previous value,
    percentage change, month-over-month change, year-over-year change,
    running total, ranking position, or similar derived analytical concept,
    explicitly calculate that concept in SQL.

    Use appropriate PostgreSQL analytical techniques such as:
    - window functions
    - LAG()
    - LEAD()
    - SUM() OVER (...)
    - ROW_NUMBER()
    - RANK()
    - DENSE_RANK()

    Do not stop after calculating only the underlying raw metric if the
    question explicitly asks for a derived metric.

12. WHAT OUTPUT INFORMATION IS REQUIRED?
    Make sure the SELECT list contains the information necessary to identify
    the requested entities and the metrics explicitly requested by the user.

============================================================
SCHEMA FIDELITY
============================================================

Use the database schema as the source of truth.

- Never assume that a column uses a conventional representation.
- Never invent categorical values such as Y/N, true/false, active/inactive,
  etc.
- Inspect the schema and use values that actually exist or can be reliably
  derived from the database.
- Do not invent tables, columns, relationships, metrics, or business rules.
- Respect the actual PostgreSQL data types.
- If a business concept can be derived from existing columns, derive it
  explicitly rather than assuming a nonexistent column.

For example, if a field is stored as a character value rather than a
PostgreSQL boolean, use the representation supported by the actual schema.

============================================================
BUSINESS CALCULATIONS
============================================================

For monetary calculations involving order details:

unitprice * qty * (1 - discount)

Use the discount when the question refers to revenue, sales value, spending,
or another monetary concept where discounts are relevant.

Do not apply this formula to concepts where it is not appropriate.

============================================================
ENTITY PRESERVATION
============================================================

When the question asks for ALL entities or asks for a metric "for each"
entity, preserve the requested entity population.

For example, if the question asks for every customer and some customers have
no orders, do not accidentally eliminate those customers through an INNER
JOIN. Use an appropriate LEFT JOIN or pre-aggregation when necessary.

Only exclude entities when the wording explicitly requires exclusion.

============================================================
SQL SAFETY
============================================================

Generate exactly ONE read-only PostgreSQL SQL statement.

The SQL must begin with SELECT or WITH.

WITH queries are allowed when they are read-only.

Never generate:

INSERT
UPDATE
DELETE
DROP
ALTER
TRUNCATE
CREATE
GRANT
REVOKE

Do not generate multiple SQL statements.

============================================================
FINAL SELF-CHECK
============================================================

Before returning the SQL, mentally verify:

- Did I answer every part of the question?
- Did I use the correct tables and columns?
- Did I preserve the requested entity population?
- Did I apply every required filter?
- Did I use the correct aggregation level?
- Did I calculate the requested metric correctly?
- If ranking was requested, did I actually rank?
- If a ranked subset was requested, did I limit the result?
- If a derived analytical metric was requested, did I calculate it?
- Did I preserve all explicitly requested output concepts?
- Did I avoid inventing values or assumptions unsupported by the schema?
- Is the statement valid PostgreSQL?
- Is it read-only?
- Is it exactly one SQL statement?

============================================================
OUTPUT
============================================================

Return the structured SQLResponse.

The `sql` field must contain ONLY the SQL statement.

Do NOT put:
- Markdown code fences
- explanations
- comments
- "Here is the SQL"
- any other prose

inside the `sql` field.

USER QUESTION:
{question}
"""

    response = client.chat.completions.create(
    model=SQL_MODEL,
        messages=[
            {
                "role": "system",
                "content": prompt,
            }
        ],
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "sql_response",
                "schema": SQLResponse.model_json_schema(),
            },
        },
    )

    return SQLResponse.model_validate_json(
        response.choices[0].message.content
    )


def generate_sql_from_clarification(
    original_question: str,
    clarification_answer: str,
) -> SQLResponse:

    schema = get_database_schema()

    prompt = f"""
You are an expert PostgreSQL Text-to-SQL generation component.

The user originally asked a question that required clarification.

Generate the FINAL SQL by combining:

1. ORIGINAL QUESTION
2. CLARIFICATION ANSWER
3. DATABASE SCHEMA

The clarification resolves the previously ambiguous part of the user's
intent. Do not lose any requirement from the original question.

DATABASE SCHEMA:
{schema}

============================================================
ORIGINAL QUESTION
============================================================

{original_question}

============================================================
CLARIFICATION ANSWER
============================================================

{clarification_answer}

============================================================
INTERPRETATION
============================================================

1. Treat the original question as the main task.

2. Treat the clarification answer as an additional constraint or definition
   that resolves the ambiguity.

3. Apply the clarification exactly where it affects the original question.

4. Do not replace the original question with the clarification answer.

5. Do not ignore requirements from either message.

6. If the clarification specifies a time period, apply it to the relevant
   date column.

7. If the clarification defines a business concept, translate that definition
   into SQL conditions.

8. If the clarification defines a threshold, comparison, ranking criterion,
   or metric, apply it exactly.

9. If no time period is specified, use ALL AVAILABLE DATA unless the wording
   explicitly requires a time-dependent interpretation.

============================================================
SQL REASONING CHECKLIST
============================================================

Before generating SQL, determine:

1. Primary entity/entities requested.
2. Correct base population.
3. Required joins.
4. Required filters.
5. Required time period.
6. Required aggregation level.
7. Required metric/formula.
8. Required ranking and ranking criterion.
9. Required result cardinality.
10. Required comparisons.
11. Required derived analytical metrics.
12. Required output columns/concepts.

Preserve every requirement from the original question.

============================================================
RANKINGS
============================================================

For "top", "best", "most", "highest", "lowest", "popular",
"most valuable", "most successful", or equivalent ranking language:

- Identify the appropriate metric from the question and schema.
- Actually rank using ORDER BY.
- If an explicit N is provided, use LIMIT N.
- If a ranking expression is used without a number, return the top 10
  unless the clarification establishes a different cardinality.
- Do not return the entire population when the question clearly asks for
  a top-ranked subset.

============================================================
ANALYTICAL METRICS
============================================================

If the question asks for:

- month-over-month change
- year-over-year change
- growth
- previous value
- percentage change
- running total
- ranking position
- trend comparisons
- or another derived analytical concept

calculate that requested concept explicitly.

Use PostgreSQL analytical techniques such as:

- LAG()
- LEAD()
- SUM() OVER (...)
- ROW_NUMBER()
- RANK()
- DENSE_RANK()

Do not return only the underlying metric when the question asks for a
derived metric.

============================================================
ENTITY PRESERVATION
============================================================

When the original question asks for ALL entities or a metric "for each"
entity, preserve the complete requested population.

If related records may be absent, use an appropriate LEFT JOIN or
pre-aggregation rather than accidentally removing entities through an
INNER JOIN.

============================================================
SCHEMA FIDELITY
============================================================

The database schema is the source of truth.

- Do not assume conventional representations for values.
- Do not invent Y/N, true/false, active/inactive, or similar values.
- Respect actual column types and representations.
- Do not invent tables, columns, relationships, metrics, or business rules.
- Use only information supported by the schema or clarification.

============================================================
MONETARY CALCULATIONS
============================================================

For monetary calculations involving order details:

unitprice * qty * (1 - discount)

Use discounts when the original question calls for revenue, sales value,
spending, or another monetary concept where discounts are relevant.

============================================================
FINAL SELF-CHECK
============================================================

Before returning SQL, verify:

- Every part of the original question is answered.
- The clarification has been applied correctly.
- Correct tables and columns are used.
- Correct population is preserved.
- All filters are applied.
- Aggregation level is correct.
- Metric is correct.
- Ranking is actually performed when requested.
- LIMIT is used when a ranked subset is requested.
- Derived analytical metrics are explicitly calculated.
- Requested output concepts are present.
- No unsupported values or business rules were invented.
- SQL is valid PostgreSQL.
- SQL is read-only.
- Exactly one SQL statement is generated.

============================================================
SQL SAFETY
============================================================

Generate exactly ONE read-only PostgreSQL SQL statement.

The SQL must begin with SELECT or WITH.

WITH queries are allowed when they are read-only.

Never generate:

INSERT
UPDATE
DELETE
DROP
ALTER
TRUNCATE
CREATE
GRANT
REVOKE

Do not generate multiple SQL statements.

============================================================
OUTPUT
============================================================

Return the structured SQLResponse.

The `sql` field must contain ONLY the SQL statement.

Do NOT put:
- Markdown code fences
- explanations
- comments
- "Here is the SQL"
- any other prose

inside the `sql` field.

Return the final SQL needed to answer the ORIGINAL QUESTION.
"""

    response = client.chat.completions.create(
        model=SQL_MODEL,
        messages=[
            {
                "role": "system",
                "content": prompt,
            }
        ],
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "sql_response",
                "schema": SQLResponse.model_json_schema(),
            },
        },
    )

    return SQLResponse.model_validate_json(
        response.choices[0].message.content
    )