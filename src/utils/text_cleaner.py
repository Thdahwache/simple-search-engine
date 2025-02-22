import re

def clean_text_for_json(text: str) -> str:
    """
    Clean text to make it safe for JSON serialization by handling:
    - Windows paths with backslashes
    - Command syntax with backslashes
    - Trailing backslashes
    - Line endings
    
    Args:
        text: The input text to clean
        
    Returns:
        Cleaned text safe for JSON serialization
    """
    # Replace Windows-style double backslashes with forward slashes
    text = re.sub(r'\\\\', '/', text)
    
    # Handle command syntax (like \d) by escaping the backslash
    text = re.sub(r'(?<!\\)\\([a-zA-Z])', r'\\\1', text)
    
    # Replace trailing backslashes with forward slash
    text = re.sub(r'\\$', '/', text.rstrip())
    
    # Normalize line endings to \n
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    
    return text

def clean_documents(documents: dict) -> dict:
    """
    Clean a dictionary of documents for JSON serialization
    
    Args:
        documents: Dictionary of document IDs to text content
        
    Returns:
        Dictionary with cleaned text content
    """
    return {
        doc_id: clean_text_for_json(text)
        for doc_id, text in documents.items()
    } 