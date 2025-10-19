

def human_question (query, context):
    prompt = f""" Question: {query}\n\nContext:\n{context}   """
    return prompt