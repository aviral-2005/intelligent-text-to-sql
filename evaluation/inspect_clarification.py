import json
from pathlib import Path


FILE = Path("evaluation/clarification_results.json")

data = json.loads(FILE.read_text(encoding="utf-8"))

for item in data["results"]:

    if item["status"] == "PASS":
        continue

    print("\n" + "=" * 80)
    print(f"Q{item['id']:02d}: {item['question']}")
    print(f"Status: {item['status']}")

    response = item["response"]

    print("\nFIRST RESPONSE:")
    print(json.dumps(response, indent=2, default=str))

    if item["expected_behavior"] == "clarification":
        print("\nEXPECTED BEHAVIOR: clarification")

        # The second response isn't currently stored by our evaluator.
        # So we need to identify the problem from the first response.