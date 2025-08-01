#!/usr/bin/env python3
"""
Test script for enhanced file processing capabilities
"""
import pandas as pd
import numpy as np
import tempfile
import os
from utils.file_processor import load_data, get_file_info, FileProcessingError

def create_test_csv_files():
    """Create test CSV files with different encodings and formats"""
    test_files = []
    
    # Test 1: Standard CSV with UTF-8
    df1 = pd.DataFrame({
        'Name': ['John', 'Jane', 'Bob'],
        'Age': [25, 30, 35],
        'City': ['New York', 'London', 'Paris']
    })
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8') as f:
        df1.to_csv(f.name, index=False)
        test_files.append(('standard_utf8.csv', f.name))
    
    # Test 2: CSV with semicolon separator
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8') as f:
        df1.to_csv(f.name, index=False, sep=';')
        test_files.append(('semicolon_separated.csv', f.name))
    
    # Test 3: CSV with tab separator
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8') as f:
        df1.to_csv(f.name, index=False, sep='\t')
        test_files.append(('tab_separated.csv', f.name))
    
    # Test 4: CSV with Latin-1 encoding (simulated)
    df2 = pd.DataFrame({
        'Name': ['José', 'François', 'Müller'],
        'Age': [28, 32, 29],
        'City': ['Madrid', 'Paris', 'Berlin']
    })
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='latin-1') as f:
        df2.to_csv(f.name, index=False)
        test_files.append(('latin1_encoded.csv', f.name))
    
    return test_files

def create_test_excel_files():
    """Create test Excel files"""
    test_files = []
    
    # Test 1: Standard Excel file
    df1 = pd.DataFrame({
        'Product': ['Laptop', 'Phone', 'Tablet'],
        'Price': [999.99, 599.99, 399.99],
        'Category': ['Electronics', 'Electronics', 'Electronics']
    })
    
    with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as f:
        df1.to_excel(f.name, index=False)
        test_files.append(('standard_excel.xlsx', f.name))
    
    return test_files

def test_file_processing():
    """Test the enhanced file processing capabilities"""
    
    print("🧪 Testing Enhanced File Processing")
    print("=" * 50)
    
    # Create test files
    print("📁 Creating test files...")
    csv_files = create_test_csv_files()
    excel_files = create_test_excel_files()
    all_files = csv_files + excel_files
    
    results = []
    
    for test_name, file_path in all_files:
        print(f"\n--- Testing: {test_name} ---")
        
        try:
            # Read file bytes
            with open(file_path, 'rb') as f:
                file_bytes = f.read()
            
            # Process file
            df = load_data(file_bytes, test_name)
            
            # Get file info
            file_info = get_file_info(df)
            
            print(f"✅ Successfully processed {test_name}")
            print(f"📊 Shape: {df.shape}")
            print(f"📋 Columns: {list(df.columns)}")
            
            results.append({
                'file': test_name,
                'success': True,
                'shape': df.shape,
                'columns': list(df.columns),
                'file_info': file_info
            })
            
        except Exception as e:
            print(f"❌ Failed to process {test_name}: {e}")
            results.append({
                'file': test_name,
                'success': False,
                'error': str(e)
            })
        
        # Clean up test file
        try:
            os.unlink(file_path)
        except:
            pass
    
    # Summary
    print(f"\n{'='*50}")
    print("📊 TEST SUMMARY")
    print(f"{'='*50}")
    
    successful = [r for r in results if r['success']]
    failed = [r for r in results if not r['success']]
    
    print(f"✅ Successful: {len(successful)}/{len(results)}")
    print(f"❌ Failed: {len(failed)}/{len(results)}")
    
    if successful:
        print("\n✅ Successful files:")
        for r in successful:
            print(f"  - {r['file']}: {r['shape']}")
    
    if failed:
        print("\n❌ Failed files:")
        for r in failed:
            print(f"  - {r['file']}: {r['error']}")
    
    return len(successful) == len(results)

def test_error_handling():
    """Test error handling with invalid files"""
    
    print(f"\n{'='*50}")
    print("🧪 Testing Error Handling")
    print(f"{'='*50}")
    
    # Test 1: Empty file
    try:
        with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as f:
            f.write(b'')  # Empty file
        
        with open(f.name, 'rb') as f:
            file_bytes = f.read()
        
        df = load_data(file_bytes, 'empty.csv')
        print("❌ Should have failed for empty file")
        
    except FileProcessingError as e:
        print(f"✅ Correctly handled empty file: {e}")
    finally:
        try:
            os.unlink(f.name)
        except:
            pass
    
    # Test 2: Invalid CSV
    try:
        with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as f:
            f.write(b'invalid,csv,data\nno,proper,format\n')
        
        with open(f.name, 'rb') as f:
            file_bytes = f.read()
        
        df = load_data(file_bytes, 'invalid.csv')
        print(f"✅ Processed invalid CSV: {df.shape}")
        
    except FileProcessingError as e:
        print(f"❌ Failed to process invalid CSV: {e}")
    finally:
        try:
            os.unlink(f.name)
        except:
            pass
    
    # Test 3: Unsupported format
    try:
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as f:
            f.write(b'This is a text file')
        
        with open(f.name, 'rb') as f:
            file_bytes = f.read()
        
        df = load_data(file_bytes, 'unsupported.txt')
        print("❌ Should have failed for unsupported format")
        
    except FileProcessingError as e:
        print(f"✅ Correctly handled unsupported format: {e}")
    finally:
        try:
            os.unlink(f.name)
        except:
            pass

if __name__ == "__main__":
    success = test_file_processing()
    test_error_handling()
    
    print(f"\n{'='*50}")
    if success:
        print("🎉 All file processing tests passed!")
    else:
        print("⚠️ Some file processing tests failed.")
    print(f"{'='*50}") 