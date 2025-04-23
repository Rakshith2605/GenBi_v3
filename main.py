from fastapi import FastAPI, Depends, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
import pandas as pd
import numpy as np
import traceback
import os
import time
import threading
from io import BytesIO
from dotenv import load_dotenv
import seaborn as sns
import json
import plotly.express as px
import traceback
from auth import verify_supabase_token
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
from langchain.agents.agent_types import AgentType

load_dotenv()


class DataFrameManager:
    def __init__(self, max_idle_time=3600):  # 1 hour default timeout
        self.user_dataframes = {}  # Dictionary to store dataframes for each user
        self.last_access = {}  # Track when each user last accessed their data
        self.max_idle_time = max_idle_time
        self.llm = ChatOpenAI(temperature=0.9, model=OPENAI_MODEL, openai_api_key=OPENAI_API_KEY, max_tokens=4000)
        self._cleanup_lock = threading.Lock()
        self._setup_cleanup_thread()
    
    def _setup_cleanup_thread(self):
        """Setup a thread to periodically clean up old data"""
        self.cleanup_thread = threading.Thread(target=self._cleanup_worker, daemon=True)
        self.cleanup_thread.start()
    
    def _cleanup_worker(self):
        """Background worker that periodically cleans up old data"""
        while True:
            time.sleep(600)  # Run every 10 minutes
            with self._cleanup_lock:
                self.cleanup_old_data()
    
    def get_df(self, user_id):
        """Get the dataframe for a specific user and update access time"""
        if user_id in self.user_dataframes:
            self.last_access[user_id] = time.time()
            return self.user_dataframes.get(user_id)
        return None
    
    def set_df(self, user_id, df):
        """Set the dataframe for a specific user, overwrites any existing data"""
        self.user_dataframes[user_id] = df
        self.last_access[user_id] = time.time()
    
    def cleanup_old_data(self):
        """Remove dataframes for users who haven't accessed for max_idle_time seconds"""
        current_time = time.time()
        users_to_remove = []
        
        for user_id in list(self.last_access.keys()):
            if current_time - self.last_access[user_id] > self.max_idle_time:
                users_to_remove.append(user_id)
        
        for user_id in users_to_remove:
            if user_id in self.user_dataframes:
                print(f"🧹 Cleaning up data for inactive user: {user_id}")
                del self.user_dataframes[user_id]
                del self.last_access[user_id]


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
        
        user_id = user["sub"]
        user_df = load_data(file_bytes, file.filename)

        if user_df is None or user_df.empty:
            raise HTTPException(status_code=400, detail="Failed to process file: DataFrame is empty.")
        
        # Store the dataframe for this specific user (overwrites any existing data)
        df_manager.set_df(user_id, user_df)
        print(f"✅ Processed file for user: {user_id}")

        return {
            "message": "File uploaded successfully.",
            "columns": list(user_df.columns),
            "rows": len(user_df),
            "df": user_df.head(10).to_dict(orient="records")
        }
    except Exception as e:
        print(f"❌ ERROR: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/demo")
async def demo_session(user=Depends(verify_supabase_token)):
    user_id = user["sub"]
    user_df = pd.read_csv("supermarket_sales.csv")

    cat_columns = user_df.select_dtypes(include=['category']).columns
    for col in cat_columns:
        user_df[col] = user_df[col].cat.add_categories("NA")

    user_df = user_df.fillna("NA")
    
    # Store the demo dataframe for this specific user (overwrites any existing data)
    df_manager.set_df(user_id, user_df)
    
    df_json = user_df.head(10).to_dict(orient="records")

    return {
        "message": "Demo data loaded successfully.",
        "columns": list(user_df.columns),
        "rows": len(user_df),
        "df": df_json
    }


@app.post("/query")
async def process_query_endpoint(data: dict, user=Depends(verify_supabase_token)):
    user_id = user["sub"]
    user_df = df_manager.get_df(user_id)
    
    if user_df is None:
        raise HTTPException(status_code=400, detail="No DataFrame loaded for this user. Please upload a file first.")

    if "query" not in data:
        raise HTTPException(status_code=400, detail="Missing query in request.")

    user_query = data["query"]
    memory = get_user_memory(user_id)

    optimised_query = expand_query_with_chain_of_thought(user_query, user_df, memory)
    print(f"🧠 Optimized Query: {optimised_query}")
    query_type = classify_query(optimised_query)

    try:
        if query_type == "plot":
            fig = generate_plotly_chart(user_df, memory, optimised_query)
            memory.save_context({"input": optimised_query}, {"output": "Plot generated"})
            result = {"type": "plot", "content": fig.to_json()}
            
        elif query_type == "table":
            try:
                result_df = generate_table(user_df, memory, optimised_query)
                if not isinstance(result_df, pd.DataFrame):
                    raise ValueError("The code did not define a valid DataFrame named `result_df`.")
                # Save summary to memory
                memory_output = result_df.head(2).to_string(index=False)
                memory.save_context({"input": optimised_query}, {"output": memory_output})
                # Send full table to frontend
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
            You are an expert data analyst working with pandas DataFrames.Be thorough in your analysis. 
            Use **as many tokens as needed** to explain the reasoning, and do not shorten any explanations.
            Use full sentences and **rich descriptions**, making sure every step and reasoning is completely described.
            Don’t skip steps. If needed, break complex logic into parts and explain each one clearly.


            When answering user queries, follow these steps:
            1. UNDERSTAND: First, understand what the query is asking for and identify the key analysis requirements.
            2. PLAN: Outline the step-by-step approach you'll take to solve the problem, including which pandas operations to use.
            3. EXECUTE: For each step in your plan:
            - Show the code you would execute
            - Explain what this code does and why it's needed
            - When appropriate, describe what the output would look like
            4. ANALYZE: Interpret the results of your analysis, highlighting key patterns, insights, or anomalies.
            5. CONCLUDE: Summarize your findings and directly answer the original query.

            Always support your answers with:
            - Numerical evidence (calculations, aggregations, statistics)
            - Comparative analysis (before/after, between groups, against benchmarks)
            - Clear reasoning about why your approach is appropriate
            - Explain in points with Statistics supporting the respective point. 

            Your explanations should be detailed enough that someone could follow your logic and reproduce your analysis.
            If there are multiple ways to approach the problem, explain which approach you chose and why.
            """

            agent = create_pandas_dataframe_agent(
                df_manager.llm,
                user_df,
                agent_type=AgentType.OPENAI_FUNCTIONS,
                memory=memory,
                verbose=True,
                allow_dangerous_code=True,
                prompt=detailed_prompt
            )

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