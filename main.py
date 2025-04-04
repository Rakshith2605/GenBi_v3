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

from auth import verify_supabase_token
import session_manager
from file_processor import load_data
from agents.classifier import classify_query
from agents.prompt_generator import generate_data_manipulation_prompt
from agents.visualization import create_visualization
from agents.query_optimiser import expand_query_with_chain_of_thought
from utils.data_processor import process_dataframe
from agents.table_generator import get_df
from langchain_experimental.agents import create_pandas_dataframe_agent
from langchain_openai import ChatOpenAI
from config import OPENAI_API_KEY, OPENAI_MODEL
from utils.memory_manager import get_user_memory  # ✅ NEW

load_dotenv()


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

llm = ChatOpenAI(temperature=0.9, model=OPENAI_MODEL, openai_api_key=OPENAI_API_KEY)

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


def convert_numpy_types(obj):
    if isinstance(obj, np.generic):
        return obj.item()
    elif isinstance(obj, dict):
        return {key: convert_numpy_types(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy_types(element) for element in obj]
    return obj


@app.post("/upload")
async def upload_file(file: UploadFile = File(...), user=Depends(verify_supabase_token)):
    try:
        print(f"🔍 Received file: {file.filename}")
        contents = await file.read()
        file_bytes = BytesIO(contents)
        file_bytes.name = file.filename
        
        global df
        df = load_data(file_bytes, file.filename)

        if df is None or df.empty:
            raise HTTPException(status_code=400, detail="Failed to process file: DataFrame is empty.")
        
        user_id = user["sub"]
        print(f"✅ Storing file for user: {user_id}")
        session_manager.update_session(user_id, "df", df.head(10))

        return {
            "message": "File uploaded successfully.",
            "columns": list(df.columns),
            "rows": len(df),
            "df": df.head(10).to_dict(orient="records")
        }
    except Exception as e:
        print(f"❌ ERROR: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/demo")
async def demo_session(user=Depends(verify_supabase_token)):
    global df
    df = pd.read_csv("supermarket_sales.csv")

    cat_columns = df.select_dtypes(include=['category']).columns
    for col in cat_columns:
        df[col] = df[col].cat.add_categories("NA")

    df = df.fillna("NA")
    df_json = df.head(10).to_dict(orient="records")

    return {
        "message": "File uploaded successfully.",
        "columns": list(df.columns),
        "rows": len(df),
        "df": df_json
    }


@app.post("/query")
async def process_query_endpoint(data: dict, user=Depends(verify_supabase_token)):
    global df

    if "query" not in data:
        raise HTTPException(status_code=400, detail="Missing query in request.")

    user_query = data["query"]
    user_id = user["sub"]
    memory = get_user_memory(user_id)

    optimised_query = expand_query_with_chain_of_thought(user_query, df, memory)
    print(f"🧠 Optimized Query: {optimised_query}")
    query_type = classify_query(optimised_query)

    try:
        if query_type == "plot":
            '''
            manipulation_prompt = generate_data_manipulation_prompt(optimised_query, df)
            processed_df = process_dataframe(manipulation_prompt, df)
            fig = create_visualization(processed_df, optimised_query)
            memory.save_context({"input": optimised_query}, {"output": "Plot generated"})
            result = {"type": "plot", "content": fig.to_json()}
            '''

            try:
                agent = create_pandas_dataframe_agent(
                    llm, df, memory=memory, verbose=False, allow_dangerous_code=True,
                    handle_parsing_errors=True
                )

                agent_prompt = (
                    f"{optimised_query.strip()}\n"
                    "Return only valid Python code using Plotly Express that defines and returns a figure object named `fig`. "
                    "Do not include comments, markdown, or explanation. "
                    "Use only the columns available in the DataFrame `df`. "
                    "The plot must be meaningful, colorful, and aggregated if needed (e.g., using `groupby` and `agg`)."
                )

                generated_code = agent.run(agent_prompt).strip()
                print("📦 Generated Plotly Code:\n", generated_code)

                # ✅ Clean accidental markdown/code fences
                if "```" in generated_code:
                    generated_code = generated_code.replace("```python", "").replace("```", "").strip()

                print("🧪 Cleaned Code to Execute:\n", generated_code)

                # ✅ Execute safely
                exec_env = {'df': df, 'pd': pd, 'px': px}
                exec(generated_code, {}, exec_env)

                # ✅ Retrieve the result
                fig = exec_env.get("fig")
                if fig is None:
                    raise ValueError("The code did not define a valid Plotly figure named `fig`.")

                # ✅ Save to memory for context
                memory_output = f"Generated a visualization with Plotly. Query: {optimised_query}"
                memory.save_context({"input": optimised_query}, {"output": memory_output})

                # ✅ Send to frontend
                result = {
                    "type": "visualization",
                    "content": fig.to_dict()  # Optional: or fig.to_json() if needed
                }

            except Exception as e:
                result = {
                    "type": "error",
                    "content": f"Error generating visualization: {str(e)}"
                }


        elif query_type == "table":
            try:
                agent = create_pandas_dataframe_agent(
                    llm, df, memory=memory, verbose=False, allow_dangerous_code=True,
                    handle_parsing_errors=True
                )


                agent_prompt = (
                    f"{optimised_query.strip()}\n"
                    "Return only valid Python code that defines a DataFrame named `result_df`. "
                    "Do not include comments, markdown, or explanation."
                )

                generated_code = agent.run(agent_prompt).strip()
                print("📦 Generated Code:\n", generated_code)

                # ✅ Clean accidental markdown/code fences
                if "```" in generated_code:
                    generated_code = generated_code.replace("```python", "").replace("```", "").strip()

                print("🧪 Cleaned Code to Execute:\n", generated_code)

                # ✅ Execute safely
                exec_env = {'df': df, 'pd': pd}
                exec(generated_code, {}, exec_env)

                # ✅ Retrieve the result
                result_df = exec_env.get("result_df")
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
            """
            agent = create_pandas_dataframe_agent(llm, df, memory=memory, verbose=True, allow_dangerous_code=True, prompt=detailed_prompt)
            answer = agent.run(optimised_query)
            memory.save_context({"input": optimised_query}, {"output": answer})
            result = {"type": "text", "content": answer}

        return jsonable_encoder(convert_numpy_types(result))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/session")
def get_session_data(user=Depends(verify_supabase_token)):
    user_id = user["sub"]
    session = session_manager.get_session(user_id)

    session_info = {
        "queries": session.get("queries", []),
        "answers": session.get("answers", []),
        "data_summary": {
            "columns": list(session["df"].columns) if session.get("df") is not None else [],
            "rows": len(session["df"]) if session.get("df") is not None else 0,
        }
    }
    return session_info


import uvicorn

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print(f"🚀 Starting API on port {port}...")
    uvicorn.run(app, host="0.0.0.0", port=port)
