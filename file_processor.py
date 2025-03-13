import pandas as pd
import io

def load_data(file):
    """
    Load data from various file formats (CSV, Excel, JSON) using Pandas.
    The input 'file' should be a file-like object with a name attribute.
    """
    filename = getattr(file, "name", "")
    file_extension = filename.split('.')[-1].lower()

    try:
        # Read the file according to its extension
        if file_extension == 'csv':
            df = pd.read_csv(file)
        elif file_extension in ['xlsx', 'xls']:
            # Ensure the file pointer is at the beginning
            file.seek(0)
            df = pd.read_excel(file)
        elif file_extension == 'json':
            file.seek(0)
            df = pd.read_json(file)
        else:
            return None

        # For each column with string data, remove commas and attempt to convert to numeric.
        # This will convert values that represent numbers (even with commas) into float,
        # and replace non-convertible values with NaN.
        for col in df.select_dtypes(include=['object']).columns:
            df[col] = pd.to_numeric(df[col].str.replace(',', ''), errors='coerce')
        
        return df
    except Exception as e:
        print(f"Error loading file: {e}")
        return None
