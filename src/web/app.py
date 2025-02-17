import streamlit as st

from src.core.utils.logger import setup_logger
from src.rag.qa_bot import QABot, SearchMethod
from src.elastic.client import get_elasticsearch_client
from src.core.config import ElasticsearchConfig, OpenAIConfig

logger = setup_logger(__name__)

def get_available_courses() -> list[str]:
    """Get the list of available courses from Elasticsearch."""
    es_client = get_elasticsearch_client()
    es_config = ElasticsearchConfig()
    response = es_client.search(
        index=es_config.index_name,
        body={
            "size": 0,
            "aggs": {
                "unique_courses": {
                    "terms": {
                        "field": "course"
                    }
                }
            }
        }
    )
    courses = ["All courses"]  # Add "All courses" as the first option
    courses.extend([bucket["key"] for bucket in response["aggregations"]["unique_courses"]["buckets"]])
    return courses

def initialize_qa_system(search_method: SearchMethod, temperature: float) -> QABot:
    """Initialize the QA system with required components."""
    try:
        # Create a custom OpenAI config with the user-selected temperature
        openai_config = OpenAIConfig()
        openai_config.temperature = temperature
        
        qa_bot = QABot(search_method=search_method)
        qa_bot.openai_config = openai_config
        return qa_bot
    except Exception as e:
        logger.log_error("Failed to initialize QA system", ex=e)
        st.error("Failed to initialize the Q&A system. Please try again later.")
        st.stop()


def main():
    """Main entry point for the Streamlit web application."""
    st.title("DataTalks.Club Q&A System")
    st.subheader("Ask questions about our courses")

    # Sidebar for settings
    with st.sidebar:
        st.header("Settings ⚙️")
        
        # Search method selection
        search_method_str = st.radio(
            "Search Method",
            options=["Text-based", "Vector-based (Semantic)"],
            help="Choose between traditional text search or semantic vector search"
        )
        search_method = SearchMethod.TEXT if search_method_str == "Text-based" else SearchMethod.VECTOR
        
        # Temperature control
        temperature = st.slider(
            "Temperature",
            min_value=0.0,
            max_value=1.0,
            value=0.7,
            step=0.1,
            help="Controls the randomness in the AI's responses. Higher values make the output more creative but less focused."
        )
        
        st.markdown("---")
        st.markdown("""
        ### Search Methods Info ℹ️
        - **Text-based**: Traditional keyword matching
        - **Vector-based**: Semantic similarity search using embeddings
        """)

    # Initialize QA bot with selected settings
    qa_bot = initialize_qa_system(search_method, temperature)

    with st.form(key="qa_form"):
        selected_course = st.selectbox(
            "Select a course",
            options=get_available_courses(),
            help="Choose the course you want to ask about. Select 'All courses' to search across all courses.",
        )

        # Convert "All courses" to None for the backend
        course_filter = None if selected_course == "All courses" else selected_course

        user_question = st.text_input("Your question", placeholder="Type your question here...")

        response_placeholder = st.empty()
        submit_button = st.form_submit_button(label="Ask Question")

    if submit_button:
        if not user_question.strip():
            st.warning("Please enter a question.")
            return

        try:
            with st.spinner("Finding answer..."):
                response = qa_bot.answer_question(user_question, course=course_filter)
                response_placeholder.markdown(response)
        except Exception as e:
            logger.log_error("Error processing question", ex=e)
            response_placeholder.error(
                "An error occurred while processing your question. Please try again."
            )


if __name__ == "__main__":
    main()
