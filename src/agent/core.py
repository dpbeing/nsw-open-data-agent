import json
from pathlib import Path
from ollama import chat
from agent.tools import rank_median_rents, median_rent_for_postcode

MODEL = "qwen3:8b"
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATABASE = PROJECT_ROOT / "data" / "processed" / "rental_bonds.duckdb"
# DATABASE = (
#         Path(__file__).resolve().parent / "data" / "processed" / "rental_bonds.duckdb"
# )

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

Use only the tool result for factual rent figures. Explain the filters,
sample size, and that bond lodgements are not all current rental contracts.
If the question cannot be answered with this tool, say so.
Be concise.
"""

def ask_agent(question: str) -> dict:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": question},
    ]

    available_tools = {
        "rank_median_rents": rank_median_rents,
        "median_rent_for_postcode": median_rent_for_postcode,
    }
    tool_trace = []

    for _ in range(3):
        response = chat(
            model=MODEL,
            messages=messages,
            tools=list(available_tools.values()),
            think=False,
            options={"temperature": 0},
        )
        messages.append(response.message)

        if not response.message.tool_calls:
            answer = (response.message.content or "").strip()
            if not answer:
                answer = "The model returned no text."
            return {"answer": answer, "evidence": tool_trace}

        for tool_call in response.message.tool_calls:
            name = tool_call.function.name
            arguments = tool_call.function.arguments
            print("Tool call:", name, arguments)

            function = available_tools.get(name)
            result = (
                function(**arguments)
                if function
                else {"error": "Unknown tool"}
            )

            tool_trace.append({
                "tool": name,
                "arguments": arguments,
                "result": result,
            })
            messages.append({
                "role": "tool",
                "tool_name": name,
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
