from backend.ambiguity import detect_ambiguity


questions = [
    "How many customers are there?",
    "Which customers are located in London?",
    "What are our top customers?",
    "Which products performed best?",
    "How many orders did each employee handle?",
    "What are our recent orders?",
    "Which products are considered expensive?",
    "Show me our active customers.",
    "Which orders would you consider large?",
]


for question in questions:

    print("\nQuestion:", question)

    result = detect_ambiguity(question)

    print("Ambiguous:", result.is_ambiguous)
    print("Clarification:", result.clarification_question)