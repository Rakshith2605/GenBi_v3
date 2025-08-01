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
    print(f"🔍 DEBUG: Starting plot generation for query: {optimised_query}")
    print(f"🔍 DEBUG: DataFrame shape: {df.shape}")
    print(f"🔍 DEBUG: DataFrame columns: {list(df.columns)}")
    
    try:
        # Check if tabulate is available, if not, use fallback
        try:
            import tabulate
            print("✅ DEBUG: Tabulate dependency available")
        except ImportError:
            print("⚠️ DEBUG: Tabulate not available, using fallback chart generation")
            return create_fallback_chart(df, optimised_query)
        
        print("🔍 DEBUG: Creating LangChain agent...")
        agent = create_pandas_dataframe_agent(
            llm, df, memory=memory, verbose=False, allow_dangerous_code=True,
            handle_parsing_errors=True
        )
        print("✅ DEBUG: LangChain agent created successfully")
        
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
        
        print("🔍 DEBUG: Running agent with prompt...")
        generated_code = agent.run(agent_prompt).strip()
        print("🎨 DEBUG: Generated Plotly Code:\n", generated_code)
        print(f"🔍 DEBUG: Generated code length: {len(generated_code)} characters")
        
        # ✅ Clean accidental markdown/code fences
        print("🔍 DEBUG: Cleaning generated code...")
        if "```" in generated_code:
            generated_code = generated_code.replace("```python", "").replace("```", "").strip()
            print("🔍 DEBUG: Removed markdown code fences")
        
        # ✅ Remove any .show() calls that might still be generated
        original_code = generated_code
        generated_code = generated_code.replace(".show()", "")
        generated_code = generated_code.replace("fig.show()", "")
        generated_code = generated_code.replace("plt.show()", "")
        if original_code != generated_code:
            print("🔍 DEBUG: Removed .show() calls")
        
        # ✅ Remove any print statements that might interfere
        generated_code = generated_code.replace("print(", "# print(")
        
        # ✅ Remove any display() calls
        generated_code = generated_code.replace("display(", "# display(")
        
        print("🧪 DEBUG: Cleaned Code to Execute:\n", generated_code)
        print(f"🔍 DEBUG: Cleaned code length: {len(generated_code)} characters")
        
        # ✅ Execute safely
        print("🔍 DEBUG: Setting up execution environment...")
        import plotly.express as px
        import plotly.graph_objects as go
        
        exec_env = {'df': df, 'px': px, 'go': go}
        print("✅ DEBUG: Execution environment created")
        
        try:
            print("🔍 DEBUG: Executing generated code...")
            exec(generated_code, {}, exec_env)
            print("✅ DEBUG: Code executed successfully")
        except Exception as e:
            print(f"❌ DEBUG: Error executing generated code: {e}")
            print(f"🔍 DEBUG: Generated code was: {generated_code}")
            print("🔍 DEBUG: Using fallback chart...")
            # Try a fallback approach
            return create_fallback_chart(df, optimised_query)
        
        # ✅ Return the figure object
        print("🔍 DEBUG: Checking for 'fig' variable...")
        fig = exec_env.get("fig")
        if fig is None:
            print("⚠️ DEBUG: Generated code did not create a 'fig' variable, using fallback")
            return create_fallback_chart(df, optimised_query)
        
        print("✅ DEBUG: Figure object created successfully")
        return fig
        
    except Exception as e:
        print(f"❌ DEBUG: Error in generate_plotly_chart: {e}")
        print(f"🔍 DEBUG: Full error details: {str(e)}")
        import traceback
        print(f"🔍 DEBUG: Traceback: {traceback.format_exc()}")
        return create_fallback_chart(df, optimised_query)


def create_fallback_chart(df, query):
    """
    Create a dynamic fallback chart based on the query content
    """
    print(f"🔍 DEBUG: Creating fallback chart for query: {query}")
    print(f"🔍 DEBUG: DataFrame shape: {df.shape}")
    print(f"🔍 DEBUG: DataFrame columns: {list(df.columns)}")
    
    try:
        query_lower = query.lower()
        print(f"🔍 DEBUG: Query (lowercase): {query_lower}")
        
        # Extract column names from the query
        import re
        column_matches = re.findall(r"'([^']+)'", query)
        if not column_matches:
            column_matches = re.findall(r'"([^"]+)"', query)
        print(f"🔍 DEBUG: Column matches from query: {column_matches}")
        
        # Determine chart type from query
        chart_type = "histogram"  # default
        if "bar" in query_lower or "barplot" in query_lower:
            chart_type = "bar"
        elif "line" in query_lower:
            chart_type = "line"
        elif "scatter" in query_lower:
            chart_type = "scatter"
        elif "pie" in query_lower:
            chart_type = "pie"
        elif "box" in query_lower:
            chart_type = "box"
        
        print(f"🔍 DEBUG: Detected chart type: {chart_type}")
        
        # Find the best column to use
        target_column = None
        
        # First, try to use columns mentioned in the query
        if column_matches:
            for col in column_matches:
                if col in df.columns:
                    target_column = col
                    print(f"🔍 DEBUG: Found target column from query: {target_column}")
                    break
        
        # If no column found in query, try to find it by partial match
        if not target_column:
            for col in df.columns:
                if any(word in col.lower() for word in query_lower.split()):
                    target_column = col
                    print(f"🔍 DEBUG: Found target column by partial match: {target_column}")
                    break
        
        # If still no column found, use the first appropriate column
        if not target_column:
            if chart_type in ["histogram", "bar", "pie"]:
                categorical_cols = df.select_dtypes(include=['object', 'category']).columns
                if len(categorical_cols) > 0:
                    target_column = categorical_cols[0]
                    print(f"🔍 DEBUG: Using first categorical column: {target_column}")
                else:
                    target_column = df.columns[0]
                    print(f"🔍 DEBUG: Using first column: {target_column}")
            else:
                numeric_cols = df.select_dtypes(include=['number']).columns
                if len(numeric_cols) > 0:
                    target_column = numeric_cols[0]
                    print(f"🔍 DEBUG: Using first numeric column: {target_column}")
                else:
                    target_column = df.columns[0]
                    print(f"🔍 DEBUG: Using first column: {target_column}")
        
        print(f"🔍 DEBUG: Final target column: {target_column}")
        print(f"🔍 DEBUG: Target column dtype: {df[target_column].dtype}")
        
        # Create the appropriate chart
        print(f"🔍 DEBUG: Creating {chart_type} chart...")
        
        if chart_type == "histogram":
            fig = px.histogram(df, x=target_column, title=f"Distribution of {target_column}")
            print("✅ DEBUG: Histogram created")
        elif chart_type == "bar":
            value_counts = df[target_column].value_counts()
            fig = px.bar(x=value_counts.index, y=value_counts.values, 
                        title=f"Count of {target_column} values")
            print("✅ DEBUG: Bar chart created")
        elif chart_type == "line":
            if df[target_column].dtype in ['object', 'category']:
                # For categorical data, create a line plot of value counts
                value_counts = df[target_column].value_counts()
                fig = px.line(x=value_counts.index, y=value_counts.values, 
                             title=f"Trend of {target_column} values")
                print("✅ DEBUG: Line chart (categorical) created")
            else:
                # For numeric data, create a line plot
                fig = px.line(df, x=df.index, y=target_column, 
                             title=f"Trend of {target_column}")
                print("✅ DEBUG: Line chart (numeric) created")
        elif chart_type == "scatter":
            # For scatter, we need two numeric columns
            numeric_cols = df.select_dtypes(include=['number']).columns
            if len(numeric_cols) >= 2:
                fig = px.scatter(df, x=numeric_cols[0], y=numeric_cols[1], 
                                title=f"Scatter plot: {numeric_cols[0]} vs {numeric_cols[1]}")
                print("✅ DEBUG: Scatter chart (2 numeric columns) created")
            else:
                fig = px.scatter(df, x=df.index, y=target_column, 
                                title=f"Scatter plot of {target_column}")
                print("✅ DEBUG: Scatter chart (index vs target) created")
        elif chart_type == "pie":
            value_counts = df[target_column].value_counts().head(10)
            fig = px.pie(values=value_counts.values, names=value_counts.index, 
                        title=f"Distribution of {target_column}")
            print("✅ DEBUG: Pie chart created")
        elif chart_type == "box":
            if df[target_column].dtype in ['number']:
                fig = px.box(df, y=target_column, title=f"Box plot of {target_column}")
                print("✅ DEBUG: Box chart (numeric) created")
            else:
                # For categorical data, create a box plot of a numeric column
                numeric_cols = df.select_dtypes(include=['number']).columns
                if len(numeric_cols) > 0:
                    fig = px.box(df, x=target_column, y=numeric_cols[0], 
                                title=f"Box plot: {numeric_cols[0]} by {target_column}")
                    print("✅ DEBUG: Box chart (categorical vs numeric) created")
                else:
                    fig = px.histogram(df, x=target_column, title=f"Distribution of {target_column}")
                    print("✅ DEBUG: Box chart fallback to histogram created")
        else:
            # Default to histogram
            fig = px.histogram(df, x=target_column, title=f"Distribution of {target_column}")
            print("✅ DEBUG: Default histogram created")
        
        # Apply consistent styling
        print("🔍 DEBUG: Applying chart styling...")
        fig.update_layout(
            template="plotly_white",
            title_x=0.5,
            margin=dict(t=50, l=50, r=50, b=50),
            showlegend=True
        )
        
        print("✅ DEBUG: Fallback chart created successfully")
        return fig
        
    except Exception as e:
        print(f"❌ DEBUG: Error in fallback chart: {e}")
        print(f"🔍 DEBUG: Full fallback error details: {str(e)}")
        import traceback
        print(f"🔍 DEBUG: Fallback traceback: {traceback.format_exc()}")
        # Create a minimal chart as last resort
        print("🔍 DEBUG: Creating minimal chart as last resort...")
        import plotly.graph_objects as go
        fig = go.Figure()
        fig.add_trace(go.Bar(x=['Data'], y=[len(df)], name='Row Count'))
        fig.update_layout(
            title="Dataset Overview", 
            template="plotly_white",
            title_x=0.5,
            margin=dict(t=50, l=50, r=50, b=50)
        )
        print("✅ DEBUG: Minimal chart created as last resort")
        return fig