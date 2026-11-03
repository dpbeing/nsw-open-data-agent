import json
from pathlib import Path
import os
from openai import OpenAI
from agent.tools import rank_median_rents, median_rent_for_postcode, monthly_rent_trend

MODEL = "qwen3:8b"
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATABASE = PROJECT_ROOT / "data" / "processed" / "rental_bonds.duckdb"

SYSTEM_PROMPT = """
You answer questions using NSW Fair Trading rental bond lodgements for 2025.

You have two tool: rank_median_rents and also by postcodes.
Use it for questions comparing median weekly rent by postcode.
The tool accepts a dwelling type code:
F = flat/unit, H = house, T = terrace/townhouse/semi-detached,
O = other.
When the question names one postcode, use median_rent_for_postcode.
When it asks to rank postcodes, use rank_median_rents.
The dataset measures bedrooms, not total rooms. If you interpret “rooms”
as bedrooms, say so in the answer.

For questions about how rent changed month by month in a postcode, use
monthly_rent_trend. For a single postcode median, use
median_rent_for_postcode. For ranking postcodes, use rank_median_rents.

Use only the tool result for factual rent figures. Explain the filters,
sample size, and that bond lodgements are not all current rental contracts.
If the question cannot be answered with this tool, say so.
Be concise.
"""

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "rank_median_rents",
            "description": "Rank postcodes by 2025 median weekly rent for a dwelling type and bedroom count.",
            "parameters": {
                "type": "object",
                "properties": {
                    "dwelling_type": {"type": "string"},
                    "bedrooms": {"type": "integer"},
                },
                "required": ["dwelling_type", "bedrooms"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "median_rent_for_postcode",
            "description": "Get the 2025 median weekly rent for one postcode, dwelling type, and bedroom count.",
            "parameters": {
                "type": "object",
                "properties": {
                    "postcode": {"type": "string"},
                    "dwelling_type": {"type": "string"},
                    "bedrooms": {"type": "integer"},
                },
                "required": ["postcode", "dwelling_type", "bedrooms"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "monthly_rent_trend",
            "description": "Get monthly 2025 median weekly rents and lodgement counts for one postcode, dwelling type, and bedroom count.",
            "parameters": {
                "type": "object",
                "properties": {
                    "postcode": {"type": "string"},
                    "dwelling_type": {"type": "string"},
                    "bedrooms": {"type": "integer"},
                },
                "required": ["postcode", "dwelling_type", "bedrooms"],
                "additionalProperties": False,
            },
        },
    },
]

def ask_agent(
            question: str,
            *,
            provider: str | None = None,
            api_key: str | None = None,
    ) -> dict:
    provider = (provider or os.getenv("LLM_PROVIDER", "ollama")).strip().lower()

    if provider == "ollama":
        client = OpenAI(
            base_url="http://localhost:11434/v1",
            api_key="ollama",  # Local Ollama ignores this value.
        )
        model = os.getenv("OLLAMA_MODEL", "qwen3:8b")
    elif provider == "groq":
        api_key = api_key or os.getenv("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError("GROQ_API_KEY is required when LLM_PROVIDER=groq.")
        client = OpenAI(
            base_url="https://api.groq.com/openai/v1",
            api_key=api_key,
        )
        model = os.getenv("GROQ_MODEL", "qwen/qwen3.8-27b")
    else:
        raise ValueError("LLM_PROVIDER must be 'ollama' or 'groq'.")

    available_tools = {
        "rank_median_rents": rank_median_rents,
        "median_rent_for_postcode": median_rent_for_postcode,
        "monthly_rent_trend": monthly_rent_trend,
    }
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": question},
    ]
    tool_trace = []

    for _ in range(3):
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=TOOL_SCHEMAS,
            temperature=0,
            reasoning_effort="none",
        )
        message = response.choices[0].message
        tool_calls = message.tool_calls or []

        assistant_message = {"role": "assistant", "content": message.content}
        if tool_calls:
            assistant_message["tool_calls"] = [
                {
                    "id": call.id,
                    "type": "function",
                    "function": {
                        "name": call.function.name,
                        "arguments": call.function.arguments,
                    },
                }
                for call in tool_calls
            ]
        messages.append(assistant_message)

        if not tool_calls:
            answer = (message.content or "").strip()
            return {
                "answer": answer or "The model returned no text.",
                "evidence": tool_trace,
            }

        for call in tool_calls:
            name = call.function.name
            try:
                arguments = json.loads(call.function.arguments or "{}")
                function = available_tools.get(name)
                result = (
                    function(**arguments)
                    if function
                    else {"error": f"Unknown tool: {name}"}
                )
            except (json.JSONDecodeError, TypeError) as error:
                arguments = call.function.arguments
                result = {"error": f"Invalid tool arguments: {error}"}

            tool_trace.append({
                "tool": name,
                "arguments": arguments,
                "result": result,
            })
            messages.append({
                "role": "tool",
                "tool_call_id": call.id,
                "content": json.dumps(result),
            })

    return {
        "answer": "I couldn't complete the answer within the tool-call limit.",
        "evidence": tool_trace,
    }


if __name__ == "__main__":
    question = input(
        "Ask about 2025 NSW rents "
        "(e.g. 'Which postcodes have the highest median rent for "
        "2-bedroom flats?'): "
    )
    print("\nAgent:", ask_agent(question))
