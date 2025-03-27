import openai
import os
from langchain.chains import LLMChain
from langchain.memory import ConversationBufferMemory
from langchain.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate
#from langchain.chat_models import ChatOpenAI
import pandas as pd
from langchain_openai import ChatOpenAI
from langchain_openai import ChatOpenAI
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langchain.memory import ConversationBufferMemory
from langchain_experimental.agents import create_pandas_dataframe_agent
import pandas as pd
import os


api_key=os.getenv("OPENAI_API_KEY")

client = openai.OpenAI(api_key=api_key) 

#def expand_query_with_chain_of_thought(user_query, df, buffer_memory):

def expand_query_with_chain_of_thought(query: str, df: pd.DataFrame, memory: ConversationBufferMemory) -> str:
    """
    Expands a user query using conversation history and DataFrame context to make it self-contained.

    Parameters:
        query (str): User's raw query.
        df (pd.DataFrame): The DataFrame to query against.
        memory (ConversationBufferMemory): LangChain memory storing chat history.

    Returns:
        str: A context-aware, refined query suitable for downstream use.
    """
    # Initialize language model
    llm = ChatOpenAI(temperature=0.7, model="gpt-4")

    # Prepare the prompt
    rephrase_prompt = PromptTemplate(
        input_variables=["history", "question", "df_columns", "sample_data"],
        template="""
You are a helpful assistant. Given the following conversation history and a follow-up question, 
rephrase the question to make it self-contained, with full context and structure.

DataFrame columns: {df_columns}
Sample data: {sample_data}
Conversation history: {history}
Follow-up question: {question}

Guidelines:
1. If the query is irrelevant to the DataFrame columns, return: "Query is not relevant to the data".
2. If context is missing, use previous questions from conversation history to infer intent.
3. Identify the user's intent and relevant columns.
4. Use a precise, analytical style: begin with 'Wh' for questions or 'Generate' for charts/tables.
5. Avoid vague or conversational tone.

Rephrased question:"""
    )

    # Create rephraser chain
    rephraser_chain = LLMChain(llm=llm, prompt=rephrase_prompt)

    # Build inputs
    df_columns = ", ".join(df.columns)
    sample_data = df.head(3).to_dict(orient="records")
    history = memory.buffer

    # Run rephrasing
    rephrased_query = rephraser_chain.run({
        "history": history,
        "question": query,
        "df_columns": df_columns,
        "sample_data": sample_data
    }).strip()

    return rephrased_query

    
    
    
#memory = ConversationBufferMemory()
#memory.save_context({"input": user_input}, {"output": answer})

#new_query=expand_query_with_chain_of_thought(query, df, memory)