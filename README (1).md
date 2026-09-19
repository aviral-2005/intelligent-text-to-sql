# QueryLens — Natural-Language Database Explorer

> An intelligent Text-to-SQL system that detects ambiguity in natural-language database questions and asks for clarification before generating SQL when the user's intent is not sufficiently specified.

## Overview

QueryLens lets users explore a relational database using natural language.

Instead of sending every question directly to an SQL-generating LLM, QueryLens first checks whether the question is materially ambiguous. If clarification is required, the system asks the user a targeted follow-up question before generating SQL.

```text
Natural-language question
          ↓
    Ambiguity Detection
          ↓
   ┌──────┴──────┐
   │             │
 Clear       Ambiguous
   │             │
   │       Ask clarification
   │             │
   └──────┬──────┘
          ↓
     SQL Generation
          ↓
      SQL Validation
          ↓
      PostgreSQL
          ↓
      Query Results
       ↙        ↘
   Answer      Data Table
```

## The Problem

Text-to-SQL systems can generate syntactically valid SQL even when a natural-language question is underspecified.

For example:

> "Show me the top customers."

Top by what?

- Revenue?
- Number of orders?
- Quantity purchased?
- Recent activity?

QueryLens treats this as an intent problem and asks for clarification instead of silently choosing an interpretation.

## Key Features

- Natural-language database querying
- Ambiguity detection before SQL generation
- Conversational clarification flow
- Separate LLM routing for different tasks
- Structured LLM outputs using Pydantic/JSON schemas
- SQL validation and read-only query protection
- PostgreSQL execution through SQLAlchemy
- Human-readable answer generation
- Interactive result tables
- Executed SQL visibility
- Query/session history
- Responsive React frontend
- Dark mode
- Production deployment with Vercel + Render
- Fixed 50-question evaluation benchmark
- Deterministic + AI-assisted evaluation methodology

## Architecture

```text
                           ┌──────────────────────┐
                           │       User           │
                           └──────────┬───────────┘
                                      │
                                      ▼
                           ┌──────────────────────┐
                           │ QueryLens Frontend   │
                           │ React + TypeScript   │
                           └──────────┬───────────┘
                                      │
                                      ▼
                           ┌──────────────────────┐
                           │    FastAPI Backend   │
                           └──────────┬───────────┘
                                      │
                                      ▼
                           ┌──────────────────────┐
                           │ Ambiguity Detection  │
                           │      Groq 20B        │
                           └──────────┬───────────┘
                                      │
                         ┌────────────┴────────────┐
                         │                         │
                       Clear                   Ambiguous
                         │                         │
                         │                         ▼
                         │                ┌─────────────────┐
                         │                │ Clarification   │
                         │                │     Question    │
                         │                └────────┬────────┘
                         │                         │
                         │                  User clarification
                         │                         │
                         └────────────┬────────────┘
                                      ▼
                           ┌──────────────────────┐
                           │   SQL Generation     │
                           │      Groq 120B       │
                           └──────────┬───────────┘
                                      │
                                      ▼
                           ┌──────────────────────┐
                           │   SQL Validation     │
                           └──────────┬───────────┘
                                      │
                                      ▼
                           ┌──────────────────────┐
                           │ PostgreSQL Northwind │
                           └──────────┬───────────┘
                                      │
                                      ▼
                           ┌──────────────────────┐
                           │    Query Results     │
                           └──────────┬───────────┘
                                      │
                         ┌────────────┴────────────┐
                         ▼                         ▼
                ┌─────────────────┐       ┌─────────────────┐
                │ Answer Generator│       │ Structured Data │
                │     Groq 20B    │       │   Result Table  │
                └────────┬────────┘       └────────┬────────┘
                         │                         │
                         └────────────┬────────────┘
                                      ▼
                           ┌──────────────────────┐
                           │      QueryLens       │
                           │       Results        │
                           └──────────────────────┘
```

## Model Routing

| Task | Model |
|---|---|
| Ambiguity detection | `openai/gpt-oss-20b` |
| SQL generation | `openai/gpt-oss-120b` |
| SQL generation after clarification | `openai/gpt-oss-120b` |
| Human-readable answer generation | `openai/gpt-oss-20b` |
| AI-assisted evaluation | `openai/gpt-oss-20b` |

Configured through:

```env
GROQ_SMALL_MODEL=openai/gpt-oss-20b
GROQ_SQL_MODEL=openai/gpt-oss-120b
```

## Clarification Engine

The ambiguity detector checks for missing information that could materially change the generated SQL, including:

- Missing metric
- Missing ranking criterion
- Missing threshold interpretation
- Missing time period
- Ambiguous business meaning
- Underspecified analytical intent

Example:

**User:**

> Show me the top customers.

**QueryLens:**

> What should customers be ranked by — total revenue, number of orders, or another metric?

After clarification, the original question and clarification answer are passed to SQL generation.

For a clear question such as:

> How many customers are there?

QueryLens can directly generate:

```sql
SELECT COUNT(*) AS total_customers
FROM customer;
```

## SQL Generation

The SQL-generation stage receives the database schema and natural-language request.

The generation process considers:

1. Target entity/population
2. Filters
3. Time period
4. Metric
5. Aggregation
6. Required joins
7. Ranking
8. Cardinality
9. Comparisons
10. Derived analytical metrics

The prompt emphasizes schema fidelity so generated SQL follows the actual database representation.

## SQL Validation

Generated SQL passes through a validation layer before execution.

The validator:

- Removes Markdown SQL code fences
- Requires read-only SQL
- Blocks `INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `TRUNCATE`, `CREATE`, `GRANT`, and `REVOKE`
- Allows analytical read queries, including CTE-based queries

The current validator is lightweight and regex-based. A full SQL parser and stricter production database permissions are future improvements.

## Human-Readable Answers

After SQL execution, QueryLens generates a concise natural-language answer alongside structured results.

The answer generator does not independently query the database; PostgreSQL results are the source of truth.

Example:

```text
User:
How many customers are there?

Answer:
There are 91 customers.
```

For large result sets:

```text
91 records match your request. The complete results are available in the table below.
```

The frontend also exposes the structured rows and executed SQL.

## Database

QueryLens currently uses the **Northwind PostgreSQL sample database**.

The database contains 13 tables and entities such as customers, employees, products, suppliers, orders, order details, categories, and shippers.

Selected dataset characteristics:

| Entity | Rows |
|---|---:|
| Customers | 91 |
| Products | 77 |
| Orders | 830 |

The database was migrated from local PostgreSQL to hosted PostgreSQL for the deployed application.

## Evaluation

A fixed **50-question benchmark** was created to evaluate the system.

The benchmark includes clear and ambiguous questions covering aggregations, ranking, filtering, date-based analysis, joins, derived metrics, analytical SQL, and clarification-dependent questions.

The expected SQL was verified for execution before evaluation.

### Final trusted hybrid evaluation

| Metric | Result |
|---|---:|
| Total questions | 50 |
| Correct | 38 |
| Incorrect | 12 |
| Overall correctness | **76%** |
| Direct-query correctness | **71.05%** |
| Clarification-query correctness | **91.67%** |
| Ambiguity detection accuracy | **98%** |
| Ambiguity recall | **100%** |
| Invalid SQL | **0%** |
| Execution failures | **0%** |

### Ambiguity detection

```text
True Positives  = 12
True Negatives  = 37
False Positives = 1
False Negatives = 0
```

Therefore:

```text
Accuracy = 98%
Recall   = 100%
```

The evaluation combines deterministic checks and AI-assisted semantic evaluation where exact SQL comparison is insufficient.

These results apply to the current 50-question benchmark and are not intended to represent universal Text-to-SQL performance.

## Frontend

QueryLens uses a custom React interface designed as a **data exploration workspace rather than a chatbot**.

### Stack

- React 19
- TypeScript
- Vite
- Vanilla CSS
- Lucide React
- Highlight.js

### Interface

- Natural-language query input
- Example queries
- Clarification interface
- Human-readable answer
- Dynamic result table
- SQL viewer and copy action
- Session history
- Collapsible sidebar
- Dark mode
- Responsive layout
- Loading and error states
- Number and currency formatting

## API

Primary endpoint:

```text
POST /query
```

### Initial question

```json
{
  "conversation_id": "example-1",
  "question": "How many customers are there?",
  "clarification_answer": null
}
```

### Ready response

```json
{
  "status": "ready",
  "answer": "There are 91 customers.",
  "sql": "SELECT COUNT(*) AS total_customers FROM customer;",
  "result": [
    {
      "total_customers": 91
    }
  ]
}
```

### Clarification response

```json
{
  "status": "clarification_needed",
  "clarification_question": "What should customers be ranked by?"
}
```

Additional endpoints:

```text
GET /
GET /docs
GET /test-db
GET /schema
POST /query
```

## Project Structure

```text
intelligent-text-to-sql/
│
├── backend/
│   ├── main.py
│   ├── database.py
│   ├── schema.py
│   ├── models.py
│   ├── llm.py
│   ├── ambiguity.py
│   ├── answer_generator.py
│   ├── validator.py
│   ├── executor.py
│   ├── conversation.py
│   ├── baseline.py
│   └── test_*.py
│
├── evaluation/
│   ├── benchmark_with_expected_sql.json
│   ├── benchmark_verified.json
│   ├── verify_benchmark.py
│   ├── baseline_results.json
│   ├── compare_baseline.py
│   ├── clarification_results.json
│   ├── run_clarification_evaluation.py
│   └── ...
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── hooks/
│   │   ├── services/
│   │   ├── types/
│   │   ├── utils/
│   │   ├── styles/
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── public/
│   ├── package.json
│   └── vite.config.ts
│
├── requirements.txt
├── .env.example
└── README.md
```

## Local Development

### Prerequisites

- Python 3.12+
- Node.js
- PostgreSQL
- Groq API key

### Clone

```bash
git clone https://github.com/aviral-2005/intelligent-text-to-sql.git
cd intelligent-text-to-sql
```

### Backend

```powershell
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

Create `.env`:

```env
DATABASE_URL=postgresql+psycopg://username:password@localhost:5432/northwind
GROQ_API_KEY=your_groq_api_key
GROQ_SMALL_MODEL=openai/gpt-oss-20b
GROQ_SQL_MODEL=openai/gpt-oss-120b
```

Start FastAPI:

```bash
uvicorn backend.main:app --reload
```

API:

```text
http://localhost:8000
```

Swagger:

```text
http://localhost:8000/docs
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Use the Vite URL shown in the terminal.

## Deployment

Current deployment:

```text
Frontend → Vercel
Backend  → Render
Database → Render PostgreSQL
```

Backend start command:

```bash
uvicorn backend.main:app --host 0.0.0.0 --port $PORT
```

Backend:

https://querylens-api-xl5o.onrender.com

Swagger:

https://querylens-api-xl5o.onrender.com/docs

Required backend environment variables:

```env
DATABASE_URL=...
GROQ_API_KEY=...
GROQ_SMALL_MODEL=openai/gpt-oss-20b
GROQ_SQL_MODEL=openai/gpt-oss-120b
```

Secrets and connection strings should be configured through the hosting provider and never committed to Git.

> The current hosted PostgreSQL instance uses a free/temporary hosting configuration. Long-term database persistence should be revisited before treating the demo as a permanent production service.

## Limitations

- SQL correctness is not perfect.
- Ambiguity detection can produce false positives.
- The SQL validator is regex-based.
- The benchmark contains 50 questions and does not cover every possible database workload.
- The current database is the Northwind sample dataset.
- Authentication and user management are not implemented.
- Rate limiting is not implemented.
- Long-term database persistence requires a permanent hosting strategy.
- Model behavior can vary with model/provider changes.

## Future Improvements

- Larger and more diverse Text-to-SQL benchmarks
- More robust SQL parsing and validation
- Database permission isolation
- Query cost/complexity checks
- Schema-aware retrieval for larger databases
- Query result visualization
- Automatic chart generation
- Streaming responses
- Authentication and user accounts
- Persistent query history
- Multiple database connections
- Support for additional SQL dialects
- Better ambiguity explanations
- Human feedback loops for evaluation
- More systematic error analysis

## Why QueryLens?

Most Text-to-SQL demonstrations focus primarily on:

```text
Natural language → SQL
```

QueryLens focuses on the step **before** SQL generation:

```text
Natural language
       ↓
Is the intent sufficiently specified?
       ↓
      Yes ─────────→ SQL
       │
       No
       ↓
Clarify with the user
       ↓
Generate SQL
```

This makes QueryLens an exploration of **intent-aware Text-to-SQL**, rather than only an SQL-generation wrapper around an LLM.

## Repository

GitHub:

https://github.com/aviral-2005/intelligent-text-to-sql

Backend API:

https://querylens-api-xl5o.onrender.com

API documentation:

https://querylens-api-xl5o.onrender.com/docs

## Author

**Aviral Tripathi**

B.Tech — Computer Science & Data Science

Interested in:

- AI / ML
- Generative AI
- LLM applications
- Data Science
- Backend Engineering
- Intelligent developer tools
