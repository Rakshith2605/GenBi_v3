from fastapi import FastAPI, Depends, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import pandas as pd

from auth import verify_firebase_token
import session_manager
from file_processor import load_data
from agents.classifier import classify_query
from agents.prompt_generator import generate_data_manipulation_prompt
from agents.visualization import create_visualization
from utils.data_processor import process_dataframe
from agents.table_generator import get_df
from langchain_experimental.agents import create_pandas_dataframe_agent
from langchain_community.chat_models import ChatOpenAI
from config import OPENAI_API_KEY, OPENAI_MODEL

# Initialize a global LLM instance using the key from .env
llm = ChatOpenAI(temperature=0, model=OPENAI_MODEL, openai_api_key=OPENAI_API_KEY)

app = FastAPI()

# Configure CORS so your React app can access these endpoints.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend domain here.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def health_check():
    return {"status": "ok"}

@app.post("/upload")
async def upload_file(file: UploadFile = File(...), user=Depends(verify_firebase_token)):
    """
    Upload a dataset file (CSV, Excel, or JSON) and store it in the user's session.
    """
    try:
        contents = await file.read()
        from io import BytesIO
        file_bytes = BytesIO(contents)
        file_bytes.name = file.filename  # ensure the file-like object has a name attribute
        df = load_data(file_bytes)
        if df is None:
            raise HTTPException(status_code=400, detail="Failed to process file.")
        # Save dataframe in the user’s session (using the Firebase UID as key)
        user_id = user["uid"]
        session = session_manager.get_session(user_id)
        session["df"] = df
        return {"message": "File uploaded successfully.", "columns": list(df.columns), "rows": len(df)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/query")
async def process_query_endpoint(data: dict, user=Depends(verify_firebase_token)):
    """
    Process a user query about the uploaded data. The endpoint determines the query type
    (plot, table, or answer) and returns either a serialized Plotly figure or text.
    """
    if "query" not in data:
        raise HTTPException(status_code=400, detail="Missing query in request.")
    user_query = data["query"]
    user_id = user["uid"]
    session = session_manager.get_session(user_id)
    if "df" not in session or session["df"] is None:
        raise HTTPException(status_code=400, detail="No dataset uploaded.")

    query_type = classify_query(user_query)
    try:
        if query_type == "plot":
            manipulation_prompt = generate_data_manipulation_prompt(user_query, session["df"])
            processed_df = process_dataframe(manipulation_prompt, session["df"])
            fig = create_visualization(processed_df, user_query)
            # Return the Plotly figure as JSON so the React frontend can render it
            fig_json = fig.to_json()
            result = {"type": "plot", "content": fig_json}
        elif query_type == "table":
            result_text = get_df(session["df"], user_query)
            result = {"type": "text", "content": result_text}
        else:  # answer
            agent = create_pandas_dataframe_agent(
                llm,
                session["df"],
                verbose=True,
                allow_dangerous_code=True
            )
            answer = agent.run(user_query)
            result = {"type": "text", "content": answer}

        # Save the query and its response in the session
        session.setdefault("queries", []).append(user_query)
        session.setdefault("answers", []).append(result)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/session")
def get_session_data(user=Depends(verify_firebase_token)):
    """
    Retrieve session information (queries, answers, and a summary of the uploaded dataset)
    for the authenticated user.
    """
    user_id = user["uid"]
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
    uvicorn.run(app, host="0.0.0.0", port=8000)
