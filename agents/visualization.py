import pandas as pd
import plotly.express as px
from utils.openai_helpers import get_openai_response
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
import os
from pathlib import Path
from langchain_experimental.agents import create_pandas_dataframe_agent

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
    
    

def generate_plotly_chart(df, memory, optimised_query):
    """
    Generate a Plotly chart using LangChain agent with improved error handling
    """
    try:
        agent = create_pandas_dataframe_agent(
            llm, df, memory=memory, verbose=False, allow_dangerous_code=True,
            handle_parsing_errors=True
        )
        
        agent_prompt = (
            f"{optimised_query.strip()}\n"
            "Use only Plotly Express (px) to create the chart.\n"
            "Assume `df` is already available. Do not redefine it.\n"
            "Return ONLY valid Python code that creates a figure named `fig`.\n"
            "IMPORTANT: Do NOT use .show() method - just create the figure object.\n"
            "Do not include comments, markdown, or explanation.\n"
            "Do not use print() statements.\n\n"
            "Example format:\n"
            "fig = px.histogram(df, x='column_name')\n\n"
            "Follow these guidelines:\n"
            "1. Use professional color palettes\n"
            "2. Include clear titles\n"
            "3. Ensure text is legible\n"
            "4. Apply subtle grid lines\n"
            "5. Sort bars by value for bar charts\n"
            "6. Use thicker lines for line charts\n"
            "7. Limit pie charts to 5-7 slices\n"
            "8. Start y-axis at zero for bar charts\n"
            "9. Use value labels on bars when possible\n"
            "10. Prefer grouped bars over stacked bars"
        )
        
        generated_code = agent.run(agent_prompt).strip()
        print("🎨 Generated Plotly Code:\n", generated_code)
        
        # ✅ Clean accidental markdown/code fences
        if "```" in generated_code:
            generated_code = generated_code.replace("```python", "").replace("```", "").strip()
        
        # ✅ Remove any .show() calls that might still be generated
        generated_code = generated_code.replace(".show()", "")
        generated_code = generated_code.replace("fig.show()", "")
        generated_code = generated_code.replace("plt.show()", "")
        
        # ✅ Remove any print statements that might interfere
        generated_code = generated_code.replace("print(", "# print(")
        
        # ✅ Remove any display() calls
        generated_code = generated_code.replace("display(", "# display(")
        
        print("🧪 Cleaned Code to Execute:\n", generated_code)
        
        # ✅ Execute safely
        import plotly.express as px
        import plotly.graph_objects as go
        
        exec_env = {'df': df, 'px': px, 'go': go}
        
        try:
            exec(generated_code, {}, exec_env)
        except Exception as e:
            print(f"❌ Error executing generated code: {e}")
            print(f"Generated code was: {generated_code}")
            # Try a fallback approach
            return create_fallback_chart(df, optimised_query)
        
        # ✅ Return the figure object
        fig = exec_env.get("fig")
        if fig is None:
            print("⚠️ Generated code did not create a 'fig' variable, using fallback")
            return create_fallback_chart(df, optimised_query)
        
        return fig
        
    except Exception as e:
        print(f"❌ Error in generate_plotly_chart: {e}")
        return create_fallback_chart(df, optimised_query)


def create_fallback_chart(df, query):
    """
    Create a fallback chart when the agent fails
    """
    try:
        # Try to create a simple histogram for the first categorical column
        categorical_cols = df.select_dtypes(include=['object', 'category']).columns
        if len(categorical_cols) > 0:
            col = categorical_cols[0]
            fig = px.histogram(df, x=col, title=f"Distribution of {col}")
        else:
            # If no categorical columns, use the first numeric column
            numeric_cols = df.select_dtypes(include=['number']).columns
            if len(numeric_cols) > 0:
                col = numeric_cols[0]
                fig = px.histogram(df, x=col, title=f"Distribution of {col}")
            else:
                # Last resort - create a simple bar chart of the first column
                col = df.columns[0]
                fig = px.bar(df[col].value_counts().head(10), title=f"Top 10 values in {col}")
        
        fig.update_layout(
            template="plotly_white",
            title_x=0.5,
            margin=dict(t=50, l=50, r=50, b=50)
        )
        return fig
        
    except Exception as e:
        print(f"❌ Error in fallback chart: {e}")
        # Create a minimal chart
        import plotly.graph_objects as go
        fig = go.Figure()
        fig.add_trace(go.Bar(x=['Data'], y=[len(df)], name='Row Count'))
        fig.update_layout(title="Dataset Overview", template="plotly_white")
        return fig