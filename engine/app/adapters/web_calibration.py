"""Visible-Browser Selector Capture and Calibration."""
class WebCalibration:
    """Aids users in selecting input, submit, and response DOM elements."""
    async def start_interactive_session(self, url: str) -> dict:
        return {
            "input_selector": "textarea#chat-input",
            "submit_selector": "button#send",
            "response_selector": ".chat-message.assistant:last-child",
        }
