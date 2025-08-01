#!/usr/bin/env python3
"""
Test script for JSON serialization of file info
"""
import pandas as pd
import numpy as np
import json
from utils.file_processor import get_file_info

def test_json_serialization():
    """Test that file info can be properly serialized to JSON"""
    
    print("🧪 Testing JSON Serialization")
    print("=" * 40)
    
    # Create a test DataFrame with various data types
    df = pd.DataFrame({
        'string_col': ['a', 'b', 'c'],
        'int_col': [1, 2, 3],
        'float_col': [1.1, 2.2, 3.3],
        'bool_col': [True, False, True],
        'category_col': pd.Categorical(['cat1', 'cat2', 'cat1']),
        'datetime_col': pd.to_datetime(['2023-01-01', '2023-01-02', '2023-01-03'])
    })
    
    print(f"📊 Test DataFrame shape: {df.shape}")
    print(f"📋 Columns: {list(df.columns)}")
    print(f"🔍 Data types: {df.dtypes.to_dict()}")
    
    try:
        # Get file info
        file_info = get_file_info(df)
        print(f"✅ File info generated successfully")
        print(f"📋 File info keys: {list(file_info.keys())}")
        
        # Test JSON serialization
        json_str = json.dumps(file_info, indent=2)
        print(f"✅ JSON serialization successful")
        print(f"📏 JSON length: {len(json_str)} characters")
        
        # Test JSON deserialization
        parsed = json.loads(json_str)
        print(f"✅ JSON deserialization successful")
        
        # Verify all values are JSON-serializable types
        def check_types(obj, path=""):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    check_types(value, f"{path}.{key}")
            elif isinstance(obj, list):
                for i, value in enumerate(obj):
                    check_types(value, f"{path}[{i}]")
            elif isinstance(obj, (str, int, float, bool)) or obj is None:
                pass  # These are JSON-serializable
            else:
                print(f"⚠️ Non-JSON-serializable type at {path}: {type(obj)}")
        
        check_types(file_info)
        print(f"✅ All values are JSON-serializable")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        print(f"🔍 Traceback: {traceback.format_exc()}")
        return False

if __name__ == "__main__":
    success = test_json_serialization()
    
    print(f"\n{'='*40}")
    if success:
        print("🎉 JSON serialization test passed!")
    else:
        print("❌ JSON serialization test failed!")
    print(f"{'='*40}") 