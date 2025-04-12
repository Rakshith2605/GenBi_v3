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
    
    

def generate_plotly_chart(df, memory, optimised_query):
    import plotly.express as px
    import plotly.graph_objects as go
    import pandas as pd
    import re
    
    agent = create_pandas_dataframe_agent(
        llm, df, memory=memory, verbose=False, allow_dangerous_code=True,
        handle_parsing_errors=True
    )
    
    agent_prompt = (
        f"{optimised_query.strip()}\n"
        "Use only Plotly Express (px) or Plotly Graph Objects (go) to create the chart.\n"
        "Assume `df` is already available. Do not redefine it.\n"
        "Return only valid Python code that defines a figure named `fig` and displays it using `.show()`.\n"
        "Also set a descriptive title for the plot using fig.update_layout(title=...).\n"
        "Do not include comments, markdown, or explanation."
    )
    
    generated_code = agent.run(agent_prompt).strip()
    
    if "```" in generated_code:
        generated_code = generated_code.replace("```python", "").replace("```", "").strip()
    
    print("🧪 Generated Code:\n", generated_code)
    
    # Execute safely
    exec_env = {'df': df, 'px': px, 'go': go, 'pd': pd}
    exec(generated_code, {}, exec_env)
    
    fig = exec_env.get("fig")
    
    if fig is None:
        raise ValueError("The generated code did not produce a figure named 'fig'")
    
    # Extract chart type and generate default title if none exists
    chart_title = "Data Visualization"
    
    # Check if title already exists in the figure layout
    current_layout = getattr(fig, 'layout', None)
    current_title = getattr(current_layout, 'title', None)
    
    if current_title and getattr(current_title, 'text', None):
        # Use existing title if it's already set
        chart_title = current_title.text
    else:
        # Try to generate a title based on the query
        query_terms = optimised_query.lower()
        
        # Determine chart type from generated code
        chart_type = "Chart"
        if "histogram" in generated_code.lower():
            chart_type = "Histogram"
        elif "scatter" in generated_code.lower():
            chart_type = "Scatter Plot"
        elif "bar" in generated_code.lower():
            chart_type = "Bar Chart"
        elif "pie" in generated_code.lower():
            chart_type = "Pie Chart"
        elif "line" in generated_code.lower():
            chart_type = "Line Chart"
        elif "box" in generated_code.lower():
            chart_type = "Box Plot"
        elif "heatmap" in generated_code.lower():
            chart_type = "Heat Map"
        
        # Extract key column names from code
        columns_match = re.findall(r'df\[[\'"]([^\'"]+)[\'"]\]', generated_code)
        columns = list(set(columns_match))  # Remove duplicates
        
        # Generate descriptive title
        if columns:
            if len(columns) == 1:
                chart_title = f"{chart_type} of {columns[0]}"
            elif len(columns) == 2:
                chart_title = f"{chart_type} of {columns[0]} vs {columns[1]}"
            else:
                chart_title = f"{chart_type} of {', '.join(columns[:2])} and Others"
        else:
            # Fallback: Use words from the query
            query_words = [w for w in query_terms.split() if len(w) > 3]
            if query_words:
                chart_title = f"{chart_type} for {' '.join(query_words[:3])}"
            else:
                chart_title = f"{chart_type} Visualization"
    
    # Detect chart type for appropriate styling
    is_scatter = any('scatter' in str(trace.type).lower() for trace in fig.data)
    is_bar = any('bar' in str(trace.type).lower() for trace in fig.data)
    is_pie = any('pie' in str(trace.type).lower() for trace in fig.data)
    is_line = any('line' in str(trace.type).lower() or 'scatter' in str(trace.type).lower() and hasattr(trace, 'mode') and 'lines' in trace.mode for trace in fig.data)
    
    # Apply appropriate styling based on chart type
    if is_scatter:
        for trace in fig.data:
            if 'scatter' in str(trace.type).lower():
                trace.marker.update(
                    size=10,
                    opacity=0.8,
                    line=dict(width=1, color='darkslategray')
                )
                # Only set color if not already using a color mapping
                if not trace.marker.get('color', None) or not isinstance(trace.marker.color, list):
                    trace.marker.color = 'rgba(99, 110, 250, 0.8)'
    
    if is_bar:
        for trace in fig.data:
            if 'bar' in str(trace.type).lower():
                # Only apply if not using a color mapping
                if not trace.marker.get('color', None) or not isinstance(trace.marker.color, list):
                    trace.marker.update(
                        color='rgba(99, 110, 250, 0.8)',
                        line=dict(width=1, color='darkslategray')
                    )
    
    if is_line:
        for trace in fig.data:
            if 'scatter' in str(trace.type).lower() and hasattr(trace, 'mode') and 'lines' in trace.mode:
                trace.line.update(width=2.5)
                # If it's a single trace and doesn't have color mapping
                if len(fig.data) == 1 and not trace.get('line', {}).get('color', None):
                    trace.line.color = 'rgba(99, 110, 250, 0.9)'
    
    # Don't style pie charts - they have their own coloring
    
    # Layout updates - apply to all chart types
    fig.update_layout(
        title=dict(
            text=chart_title,
            font=dict(size=20, family='Arial', color='darkblue'),
            x=0.5,
            xanchor='center'
        ),
        font=dict(family='Arial', size=14, color='black'),
        plot_bgcolor='white',
        paper_bgcolor='white',
        margin=dict(l=40, r=40, t=60, b=80),
        hovermode="closest"
    )
    
    # Apply axis styling but skip for pie charts
    if not is_pie:
        fig.update_xaxes(
            tickangle=-45,
            showgrid=True,
            gridwidth=1,
            gridcolor='lightgrey',
            zeroline=False
        )
        
        fig.update_yaxes(
            showgrid=True,
            gridwidth=1,
            gridcolor='lightgrey',
            zeroline=False,
            tickformat="," if fig.layout.yaxis.type != 'category' else ""
        )
        
        # Add axis scaling for numerical x-axis
        if len(df.columns) > 0:
            # Check if first column is numeric or has many unique values
            if pd.api.types.is_numeric_dtype(df[df.columns[0]]) or df[df.columns[0]].nunique() > 10:
                fig.update_xaxes(tickmode='auto', nticks=10)
    
    fig.show()
    return fig