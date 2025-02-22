from openai import OpenAI
from src.rag.templates import GROUND_TRUTH_PROMPT
from src.core.utils.logger import setup_logger
import json

logger = setup_logger(__name__)
client = OpenAI()


def generate_questions(doc):
    prompt = GROUND_TRUTH_PROMPT.format(**doc)

    response = client.chat.completions.create(
        model='gpt-4o-mini',
        messages=[{"role": "user", "content": prompt}]
    )

    json_response = response.choices[0].message.content
    
    try:
        # Try to parse and validate the response
        questions = json.loads(json_response)
        
        # Validate that we got a list of exactly 5 questions
        if not isinstance(questions, list):
            raise ValueError("Response is not a list")
        if len(questions) != 5:
            raise ValueError(f"Expected 5 questions, got {len(questions)}")
        if not all(isinstance(q, str) for q in questions):
            raise ValueError("All items must be strings")
            
        return json_response
        
    except Exception as e:
        logger.log_error(
            f"Failed to parse GPT response for document {doc['id']}",
            ex=e,
            extra={
                "document_id": doc["id"],
                "raw_response": json_response,
                "prompt": prompt
            }
        )
        raise

class GroundTruthEvaluator:
    def __init__(self, model: str = 'gpt-4o-mini'):
        self.model = model
        self.client = OpenAI()

    def load_ground_truth_data(self, ground_truth_data):
    def hit_rate(self, relevance_total):
        cnt = 0

        for line in relevance_total:
            if True in line:
                cnt = cnt + 1

        return cnt / len(relevance_total)
    
    def mrr(self, relevance_total):
        total_score = 0.0

        for line in relevance_total:
            for rank in range(len(line)):
                if line[rank] == True:
                    total_score = total_score + 1 / (rank + 1)

        return total_score / len(relevance_total)
    
    def evaluate_ground_truth(self, ground_truth_data):
        relevance_total = []
        for doc in ground_truth_data:
            questions = generate_questions(doc)
            relevance_total.append(questions)

        return self.hit_rate(relevance_total), self.mrr(relevance_total)