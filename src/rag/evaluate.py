from openai import OpenAI
from typing import List, Dict, Callable, Any
import pandas as pd
from tqdm import tqdm
import time
from src.elastic.queries import build_text_search_query, build_vector_search_query
from src.core.utils.logger import setup_logger

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
            required_columns = ['document', 'question', 'course']
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

    def hit_rate(self, relevance_total: List[List[bool]]) -> float:
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
    
    def mrr(self, relevance_total: List[List[bool]]) -> float:
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
                      search_function: Callable[[Dict[str, Any]], List[Dict[str, Any]]]) -> tuple[float, float]:
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
                    relevance = [d.get('id') == row['document'] for d in results]
                    
                relevance_total.append(relevance)
                successful_queries += 1
                
                query_time = (time.time() - query_start) * 1000
                logger.log_debug(
                    "Query evaluation completed",
                    query=query_dict['question'],
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
        
        start_time = time.time()
        evaluator.load_ground_truth_data('data/output/ground-truth-data.csv')
        
        hit_rate, mrr = evaluator.evaluate_query(
            lambda q: build_text_search_query(query=q['question'], course=q['course'])
        )
        
        total_time = (time.time() - start_time) * 1000
        logger.log_info(
            "Evaluation completed successfully",
            hit_rate=round(hit_rate, 3),
            mrr=round(mrr, 3),
            total_time_ms=round(total_time, 2)
        )
        
    except Exception as e:
        logger.log_error("Evaluation failed", ex=e)
        raise

if __name__ == '__main__':
    main()
