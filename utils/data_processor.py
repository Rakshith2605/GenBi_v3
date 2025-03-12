import pandas as pd

def process_dataframe(manipulation_code: str, df: pd.DataFrame, numeric_columns: list = None) -> pd.DataFrame:
    """
    Process and manipulate a DataFrame with flexible column handling.
    
    Parameters:
    - manipulation_code: String containing pandas manipulation code
    - df: Input pandas DataFrame
    - numeric_columns: Optional list of column names to treat as numeric
    
    Returns:
    - Processed pandas DataFrame
    """
    try:
        # Create a copy of the dataframe to avoid modifying the original
        df_copy = df.copy()

        # If numeric_columns not specified, try to auto-detect numeric columns
        if numeric_columns is None:
            numeric_columns = df_copy.select_dtypes(include=['int64', 'float64', 'int32']).columns.tolist()

        # Convert specified or detected numeric columns to proper numeric type
        for col in df_copy.columns:
            if col in numeric_columns:
                try:
                    # Handle various numeric formats (remove commas, dollar signs, etc.)
                    df_copy[col] = pd.to_numeric(
                        df_copy[col].astype(str)
                        .str.replace(r'[\$,]', '', regex=True),
                        errors='coerce'
                    )
                except Exception as e:
                    print(f"Error converting column {col} to numeric: {str(e)}")
            # For non-numeric columns, keep original data type but clean if needed
            elif df_copy[col].dtype == object:
                try:
                    # Remove leading/trailing whitespace from string columns
                    df_copy[col] = df_copy[col].str.strip()
                except Exception:
                    pass  # Skip if column can't be stripped

        # Optional: Drop rows with all NaN values (can be customized)
        df_copy = df_copy.dropna(how='all')

        # Create local namespace with necessary variables
        local_vars = {"df": df_copy, "pd": pd}

        # If no manipulation code provided, return the cleaned dataframe
        if not manipulation_code or manipulation_code.isspace():
            return df_copy

        # Execute the manipulation code
        try:
            exec(manipulation_code, globals(), local_vars)
        except Exception as e:
            print(f"Error executing manipulation code: {str(e)}")
            print(f"Code attempted: {manipulation_code}")
            return df_copy

        # Get the processed dataframe from local namespace
        processed_df = local_vars.get('df')

        if processed_df is None or not isinstance(processed_df, pd.DataFrame):
            print("Warning: Manipulation code did not produce a valid DataFrame")
            return df_copy

        return processed_df

    except Exception as e:
        raise Exception(f"Error processing DataFrame: {str(e)}\nCode attempted: {manipulation_code}")
