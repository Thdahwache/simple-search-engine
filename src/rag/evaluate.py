import time
from collections.abc import Callable
from typing import Any

import pandas as pd
from openai import OpenAI
from tqdm import tqdm

from src.core.config import ElasticsearchConfig
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

logger = setup_logger(__name__)
client = OpenAI()

class GroundTruthEvaluator:
    """Evaluates search results against ground truth data using standard metrics."""

    def __init__(self):
        """Initialize the evaluator."""
        self.ground_truth_data = None

    def load_ground_truth_data(self, ground_truth_csv_path: str) -> None:
        """Load ground truth data from a CSV file.
        
        Args:
            ground_truth_csv_path: Path to the CSV containing ground truth data
            
        Raises:
            FileNotFoundError: If the CSV file doesn't exist
            ValueError: If required columns are missing

        """
        try:
            start_time = time.time()
            self.ground_truth_data = pd.read_csv(ground_truth_csv_path)
            required_columns = ["document", "question", "course"]
            missing_columns = [col for col in required_columns if col not in self.ground_truth_data.columns]

            if missing_columns:
                logger.log_error(
                    "Missing required columns in ground truth data",
                    ex=ValueError(f"Missing columns: {missing_columns}"),
                    file_path=ground_truth_csv_path,
                    missing_columns=missing_columns
                )
                raise ValueError(f"Missing required columns: {missing_columns}")

            load_time = (time.time() - start_time) * 1000
            logger.log_info(
                "Ground truth data loaded successfully",
                file_path=ground_truth_csv_path,
                row_count=len(self.ground_truth_data),
                load_time_ms=round(load_time, 2)
            )
        except FileNotFoundError:
            logger.log_error(
                "Ground truth file not found",
                ex=FileNotFoundError(f"File not found: {ground_truth_csv_path}"),
                file_path=ground_truth_csv_path
            )
            raise
        except Exception as e:
            logger.log_error(
                "Error loading ground truth data",
                ex=e,
                file_path=ground_truth_csv_path
            )
            raise

    def hit_rate(self, relevance_total: list[list[bool]]) -> float:
        """Calculate hit rate (presence of correct document in results).
        
        Args:
            relevance_total: List of boolean lists indicating correct document presence
        
        Returns:
            Float between 0 and 1 representing hit rate

        """
        if not relevance_total:
            logger.log_warning("Empty relevance list provided for hit rate calculation")
            return 0.0
        return sum(any(line) for line in relevance_total) / len(relevance_total)

    def mrr(self, relevance_total: list[list[bool]]) -> float:
        """Calculate Mean Reciprocal Rank (position of correct document).
        
        Args:
            relevance_total: List of boolean lists indicating correct document presence
        
        Returns:
            Float representing MRR score

        """
        if not relevance_total:
            logger.log_warning("Empty relevance list provided for MRR calculation")
            return 0.0
        total_score = 0.0
        for line in relevance_total:
            for rank, is_relevant in enumerate(line):
                if is_relevant:
                    total_score += 1 / (rank + 1)
                    break
        return total_score / len(relevance_total)

    def evaluate_query(self,
                      search_function: Callable[[dict[str, Any]], list[dict[str, Any]]]) -> tuple[float, float]:
        """Evaluate search results against ground truth.
        
        Args:
            search_function: Function that returns search results
        
        Returns:
            Tuple of (hit_rate, mrr) scores
            
        Raises:
            ValueError: If ground truth data hasn't been loaded

        """
        if self.ground_truth_data is None:
            logger.log_error(
                "Ground truth data not loaded",
                ex=ValueError("Ground truth data must be loaded before evaluation")
            )
            raise ValueError("Ground truth data must be loaded before evaluation")

        start_time = time.time()
        relevance_total = []
        successful_queries = 0
        failed_queries = 0

        for idx, row in tqdm(self.ground_truth_data.iterrows(), total=len(self.ground_truth_data)):
            query_start = time.time()
            try:
                query_dict = row.to_dict()
                results = search_function(query_dict)

                if not results:
                    logger.log_debug(
                        "No results returned for query",
                        query=query_dict,
                        index=idx
                    )
                    relevance = [False]
                else:
                    relevance = [d.get("id") == row["document"] for d in results]

                relevance_total.append(relevance)
                successful_queries += 1

                query_time = (time.time() - query_start) * 1000
                logger.log_debug(
                    "Query evaluation completed",
                    query=query_dict["question"],
                    results_count=len(results),
                    found_match=any(relevance),
                    execution_time_ms=round(query_time, 2)
                )

            except Exception as e:
                failed_queries += 1
                logger.log_error(
                    "Error processing query",
                    ex=e,
                    query=row.to_dict(),
                    index=idx
                )
                relevance_total.append([False])

        total_time = (time.time() - start_time) * 1000
        hit_rate = self.hit_rate(relevance_total)
        mrr_score = self.mrr(relevance_total)

        logger.log_info(
            "Evaluation completed",
            total_queries=len(self.ground_truth_data),
            successful_queries=successful_queries,
            failed_queries=failed_queries,
            hit_rate=round(hit_rate, 3),
            mrr=round(mrr_score, 3),
            total_time_ms=round(total_time, 2)
        )

        return hit_rate, mrr_score

def main():
    """Main function to run the evaluation process."""
    try:
        logger.log_info("Starting evaluation process")
        evaluator = GroundTruthEvaluator()

        # Load the ground truth data
        evaluator.load_ground_truth_data("data/output/ground-truth-data.csv")

        # Get the Elasticsearch client
        es_client = get_elasticsearch_client()

        def execute_search(query_builder_func):
            """Creates a function that builds and executes a search query.
            
            Args:
                query_builder_func: Function that builds an Elasticsearch query
                
            Returns:
                Function that takes a query dict and returns search results

            """
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

        # Dictionary to store results of all search methods
        all_results = {}
        overall_start_time = time.time()

        # 1. Evaluate text search (baseline)
        logger.log_info("Evaluating traditional text search...")
        method_start_time = time.time()
        text_search_function = execute_search(build_text_search_query)
        text_hit_rate, text_mrr = evaluator.evaluate_query(text_search_function)
        method_time_min = (time.time() - method_start_time) / 60
        all_results["text_search"] = {
            "hit_rate": text_hit_rate,
            "mrr": text_mrr,
            "time_minutes": method_time_min
        }

        logger.log_info(
            "Text search evaluation results",
            hit_rate=round(text_hit_rate, 3),
            mrr=round(text_mrr, 3),
            time_minutes=round(method_time_min, 2)
        )

        # 2. Evaluate vector search
        logger.log_info("Evaluating vector search...")
        method_start_time = time.time()
        vector_search_function = execute_search(build_vector_search_query)
        vector_hit_rate, vector_mrr = evaluator.evaluate_query(vector_search_function)
        method_time_min = (time.time() - method_start_time) / 60
        all_results["vector_search"] = {
            "hit_rate": vector_hit_rate,
            "mrr": vector_mrr,
            "time_minutes": method_time_min
        }

        logger.log_info(
            "Vector search evaluation results",
            hit_rate=round(vector_hit_rate, 3),
            mrr=round(vector_mrr, 3),
            time_minutes=round(method_time_min, 2)
        )

        # 3. Evaluate question vector KNN search
        logger.log_info("Evaluating question vector KNN search...")
        method_start_time = time.time()
        question_knn_function = execute_search(build_question_vector_knn_query)
        q_knn_hit_rate, q_knn_mrr = evaluator.evaluate_query(question_knn_function)
        method_time_min = (time.time() - method_start_time) / 60
        all_results["question_knn"] = {
            "hit_rate": q_knn_hit_rate,
            "mrr": q_knn_mrr,
            "time_minutes": method_time_min
        }

        logger.log_info(
            "Question vector KNN search results",
            hit_rate=round(q_knn_hit_rate, 3),
            mrr=round(q_knn_mrr, 3),
            time_minutes=round(method_time_min, 2)
        )

        # 4. Evaluate text vector KNN search
        logger.log_info("Evaluating text vector KNN search...")
        method_start_time = time.time()
        text_knn_function = execute_search(build_text_vector_knn_query)
        t_knn_hit_rate, t_knn_mrr = evaluator.evaluate_query(text_knn_function)
        method_time_min = (time.time() - method_start_time) / 60
        all_results["text_knn"] = {
            "hit_rate": t_knn_hit_rate,
            "mrr": t_knn_mrr,
            "time_minutes": method_time_min
        }

        logger.log_info(
            "Text vector KNN search results",
            hit_rate=round(t_knn_hit_rate, 3),
            mrr=round(t_knn_mrr, 3),
            time_minutes=round(method_time_min, 2)
        )

        # 5. Evaluate question-text vector KNN search
        logger.log_info("Evaluating question-text vector KNN search...")
        method_start_time = time.time()
        qt_knn_function = execute_search(build_question_text_vector_knn_query)
        qt_knn_hit_rate, qt_knn_mrr = evaluator.evaluate_query(qt_knn_function)
        method_time_min = (time.time() - method_start_time) / 60
        all_results["question_text_knn"] = {
            "hit_rate": qt_knn_hit_rate,
            "mrr": qt_knn_mrr,
            "time_minutes": method_time_min
        }

        logger.log_info(
            "Question-text vector KNN search results",
            hit_rate=round(qt_knn_hit_rate, 3),
            mrr=round(qt_knn_mrr, 3),
            time_minutes=round(method_time_min, 2)
        )

        # 6. Evaluate combined vector KNN search
        logger.log_info("Evaluating combined vector KNN search...")
        method_start_time = time.time()
        combined_knn_function = execute_search(build_combined_vector_knn_query)
        combined_hit_rate, combined_mrr = evaluator.evaluate_query(combined_knn_function)
        method_time_min = (time.time() - method_start_time) / 60
        all_results["combined_knn"] = {
            "hit_rate": combined_hit_rate,
            "mrr": combined_mrr,
            "time_minutes": method_time_min
        }

        logger.log_info(
            "Combined vector KNN search results",
            hit_rate=round(combined_hit_rate, 3),
            mrr=round(combined_mrr, 3),
            time_minutes=round(method_time_min, 2)
        )

        total_time_min = (time.time() - overall_start_time) / 60

        # Create a formatted results table
        logger.log_info(f"=== SEARCH METHOD COMPARISON (Total time: {round(total_time_min, 2)} minutes) ===")

        # Table header
        header = f"{'Method':<20} | {'Hit Rate':^10} | {'MRR':^10} | {'Time (min)':^12}"
        separator = f"{'-'*20} | {'-'*10} | {'-'*10} | {'-'*12}"
        logger.log_info(header)
        logger.log_info(separator)

        # Sort results by MRR (best performing first)
        sorted_results = sorted(all_results.items(), key=lambda x: x[1]["mrr"], reverse=True)

        # Table rows
        for method, metrics in sorted_results:
            method_name = method.replace("_", " ").title()
            row = f"{method_name:<20} | {metrics['hit_rate']:^10.3f} | {metrics['mrr']:^10.3f} | {metrics['time_minutes']:^12.2f}"
            logger.log_info(row)

        # Find the best method based on MRR
        best_method = sorted_results[0]
        logger.log_info(separator)
        logger.log_info(
            f"Best performing method: {best_method[0].replace('_', ' ').title()}"
        )

    except Exception as e:
        logger.log_error("Evaluation failed", ex=e)
        raise

if __name__ == "__main__":
    main()
