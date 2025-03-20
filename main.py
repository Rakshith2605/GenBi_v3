from fastapi import FastAPI, Depends, UploadFile, File, HTTPException
import session_manager  

from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import pandas as pd
import numpy as np
from fastapi.encoders import jsonable_encoder

from auth import verify_firebase_token
import session_manager  # Now using Firestore-based session management
from file_processor import load_data
from agents.classifier import classify_query
from agents.prompt_generator import generate_data_manipulation_prompt
from agents.visualization import create_visualization
from utils.data_processor import process_dataframe
from agents.table_generator import get_df
from langchain_experimental.agents import create_pandas_dataframe_agent
from langchain_community.chat_models import ChatOpenAI
from config import OPENAI_API_KEY, OPENAI_MODEL
from io import BytesIO

# Initialize a global LLM instance using OpenAI API
llm = ChatOpenAI(temperature=0, model=OPENAI_MODEL, openai_api_key=OPENAI_API_KEY)

app = FastAPI()

# Configure CORS so your frontend can access these endpoints.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change this to your frontend URL in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def health_check():
    """Check if the API is running."""
    return {"status": "ok"}


def load_data(file_bytes: BytesIO):
    """
    Load a DataFrame from a BytesIO object based on file extension.
    """
    filename = file_bytes.name.lower()
    try:
        if filename.endswith('.csv'):
            # Using engine='python' and sep=None to auto-detect the separator if needed
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
    """
    Recursively convert NumPy data types into native Python types.
    """
    if isinstance(obj, np.generic):
        # Convert NumPy scalar (np.int64, np.float64, etc.) to Python scalar
        return obj.item()
    elif isinstance(obj, dict):
        # Recursively convert within a dictionary
        return {key: convert_numpy_types(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        # Recursively convert within a list
        return [convert_numpy_types(element) for element in obj]
    return obj


@app.post("/upload")
async def upload_file(file: UploadFile = File(...), user=Depends(verify_firebase_token)):
    """
    Upload a dataset file (CSV, Excel, or JSON) and store it in the user's session.
    """
    try:
        contents = await file.read()
        file_bytes = BytesIO(contents)
        file_bytes.name = file.filename  # assign name attribute for file type detection
        global df
        df = load_data(file_bytes)
        
        if df is None or df.empty:
            raise HTTPException(status_code=400, detail="Failed to process file: DataFrame is empty.")
        
        # Save only the top 10 rows in the user's session
        user_id = user["uid"]
        session_manager.update_session(user_id, "df", df.head(10))

        return {
            "message": "File uploaded successfully.",
            "columns": list(df.columns),
            "rows": len(df),
            "df": df.head(10).to_dict(orient="records")  # Convert to dict for JSON serialization
        }
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

    if not session or "df" not in session or session["df"] is None:
        raise HTTPException(status_code=400, detail="No dataset uploaded.")

    query_type = classify_query(user_query)
    try:
        if query_type == "plot":
            manipulation_prompt = generate_data_manipulation_prompt(user_query, session["df"])
            processed_df = process_dataframe(manipulation_prompt, df)
            fig = create_visualization(processed_df, user_query)

            # Serialize Plotly figure as JSON for frontend rendering
            fig_json = fig.to_json()
            result = {"type": "plot", "content": fig_json}

        elif query_type == "table":
            agent = create_pandas_dataframe_agent(
                llm,
                df,
                verbose=True,
                allow_dangerous_code=True
            )

            # Ask LangChain to generate a Pandas DataFrame
            agent_query = f"""
            {user_query}
            Provide Python code to generate a Pandas DataFrame named `result_df`.
            Do not include explanations.
            """
            agent_response = agent.run(agent_query)

            # Execute generated code safely
            local_vars = {'df': df}
            try:
                exec(agent_response, {}, local_vars)
                result_df = local_vars.get('result_df', pd.DataFrame({"Result": ["No data generated."]}))
            except Exception as e:
                result_df = pd.DataFrame({"Error": [str(e)]})

            result = {
                "type": "table",
                "content": result_df.to_dict(orient="records")
            }


        else:  # Query Type: Answer
            detailed_prompt = """
            You are an expert data analyst working with pandas DataFrames.
            When answering the user query, please explain your reasoning in detail,
            including intermediate steps, data exploration, and analysis before presenting your final answer.
            """

            # Create the agent with your custom prompt and desired settings.
            agent = create_pandas_dataframe_agent(
                llm,
                df,
                verbose=True,
                allow_dangerous_code=True,
                prompt=detailed_prompt  # Pass the detailed prompt to the agent (if supported)
            )

            # Run the agent with the user query.
            answer = agent.run(user_query)

            # Format the result.
            result = {"type": "text", "content": answer}

        # Store query history in Firestore
        session.setdefault("queries", []).append(user_query)
        session.setdefault("answers", []).append(result)
        session_manager.update_session(user_id, "queries", session["queries"])
        session_manager.update_session(user_id, "answers", session["answers"])

        return jsonable_encoder(convert_numpy_types(result))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/session")
def get_session_data(user=Depends(verify_firebase_token)):
    """
    Retrieve session information (queries, answers, and a summary of the uploaded dataset)
    from Firestore for the authenticated user.
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