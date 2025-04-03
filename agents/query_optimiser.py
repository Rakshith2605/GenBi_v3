import os
import pandas as pd
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langchain.memory import ConversationBufferMemory
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")

# Function to expand query with full context using memory
def expand_query_with_chain_of_thought(query: str, df: pd.DataFrame, memory: ConversationBufferMemory) -> str:
    llm = ChatOpenAI(
        temperature=0.7,
        model="gpt-4",
        openai_api_key=api_key
    )

    rephrase_prompt = PromptTemplate(
        input_variables=["history", "question", "df_columns", "sample_data"],
        template="""
You are a helpful assistant. Given the following conversation history and a follow-up question,
rephrase the question to make it self-contained, using full context and structure.

📊 DataFrame columns:
{df_columns}

🧪 Sample data:
{sample_data}

🗣️ Conversation history:
{history}

❓ Follow-up question:
{question}

Guidelines:
1. If the query is irrelevant to the DataFrame columns, return: "Query is not relevant to the data".
2. If context is missing, use previous questions from history to infer intent.
3. Identify the user's intent and relevant columns.
4. Use a precise, analytical style. Begin with 'Wh' for questions or 'Generate' for charts/tables.
5. Avoid casual tone, markdown, or emojis.

🔁 Rephrased question:
"""
    )

    rephraser_chain = LLMChain(llm=llm, prompt=rephrase_prompt)

    df_columns = ", ".join(df.columns)
    sample_data = df.head(3).to_dict(orient="records")
    history = memory.buffer

    rephrased_query = rephraser_chain.run({
        "history": history,
        "question": query,
        "df_columns": df_columns,
        "sample_data": sample_data
    }).strip()

    return rephrased_query
