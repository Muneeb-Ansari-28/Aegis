Given the following conversation history between a user and an AI security assistant, rewrite the last user message as a single, self-contained search query for retrieving technical security documentation.

Rules:
- Resolve ambiguous references and pronouns such as "it", "its mitigations", "that one", "the second one", or "why" using the preceding turns.
- If the user query is already self-contained (e.g. "What is LLM01:2026?"), keep it as is.
- Preserve exact vulnerability codes (e.g. LLM08:2026, LLM01:2026).
- Output ONLY the search query string and nothing else.

Conversation History:
{history_turns}

User's last message:
{message}
