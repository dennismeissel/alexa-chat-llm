import logging
import ask_sdk_core.utils as ask_utils
import requests
import os
import json
from dotenv import load_dotenv

from ask_sdk_core.skill_builder import SkillBuilder
from ask_sdk_core.dispatch_components import AbstractRequestHandler
from ask_sdk_core.dispatch_components import AbstractExceptionHandler
from ask_sdk_core.handler_input import HandlerInput

from ask_sdk_core.utils import get_slot_value
from ask_sdk_model.dialog import DelegateDirective
from ask_sdk_model import Response, Intent, Slot

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

load_dotenv()

LLM_URL = os.getenv("LLM_URL", "").strip()
LLM_KEY = os.getenv("LLM_KEY", "").strip()
LLM_MODEL = os.getenv("LLM_MODEL", "").strip()
SYSTEM_PROMPT = os.getenv("SYSTEM_PROMPT", "").strip()

# Load responses from .env
RESPONSES = {
    "en": {
        "launch": os.getenv("EN_LAUNCH_MESSAGE"),
        "no_question": os.getenv("EN_NO_QUESTION"),
        "config_error": os.getenv("EN_CONFIG_ERROR"),
        "error": os.getenv("EN_ERROR_MESSAGE"),
        "goodbye": os.getenv("EN_GOODBYE"),
        "fallback": os.getenv("EN_FALLBACK"),
        "help": os.getenv("EN_HELP_MESSAGE")
    },
    "de": {
        "launch": os.getenv("DE_LAUNCH_MESSAGE"),
        "no_question": os.getenv("DE_NO_QUESTION"),
        "config_error": os.getenv("DE_CONFIG_ERROR"),
        "error": os.getenv("DE_ERROR_MESSAGE"),
        "goodbye": os.getenv("DE_GOODBYE"),
        "fallback": os.getenv("DE_FALLBACK"),
        "help": os.getenv("DE_HELP_MESSAGE")
    }
}

def get_locale(handler_input):
    """Extract locale from request."""
    return handler_input.request_envelope.request.locale[:2]  # "en" or "de"

def get_response(handler_input, key):
    """Get the correct response message based on locale."""
    locale = get_locale(handler_input)
    return RESPONSES.get(locale, RESPONSES["en"]).get(key, "Error: Missing response.")

class LaunchRequestHandler(AbstractRequestHandler):
    """Handler for Skill Launch."""
    def can_handle(self, handler_input):
        return ask_utils.is_request_type("LaunchRequest")(handler_input)

    def handle(self, handler_input):
        speak_output = get_response(handler_input, "launch")
        
        updated_intent = Intent(
            name="llm_call",
            slots={"question": Slot(name="question")}
        )
        delegate_directive = DelegateDirective(updated_intent)
        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(speak_output)
                .add_directive(delegate_directive)
                .response
        )

class LLMCallIntentHandler(AbstractRequestHandler):
    """Handler for LLM Call Intent."""
    def can_handle(self, handler_input):
        return ask_utils.is_intent_name("llm_call")(handler_input)

    def handle(self, handler_input):
        if not LLM_URL or not LLM_KEY:
            return handler_input.response_builder.speak(get_response(handler_input, "config_error")).response

        question = get_slot_value(handler_input, "question") or ""
        if not question:
            speak_output = get_response(handler_input, "no_question")
            return handler_input.response_builder.speak(speak_output).ask(speak_output).response

        payload = {
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": question}
            ],
            "model": LLM_MODEL,
            "max_tokens": 256,
            "stream": "true",
            "temperature": 0
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {LLM_KEY}"
        }

        try:
            response = requests.post(LLM_URL, headers=headers, json=payload, stream=True)
            response.raise_for_status()

            assistant_content = ""
            for line in response.iter_lines():
                if line:
                    line_str = line.decode("utf-8").strip()
                    if line_str.startswith("data:"):
                        line_str = line_str[5:].strip()
                    if line_str == "[DONE]":
                        break
                    try:
                        data = json.loads(line_str)
                        assistant_content += data.get("choices", [{}])[0].get("delta", {}).get("content", "")
                    except json.JSONDecodeError as json_err:
                        logger.error(f"JSON decoding error: {json_err}, received: {line_str}")

            return handler_input.response_builder.speak(assistant_content).ask(assistant_content).add_directive(
                DelegateDirective(Intent(name="llm_call", slots={"question": Slot(name="question")}))).response

        except requests.exceptions.RequestException as e:
            logger.error(f"LLM service error: {e}, payload: {payload}")
            return handler_input.response_builder.speak(get_response(handler_input, "error")).response



class HelpIntentHandler(AbstractRequestHandler):
    """Handler for Help Intent."""
    def can_handle(self, handler_input):
        return ask_utils.is_intent_name("AMAZON.HelpIntent")(handler_input)

    def handle(self, handler_input):
        speak_output = get_response(handler_input, "help")
        return handler_input.response_builder.speak(speak_output).ask(speak_output).response


class CancelOrStopOrNoIntentHandler(AbstractRequestHandler):
    """Handler for Cancel, Stop, or No Intent."""
    def can_handle(self, handler_input):
        return (ask_utils.is_intent_name("AMAZON.CancelIntent")(handler_input) or
                ask_utils.is_intent_name("AMAZON.StopIntent")(handler_input) or
                ask_utils.is_intent_name("AMAZON.NoIntent")(handler_input))

    def handle(self, handler_input):
        return handler_input.response_builder.speak(get_response(handler_input, "goodbye")).set_should_end_session(True).response


class FallbackIntentHandler(AbstractRequestHandler):
    """Handler for Fallback Intent."""
    def can_handle(self, handler_input):
        return ask_utils.is_intent_name("AMAZON.FallbackIntent")(handler_input)

    def handle(self, handler_input):
        return handler_input.response_builder.speak(get_response(handler_input, "fallback")).ask(get_response(handler_input, "fallback")).response


class SessionEndedRequestHandler(AbstractRequestHandler):
    """Handler for Session End."""
    def can_handle(self, handler_input):
        return ask_utils.is_request_type("SessionEndedRequest")(handler_input)

    def handle(self, handler_input):
        return handler_input.response_builder.response


class CatchAllExceptionHandler(AbstractExceptionHandler):
    """Generic error handler."""
    def can_handle(self, handler_input, exception):
        return True

    def handle(self, handler_input, exception):
        logger.error(exception, exc_info=True)
        return handler_input.response_builder.speak(get_response(handler_input, "error")).ask(get_response(handler_input, "error")).response


sb = SkillBuilder()

sb.add_request_handler(LaunchRequestHandler())
sb.add_request_handler(LLMCallIntentHandler())
sb.add_request_handler(HelpIntentHandler())
sb.add_request_handler(CancelOrStopOrNoIntentHandler())
sb.add_request_handler(FallbackIntentHandler())
sb.add_request_handler(SessionEndedRequestHandler())

sb.add_exception_handler(CatchAllExceptionHandler())

lambda_handler = sb.lambda_handler()
