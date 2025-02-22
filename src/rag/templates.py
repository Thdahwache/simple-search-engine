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

GROUND_TRUTH_PROMPT = """
You emulate a student who's taking our course.
Formulate 5 questions this student might ask based on a FAQ record. The record
should contain the answer to the questions, and the questions should be complete and not too short.
If possible, use as fewer words as possible from the record. 

The record:

section: {section}
question: {question}
answer: {text}

Provide the output in parsable JSON without using code block:
EXAMPLE:
["question1", "question2", ..., "question5"]
""".strip()
