"""Simple conversation memory management for the study buddy chatbot."""


class ConversationMemory:
    """Store and manage conversation history with a rolling window."""

    def __init__(self, max_turns: int = 10):
        """
        Initialize memory with a max turn limit.
        
        Args:
            max_turns: Maximum number of (user, assistant) turn pairs to keep.
                      Default is 10 turns.
        """
        self.max_turns = max_turns
        self.messages = []

    def add_user_message(self, content: str) -> None:
        """Add a user message to the conversation."""
        if content and isinstance(content, str):
            self.messages.append({"role": "user", "content": content.strip()})
            self._trim_to_max_turns()

    def add_assistant_message(self, content: str) -> None:
        """Add an assistant message to the conversation."""
        if content and isinstance(content, str):
            self.messages.append({"role": "assistant", "content": content.strip()})
            self._trim_to_max_turns()

    def get_messages(self) -> list[dict]:
        """Return all stored messages."""
        return self.messages.copy()

    def get_context_text(self) -> str:
        """
        Format conversation as readable context for context window management.
        
        Returns:
            A formatted string of recent conversation suitable for display or
            as additional context to a model.
        """
        if not self.messages:
            return ""

        lines = []
        for msg in self.messages:
            role = msg.get("role", "unknown").capitalize()
            content = msg.get("content", "")
            lines.append(f"{role}: {content}")

        return "\n".join(lines)

    def clear(self) -> None:
        """Clear all messages from memory."""
        self.messages = []

    def _trim_to_max_turns(self) -> None:
        """Keep only the most recent max_turns (user, assistant) pairs."""
        # Count assistant messages; each pair is one turn
        assistant_count = sum(1 for m in self.messages if m.get("role") == "assistant")

        # If we exceed max_turns, remove oldest messages
        if assistant_count > self.max_turns:
            excess = assistant_count - self.max_turns
            removed = 0
            i = 0
            while removed < excess and i < len(self.messages):
                if self.messages[i].get("role") == "assistant":
                    removed += 1
                i += 1

            # Remove messages up to this point (typically a user + assistant pair)
            self.messages = self.messages[i:]


if __name__ == "__main__":
    print("Conversation Memory Test")
    print("=" * 60)

    # Create memory with small limit for testing
    memory = ConversationMemory(max_turns=3)

    # Add messages
    print("\nAdding messages...")
    memory.add_user_message("What is function calling?")
    memory.add_assistant_message("Function calling lets the model request that the application execute a function.")
    memory.add_user_message("How do I use it in my project?")
    memory.add_assistant_message("You define tools as JSON schemas and pass them to the API.")
    memory.add_user_message("Can I combine it with embeddings?")
    memory.add_assistant_message("Yes, you can use embeddings to retrieve context and then call functions based on that context.")

    print(f"\nCurrent conversation ({len(memory.messages)} messages):")
    print("-" * 60)
    print(memory.get_context_text())

    # Add more messages to trigger trimming
    print("\n\nAdding more messages to test trimming (max_turns=3)...")
    memory.add_user_message("What about ChromaDB?")
    memory.add_assistant_message("ChromaDB is a vector database for storing and querying embeddings.")
    memory.add_user_message("How do I persist it?")
    memory.add_assistant_message("Use PersistentClient with a path to save embeddings to disk.")

    print(f"\nAfter trimming ({len(memory.messages)} messages):")
    print("-" * 60)
    print(memory.get_context_text())

    # Test get_messages
    print("\n\nRaw messages list:")
    print("-" * 60)
    for i, msg in enumerate(memory.get_messages()):
        print(f"{i + 1}. {msg}")

    # Test clear
    print("\n\nClearing memory...")
    memory.clear()
    print(f"Messages after clear: {len(memory.get_messages())}")
