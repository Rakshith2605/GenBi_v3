import polars as pl
import io

def load_data(file):
    """
    Load data from various file formats (CSV, Excel, JSON) using Polars.
    The input 'file' should be a file-like object with a name attribute.
    """
    filename = getattr(file, "name", "")
    file_extension = filename.split('.')[-1].lower()

    try:
        if file_extension == 'csv':
            df = pl.read_csv(file)
        elif file_extension in ['xlsx', 'xls']:
            df = pl.read_excel(io.BytesIO(file.read()))  # Convert file object for Polars
        elif file_extension == 'json':
            df = pl.read_json(io.BytesIO(file.read()))  # Convert file object for Polars
        else:
            return None

        # Convert columns to numeric where possible
        df = df.with_columns([
            pl.col(col).str.replace(',', '').cast(pl.Float64, strict=False)  # Convert to numeric
            for col in df.columns if df[col].dtype == pl.Utf8
        ])

        return df
    except Exception as e:
        print(f"Error loading file: {e}")
        return None
