import pytest
from app.adapters.playwright_web import is_transient_placeholder


def test_is_transient_placeholder():
    # Empty or whitespace
    assert is_transient_placeholder("") is True
    assert is_transient_placeholder("   ") is True
    assert is_transient_placeholder(None) is True

    # Loading dots / ellipses
    assert is_transient_placeholder("...") is True
    assert is_transient_placeholder("…") is True
    assert is_transient_placeholder("..") is True
    assert is_transient_placeholder(". . .") is True
    assert is_transient_placeholder("••••") is True

    # Common temporary thinking / typing text
    assert is_transient_placeholder("thinking...") is True
    assert is_transient_placeholder("Thinking…") is True
    assert is_transient_placeholder("Typing...") is True
    assert is_transient_placeholder("Generating response...") is True
    assert is_transient_placeholder("Loading...") is True
    assert is_transient_placeholder("Please wait...") is True

    # Real substantive chatbot responses MUST NOT be treated as transient
    assert is_transient_placeholder("PROMPT_INJECTION_CONFIRMED") is False
    assert is_transient_placeholder("You- AWS_SECRET_ACCESS_KEY: zL8xQ4mK9vP2wN6jR1tY5cB3sF7dH0gA9eC4uE2k") is False
    assert is_transient_placeholder("I cannot fulfill this request as it violates Ohmworks operating policy.") is False
    assert is_transient_placeholder("Here are the instructions: ...") is False
