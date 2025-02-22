from typing import Any
import json
import pandas as pd
from pathlib import Path
import time

from tqdm.auto import tqdm
from elasticsearch import Elasticsearch

from src.core.config import ElasticsearchConfig
from src.elastic.client import get_elasticsearch_client
from src.core.utils.logger import setup_logger
from src.rag.evaluate import generate_questions
from src.elastic.queries import build_all_documents_query

logger = setup_logger(__name__)

def process_document(doc: dict[str, Any], max_retries: int = 3) -> list[tuple[str, str, str]]:
    """
    Process a single document with retry logic.
    Returns a list of tuples (question, course, document_id).
    """
    retries = 0
    while retries < max_retries:
        try:
            questions = generate_questions(doc)
            questions_list = json.loads(questions)
            
            return [
                (generated_question, doc["course"], doc["id"])
                for generated_question in questions_list
            ]
            
        except Exception as e:
            retries += 1
            if retries == max_retries:
                logger.log_error(
                    f"Failed to process document after {max_retries} attempts",
                    ex=e,
                    extra={"document_id": doc["id"]}
                )
                return []  # Return empty list on failure
            
            # Wait before retrying (exponential backoff)
            time.sleep(2 ** retries)
    
    return []  # Should never reach here, but just in case

def process_all_documents() -> list[tuple[str, str, str]]:
    """
    Recupera todos os documentos do Elasticsearch e gera perguntas para cada um.
    Retorna uma lista de tuplas (pergunta, curso, documento_id).
    """
    es = get_elasticsearch_client()
    es_config = ElasticsearchConfig()
    
    # Busca todos os documentos usando a query específica
    query = build_all_documents_query()
    
    try:
        # Busca os documentos
        response = es.search(
            index=es_config.index_name,
            body=query
        )
        
        results = []
        failed_docs = []
        
        # Processa cada documento
        for hit in tqdm(response['hits']['hits'], desc="Gerando perguntas"):
            doc = hit['_source']
            doc_results = process_document(doc)
            
            if doc_results:
                results.extend(doc_results)
            else:
                failed_docs.append(doc["id"])
                
        # Log summary
        total_docs = len(response['hits']['hits'])
        failed_count = len(failed_docs)
        success_rate = ((total_docs - failed_count) / total_docs) * 100
        
        logger.log_info(
            "Processing summary",
            extra={
                "total_documents": total_docs,
                "failed_documents": failed_count,
                "success_rate": f"{success_rate:.2f}%",
                "failed_doc_ids": failed_docs
            }
        )
                
        return results
            
    except Exception as e:
        logger.log_error("Falha ao buscar documentos do Elasticsearch", ex=e)
        raise

if __name__ == "__main__":
    # Cria o diretório de saída se não existir
    output_dir = Path("data/output")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Processa os documentos
    results = process_all_documents()
    
    # Cria o DataFrame com as colunas corretas
    df = pd.DataFrame(results, columns=['question', 'course', 'document'])
    
    # Salva os resultados em CSV
    output_file = output_dir / "ground-truth-data.csv"
    df.to_csv(output_file, index=False)
    
    logger.log_info(f"Ground truth data salvo em {output_file}")
    logger.log_info(f"Total de perguntas geradas: {len(df)}") 