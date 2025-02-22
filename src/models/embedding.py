from sentence_transformers import SentenceTransformer

model = SentenceTransformer("all-mpnet-base-v2")

def embed_text(text: str) -> list[float]:
    """Convert text into a dense vector representation using MPNET.

    This function uses the all-mpnet-base-v2 model to create semantic embeddings
    that capture the meaning of the input text in a 768-dimensional vector space.

    Args:
        text: Input text to be embedded.

    Returns:
        list[float]: A 768-dimensional vector representation of the input text.
    """
    return model.encode(text).tolist()

