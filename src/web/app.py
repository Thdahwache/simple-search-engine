import streamlit as st

from src.core.config import AppConfig
from src.core.utils.logger import setup_logger
from src.rag.qa_bot import QABot
from src.elastic.client import get_elasticsearch_client
from src.elastic.queries import unique_course_values
from src.core.config import ElasticsearchConfig

logger = setup_logger(__name__)

def get_available_courses() -> list[str]:
    """Get the list of available courses from Elasticsearch."""
    es_client = get_elasticsearch_client()
    es_config = ElasticsearchConfig()
    response = es_client.search(index=es_config.index_name, body=unique_course_values)
    return response["aggregations"]["unique_values"]["buckets"]

def initialize_qa_system() -> QABot:
    """Initialize the QA system with required components."""
    try:
        return QABot()
    except Exception as e:
        logger.log_error("Failed to initialize QA system", ex=e)
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
            options=get_available_courses(),
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
            logger.log_error("Error processing question", ex=e)
            response_placeholder.error(
                "An error occurred while processing your question. Please try again."
            )


if __name__ == "__main__":
    main()
