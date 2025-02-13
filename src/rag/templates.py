CONTEXT_TEMPLATE = """
Section: {section}
Question: {question}
Answer: {text}
""".strip()

PROMPT_TEMPLATE = """
You're a course teaching assistant.
Answer the user QUESTION based on CONTEXT - the documents retrieved from our FAQ database.
Don't use other information outside of the provided CONTEXT.  

QUESTION: {user_question}

CONTEXT:

{context}
""".strip()
