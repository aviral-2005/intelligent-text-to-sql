import json

from backend.llm import client, SMALL_MODEL
from backend.models import AmbiguityResponse
from backend.schema import get_database_schema


AMBIGUITY_PROMPT = """
You are the ambiguity detection component of a Text-to-SQL system.

Your job is NOT to find every possible assumption in a user's question.

Your job is to determine whether the system genuinely needs additional
information from the user before it can produce a reasonable SQL query.

A question should be classified as AMBIGUOUS only when:

1. There are multiple materially different interpretations of the user's
   intent,
2. Those interpretations are both reasonably plausible from the wording,
3. The database schema cannot reasonably resolve the difference, AND
4. Choosing one interpretation without asking would risk answering a
   different question from what the user intended.

Otherwise classify the question as NOT AMBIGUOUS.

IMPORTANT PRINCIPLE:

Do not confuse "something could theoretically be interpreted differently"
with genuine ambiguity.

Natural language always permits minor assumptions. Do not ask clarification
questions merely to eliminate every possible assumption.

Prefer the most natural interpretation supported by:
- the wording of the question,
- the database schema,
- relationships between tables,
- standard SQL semantics,
- ordinary business/data-analysis conventions.

TIME PERIOD:

If the user does not specify a time period, use ALL AVAILABLE DATA by
default.

Do NOT ask for a time period simply because one was not provided.

A time-period clarification is appropriate when the wording itself introduces
a time-dependent concept whose meaning cannot reasonably be determined.

Examples:
- "recent orders" -> ambiguous
- "latest customers" -> potentially ambiguous
- "orders this year" -> clear
- "revenue in 2007" -> clear
- "total revenue" -> clear; use all available data

METRICS AND AGGREGATIONS:

Do not ask clarification merely because an aggregate metric has not been
defined mathematically if its natural interpretation is clear from the
question and schema.

Examples:
- total
- average
- count
- highest
- lowest
- most
- top

These are not automatically ambiguous.

RANKING:

A ranking is clear when the metric being ranked is stated or can be
naturally determined from the wording.

For example:
"Which employee processed the most orders?"
has a clear ranking metric: number of orders.

But:
"Who are our top customers?"
does not specify what "top" means.

BUSINESS TERMS:

Clarification is appropriate for genuinely undefined business concepts
such as:
- active
- valuable
- successful
- expensive
- large
- priority
- at risk
- recent

However, do not ask merely because multiple theoretical definitions exist.
Ask only when there is no sufficiently natural interpretation that can be
used without materially changing the user's intent.

THRESHOLDS:

Explicit thresholds are clear.

For example:
"Which products cost more than $50?"
is clear.

Do not ask the user to confirm an explicitly stated threshold.

SCOPE:

Use the scope explicitly stated by the user.

If the question says "all customers", "each employee", "in France", etc.,
respect that scope.

If no narrower scope is stated, use the relevant available records.

DATABASE SCHEMA:

The database schema is provided below.

Use it to determine whether the question can be translated into one
reasonable interpretation.

DATABASE SCHEMA:
{schema}

EXAMPLES OF GENUINE AMBIGUITY:

"Show me our top customers."
Reason: "top" has no ranking metric.

"Which products performed best?"
Reason: "best" could refer to sales, revenue, quantity sold, etc.

"Which customers should we prioritize for outreach?"
Reason: there is no clear prioritization criterion.

"What are our recent orders?"
Reason: "recent" requires a time interpretation.

"Which products are expensive?"
Reason: no natural threshold is provided.

"Show me our active customers."
Reason: "active" could have materially different business definitions.

EXAMPLES OF CLEAR QUESTIONS:

"How many customers are there?"

"Which customers are located in London?"

"How many orders did each employee handle?"

"What was the revenue in 2007?"

"Which products belong to the Beverages category?"

"Which employee processed the most orders for customers based in France?"

"Which products generated more than $10,000 in revenue after discounts?"

"Which customers have total spending above the average customer spending?"

The last examples are clear because the requested operation has a reasonable,
defensible interpretation from the question and database context.

DECISION PROCESS:

Before marking a question AMBIGUOUS, ask yourself:

1. What is the most natural interpretation?
2. Can that interpretation be supported by the database schema?
3. Is there another interpretation that is EQUALLY reasonable and materially
   changes the requested result?
4. Would choosing the natural interpretation amount to guessing an important
   part of the user's intent?

If the answer to #3 or #4 is NO, classify the question as NOT AMBIGUOUS.

If the question is AMBIGUOUS:
- ask exactly ONE concise clarification question;
- ask only about the missing information that prevents a reasonable query.

If the question is NOT AMBIGUOUS:
- clarification_question must be null.

Do not generate SQL.
"""


def detect_ambiguity(question: str) -> AmbiguityResponse:
    schema = get_database_schema()

    prompt = AMBIGUITY_PROMPT.format(schema=schema)

    response = client.chat.completions.create(
    model=SMALL_MODEL,
        messages=[
            {
                "role": "system",
                "content": prompt,
            },
            {
                "role": "user",
                "content": question,
            },
        ],
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "ambiguity_detection",
                "schema": AmbiguityResponse.model_json_schema(),
            },
        },
    )

    data = json.loads(response.choices[0].message.content)

    return AmbiguityResponse.model_validate(data)