from pandasai import SmartDataframe
from pandasai.llm import OpenAI
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
import os
from pathlib import Path
from langchain_experimental.agents import create_pandas_dataframe_agent
from langchain.agents.agent_types import AgentType



root_dir = Path(__file__).parent.parent
load_dotenv(root_dir / '.env')
api_key=os.getenv("OPENAI_API_KEY")
llm = ChatOpenAI(
    api_key=api_key,
    temperature=0.9,
    model_name="gpt-4.1"
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


def answer_query(user_df,memory,optimised_query):
    detailed_prompt = """
            You are an expert data analyst working with pandas DataFrames.Be thorough in your analysis. 
            Use **as many tokens as needed** to explain the reasoning, and do not shorten any explanations.
            Use full sentences and **rich descriptions**, making sure every step and reasoning is completely described.
            Don’t skip steps. If needed, break complex logic into parts and explain each one clearly.
            [Important]When explaining a plot/visulisation, follow these steps strictly to ensure accurecy:
                _ You are Expert Data Analyst who can explain visulisation and it's key Influencer.
                - You should not explain how or create a visulisation strictly. 
                - Assume Plot is alredy created in previous chat and user asking for analysis.
                - Perferm respective Data manupulation related to respective plot/visulisation which can answer the character and values of plot
                    ex= grouping, ordering, frequency counting, unique values etc..
                - Data Manipulation: Preprocess or transform data as needed to highlight key patterns or trends relevant to the plot.
                - Statistical Extraction: Compute and present core statistics (e.g., mean, median, variance, correlation coefficients) to quantify insights.
                - Insightful Explanation: Use the extracted statistics to explain what the plot reveals, why it matters, and how it relates to the broader context or objective.
                - Be concise, context-aware, and avoid redundant narration of what the plot visibly shows.

            When answering user queries, follow these steps:
            1. UNDERSTAND: First, understand what the query is asking for and identify the key analysis requirements.
            2. PLAN: Outline the step-by-step approach you'll take to solve the problem, including which pandas operations to use.
            3. EXECUTE: For each step in your plan:
            - Show the code you would execute
            - Explain what this code does and why it's needed
            - When appropriate, describe what the output would look like
            4. ANALYZE: Interpret the results of your analysis, highlighting key patterns, insights, or anomalies.
            5. CONCLUDE: Summarize your findings and directly answer the original query.
            

                
            Always support your answers with:
            - Numerical evidence (calculations, aggregations, statistics)
            - Comparative analysis (before/after, between groups, against benchmarks)
            - Clear reasoning about why your approach is appropriate
            - Explain in points with Statistics supporting the respective point. 

            Your explanations should be detailed enough that someone could follow your logic and reproduce your analysis.
            If there are multiple ways to approach the problem, explain which approach you chose and why.
            """

    agent = create_pandas_dataframe_agent(
                llm,
                user_df,
                agent_type=AgentType.OPENAI_FUNCTIONS,
                memory=memory,
                verbose=True,
                allow_dangerous_code=True,
                prompt=detailed_prompt
            )

    answer = agent.run(optimised_query)
    
    return answer


def explain_plot(user_df,memory,optimised_query):
    detailed_prompt = """
                [Important]When explaining a plot/visulisation, follow these steps strictly to ensure accurecy:
                _ You are Expert Data Analyst who can explain visulisation and it's key Influencer.
                - You should not explain how or create a visulisation strictly. 
                - Assume Plot is alredy created in previous chat and user asking for analysis.
                - Perferm respective Data manupulation related to respective plot/visulisation which can answer the character and values of plot
                    ex= grouping, ordering, frequency counting, unique values etc..
                - Data Manipulation: Preprocess or transform data as needed to highlight key patterns or trends relevant to the plot.
                - Statistical Extraction: Compute and present core statistics (e.g., mean, median, variance, correlation coefficients) to quantify insights.
                - Insightful Explanation: Use the extracted statistics to explain what the plot reveals, why it matters, and how it relates to the broader context or objective.
                - Be concise, context-aware, and avoid redundant narration of what the plot visibly shows.
    
    """
    agent = create_pandas_dataframe_agent(
                llm,
                user_df,
                agent_type=AgentType.OPENAI_FUNCTIONS,
                memory=memory,
                verbose=True,
                allow_dangerous_code=True,
                prompt=detailed_prompt
            )

    answer = agent.run(optimised_query)
    
    return answer