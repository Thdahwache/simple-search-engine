import streamlit as st

from src.core.config import AppConfig
from src.core.utils.logger import setup_logger
from src.rag.qa_bot import QABot

logger = setup_logger(__name__)


def initialize_qa_system() -> QABot:
    """Initialize the QA system with required components."""
    try:
        return QABot()
    except Exception as e:
        logger.error(f"Failed to initialize QA system: {e}")
        st.error("Failed to initialize the Q&A system. Please try again later.")
        st.stop()


def main():
    """Main entry point for the Streamlit web application."""
    st.title("DataTalks.Club Q&A System")
    st.subheader("Ask questions about our courses")

    qa_bot = initialize_qa_system()
    app_config = AppConfig()

    with st.form(key="qa_form"):
        selected_course = st.selectbox(
            "Select a course",
            options=app_config.available_courses,
            help="Choose the course you want to ask about",
        )

        user_question = st.text_input("Your question", placeholder="Type your question here...")

        response_placeholder = st.empty()
        submit_button = st.form_submit_button(label="Ask Question")

    if submit_button:
        if not user_question.strip():
            st.warning("Please enter a question.")
            return

        try:
            with st.spinner("Finding answer..."):
                response = qa_bot.answer_question(user_question, course=selected_course)
                response_placeholder.markdown(response)
        except Exception as e:
            logger.error(f"Error processing question: {e}")
            response_placeholder.error(
                "An error occurred while processing your question. Please try again."
            )


if __name__ == "__main__":
    main()
