"""Unit tests for Site-Type Classifier and Heuristic Fallbacks."""
import pytest
from app.recon.classifier import SiteTypeClassifier


@pytest.mark.asyncio
async def test_classifier_deterministic_fallback():
    classifier = SiteTypeClassifier()

    # Customer support keywords
    res1 = classifier._deterministic_fallback(
        page_title="Acme Help Desk",
        page_text="Welcome to customer service and support FAQ.",
        scope_reply="I help customers with billing and support.",
    )
    assert res1.site_type == "customer_support"
    assert res1.confidence >= 0.70

    # Code assistant keywords
    res2 = classifier._deterministic_fallback(
        page_title="Code Pilot",
        page_text="AI programming helper for Python and TypeScript software developers.",
        scope_reply="I can debug code and explain functions.",
    )
    assert res2.site_type == "code_assistant"
    assert res2.primary_domain == "software"

    # Default fallback
    res3 = classifier._deterministic_fallback(
        page_title="Something Unknown",
        page_text="Hello world.",
        scope_reply="Hi.",
    )
    assert res3.site_type == "general_assistant"

    # Booking bot keywords (including "agent" in scope_reply should still classify as booking_bot)
    res4 = classifier._deterministic_fallback(
        page_title="SkyReserve",
        page_text="Manage your flight booking, hotel reservation, and itinerary.",
        scope_reply="I am your travel booking agent.",
    )
    assert res4.site_type == "booking_bot"
    assert res4.primary_domain == "travel"

    # Education bot keywords
    res5 = classifier._deterministic_fallback(
        page_title="UniLearn LMS",
        page_text="Welcome student! Check your course exam schedule and grade.",
        scope_reply="I am your AI tutor.",
    )
    assert res5.site_type == "education_bot"
    assert res5.primary_domain == "education"

