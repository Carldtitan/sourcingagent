"""Reading JSON back out of a model reply.

Models fence their JSON, apologise before it, and occasionally run out of
tokens halfway through. None of that is worth a failed run, so the reply is
unwrapped, repaired where the repair is unambiguous, and retried once when it
genuinely cannot be read.
"""

from __future__ import annotations

import json
import re

from . import config


FENCE = re.compile(r"```(?:json)?\s*(.*?)```", re.S)


def extract(raw: str) -> dict:
    text = raw.strip()

    fence = FENCE.search(text)
    if fence:
        text = fence.group(1).strip()

    start = text.find("{")
    if start == -1:
        raise ValueError(f"no JSON object in reply: {raw[:300]}")

    depth = 0
    in_string = False
    escaped = False
    for index in range(start, len(text)):
        char = text[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return json.loads(text[start : index + 1])

    # The reply was cut off mid-object. Close what is open and keep the
    # complete keys, which beats losing the whole reply.
    truncated = text[start:].rstrip().rstrip(",")
    if in_string:
        truncated += '"'
    return json.loads(truncated + "}" * max(depth, 1))


def ask(prompt: str, *, max_tokens: int = 1400) -> dict:
    from anthropic import Anthropic

    client = Anthropic(api_key=config.need("ANTHROPIC_API_KEY"))

    strict = (
        prompt
        + "\n\nRespond with the JSON object only. No code fence, no commentary, "
        "nothing before or after it."
    )

    last: Exception | None = None
    for attempt in range(2):
        response = client.messages.create(
            model=config.MODEL,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": strict}],
        )
        raw = "".join(b.text for b in response.content if b.type == "text")
        try:
            return extract(raw)
        except Exception as error:
            last = error
            max_tokens *= 2

    raise ValueError(f"could not read JSON from the model: {last}")
