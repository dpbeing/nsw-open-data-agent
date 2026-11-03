import os
import streamlit as st
import pandas as pd

from agent.core import ask_agent

def get_llm_settings() -> tuple[str, str | None]:
    try:
        provider = st.secrets.get(
            "LLM_PROVIDER",
            os.getenv("LLM_PROVIDER", "ollama"),
        )
        api_key = st.secrets.get(
            "GROQ_API_KEY",
            os.getenv("GROQ_API_KEY"),
        )
    except FileNotFoundError:
        provider = os.getenv("LLM_PROVIDER", "ollama")
        api_key = os.getenv("GROQ_API_KEY")

    return provider, api_key

def render_monthly_rent_chart(evidence: list[dict]) -> None:
    trend_call = next(
        (item for item in evidence if item.get("tool") == "monthly_rent_trend"),
        None,
    )
    if trend_call is None:
        return

    months = trend_call.get("result", {}).get("months", [])
    if not months:
        return

    chart_data = pd.DataFrame(months).set_index("month")

    st.caption(
        "Monthly median weekly rent "
        f"for postcode {trend_call['arguments']['postcode']}"
    )
    st.line_chart(
        chart_data,
        y="median_weekly_rent_aud",
        x_label="Month",
        y_label="Median weekly rent (AUD)",
        alt="Monthly median weekly rent from 2025 rental bond lodgements",
    )

st.set_page_config(
    page_title="NSW Rent Insights Agent",
    page_icon="🏠",
    layout="centered",
)

st.title("NSW Rent Insights Agent")
st.caption("Ask questions about NSW rental bond lodgements from 2025.")

with st.sidebar:
    st.header("About this data")
    st.write("Source: NSW Fair Trading rental bond lodgements.")
    st.write("Coverage: calendar year 2025.")
    st.write("Breakdowns: postcode, dwelling type, and bedrooms.")
    st.write(
        "Unknown and non-positive rents are excluded from rent calculations."
    )
    st.caption(
        "These are bond lodgements, not all current rental contracts. "
        "The data records bedrooms, not total room counts."
    )
    st.caption("Each question is processed independently; chat memory comes later.")

if "messages" not in st.session_state:
    st.session_state.messages = []

if st.sidebar.button("Clear chat"):
    st.session_state.messages = []
    st.rerun()

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

question = st.chat_input("For example: What is the median rent for a 4-bedroom house in 2570?")

if question:
    st.session_state.messages.append(
        {"role": "user", "content": question}
    )
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        with st.spinner("Querying the local agent..."):
            provider, api_key = get_llm_settings()
            result = ask_agent(question, provider=provider, api_key=api_key)
            print("Agent result:", repr(result))

            if isinstance(result, str):
                result = {"answer": result, "evidence": []}

            answer = result.get("answer") or "No answer text was returned."
            st.markdown(answer)
            render_monthly_rent_chart(result["evidence"])

            if result.get("evidence"):
                with st.expander("See data and tool details"):
                    for item in result["evidence"]:
                        st.write("Tool:", item["tool"])
                        st.write("Arguments:", item["arguments"])
                        st.json(item["result"])

    st.session_state.messages.append(
        {"role": "assistant", "content": answer}
    )