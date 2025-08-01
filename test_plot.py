#!/usr/bin/env python3
"""
Test script for plot generation functionality
"""
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json

def test_fallback_chart():
    """Test the fallback chart creation"""
    # Create sample data
    df = pd.read_csv('supermarket_sales.csv')
    
    print("📊 Testing fallback chart creation...")
    
    # Test categorical column
    categorical_cols = df.select_dtypes(include=['object', 'category']).columns
    if len(categorical_cols) > 0:
        col = categorical_cols[0]
        print(f"✅ Creating histogram for categorical column: {col}")
        fig = px.histogram(df, x=col, title=f"Distribution of {col}")
        fig.update_layout(
            template="plotly_white",
            title_x=0.5,
            margin=dict(t=50, l=50, r=50, b=50)
        )
        
        # Convert to JSON
        plot_json = fig.to_json()
        print("✅ Plot JSON generated successfully!")
        print(f"📏 JSON length: {len(plot_json)} characters")
        
        # Test JSON parsing
        try:
            parsed = json.loads(plot_json)
            print("✅ JSON is valid!")
            return True
        except Exception as e:
            print(f"❌ JSON parsing failed: {e}")
            return False
    
    return False

def test_simple_plot():
    """Test a simple plot creation"""
    print("\n🎨 Testing simple plot creation...")
    
    # Create a simple bar chart
    data = {'Branch': ['A', 'B', 'C'], 'Count': [300, 350, 250]}
    df = pd.DataFrame(data)
    
    fig = px.bar(df, x='Branch', y='Count', title='Branch Distribution')
    fig.update_layout(
        template="plotly_white",
        title_x=0.5,
        margin=dict(t=50, l=50, r=50, b=50)
    )
    
    plot_json = fig.to_json()
    print("✅ Simple plot created successfully!")
    print(f"📏 JSON length: {len(plot_json)} characters")
    
    return True

if __name__ == "__main__":
    print("🧪 Testing Plot Generation Functionality")
    print("=" * 50)
    
    # Test 1: Fallback chart
    success1 = test_fallback_chart()
    
    # Test 2: Simple plot
    success2 = test_simple_plot()
    
    print("\n" + "=" * 50)
    if success1 and success2:
        print("✅ All tests passed! Plot generation is working correctly.")
    else:
        print("❌ Some tests failed. Check the output above.") 