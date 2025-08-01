#!/usr/bin/env python3
"""
Enhanced file processing module with comprehensive encoding support and error handling
"""
import pandas as pd
import numpy as np
import chardet
import io
import logging
from typing import Union, Optional, Dict, Any
from pathlib import Path
import warnings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Suppress pandas warnings for cleaner output
warnings.filterwarnings('ignore', category=pd.errors.ParserWarning)
warnings.filterwarnings('ignore', category=UserWarning)


class FileProcessingError(Exception):
    """Custom exception for file processing errors"""
    pass


def detect_encoding(file_bytes: bytes) -> str:
    """
    Detect the encoding of a file using chardet
    
    Args:
        file_bytes: Raw file bytes
        
    Returns:
        Detected encoding string
    """
    try:
        # Use chardet to detect encoding
        result = chardet.detect(file_bytes)
        encoding = result['encoding']
        confidence = result['confidence']
        
        logger.info(f"🔍 Detected encoding: {encoding} (confidence: {confidence:.2f})")
        
        # If confidence is low, try common encodings
        if confidence < 0.7:
            logger.warning(f"⚠️ Low confidence in encoding detection: {encoding}")
            # Try common encodings
            common_encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
            for enc in common_encodings:
                try:
                    file_bytes.decode(enc)
                    logger.info(f"✅ Successfully decoded with {enc}")
                    return enc
                except UnicodeDecodeError:
                    continue
        
        return encoding if encoding else 'utf-8'
        
    except Exception as e:
        logger.warning(f"⚠️ Encoding detection failed: {e}, using utf-8")
        return 'utf-8'


def try_csv_parsing(file_bytes: bytes, filename: str) -> pd.DataFrame:
    """
    Try multiple approaches to parse CSV files with different encodings and separators
    
    Args:
        file_bytes: Raw file bytes
        filename: Original filename
        
    Returns:
        Parsed DataFrame
        
    Raises:
        FileProcessingError: If all parsing attempts fail
    """
    # Detect encoding
    encoding = detect_encoding(file_bytes)
    
    # Common CSV separators to try
    separators = [',', ';', '\t', '|', ' ']
    
    # Common encodings to try if the detected one fails
    encodings_to_try = [encoding, 'utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
    
    for enc in encodings_to_try:
        for sep in separators:
            try:
                logger.info(f"🔍 Trying CSV parsing with encoding: {enc}, separator: '{sep}'")
                
                # Try with pandas
                df = pd.read_csv(
                    io.BytesIO(file_bytes),
                    encoding=enc,
                    sep=sep,
                    engine='python',
                    on_bad_lines='skip',
                    low_memory=False
                )
                
                # Check if we got a reasonable DataFrame
                if len(df.columns) > 0 and len(df) > 0:
                    logger.info(f"✅ Successfully parsed CSV with encoding: {enc}, separator: '{sep}'")
                    logger.info(f"📊 DataFrame shape: {df.shape}")
                    return df
                    
            except Exception as e:
                logger.debug(f"❌ Failed with encoding: {enc}, separator: '{sep}': {e}")
                continue
    
    # If all attempts fail, try with default settings
    try:
        logger.info("🔍 Trying default CSV parsing...")
        df = pd.read_csv(io.BytesIO(file_bytes), sep=None, engine='python')
        logger.info(f"✅ Successfully parsed with default settings")
        return df
    except Exception as e:
        logger.error(f"❌ All CSV parsing attempts failed: {e}")
        raise FileProcessingError(f"Failed to parse CSV file: {e}")


def try_excel_parsing(file_bytes: bytes, filename: str) -> pd.DataFrame:
    """
    Try multiple approaches to parse Excel files
    
    Args:
        file_bytes: Raw file bytes
        filename: Original filename
        
    Returns:
        Parsed DataFrame
        
    Raises:
        FileProcessingError: If all parsing attempts fail
    """
    try:
        logger.info(f"🔍 Parsing Excel file: {filename}")
        
        # Try reading with openpyxl engine
        df = pd.read_excel(
            io.BytesIO(file_bytes),
            engine='openpyxl',
            sheet_name=0  # Read first sheet
        )
        
        logger.info(f"✅ Successfully parsed Excel file")
        logger.info(f"📊 DataFrame shape: {df.shape}")
        return df
        
    except Exception as e:
        logger.warning(f"⚠️ openpyxl failed: {e}")
        
        try:
            # Try with xlrd engine for older Excel files
            df = pd.read_excel(
                io.BytesIO(file_bytes),
                engine='xlrd',
                sheet_name=0
            )
            
            logger.info(f"✅ Successfully parsed Excel file with xlrd")
            logger.info(f"📊 DataFrame shape: {df.shape}")
            return df
            
        except Exception as e2:
            logger.error(f"❌ Both Excel engines failed: {e2}")
            raise FileProcessingError(f"Failed to parse Excel file: {e2}")


def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean and prepare DataFrame for analysis
    
    Args:
        df: Raw DataFrame
        
    Returns:
        Cleaned DataFrame
    """
    logger.info("🧹 Cleaning DataFrame...")
    
    # Make a copy to avoid modifying original
    df_clean = df.copy()
    
    # Remove completely empty rows and columns
    df_clean = df_clean.dropna(how='all')
    df_clean = df_clean.dropna(axis=1, how='all')
    
    # Clean column names
    df_clean.columns = df_clean.columns.str.strip()
    df_clean.columns = df_clean.columns.str.replace('\n', ' ')
    df_clean.columns = df_clean.columns.str.replace('\r', ' ')
    
    # Handle categorical columns
    categorical_columns = df_clean.select_dtypes(include=['object']).columns
    for col in categorical_columns:
        # Add 'NA' category if it's a categorical column
        if df_clean[col].dtype == 'category':
            df_clean[col] = df_clean[col].cat.add_categories("NA")
        # Fill NaN values in categorical columns
        df_clean[col] = df_clean[col].fillna("NA")
    
    # Fill remaining NaN values
    df_clean = df_clean.fillna("NA")
    
    logger.info(f"✅ DataFrame cleaned. Final shape: {df_clean.shape}")
    return df_clean


def validate_dataframe(df: pd.DataFrame, filename: str) -> bool:
    """
    Validate that the DataFrame is suitable for analysis
    
    Args:
        df: DataFrame to validate
        filename: Original filename
        
    Returns:
        True if valid, raises FileProcessingError if not
    """
    logger.info("🔍 Validating DataFrame...")
    
    # Check if DataFrame is empty
    if df.empty:
        raise FileProcessingError(f"File '{filename}' is empty or contains no data")
    
    # Check if DataFrame has columns
    if len(df.columns) == 0:
        raise FileProcessingError(f"File '{filename}' has no columns")
    
    # Check for reasonable size (not too large)
    if len(df) > 1000000:  # 1 million rows
        logger.warning(f"⚠️ Large dataset detected: {len(df)} rows")
    
    if len(df.columns) > 100:  # 100 columns
        logger.warning(f"⚠️ Many columns detected: {len(df.columns)} columns")
    
    logger.info(f"✅ DataFrame validation passed")
    return True


def load_data(file_bytes: bytes, filename: str) -> pd.DataFrame:
    """
    Enhanced file loading function with comprehensive error handling
    
    Args:
        file_bytes: Raw file bytes
        filename: Original filename
        
    Returns:
        Cleaned and validated DataFrame
        
    Raises:
        FileProcessingError: If file cannot be processed
    """
    logger.info(f"📁 Processing file: {filename}")
    
    try:
        # Determine file type and parse accordingly
        if filename.lower().endswith('.csv'):
            logger.info("📊 Processing CSV file...")
            df = try_csv_parsing(file_bytes, filename)
            
        elif filename.lower().endswith(('.xls', '.xlsx')):
            logger.info("📊 Processing Excel file...")
            df = try_excel_parsing(file_bytes, filename)
            
        elif filename.lower().endswith('.json'):
            logger.info("📊 Processing JSON file...")
            try:
                df = pd.read_json(io.BytesIO(file_bytes))
            except Exception as e:
                raise FileProcessingError(f"Failed to parse JSON file: {e}")
                
        else:
            raise FileProcessingError(f"Unsupported file format: {filename}")
        
        # Clean and validate the DataFrame
        df_clean = clean_dataframe(df)
        validate_dataframe(df_clean, filename)
        
        logger.info(f"✅ File processing completed successfully")
        return df_clean
        
    except FileProcessingError:
        # Re-raise our custom exceptions
        raise
    except Exception as e:
        logger.error(f"❌ Unexpected error processing file: {e}")
        raise FileProcessingError(f"Unexpected error processing file '{filename}': {e}")


def get_file_info(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Get comprehensive information about the DataFrame
    
    Args:
        df: DataFrame to analyze
        
    Returns:
        Dictionary with file information (JSON-serializable)
    """
    # Convert numpy dtypes to strings for JSON serialization
    data_types = {}
    for col, dtype in df.dtypes.items():
        data_types[str(col)] = str(dtype)
    
    # Convert missing values to regular Python types
    missing_values = {}
    for col, count in df.isnull().sum().items():
        missing_values[str(col)] = int(count)
    
    info = {
        "rows": int(len(df)),
        "columns": int(len(df.columns)),
        "column_names": [str(col) for col in df.columns],
        "data_types": data_types,
        "memory_usage": int(df.memory_usage(deep=True).sum()),
        "missing_values": missing_values,
        "numeric_columns": [str(col) for col in df.select_dtypes(include=[np.number]).columns],
        "categorical_columns": [str(col) for col in df.select_dtypes(include=['object', 'category']).columns],
        "date_columns": [str(col) for col in df.select_dtypes(include=['datetime64']).columns]
    }
    
    return info 