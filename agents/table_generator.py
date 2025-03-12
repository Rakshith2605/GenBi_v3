from pandasai import SmartDataframe
from pandasai.llm import OpenAI
from dotenv import load_dotenv
from langchain_community.chat_models import ChatOpenAI
import os
from pathlib import Path



root_dir = Path(__file__).parent.parent
load_dotenv(root_dir / '.env')
api_key=os.getenv("OPENAI_API_KEY")
llm = ChatOpenAI(
    api_key=api_key,
    temperature=0,
    model_name="gpt-4"
)

def get_df(df, query):
    sdf = SmartDataframe(df, config={"llm": llm})
    k=sdf.chat(query)
    return k
