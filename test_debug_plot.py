#!/usr/bin/env python3
"""
Test script for plot generation with debug logging
"""
import pandas as pd
import plotly.express as px
import json
import sys
import os

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agents.visualization import create_fallback_chart

def test_plot_generation():
    """Test the plot generation with different queries"""
    
    # Load the data
    print("🔍 DEBUG: Loading test data...")
    df = pd.read_csv('supermarket_sales.csv')
    print(f"✅ DEBUG: Data loaded - Shape: {df.shape}")
    print(f"🔍 DEBUG: Columns: {list(df.columns)}")
    
    # Test queries
    test_queries = [
        "Generate a histogram for the 'Branch' column",
        "Create a bar plot for the 'City' column", 
        "Show me a pie chart of Product line",
        "Create a line plot of Total sales",
        "Generate a scatter plot of Unit price vs Quantity"
    ]
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n{'='*60}")
        print(f"🧪 TEST {i}: {query}")
        print(f"{'='*60}")
        
        try:
            # Test the fallback chart generation
            fig = create_fallback_chart(df, query)
            
            # Convert to JSON to test serialization
            plot_json = fig.to_json()
            print(f"✅ DEBUG: Plot JSON length: {len(plot_json)} characters")
            
            # Test JSON parsing
            try:
                parsed = json.loads(plot_json)
                print("✅ DEBUG: JSON is valid!")
            except Exception as e:
                print(f"❌ DEBUG: JSON parsing failed: {e}")
                
        except Exception as e:
            print(f"❌ DEBUG: Error in test {i}: {e}")
            import traceback
            print(f"🔍 DEBUG: Traceback: {traceback.format_exc()}")

if __name__ == "__main__":
    print("🧪 Testing Plot Generation with Debug Logging")
    print("=" * 60)
    test_plot_generation()
    print("\n" + "=" * 60)
    print("✅ Testing complete!") 