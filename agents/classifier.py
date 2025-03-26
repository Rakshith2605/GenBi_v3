from utils.openai_helpers import get_openai_response

def classify_query(query: str) -> str:
    """
    Classifies the user query into one of three types: plot, table, or answer
    """
    prompt = {
        "role": "system",
        "content": """You are a query classification assistant for pandas DataFrame analysis.

                    Your job is to classify the user's query into one of three categories:

                    - 'plot': If the user is asking for any kind of visualization, chart, or graph (even if the plot type is not explicitly stated).
                    - 'table': If the user is requesting data output, filtering, sorting, summarization, or any structured view of the DataFrame in tabular form.
                    - 'answer': If the user is asking a statistical, analytical, or descriptive question that requires a textual or numerical answer, but not a plot or full table.
                    

                    Guidelines:
                    - Classify general visualization requests (like "show a visualization" or "generate a plot") as **'plot'**.
                    - Classify requests like "top 10 rows", "show records", "filter data" as **'table'**.
                    - Classify questions like "What is the average?", "Which city has the highest sales?" as **'answer'**.
                    - Do not infer overly specific intent; stick to these categories based on the phrasing of the query.

                    Respond with **only one word**: 'plot', 'table', or 'answer'.

                    Example classifications:
                    - "Show me a bar chart of sales over time" -> plot
                    - "List the top 5 customers by revenue" -> table
                    - "What is the average revenue per customer?" -> answer
                    - "Generate a visualization" -> plot
                    - "Give me a summary table" -> table
                    - "Which product is the most popular?" -> answer
        """
    }
    
    query_message = {
        "role": "user",
        "content": query
    }
    
    response = get_openai_response([prompt, query_message])
    return response.lower().strip()
