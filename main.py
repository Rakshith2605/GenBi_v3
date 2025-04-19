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
import session_manager
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
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Union

load_dotenv()

# Make sure database tables exist
session_manager.ensure_tables_exist()

def load_data(file_bytes: BytesIO, filename: str):
    try:
        # Reset the file pointer to the beginning
        file_bytes.seek(0)
        
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
        traceback.print_exc()  # Print the full traceback for debugging
        raise ValueError(f"Error loading file: {e}")

llm = ChatOpenAI(temperature=0.9, model=OPENAI_MODEL, openai_api_key=OPENAI_API_KEY)

class DataAnalysisApp:
    def __init__(self):
        self.df = None
        
    def convert_numpy_types(self, obj):
        if isinstance(obj, np.generic):
            return obj.item()
        elif isinstance(obj, dict):
            return {key: self.convert_numpy_types(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self.convert_numpy_types(element) for element in obj]
        return obj

# Create an instance of the class
data_app = DataAnalysisApp()

# Create the FastAPI app
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 🔒 Change this in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Define API Models
class ChatMessageIn(BaseModel):
    content: str
    type: str = "text"

class NewChatSessionRequest(BaseModel):
    dataset_id: Optional[str] = None
    title: Optional[str] = None

# Base Routes
@app.get("/")
def health_check():
    return {"status": "ok"}

# File Upload & Dataset Management
@app.post("/upload")
async def upload_file(file: UploadFile = File(...), user=Depends(verify_supabase_token)):
    try:
        print(f"🔍 Received file: {file.filename}")
        contents = await file.read()
        
        # Create a BytesIO object with the file contents
        file_bytes = BytesIO(contents)
        
        # Read the DataFrame
        data_app.df = load_data(file_bytes, file.filename)

        if data_app.df is None or data_app.df.empty:
            raise HTTPException(status_code=400, detail="Failed to process file: DataFrame is empty.")
        
        user_id = user["sub"]
        print(f"✅ Creating dataset for user: {user_id}")
        
        # Create a dataset in the database
        dataset = session_manager.create_dataset(user_id, data_app.df, file.filename)
        
        if not dataset:
            raise HTTPException(status_code=500, detail="Failed to create dataset.")
        
        # Create a chat session for this dataset
        chat_session = session_manager.create_chat_session(
            user_id, 
            dataset["dataset_id"], 
            f"Chat about {file.filename}"
        )

        return {
            "message": "File uploaded successfully.",
            "dataset": dataset,
            "chat_session": chat_session,
            "columns": list(data_app.df.columns),
            "rows": len(data_app.df),
            "preview": data_app.df.head(10).to_dict(orient="records")
        }
    except Exception as e:
        print(f"❌ ERROR: {e}")
        traceback.print_exc()  # Print the full traceback for debugging
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/demo")
async def demo_session(user=Depends(verify_supabase_token)):
    try:
        # Load demo data
        data_app.df = pd.read_csv("supermarket_sales.csv")
        
        # Process the data
        cat_columns = data_app.df.select_dtypes(include=['category']).columns
        for col in cat_columns:
            data_app.df[col] = data_app.df[col].cat.add_categories("NA")

        data_app.df = data_app.df.fillna("NA")
        
        user_id = user["sub"]
        
        # Create a dataset in the database
        dataset = session_manager.create_dataset(user_id, data_app.df, "supermarket_sales.csv")
        
        if not dataset:
            raise HTTPException(status_code=500, detail="Failed to create dataset.")
        
        # Create a chat session for this dataset
        chat_session = session_manager.create_chat_session(
            user_id, 
            dataset["dataset_id"], 
            "Demo Chat: Supermarket Sales"
        )

        return {
            "message": "Demo dataset loaded successfully.",
            "dataset": dataset,
            "chat_session": chat_session,
            "columns": list(data_app.df.columns),
            "rows": len(data_app.df),
            "preview": data_app.df.head(10).to_dict(orient="records")
        }
    except Exception as e:
        print(f"❌ ERROR loading demo data: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

# Chat Session Management
@app.get("/chat-sessions")
async def get_user_chat_sessions(user=Depends(verify_supabase_token)):
    user_id = user["sub"]
    sessions = session_manager.get_user_chat_sessions(user_id)
    return {"chat_sessions": sessions}

@app.post("/chat-sessions")
async def create_new_chat_session(
    request: NewChatSessionRequest, 
    user=Depends(verify_supabase_token)
):
    user_id = user["sub"]
    new_session = session_manager.create_chat_session(
        user_id, 
        request.dataset_id, 
        request.title
    )
    
    if not new_session:
        raise HTTPException(status_code=500, detail="Failed to create chat session.")
    
    return new_session

@app.get("/chat-sessions/{session_id}")
async def get_chat_session(session_id: str, user=Depends(verify_supabase_token)):
    session = session_manager.get_chat_session(session_id)
    
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found.")
    
    # Check if the user owns this session (security check)
    if session["user_id"] != user["sub"]:
        raise HTTPException(status_code=403, detail="Access denied.")
    
    return session

@app.post("/chat-sessions/{session_id}/messages")
async def add_message_to_chat(
    session_id: str, 
    message: ChatMessageIn, 
    user=Depends(verify_supabase_token)
):
    # First, add the user message
    user_message = session_manager.add_chat_message(
        session_id,
        "user",
        message.content,
        message.type
    )
    
    # Get the current session to check if it has a dataset
    session = session_manager.get_chat_session(session_id)
    
    # Process the query and generate a response
    if session and session.get("dataset_id"):
        # Load the dataset to data_app.df
        cursor = session_manager.get_db_connection().cursor()
        cursor.execute("SELECT * FROM datasets WHERE id = %s", (session["dataset_id"],))
        dataset = cursor.fetchone()
        
        if dataset and dataset.get("storage_path"):
            # Extract bucket and path
            storage_path = dataset["storage_path"]
            parts = storage_path.split('/')
            bucket = parts[0]
            path = '/'.join(parts[1:])
            
            # Download from Supabase storage
            response = session_manager.supabase.storage.from_(bucket).download(path)
            
            # Load into pandas
            file_bytes = BytesIO(response)
            file_name = dataset["name"]
            data_app.df = load_data(file_bytes, file_name)
            
            # Process the user query
            user_id = user["sub"]
            memory = get_user_memory(user_id)
            
            optimised_query = expand_query_with_chain_of_thought(message.content, data_app.df, memory)
            print(f"🧠 Optimized Query: {optimised_query}")
            query_type = classify_query(optimised_query)
            
            try:
                if query_type == "plot":
                    fig = generate_plotly_chart(data_app.df, memory, optimised_query)
                    memory.save_context({"input": optimised_query}, {"output": "Plot generated"})
                    result = {"type": "plot", "content": fig.to_json()}
                    
                elif query_type == "table":
                    result_df = generate_table(data_app.df, memory, optimised_query)
                    if not isinstance(result_df, pd.DataFrame):
                        raise ValueError("The code did not define a valid DataFrame named `result_df`.")
                    memory_output = result_df.head(2).to_string(index=False)
                    memory.save_context({"input": optimised_query}, {"output": memory_output})
                    result = {
                        "type": "table",
                        "content": result_df.to_dict(orient="records")
                    }
                else:
                    detailed_prompt = """
                    You are an expert data analyst working with pandas DataFrames.
                    When answering the user query, please explain your reasoning in detail.
                    Always try to support your answer with numerical value, comparision and with proper reasoning.
                    """
                    agent = create_pandas_dataframe_agent(llm, data_app.df, memory=memory, verbose=True, allow_dangerous_code=True, prompt=detailed_prompt)
                    answer = agent.run(optimised_query)
                    memory.save_context({"input": optimised_query}, {"output": answer})
                    result = {"type": "text", "content": answer}
                
                # Add the assistant's response to the chat
                assistant_message = session_manager.add_chat_message(
                    session_id,
                    "assistant",
                    data_app.convert_numpy_types(result),
                    result["type"]
                )
                
                return {
                    "user_message": user_message,
                    "assistant_message": assistant_message,
                    "result": data_app.convert_numpy_types(result)
                }
            except Exception as e:
                error_message = f"Error processing query: {str(e)}"
                print(f"❌ {error_message}")
                traceback.print_exc()
                
                # Add error message from assistant
                error_result = {"type": "error", "content": error_message}
                assistant_message = session_manager.add_chat_message(
                    session_id,
                    "assistant",
                    error_result,
                    "error"
                )
                
                return {
                    "user_message": user_message,
                    "assistant_message": assistant_message,
                    "result": error_result
                }
    
    # Default response if no dataset or other issue
    default_response = "I don't have a dataset to analyze. Please upload a file first."
    assistant_message = session_manager.add_chat_message(
        session_id,
        "assistant",
        {"type": "text", "content": default_response},
        "text"
    )
    
    return {
        "user_message": user_message,
        "assistant_message": assistant_message,
        "result": {"type": "text", "content": default_response}
    }

# Dataset Management
@app.get("/datasets")
async def get_user_datasets(user=Depends(verify_supabase_token)):
    user_id = user["sub"]
    datasets = session_manager.get_user_datasets(user_id)
    return {"datasets": datasets}

@app.get("/datasets/{dataset_id}")
async def get_dataset(dataset_id: str, user=Depends(verify_supabase_token)):
    conn = session_manager.get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM datasets WHERE id = %s", (dataset_id,))
    dataset = cursor.fetchone()
    
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found.")
    
    # Check if the user owns this dataset (security check)
    if dataset["user_id"] != user["sub"]:
        raise HTTPException(status_code=403, detail="Access denied.")
    
    return dict(dataset)

# Backward compatibility route for the old API
@app.post("/query")
async def process_query_endpoint(data: dict, user=Depends(verify_supabase_token)):
    if "query" not in data:
        raise HTTPException(status_code=400, detail="Missing query in request.")

    if data_app.df is None:
        raise HTTPException(status_code=400, detail="No data loaded. Please upload a file first.")

    user_query = data["query"]
    user_id = user["sub"]
    memory = get_user_memory(user_id)

    # Get or create a chat session
    session_data = session_manager.get_session(user_id)
    session_id = session_data["session_id"]
    
    # Add the user query to the session
    session_manager.add_chat_message(session_id, "user", user_query, "text")

    optimised_query = expand_query_with_chain_of_thought(user_query, data_app.df, memory)
    print(f"🧠 Optimized Query: {optimised_query}")
    query_type = classify_query(optimised_query)

    try:
        if query_type == "plot":
            fig = generate_plotly_chart(data_app.df, memory, optimised_query)
            memory.save_context({"input": optimised_query}, {"output": "Plot generated"})
            result = {"type": "plot", "content": fig.to_json()}
            
        elif query_type == "table":
            try:
                result_df = generate_table(data_app.df, memory, optimised_query)
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
            agent = create_pandas_dataframe_agent(llm, data_app.df, memory=memory, verbose=True, allow_dangerous_code=True, prompt=detailed_prompt)
            answer = agent.run(optimised_query)
            memory.save_context({"input": optimised_query}, {"output": answer})
            result = {"type": "text", "content": answer}
        
        # Add the assistant response to the session
        session_manager.add_chat_message(
            session_id, 
            "assistant", 
            data_app.convert_numpy_types(result), 
            result["type"]
        )

        return jsonable_encoder(data_app.convert_numpy_types(result))
    except Exception as e:
        error_msg = str(e)
        # Add the error to the session
        session_manager.add_chat_message(
            session_id, 
            "assistant", 
            {"type": "error", "content": error_msg}, 
            "error"
        )
        raise HTTPException(status_code=500, detail=error_msg)

@app.get("/session")
def get_session_data(user=Depends(verify_supabase_token)):
    user_id = user["sub"]
    session = session_manager.get_session(user_id)

    session_info = {
        "queries": session.get("queries", []),
        "answers": session.get("answers", []),
        "data_summary": {
            "columns": [],
            "rows": 0,
        }
    }
    
    if session.get("df_metadata"):
        dataset = session.get("df_metadata")
        if dataset:
            session_info["data_summary"]["columns"] = dataset.get("column_names", [])
            session_info["data_summary"]["rows"] = dataset.get("row_count", 0)
    
    return session_info


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    print(f"🚀 Starting API on port {port}...")
    uvicorn.run(app, host="0.0.0.0", port=port)