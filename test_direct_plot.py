#!/usr/bin/env python3
"""
Test script for direct plot generation without OpenAI dependencies
"""
import pandas as pd
import plotly.express as px
import json
import sys
import os

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agents.visualization import create_fallback_chart

def test_direct_plot_generation():
    """Test the plot generation directly without OpenAI dependencies"""
    
    print("🧪 Testing Direct Plot Generation")
    print("=" * 60)
    
    # Load the data
    print("🔍 DEBUG: Loading test data...")
    df = pd.read_csv('supermarket_sales.csv')
    print(f"✅ DEBUG: Data loaded - Shape: {df.shape}")
    print(f"🔍 DEBUG: Columns: {list(df.columns)}")
    
    # Test different queries to see if we get different plots
    test_queries = [
        "Generate a histogram for the 'Branch' column",
        "Create a bar plot for the 'City' column", 
        "Show me a pie chart of Product line",
        "Create a line plot of Total sales",
        "Generate a scatter plot of Unit price vs Quantity"
    ]
    
    results = []
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n{'='*60}")
        print(f"🧪 TEST {i}: {query}")
        print(f"{'='*60}")
        
        try:
            # Test the fallback chart generation
            fig = create_fallback_chart(df, query)
            
            # Get the chart title to verify it's different
            title = fig.layout.title.text if fig.layout.title else "No title"
            print(f"✅ DEBUG: Generated chart title: {title}")
            
            # Convert to JSON to test serialization
            plot_json = fig.to_json()
            print(f"✅ DEBUG: Plot JSON length: {len(plot_json)} characters")
            
            # Test JSON parsing
            try:
                parsed = json.loads(plot_json)
                print("✅ DEBUG: JSON is valid!")
                results.append({
                    "test": i,
                    "query": query,
                    "title": title,
                    "success": True,
                    "json_length": len(plot_json)
                })
            except Exception as e:
                print(f"❌ DEBUG: JSON parsing failed: {e}")
                results.append({
                    "test": i,
                    "query": query,
                    "title": title,
                    "success": False,
                    "error": str(e)
                })
                
        except Exception as e:
            print(f"❌ DEBUG: Error in test {i}: {e}")
            import traceback
            print(f"🔍 DEBUG: Traceback: {traceback.format_exc()}")
            results.append({
                "test": i,
                "query": query,
                "success": False,
                "error": str(e)
            })
    
    # Summary
    print(f"\n{'='*60}")
    print("📊 TEST SUMMARY")
    print(f"{'='*60}")
    
    successful_tests = [r for r in results if r["success"]]
    failed_tests = [r for r in results if not r["success"]]
    
    print(f"✅ Successful tests: {len(successful_tests)}/{len(results)}")
    print(f"❌ Failed tests: {len(failed_tests)}/{len(results)}")
    
    if successful_tests:
        print("\n✅ Successful chart titles:")
        for result in successful_tests:
            print(f"  - Test {result['test']}: {result['title']}")
    
    if failed_tests:
        print("\n❌ Failed tests:")
        for result in failed_tests:
            print(f"  - Test {result['test']}: {result['error']}")
    
    return len(successful_tests) == len(results)

if __name__ == "__main__":
    success = test_direct_plot_generation()
    print(f"\n{'='*60}")
    if success:
        print("✅ All tests passed! Plot generation is working correctly.")
    else:
        print("❌ Some tests failed. Check the output above.")
    print(f"{'='*60}") 