from utils.openai_helpers import get_openai_response

def classify_query(query: str) -> str:
    """
    Classifies the user query into one of three types: plot, table, or answer
    """
    prompt = {
        "role": "system",
        "content": """Classify the following query into one of three categories:
        - 'plot': If the user is asking for any kind of visualization or graph
        - 'table': If the user is asking to see data in a tabular format
        - 'answer': If the user is asking a question that requires a text response
        
        Respond with just one word: 'plot', 'table', or 'answer'.
        
        Example classifications:
        - "Show me a bar chart of sales" -> plot
        - "Display the top 10 customers" -> table
        - "What is the average revenue?" -> answer
        """
    }
    
    query_message = {
        "role": "user",
        "content": query
    }
    
    response = get_openai_response([prompt, query_message])
    return response.lower().strip()
