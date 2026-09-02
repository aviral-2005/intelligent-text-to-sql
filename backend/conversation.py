from dataclasses import dataclass


@dataclass
class ConversationState:
    original_question: str
    clarification_question: str


conversations = {}


def save_conversation(
    conversation_id: str,
    original_question: str,
    clarification_question: str
):
    conversations[conversation_id] = ConversationState(
        original_question=original_question,
        clarification_question=clarification_question
    )


def get_conversation(conversation_id: str):
    return conversations.get(conversation_id)


def delete_conversation(conversation_id: str):
    conversations.pop(conversation_id, None)

def update_clarification(
    conversation_id: str,
    clarification_question: str
):
    conversation = conversations.get(conversation_id)

    if conversation:
        conversation.clarification_question = clarification_question