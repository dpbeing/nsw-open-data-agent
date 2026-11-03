import streamlit as st

from agent.core import ask_agent


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
            result = ask_agent(question)
            print("Agent result:", repr(result))

            if isinstance(result, str):
                result = {"answer": result, "evidence": []}

            answer = result.get("answer") or "No answer text was returned."
            st.markdown(answer)

            if result.get("evidence"):
                with st.expander("See data and tool details"):
                    for item in result["evidence"]:
                        st.write("Tool:", item["tool"])
                        st.write("Arguments:", item["arguments"])
                        st.json(item["result"])

    st.session_state.messages.append(
        {"role": "assistant", "content": answer}
    )