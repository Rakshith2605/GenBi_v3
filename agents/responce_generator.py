from pandasai import SmartDataframe
from pandasai.llm import OpenAI
from dotenv import load_dotenv
from langchain.chat_models import ChatOpenAI
import os
from pathlib import Path
from langchain_experimental.agents import create_pandas_dataframe_agent



root_dir = Path(__file__).parent.parent
load_dotenv(root_dir / '.env')
api_key=os.getenv("OPENAI_API_KEY")
llm = ChatOpenAI(
    api_key=api_key,
    temperature=1,
    model_name="gpt-4"
)

def generate_responce(df, query):
        agent = create_pandas_dataframe_agent(
                    llm,
                    df,
                    verbose=True,
                    allow_dangerous_code=True
                )
        answer = agent.run(query)
        
        return answer
