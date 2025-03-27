from fastapi import FastAPI, Depends, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
import pandas as pd
import traceback
import pandas as pd
import numpy as np
import os
from io import BytesIO
import os
from dotenv import load_dotenv
load_dotenv()

# ✅ Then import auth and everything else
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
from langchain.memory import ConversationBufferMemory

llm = ChatOpenAI(temperature=0.9, model=OPENAI_MODEL, openai_api_key=OPENAI_API_KEY)

app = FastAPI()

# ✅ CORS setup for Render
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change this for production security!
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def health_check():
    return {"status": "ok"}

# ✅ Fixing File Upload & Debugging
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


memory = ConversationBufferMemory()

# ✅ Fixing NumPy Data Types
def convert_numpy_types(obj):
    if isinstance(obj, np.generic):
        return obj.item()
    elif isinstance(obj, dict):
        return {key: convert_numpy_types(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy_types(element) for element in obj]
    return obj

# ✅ Fixing Upload Route with Debugging
@app.post("/upload")
async def upload_file(file: UploadFile = File(...), user=Depends(verify_supabase_token)):
    try:
        print(f"🔍 Received file: {file.filename}")  # Debugging line
        
        contents = await file.read()
        file_bytes = BytesIO(contents)
        file_bytes.name = file.filename  # Assigning a name for pandas to detect type
        
        global df
        df = load_data(file_bytes, file.filename)

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

# ✅ Fix Query Processing
@app.post("/query")
async def process_query_endpoint(data: dict, user=Depends(verify_supabase_token)):
    print(df.head())
    if "query" not in data:
        raise HTTPException(status_code=400, detail="Missing query in request.")

    user_query = data["query"]
    user_id = user["sub"]  # 🔄 Supabase user ID
    #session = session_manager.get_session(user_id)

    #if not session or "df" not in session or session["df"] is None:
        #raise HTTPException(status_code=400, detail="No dataset uploaded.")
    optimised_query = expand_query_with_chain_of_thought(user_query,df,memory)
    query_type = classify_query(optimised_query)
    try:
        if query_type == "plot":
            manipulation_prompt = generate_data_manipulation_prompt(optimised_query, df)
            processed_df = process_dataframe(manipulation_prompt, df)
            fig = create_visualization(processed_df, user_query)
            memory.save_context({"input": user_query}, {"output": fig})
            result = {"type": "plot", "content": fig.to_json()}



        elif query_type == "table":
            try:
                # Create the agent
                agent = create_pandas_dataframe_agent(
                    llm, df,memory=memory, verbose=False, allow_dangerous_code=True
                )

                # Prompt for clean Python code
                agent_prompt = (
                    f"{user_query.strip()}\n"
                    "Return only valid Python code that defines a DataFrame named `result_df`. "
                    "Do not include comments, markdown, or explanation."
                )

                # Run the agent and get the generated code
                generated_code = agent.run(agent_prompt).strip()
                print("📦 Generated Code:\n", generated_code)

                # Sanity check: remove accidental markdown or explanations
                if "```" in generated_code:
                    generated_code = generated_code.split("```")[1] if "python" in generated_code else generated_code.replace("```", "")

                # Prepare execution environment
                exec_env = {'df': df, 'pd': pd}
                exec(generated_code, {}, exec_env)

                # Validate result_df
                result_df = exec_env.get("result_df")
                if not isinstance(result_df, pd.DataFrame):
                    raise ValueError("The code did not define a valid DataFrame named `result_df`.")

                # Return as dictionary
                memory.save_context({"input": user_query}, {"output": result_df})
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
            agent = create_pandas_dataframe_agent(llm, df,memory=memory, verbose=True, allow_dangerous_code=True, prompt=detailed_prompt)
            answer = agent.run(user_query)
            memory.save_context({"input": user_query}, {"output": answer})
            result = {"type": "text", "content": answer}

        #session.setdefault("queries", []).append(user_query)
        #session.setdefault("answers", []).append(result)
        #session_manager.update_session(user_id, "queries", session["queries"])
        #session_manager.update_session(user_id, "answers", session["answers"])

        return jsonable_encoder(convert_numpy_types(result))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ✅ Fix Session Retrieval
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

# ✅ Fix Deployment for Render
import uvicorn

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))  # Use Render's PORT variable
    print(f"🚀 Starting API on port {port}...")
    uvicorn.run(app, host="0.0.0.0", port=port)
