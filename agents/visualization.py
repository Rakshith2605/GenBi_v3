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

        # Data Visualization Design Guidelines

        ## Universal Design Principles
        ### Color Usage
        * Use a consistent, professional color palette aligned with your brand (5-7 colors maximum)
        * Ensure sufficient contrast for accessibility (WCAG AA compliance)
        * Use color strategically to highlight important insights
        * Avoid rainbow color scales which can distort perception

        ### Typography
        * Use a clean, readable sans-serif font family
        * Maintain consistent font styles across all charts
        * Ensure adequate text size (minimum 12pt for labels)
        * Limit text rotation for better readability

        ### Layout
        * Maintain proper spacing between elements
        * Use a consistent aspect ratio (typically 16:9 or 4:3)
        * Align elements to an invisible grid
        * Include clear, concise titles and subtitles

        ## Chart-Specific Guidelines

        ### Line Charts
        * Use for time series and continuous data
        * Limit to 4-5 lines maximum per chart
        * Apply appropriate line thickness (1-2px)
        * Consider using area fills for emphasis with transparency

        ### Bar Charts
        * Prioritize value representation over decorative elements
        * Order bars logically (ascending/descending for nominal data)
        * Use consistent spacing between bars (50-80% of bar width)
        * Ensure bar widths are substantial enough for easy comparison

        ### Pie Charts
        * Limit to 5-7 segments maximum
        * Start at 12 o'clock position and proceed clockwise
        * Use clear segment labels (direct or with leader lines)
        * Consider using a donut chart for better label placement

        ### Heat Maps
        * Use sequential color scales for quantitative data
        * Include a clear color legend
        * Apply consistent cell sizing
        * Consider using borders for better cell distinction

        ## Axis Design

        ### X-Axis Guidelines
        * Use clear, succinct labels
        * Rotate labels only when necessary (max 45°)
        * Apply consistent tick spacing
        * Start at zero for bar charts

        ### Y-Axis Guidelines
        * Include units of measurement
        * Use appropriate scale breaks when necessary
        * Consider dual axes only when absolutely necessary
        * Apply proper grid lines (subtle, not overpowering)

        ## Data Integrity Considerations
        * Never truncate axes in a misleading way
        * Maintain proportional visual representation to data values
        * Include data sources and timestamps
        * Always consider statistical significance when showing differences
        * Use appropriate number formatting (e.g., thousands separators)


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
    
    

def generate_plotly_chart(df,memory, optimised_query):
     agent = create_pandas_dataframe_agent(
         llm, df,memory=memory, verbose=False, allow_dangerous_code=True,
         handle_parsing_errors=True
     )
 
     agent_prompt = (
    f"{optimised_query.strip()}\n"
    "Use only Plotly Express (px) or Plotly Graph Objects (go) to create the chart.\n"
    "Assume `df` is already available. Do not redefine it.\n"
    "Return only valid Python code that defines a figure named `fig` and displays it using `.show()`.\n"
    "Do not include comments, markdown, or explanation.\n\n"
    "Follow these aesthetic visualization guidelines:\n\n"
    "1. Use a professional color palette with 4-7 complementary colors\n"
    "2. Include clear titles, subtitles, and legends\n"
    "3. Ensure text is legible with sufficient contrast\n"
    "4. Apply subtle grid lines that guide but don't distract\n"
    "5. Sort bars by value for bar charts\n"
    "6. Use thicker lines (2-3px) for line charts\n"
    "7. Limit pie charts to 5-7 slices maximum\n"
    "8. Use intuitive color gradients for heat maps\n"
    "9. Start y-axis at zero for bar charts unless inappropriate\n"
    "10. Format large numbers appropriately (K, M, B)\n"
    "11. Highlight outliers and important data points\n"
    "12. Ensure sufficient color contrast (WCAG AA standard)\n"
    "13. Use value labels directly on bars when space permits\n"
  
    "Follow these guidelines to create a professional and aesthetically pleasing visualization that effectively communicates the data. Apply the most relevant guidelines based on the chart type requested."
)
 
     generated_code = agent.run(agent_prompt).strip()
     print("🎨 Generated Plotly Code:\n", generated_code)
 
     # ✅ Clean accidental markdown/code fences
     if "```" in generated_code:
         generated_code = generated_code.replace("```python", "").replace("```", "").strip()
 
     print("🧪 Cleaned Code to Execute:\n", generated_code)
 
     # ✅ Execute safely
     import plotly.express as px
     import plotly.graph_objects as go
 
     exec_env = {'df': df, 'px': px, 'go': go}
     exec(generated_code, {}, exec_env)
 
     # ✅ Return the figure object
     fig = exec_env.get("fig")
     return fig