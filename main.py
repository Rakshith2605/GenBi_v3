from fastapi import FastAPI, Depends, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder

import pandas as pd
import numpy as np
from io import BytesIO

from auth import verify_supabase_token  # 🔄 UPDATED
import session_manager  # TODO: 🔄 Update to work with PostgreSQL or a Supabase-compatible store

from file_processor import load_data
from agents.classifier import classify_query
from agents.prompt_generator import generate_data_manipulation_prompt
from agents.visualization import create_visualization
from utils.data_processor import process_dataframe
from agents.table_generator import get_df
from langchain_experimental.agents import create_pandas_dataframe_agent
from langchain_community.chat_models import ChatOpenAI
from config import OPENAI_API_KEY, OPENAI_MODEL

llm = ChatOpenAI(temperature=0, model=OPENAI_MODEL, openai_api_key=OPENAI_API_KEY)

app = FastAPI()

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change this in production!
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def health_check():
    return {"status": "ok"}


def load_data(file_bytes: BytesIO):
    filename = file_bytes.name.lower()
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
        raise ValueError(f"Error loading file: {e}")


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
        print(f"🔍 Received file: {file.filename}")  # Debugging line
        
        contents = await file.read()
        file_bytes = BytesIO(contents)
        file_bytes.name = file.filename  # Assigning a name for pandas to detect type
        
        global df
        df = load_data(file_bytes)

        if df is None or df.empty:
            raise HTTPException(status_code=400, detail="Failed to process file: DataFrame is empty.")
        
        user_id = user["sub"]  # 🔄 Supabase user ID
        print(f"✅ Storing file for user: {user_id}")  # Debugging line

        session_manager.update_session(user_id, "df", df.head(10))

        return {
            "message": "File uploaded successfully.",
            "columns": list(df.columns),
            "rows": len(df),
            "df": df.head(10).to_dict(orient="records")
        }
    except Exception as e:
        print(f"❌ ERROR: {e}")  # Debugging line
        raise HTTPException(status_code=500, detail=str(e))



@app.post("/query")
async def process_query_endpoint(data: dict, user=Depends(verify_supabase_token)):  # 🔄
    if "query" not in data:
        raise HTTPException(status_code=400, detail="Missing query in request.")

    user_query = data["query"]
    user_id = user["sub"]  # 🔄 Supabase user ID
    session = session_manager.get_session(user_id)

    if not session or "df" not in session or session["df"] is None:
        raise HTTPException(status_code=400, detail="No dataset uploaded.")

    query_type = classify_query(user_query)
    try:
        if query_type == "plot":
            manipulation_prompt = generate_data_manipulation_prompt(user_query, session["df"])
            processed_df = process_dataframe(manipulation_prompt, df)
            fig = create_visualization(processed_df, user_query)
            result = {"type": "plot", "content": fig.to_json()}

        elif query_type == "table":
            agent = create_pandas_dataframe_agent(llm, df, verbose=True, allow_dangerous_code=True)
            agent_query = f"""
            {user_query}
            Provide Python code to generate a Pandas DataFrame named `result_df`.
            Do not include explanations.
            """
            agent_response = agent.run(agent_query)

            local_vars = {'df': df}
            try:
                exec(agent_response, {}, local_vars)
                result_df = local_vars.get('result_df', pd.DataFrame({"Result": ["No data generated."]}))
            except Exception as e:
                result_df = pd.DataFrame({"Error": [str(e)]})

            result = {"type": "table", "content": result_df.to_dict(orient="records")}

        else:
            detailed_prompt = """
            You are an expert data analyst working with pandas DataFrames.
            When answering the user query, please explain your reasoning in detail.
            """
            agent = create_pandas_dataframe_agent(llm, df, verbose=True, allow_dangerous_code=True, prompt=detailed_prompt)
            answer = agent.run(user_query)
            result = {"type": "text", "content": answer}

        session.setdefault("queries", []).append(user_query)
        session.setdefault("answers", []).append(result)
        session_manager.update_session(user_id, "queries", session["queries"])
        session_manager.update_session(user_id, "answers", session["answers"])

        return jsonable_encoder(convert_numpy_types(result))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/session")
def get_session_data(user=Depends(verify_supabase_token)):  # 🔄
    user_id = user["sub"]  # 🔄 Supabase user ID
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


if __name__ == "__main__":
    import uvicorn
    import os

    port = int(os.environ.get("PORT", 8000))  # Use Render's provided PORT
    uvicorn.run(app, host="0.0.0.0", port=port)

