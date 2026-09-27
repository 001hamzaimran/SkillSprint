import json
import hashlib
import time
from openai import (
    OpenAI,
    AuthenticationError,
    RateLimitError,
    APIConnectionError,
    APITimeoutError,
    APIStatusError,
)
from .config import ROOT


class GenerationFailure(Exception):
    pass


def structured(settings, schema, template, payload, on_attempt=lambda *args: None):
    if not settings.openai_api_key:
        raise GenerationFailure(
            "Add a valid OPENAI_API_KEY to your local .env and restart the server to enable AI generation."
        )
    prompt = (ROOT / "prompt_templates" / template).read_text(encoding="utf-8")
    client = OpenAI(api_key=settings.openai_api_key, timeout=65, max_retries=0)
    try:
        for attempt in range(1, 3):
            on_attempt(attempt, "request")
            try:
                response = client.responses.parse(
                    model=settings.genai_model,
                    input=[
                        {"role": "system", "content": prompt},
                        {"role": "user", "content": json.dumps(payload)},
                    ],
                    text_format=schema,
                    max_output_tokens=18000,
                    store=False,
                )
                if response.output_parsed is None:
                    raise GenerationFailure(
                        "The provider returned an incomplete or refused structured response. No plan was approved."
                    )
                return response.output_parsed, {
                    "response_id": response.id,
                    "model": response.model,
                    "usage": response.usage.model_dump() if response.usage else {},
                    "attempts": attempt,
                    "prompt_version": template,
                    "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
                }
            except AuthenticationError:
                raise GenerationFailure(
                    "The AI provider rejected the API key. Replace OPENAI_API_KEY locally and restart."
                ) from None
            except RateLimitError:
                raise GenerationFailure(
                    "The AI provider reported a quota or rate limit. Check account billing and limits, then retry."
                ) from None
            except (APIConnectionError, APITimeoutError):
                on_attempt(attempt, "connection_or_timeout")
                if attempt == 2:
                    raise GenerationFailure(
                        "The AI provider could not be reached after two attempts. Retry when connectivity is restored."
                    ) from None
                time.sleep(1)
            except APIStatusError:
                raise GenerationFailure(
                    "The AI provider rejected this request. Check model availability and account configuration."
                ) from None
            except GenerationFailure:
                raise
            except Exception:
                on_attempt(attempt, "invalid_structured_response")
                if attempt == 2:
                    raise GenerationFailure(
                        "The AI provider returned invalid structured output twice. No plan was approved."
                    ) from None
    finally:
        client.close()
