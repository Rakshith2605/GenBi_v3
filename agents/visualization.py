import pandas as pd
import plotly.express as px
from utils.openai_helpers import get_openai_response
from pandasai import SmartDataframe
from pandasai.llm import OpenAI
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
import os
from pathlib import Path
from langchain_experimental.agents import create_pandas_dataframe_agent
import pandas as pd

api_key=os.getenv("OPENAI_API_KEY")
llm = ChatOpenAI(
    api_key=api_key,
    temperature=0,
    model_name="gpt-4"
)

def create_visualization(df: pd.DataFrame, query: str):
    """
    Creates a Plotly visualization based on the processed dataframe and user query
    """
    system_prompt = {
        "role": "system",
        "content": """Generate Python code using Plotly Express to create the visualization.
        Example: For bar charts, use this format:
        ```python
            fig = px.bar(
            data_frame=df,
            x='column_name',  # replace with actual column
            y='value_column', # replace with actual column
            title='Descriptive Title'
        )
        ```
        Guidelines for barchart:
        - First, aggregate the data using groupby and sum or mean.
        - Plot one solid bar per group.
        - Use `color` to differentiate each bar.
        - Do not plot individual rows.
        - Return only the Python code that defines and returns a `fig` object.

        The code must:
        1. Use only the columns available in the dataframe
        2. Return a figure object named 'fig'
        3. Include a descriptive title
        4. Handle numeric data appropriately
        5. For line/bar plots, make them colorful and visually appealing.
        6. Use multiple colors to differentiate categories or series using `color=...` when possible.
        7. Always try to generate solid bar for bar plots not strips of bars.




        Return only the Python code without any explanation."""
    }

    user_prompt = {
        "role": "user",
        "content": f"""
        Query: {query}

        Available columns: {list(df.columns)}
        Data types:
        {df.dtypes.to_string()}

        Generate Plotly Express code for visualization.
        If this is for house prices, use 'House Price' as the y-axis.
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
    
    

def generate_plotly_chart(df, memory, optimised_query):
    from plotly.subplots import make_subplots
    import plotly.express as px
    import plotly.graph_objects as go

    agent = create_pandas_dataframe_agent(
        llm, df, memory=memory, verbose=False, allow_dangerous_code=True,
        handle_parsing_errors=True
    )

    agent_prompt = (
        f"{optimised_query.strip()}\n"
        "Use only Plotly Express (px) or Plotly Graph Objects (go) to create the chart.\n"
        "Assume `df` is already available. Do not redefine it.\n"
        "Return only valid Python code that defines a figure named `fig` and displays it using `.show()`.\n"
        "Do not include comments, markdown, or explanation."
    )

    generated_code = agent.run(agent_prompt).strip()

    # Clean up accidental markdown/code fences
    if "```" in generated_code:
        generated_code = generated_code.replace("```python", "").replace("```", "").strip()

    print("🧪 Generated Code:\n", generated_code)

    exec_env = {'df': df, 'px': px, 'go': go}
    exec(generated_code, {}, exec_env)
    fig = exec_env.get("fig")

    # ⬇️ Add custom controls here (dropdowns, sliders, etc.)
    fig.update_layout(
        title="Enhanced Plot with Interactive Controls",
        xaxis=dict(
            rangeselector=dict(
                buttons=list([
                    dict(count=1, label="1m", step="month", stepmode="backward"),
                    dict(count=6, label="6m", step="month", stepmode="backward"),
                    dict(step="all")
                ])
            ),
            rangeslider=dict(visible=True),
            type="date" if 'date' in df.columns[0].lower() else "linear"
        ),
        updatemenus=[
            dict(
                type="dropdown",
                showactive=True,
                buttons=[
                    dict(label="Line", method="update", args=[{"type": "scatter", "mode": "lines"}]),
                    dict(label="Markers", method="update", args=[{"type": "scatter", "mode": "markers"}]),
                    dict(label="Bar", method="update", args=[{"type": "bar"}])
                ],
                direction="down",
                x=0.0,
                xanchor="left",
                y=1.1,
                yanchor="top"
            )
        ]
    )

    fig.show()
    return fig
