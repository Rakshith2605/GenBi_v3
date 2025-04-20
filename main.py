from fastapi import FastAPI, Depends, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
import pandas as pd
import numpy as np
import traceback
import os
from io import BytesIO
from dotenv import load_dotenv
import seaborn as sns
import json
import plotly.express as px
import traceback
from auth import verify_supabase_token
from file_processor import load_data
from agents.classifier import classify_query
from agents.prompt_generator import generate_data_manipulation_prompt
from agents.visualization import create_visualization, generate_plotly_chart
from agents.query_optimiser import expand_query_with_chain_of_thought
from utils.data_processor import process_dataframe
from agents.table_generator import get_df, generate_table
from langchain_experimental.agents import create_pandas_dataframe_agent
from langchain_openai import ChatOpenAI
from config import OPENAI_API_KEY, OPENAI_MODEL
from utils.memory_manager import get_user_memory

load_dotenv()


class DataFrameManager:
    def __init__(self):
        self.df = None
        self.llm = ChatOpenAI(temperature=0.9, model=OPENAI_MODEL, openai_api_key=OPENAI_API_KEY)


def load_data(file_bytes: BytesIO, filename: str):
    try:
        if filename.endswith('.csv'):
            return pd.read_csv(file_bytes, sep=None, engine='python')
        elif filename.endswith(('.xls', '.xlsx')):
            return pd.read_excel(file_bytes)
        elif filename.endswith('.json'):
            return pd.read_json(file_bytes)
        else:
            raise ValueError("Unsupported file format.")
    except Exception as e:
        print(f"❌ Error loading file: {e}")  # Debugging line
        raise ValueError(f"Error loading file: {e}")


def convert_numpy_types(obj):
    if isinstance(obj, np.generic):
        return obj.item()
    elif isinstance(obj, dict):
        return {key: convert_numpy_types(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy_types(element) for element in obj]
    return obj


# Initialize the DataFrame manager
df_manager = DataFrameManager()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 🔒 Change this in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def health_check():
    return {"status": "ok"}


@app.post("/upload")
async def upload_file(file: UploadFile = File(...), user=Depends(verify_supabase_token)):
    try:
        print(f"🔍 Received file: {file.filename}")
        contents = await file.read()
        file_bytes = BytesIO(contents)
        file_bytes.name = file.filename
        
        df_manager.df = load_data(file_bytes, file.filename)

        if df_manager.df is None or df_manager.df.empty:
            raise HTTPException(status_code=400, detail="Failed to process file: DataFrame is empty.")
        
        user_id = user["sub"]
        print(f"✅ Processed file for user: {user_id}")

        return {
            "message": "File uploaded successfully.",
            "columns": list(df_manager.df.columns),
            "rows": len(df_manager.df),
            "df": df_manager.df.head(10).to_dict(orient="records")
        }
    except Exception as e:
        print(f"❌ ERROR: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/demo")
async def demo_session(user=Depends(verify_supabase_token)):
    df_manager.df = pd.read_csv("supermarket_sales.csv")

    cat_columns = df_manager.df.select_dtypes(include=['category']).columns
    for col in cat_columns:
        df_manager.df[col] = df_manager.df[col].cat.add_categories("NA")

    df_manager.df = df_manager.df.fillna("NA")
    df_json = df_manager.df.head(10).to_dict(orient="records")

    return {
        "message": "File uploaded successfully.",
        "columns": list(df_manager.df.columns),
        "rows": len(df_manager.df),
        "df": df_json
    }


@app.post("/query")
async def process_query_endpoint(data: dict, user=Depends(verify_supabase_token)):
    if df_manager.df is None:
        raise HTTPException(status_code=400, detail="No DataFrame loaded. Please upload a file first.")

    if "query" not in data:
        raise HTTPException(status_code=400, detail="Missing query in request.")

    user_query = data["query"]
    user_id = user["sub"]
    memory = get_user_memory(user_id)

    optimised_query = expand_query_with_chain_of_thought(user_query, df_manager.df, memory)
    print(f"🧠 Optimized Query: {optimised_query}")
    query_type = classify_query(optimised_query)

    try:
        if query_type == "plot":
            fig = generate_plotly_chart(df_manager.df, memory, optimised_query)
            memory.save_context({"input": optimised_query}, {"output": "Plot generated"})
            result = {"type": "plot", "content": fig.to_json()}
            
        elif query_type == "table":
            try:
                result_df = generate_table(df_manager.df, memory, optimised_query)
                if not isinstance(result_df, pd.DataFrame):
                    raise ValueError("The code did not define a valid DataFrame named `result_df`.")
                # ✅ Save summary to memory
                memory_output = result_df.head(2).to_string(index=False)
                memory.save_context({"input": optimised_query}, {"output": memory_output})
                # ✅ Send full table to frontend
                result = {
                    "type": "table",
                    "content": result_df.to_dict(orient="records")
                }

            except Exception as e:
                print("❌ Error executing agent code:\n", traceback.format_exc())
                result = {
                    "type": "table",
                    "content": pd.DataFrame({"Error": [str(e)]}).to_dict(orient="records")
                }

        else:
            detailed_prompt = """
            You are an expert data analyst working with pandas DataFrames.
            When answering the user query, please explain your reasoning in detail.
            Always try to support your answer with numerical value, comparision and with proper reasoning.
            """
            agent = create_pandas_dataframe_agent(df_manager.llm, df_manager.df, memory=memory, verbose=True, allow_dangerous_code=True, prompt=detailed_prompt)
            answer = agent.run(optimised_query)
            memory.save_context({"input": optimised_query}, {"output": answer})
            result = {"type": "text", "content": answer}

        return jsonable_encoder(convert_numpy_types(result))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


import uvicorn

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print(f"🚀 Starting API on port {port}...")
    uvicorn.run(app, host="0.0.0.0", port=port)