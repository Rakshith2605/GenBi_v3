import openai
import os
from langchain.chains import LLMChain
from langchain.memory import ConversationBufferMemory
from langchain.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate
#from langchain.chat_models import ChatOpenAI
import pandas as pd
from langchain_openai import ChatOpenAI

api_key=os.getenv("OPENAI_API_KEY")

client = openai.OpenAI(api_key=api_key) 

#def expand_query_with_chain_of_thought(user_query, df, buffer_memory):
def expand_query_with_chain_of_thought(query, df, shared_memory):
    """
    LangChain conversation function with shared memory and a reference DataFrame.
    
    Parameters:
        query (str): The user's question.
        df (pd.DataFrame): DataFrame containing contextual information.
        shared_memory (BaseMemory): LangChain memory to persist the conversation.

    Returns:
        str: Response from the LLM.
    """
    llm = ChatOpenAI(temperature=0, model="gpt-4")

    # Prepare context
    df_columns = ", ".join(df.columns)
    sample_data = df.head(3).to_dict(orient="records")
    chat_history = shared_memory.load_memory_variables({}).get("chat_history", "")

    # Define prompt templates with input variables (NO f-string!)
    system_message = SystemMessagePromptTemplate.from_template(
        """
        You are an intelligent query assistant for analyzing pandas DataFrames.

        User's original query: "{user_query}"

        Context:
        - DataFrame columns: {df_columns}
        - Sample data: {sample_data}
        - Conversation history: {buffer_memory}

        Your task is to refine and expand the user's query so it can be accurately executed on the DataFrame.

        Follow these steps:
        1. Check if the query is relevant to the DataFrame columns. If not, return: "Query is not relevant to the data".
        2. if the query lacks context check Conversation history, if the query related to previous queries build query according to previous context.
        2. Identify what the user likely wants to know.
        3. Determine which columns or data are relevant to answering the query.
        4. If there are any ambiguities, refer to the conversation history to resolve them.
        5. If this is a follow-up question, rephrase it with context from prior conversation and relevant columns.
        6. If the query involves generating tables or plots, begin the expanded query strictly with "Generate" else strictly start with 'wh' questions.
        7. If the user requests a visualization without specifying the plot type:
          - Choose the most appropriate plot using Plotly.
          - Select columns that reveal the most important insights.
        8. If the query lacks detail or requires more information, return a dictionary in this format:
          'followup': 'follow-up question here'
        9. Ensure the expanded query includes one clear and actionable task (not phrased as a question or option).
        10. Try to start question with 'Wh' form for general question and 'Generate' for plot and tables
        11. Your question should always be data-oriented and structured. Frame it using data operations such as groupby, count, sort, filter, or aggregate, similar to how a data analyst would pose a precise analytical task. Avoid vague or conversational language — the question should reflect a clear data manipulation or insight objective.
        12. Return a refined and precise version of the query that helps the agent respond accurately.

        Expanded query:
        """
    )

    human_message = HumanMessagePromptTemplate.from_template("{user_query}")

    chat_prompt = ChatPromptTemplate.from_messages(
        [system_message, human_message]
    )
    chat_prompt.input_variables = ["user_query", "df_columns", "sample_data", "buffer_memory"]


    # Create the LLMChain
    chain = LLMChain(
          llm=llm,
          prompt=chat_prompt,
          verbose=False  # No memory here
      )

    # Run the chain
    inputs = {
        "user_query": query,
        "df_columns": df_columns,
        "sample_data": sample_data,
        "buffer_memory": chat_history
    }

    response = chain.run(inputs)
    return response