import pandas as pd

def load_data(file):
    """
    Load data from various file formats (CSV, Excel, JSON).
    The input 'file' should be a file-like object with a name attribute.
    """
    filename = getattr(file, "name", "")
    file_extension = filename.split('.')[-1].lower()

    try:
        if file_extension == 'csv':
            df = pd.read_csv(file)
        elif file_extension in ['xlsx', 'xls']:
            df = pd.read_excel(file)
        elif file_extension == 'json':
            df = pd.read_json(file)
        else:
            return None

        # Attempt to convert columns to numeric where possible.
        for col in df.columns:
            try:
                # Option A: Convert invalid values to NaN instead of ignoring
                df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', ''), errors='coerce')

                # Option B: Wrap in try/except if you want custom handling
                try:
                    df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', ''))
                except ValueError:
                    # Handle or log the error for that column
                    pass

            except Exception:
                continue

        return df
    except Exception:
        return None
