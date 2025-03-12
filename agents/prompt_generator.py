
import pandas as pd
from utils.openai_helpers import get_openai_response

def generate_data_manipulation_prompt(query: str, df: pd.DataFrame) -> str:
    """
    Generates a prompt for data manipulation based on the user query and dataframe structure
    """
    columns_info = "\n".join([f"- {col}: {df[col].dtype}" for col in df.columns])

    system_prompt = {
        "role": "system",
        "content": """Generate Python code using pandas to prepare data for visualization.
        For charts:
        1. If aggregation is needed, use groupby() and agg() functions
        2. Make sure to reset_index() after groupby operations
        3. Handle any NaN values using dropna()
        4. Ensure numeric columns are properly typed

        Example for a plot showing average values:
        ```python
        df = df.dropna(subset=['category_column', 'value_column'])
        df['value_column'] = pd.to_numeric(df['value_column'], errors='coerce')
        df = df.groupby('category_column')['value_column'].mean().reset_index()
        ```

        Return only the valid Python code without any explanation or formatting. assuming df is already declared, give only manipulation and Visualisation code.
        '}
        """
    }

    user_prompt = {
        "role": "user",
        "content": f"""
        Query: {query}

        DataFrame Information:
        Columns and their types:
        {columns_info}

        Sample data (first 3 rows):
        {df.head().to_string()}

        Generate valid Python code to prepare this data for the requested visualization.
        For a bar graph of house prices, ensure to handle the 'House Price' column properly.
        """
    }


    response = get_openai_response([system_prompt, user_prompt])
    # Ensure we return only the code part if it's wrapped in backticks
    code = response.strip('`\n ')
    if code.startswith('python'):
        code = code[6:]
    return code
