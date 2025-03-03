import datetime
import json
import time
from enum import Enum
from pathlib import Path

import pandas as pd
import streamlit as st

from src.core.config import ElasticsearchConfig, OpenAIConfig
from src.core.utils.logger import setup_logger
from src.elastic.client import get_elasticsearch_client
from src.elastic.queries import (
    build_combined_vector_knn_query,
    build_question_text_vector_knn_query,
    build_question_vector_knn_query,
    build_text_search_query,
    build_text_vector_knn_query,
    build_vector_search_query,
)
from src.rag.evaluate import GroundTruthEvaluator
from src.rag.qa_bot import QABot


# Define SearchMethod enum to match the one in qa_bot.py
class SearchMethod(Enum):
    TEXT = "text"
    VECTOR = "vector"
    QUESTION_KNN = "question_knn"
    TEXT_KNN = "text_knn"
    QUESTION_TEXT_KNN = "question_text_knn"
    COMBINED_KNN = "combined_knn"

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
        # Map our local SearchMethod to the QABot's SearchMethod
        from src.rag.qa_bot import SearchMethod as QABotSearchMethod

        # Create a mapping between our enum and QABot's enum
        method_mapping = {
            SearchMethod.TEXT: QABotSearchMethod.TEXT,
            SearchMethod.VECTOR: QABotSearchMethod.VECTOR,
            SearchMethod.QUESTION_KNN: QABotSearchMethod.QUESTION_KNN,
            SearchMethod.TEXT_KNN: QABotSearchMethod.TEXT_KNN,
            SearchMethod.QUESTION_TEXT_KNN: QABotSearchMethod.QUESTION_TEXT_KNN,
            SearchMethod.COMBINED_KNN: QABotSearchMethod.COMBINED_KNN
        }

        # Initialize QABot with the mapped search method
        qa_bot = QABot(search_method=method_mapping[search_method])

        # Create a custom OpenAI config with the user-selected temperature
        openai_config = OpenAIConfig()
        openai_config.temperature = temperature
        qa_bot.openai_config = openai_config

        # Verify that we have an OpenAI API key
        if not qa_bot.openai_config.open_api_key:
            st.warning("⚠️ No OpenAI API key found in environment. Some functionality may be limited.")
            logger.log_warning("No OpenAI API key configured")

        return qa_bot
    except Exception as e:
        logger.log_error("Failed to initialize QA system", ex=e)
        st.error(f"Failed to initialize the Q&A system: {e!s}")
        st.stop()

def qa_page():
    """Render the Q&A system page."""
    st.title("DataTalks.Club Q&A System")
    st.subheader("Ask questions about our courses")

    # Sidebar for settings
    with st.sidebar:
        st.header("Settings ⚙️")

        # Search method selection
        search_method_options = [
            ("Text Search (Baseline)", SearchMethod.TEXT, "Traditional keyword-based search"),
            ("Vector Search", SearchMethod.VECTOR, "Basic vector similarity search"),
            ("Question KNN Search", SearchMethod.QUESTION_KNN, "KNN search using question vector field"),
            ("Text KNN Search", SearchMethod.TEXT_KNN, "KNN search using text vector field"),
            ("Question-Text KNN Search", SearchMethod.QUESTION_TEXT_KNN, "KNN search using combined question-text vector field"),
            ("Combined KNN Search", SearchMethod.COMBINED_KNN, "Advanced KNN search using all vector fields with script scoring")
        ]

        search_method_str = st.radio(
            "Search Method",
            options=[opt[0] for opt in search_method_options],
            help="Choose the search method to use for finding relevant documents"
        )

        # Map the selected option string back to the enum
        search_method = next(opt[1] for opt in search_method_options if opt[0] == search_method_str)

        # Show description of selected method
        selected_description = next(opt[2] for opt in search_method_options if opt[0] == search_method_str)
        st.info(f"**{search_method_str}**: {selected_description}")

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
        ### About Search Methods ℹ️
        Different search methods use different techniques to find relevant documents.
        KNN (K-Nearest Neighbors) methods generally provide better results but may be slower.
        The best method depends on your specific use case.
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
            with st.spinner(f"Finding answer using {search_method_str}..."):
                response = qa_bot.answer_question(user_question, course=course_filter)
                response_placeholder.markdown(response)
        except Exception as e:
            logger.log_error("Error processing question", ex=e)
            response_placeholder.error(
                "An error occurred while processing your question. Please try again."
            )

def run_evaluation(selected_methods, ground_truth_path, progress_bar, status_text, results_container):
    """Run the evaluation process for selected search methods."""
    try:
        # Get the Elasticsearch client
        es_client = get_elasticsearch_client()

        # Initialize the evaluator
        evaluator = GroundTruthEvaluator()
        evaluator.load_ground_truth_data(ground_truth_path)

        # Dictionary to store all evaluation results
        all_results = {}
        overall_start_time = time.time()
        total_methods = len(selected_methods)
        completed_methods = 0

        def execute_search(query_builder_func):
            """Creates a function that builds and executes a search query."""
            def search_function(query_dict):
                # Build the query using the provided builder function
                es_query = query_builder_func(
                    query=query_dict["question"],
                    course=query_dict.get("course")
                )

                # Execute the query against Elasticsearch
                response = es_client.search(
                    index=ElasticsearchConfig.index_name,
                    body=es_query
                )

                # Extract and return the search results
                return [hit["_source"] for hit in response["hits"]["hits"]]

            return search_function

        # Define method configurations
        method_configs = {
            "text_search": {
                "name": "Text Search",
                "function": build_text_search_query,
                "description": "Traditional keyword-based search"
            },
            "vector_search": {
                "name": "Vector Search",
                "function": build_vector_search_query,
                "description": "Basic vector similarity search"
            },
            "question_knn": {
                "name": "Question KNN",
                "function": build_question_vector_knn_query,
                "description": "KNN search using question vector field"
            },
            "text_knn": {
                "name": "Text KNN",
                "function": build_text_vector_knn_query,
                "description": "KNN search using text vector field"
            },
            "question_text_knn": {
                "name": "Question-Text KNN",
                "function": build_question_text_vector_knn_query,
                "description": "KNN search using combined question-text vector field"
            },
            "combined_knn": {
                "name": "Combined KNN",
                "function": build_combined_vector_knn_query,
                "description": "KNN search using all vector fields with script scoring"
            }
        }

        # Execute evaluations for selected methods
        for method_key in selected_methods:
            if method_key not in method_configs:
                status_text.error(f"Unknown method: {method_key}")
                continue

            method_config = method_configs[method_key]
            status_text.info(f"Evaluating {method_config['name']}...")

            method_start_time = time.time()
            search_function = execute_search(method_config["function"])
            hit_rate, mrr = evaluator.evaluate_query(search_function)
            method_time_min = (time.time() - method_start_time) / 60

            all_results[method_key] = {
                "name": method_config["name"],
                "description": method_config["description"],
                "hit_rate": hit_rate,
                "mrr": mrr,
                "time_minutes": method_time_min
            }

            # Update progress
            completed_methods += 1
            progress_bar.progress(completed_methods / total_methods)
            status_text.info(f"Completed {method_config['name']} ({completed_methods}/{total_methods})")

        total_time_min = (time.time() - overall_start_time) / 60

        # Create results DataFrame
        results_df = pd.DataFrame([
            {
                "Method": result["name"],
                "Description": result["description"],
                "Hit Rate": round(result["hit_rate"], 3),
                "MRR": round(result["mrr"], 3),
                "Time (min)": round(result["time_minutes"], 2)
            }
            for method_key, result in all_results.items()
        ])

        # Sort by MRR (descending)
        results_df = results_df.sort_values("MRR", ascending=False).reset_index(drop=True)

        # Add results to container
        with results_container:
            st.subheader(f"Evaluation Results (Total time: {round(total_time_min, 2)} minutes)")
            st.dataframe(results_df, use_container_width=True)

            # Generate and save results file
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            results_dir = Path("data/evaluation_results")
            results_dir.mkdir(parents=True, exist_ok=True)

            # Save as CSV
            csv_path = results_dir / f"evaluation_results_{timestamp}.csv"
            results_df.to_csv(csv_path, index=False)

            # Save as JSON with more details
            json_data = {
                "timestamp": timestamp,
                "total_time_minutes": total_time_min,
                "methods_evaluated": len(selected_methods),
                "ground_truth_path": ground_truth_path,
                "results": all_results
            }
            json_path = results_dir / f"evaluation_results_{timestamp}.json"
            with open(json_path, "w") as f:
                json.dump(json_data, f, indent=2)

            st.success(f"Evaluation completed successfully! Results saved to {csv_path}")

            # Download buttons
            col1, col2 = st.columns(2)
            with col1:
                with open(csv_path) as f:
                    csv_content = f.read()
                st.download_button(
                    label="Download CSV",
                    data=csv_content,
                    file_name=f"evaluation_results_{timestamp}.csv",
                    mime="text/csv",
                    key=f"csv_download_{timestamp}"
                )
            with col2:
                with open(json_path) as f:
                    json_content = f.read()
                st.download_button(
                    label="Download JSON",
                    data=json_content,
                    file_name=f"evaluation_results_{timestamp}.json",
                    mime="application/json",
                    key=f"json_download_{timestamp}"
                )

        return results_df

    except Exception as e:
        status_text.error(f"Evaluation failed: {e!s}")
        logger.log_error("Evaluation failed", ex=e)
        raise

def load_past_evaluations():
    """Load and return past evaluation results."""
    results_dir = Path("data/evaluation_results")
    if not results_dir.exists():
        return []

    json_files = list(results_dir.glob("*.json"))
    json_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)

    evaluations = []
    for json_file in json_files:
        try:
            with open(json_file) as f:
                data = json.load(f)
                evaluations.append({
                    "file_path": json_file,
                    "timestamp": data.get("timestamp", json_file.stem),
                    "methods_evaluated": data.get("methods_evaluated", 0),
                    "total_time_minutes": data.get("total_time_minutes", 0)
                })
        except Exception as e:
            logger.log_error(f"Error loading evaluation file {json_file}", ex=e)

    return evaluations

def display_evaluation_result(file_path):
    """Display a specific evaluation result."""
    try:
        with open(file_path) as f:
            data = json.load(f)

        # Use timestamp from data or filename for unique keys
        timestamp = data.get("timestamp", file_path.stem)

        # Create results DataFrame
        results = []
        for method_key, result in data.get("results", {}).items():
            results.append({
                "Method": result.get("name", method_key),
                "Description": result.get("description", ""),
                "Hit Rate": round(result.get("hit_rate", 0), 3),
                "MRR": round(result.get("mrr", 0), 3),
                "Time (min)": round(result.get("time_minutes", 0), 2)
            })

        results_df = pd.DataFrame(results)
        results_df = results_df.sort_values("MRR", ascending=False).reset_index(drop=True)

        st.subheader(f"Evaluation Results from {data.get('timestamp', 'Unknown')}")
        st.dataframe(results_df, use_container_width=True)

        # Meta information
        st.markdown("### Evaluation Details")
        st.markdown(f"**Date:** {data.get('timestamp', 'Unknown')}")
        st.markdown(f"**Total Time:** {round(data.get('total_time_minutes', 0), 2)} minutes")
        st.markdown(f"**Methods Evaluated:** {data.get('methods_evaluated', 0)}")
        st.markdown(f"**Ground Truth Path:** {data.get('ground_truth_path', 'Unknown')}")

        # Download buttons
        col1, col2 = st.columns(2)
        with col1:
            csv_path = file_path.with_suffix(".csv")
            if csv_path.exists():
                with open(csv_path) as f:
                    csv_content = f.read()
                st.download_button(
                    label="Download CSV",
                    data=csv_content,
                    file_name=csv_path.name,
                    mime="text/csv",
                    key=f"past_csv_download_{timestamp}"
                )
        with col2:
            with open(file_path) as f:
                json_content = f.read()
            st.download_button(
                label="Download JSON",
                data=json_content,
                file_name=file_path.name,
                mime="application/json",
                key=f"past_json_download_{timestamp}"
            )

    except Exception as e:
        st.error(f"Error displaying evaluation result: {e!s}")
        logger.log_error("Error displaying evaluation result", ex=e)

def evaluation_page():
    """Render the evaluation page."""
    st.title("Search Methods Evaluation")
    st.subheader("Compare different search approaches")

    tab1, tab2 = st.tabs(["Run New Evaluation", "View Past Evaluations"])

    with tab1:
        st.markdown("""
        This tool evaluates different search methods against a ground truth dataset.
        Each method will be tested on its ability to retrieve relevant documents.
        """)

        # Evaluation settings
        with st.expander("Evaluation Settings", expanded=True):
            ground_truth_path = st.text_input(
                "Ground Truth Data Path",
                value="data/output/ground-truth-data.csv",
                help="Path to the CSV file containing ground truth data"
            )

            # Method selection checkboxes
            st.subheader("Select Methods to Evaluate")
            col1, col2 = st.columns(2)

            with col1:
                text_search = st.checkbox("Text Search (Baseline)", value=True)
                vector_search = st.checkbox("Vector Search", value=True)
                question_knn = st.checkbox("Question KNN", value=True)

            with col2:
                text_knn = st.checkbox("Text KNN", value=True)
                question_text_knn = st.checkbox("Question-Text KNN", value=True)
                combined_knn = st.checkbox("Combined KNN", value=True)

            # Collect selected methods
            selected_methods = []
            if text_search: selected_methods.append("text_search")
            if vector_search: selected_methods.append("vector_search")
            if question_knn: selected_methods.append("question_knn")
            if text_knn: selected_methods.append("text_knn")
            if question_text_knn: selected_methods.append("question_text_knn")
            if combined_knn: selected_methods.append("combined_knn")

            if not selected_methods:
                st.warning("Please select at least one search method to evaluate.")

        # Run evaluation button
        if st.button("Run Evaluation", disabled=not selected_methods):
            # Create placeholders for progress indicators
            progress_bar = st.progress(0)
            status_text = st.empty()
            results_container = st.container()

            # Run the evaluation
            try:
                status_text.info("Starting evaluation...")
                run_evaluation(
                    selected_methods,
                    ground_truth_path,
                    progress_bar,
                    status_text,
                    results_container
                )
            except Exception as e:
                st.error(f"Evaluation failed: {e!s}")
                logger.log_error("Evaluation failed", ex=e)

    with tab2:
        st.markdown("### Past Evaluation Results")

        # Load past evaluations
        evaluations = load_past_evaluations()

        if not evaluations:
            st.info("No past evaluations found. Run a new evaluation to see results here.")
        else:
            # Create a selection widget for evaluations
            options = [f"{e['timestamp']} ({e['methods_evaluated']} methods, {round(e['total_time_minutes'], 1)} min)" for e in evaluations]
            selected_option = st.selectbox("Select an evaluation to view", options)

            if selected_option:
                # Find the selected evaluation
                selected_index = options.index(selected_option)
                selected_evaluation = evaluations[selected_index]

                # Display the evaluation
                display_evaluation_result(selected_evaluation["file_path"])


def main():
    """Main entry point for the Streamlit web application."""
    st.sidebar.title("DataTalks.Club RAG System")

    page = st.sidebar.radio("Choose a page", ["Q&A System", "Search Evaluation"])

    if page == "Q&A System":
        qa_page()
    else:
        evaluation_page()


if __name__ == "__main__":
    main()
