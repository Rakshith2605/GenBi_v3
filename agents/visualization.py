import pandas as pd
import plotly.express as px
from utils.openai_helpers import get_openai_response

def create_visualization(df: pd.DataFrame, query: str):
    """
    Creates a Plotly visualization based on the processed dataframe and user query.
    The LLM generates Python code using Plotly Express with a creative and appropriate chart.
    """
    system_prompt = {
        "role": "system",
        "content": """You are a data visualization expert.
        Generate creative and informative Plotly Express charts based on user queries and the provided dataframe.

        Guidelines:
        1. Use only columns present in the dataframe.
        2. The output must be valid Python code using Plotly Express (px).
        3. The code must define and return a figure object named `fig`.
        4. Always include a descriptive chart title using `fig.update_layout(title=...)`.
        5. Use appropriate chart types (e.g., bar, line, scatter, box, pie, histogram, area, treemap) based on the query and data types.
        6. Use multiple colors to differentiate categories or series using `color=...` when possible.
        7. For line/bar plots, make them colorful and visually appealing.
        8. Handle date/time or categorical axes correctly.
        9. Do NOT include markdown, explanations, or comments — only return the code.
        """
            }

    user_prompt = {
        "role": "user",
        "content": f"""
        Query: {query}

        Available columns: {list(df.columns)}
        Data types:
        {df.dtypes.to_string(index=True)}

        Generate a creative and effective Plotly Express chart based on the query and dataframe.
        Return only the Python code that defines a `fig` object.
        """
            }



    viz_code = get_openai_response([system_prompt, user_prompt])

    # Clean up the response to ensure we get only the code
    viz_code = viz_code.strip('`\n ')
    if viz_code.startswith('python'):
        viz_code = viz_code[6:]

    # Execute the generated visualization code
    try:
        # Ensure we have the required columns
        if 'House Price' not in df.columns and 'house price' in query.lower():
            raise ValueError("Column 'House Price' not found in the dataframe")

        local_vars = {"df": df, "px": px}
        exec(viz_code, globals(), local_vars)
        fig = local_vars.get('fig')

        if fig is None:
            raise ValueError("Visualization code did not create a 'fig' variable")

        # Update layout for better appearance
        fig.update_layout(
            template="plotly_white",
            title_x=0.5,
            margin=dict(t=50, l=50, r=50, b=50)
        )
        return fig
    except Exception as e:
        raise Exception(f"Error creating visualization: {str(e)}\nCode attempted:\n{viz_code}")