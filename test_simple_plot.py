#!/usr/bin/env python3
"""
Simple test for plot generation without any OpenAI dependencies
"""
import pandas as pd
import plotly.express as px
import json

def test_simple_plots():
    """Test simple plot generation without any external dependencies"""
    
    print("🧪 Testing Simple Plot Generation")
    print("=" * 50)
    
    # Load data
    print("🔍 Loading data...")
    df = pd.read_csv('supermarket_sales.csv')
    print(f"✅ Data loaded: {df.shape}")
    
    # Test different plot types
    tests = [
        {
            "name": "Histogram",
            "query": "histogram for Branch",
            "function": lambda: px.histogram(df, x='Branch', title='Distribution of Branches')
        },
        {
            "name": "Bar Chart", 
            "query": "bar plot for City",
            "function": lambda: px.bar(df['City'].value_counts(), title='City Distribution')
        },
        {
            "name": "Pie Chart",
            "query": "pie chart of Product line", 
            "function": lambda: px.pie(df, names='Product line', title='Product Line Distribution')
        },
        {
            "name": "Line Chart",
            "query": "line plot of Total",
            "function": lambda: px.line(df, x=df.index, y='Total', title='Total Sales Over Time')
        },
        {
            "name": "Scatter Plot",
            "query": "scatter plot of Unit price vs Quantity",
            "function": lambda: px.scatter(df, x='Unit price', y='Quantity', title='Unit Price vs Quantity')
        }
    ]
    
    results = []
    
    for i, test in enumerate(tests, 1):
        print(f"\n--- Test {i}: {test['name']} ---")
        print(f"Query: {test['query']}")
        
        try:
            # Generate plot
            fig = test['function']()
            
            # Apply consistent styling
            fig.update_layout(
                template="plotly_white",
                title_x=0.5,
                margin=dict(t=50, l=50, r=50, b=50)
            )
            
            # Get title
            title = fig.layout.title.text if fig.layout.title else "No title"
            print(f"✅ Generated: {title}")
            
            # Test JSON conversion
            plot_json = fig.to_json()
            print(f"✅ JSON length: {len(plot_json)} chars")
            
            # Test JSON parsing
            try:
                parsed = json.loads(plot_json)
                print("✅ JSON is valid!")
                results.append({
                    "test": i,
                    "name": test['name'],
                    "title": title,
                    "success": True
                })
            except Exception as e:
                print(f"❌ JSON parsing failed: {e}")
                results.append({
                    "test": i,
                    "name": test['name'],
                    "title": title,
                    "success": False,
                    "error": str(e)
                })
                
        except Exception as e:
            print(f"❌ Error: {e}")
            results.append({
                "test": i,
                "name": test['name'],
                "success": False,
                "error": str(e)
            })
    
    # Summary
    print(f"\n{'='*50}")
    print("📊 SUMMARY")
    print(f"{'='*50}")
    
    successful = [r for r in results if r["success"]]
    failed = [r for r in results if not r["success"]]
    
    print(f"✅ Successful: {len(successful)}/{len(results)}")
    print(f"❌ Failed: {len(failed)}/{len(results)}")
    
    if successful:
        print("\n✅ Successful plots:")
        for r in successful:
            print(f"  - {r['name']}: {r['title']}")
    
    if failed:
        print("\n❌ Failed plots:")
        for r in failed:
            print(f"  - {r['name']}: {r['error']}")
    
    return len(successful) == len(results)

if __name__ == "__main__":
    success = test_simple_plots()
    print(f"\n{'='*50}")
    if success:
        print("🎉 All plot tests passed!")
    else:
        print("⚠️ Some plot tests failed.")
    print(f"{'='*50}") 