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
            
            When explaining a plot/visulisation, follow these steps strictly to ensure accurecy:
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

            ## Task Overview
            You are an advanced language model tasked with explaining the content of a given **visualization** in detail. In your response, you must do the following:

            - **Explain the Visualization:** Clearly describe what the existing plot or chart shows. (Do *not* create or modify the visualization, just explain it.)
            - **Use Data Manipulation for Accuracy:** Perform any needed calculations or data grouping (e.g. counting occurrences, sorting values, computing statistics) using the provided DataFrame to support your explanation with correct numbers.
            - **Provide Numerical Details:** Include detailed numeric information about the plot (e.g. frequencies, percentages, averages) so the reader understands the exact values and comparisons depicted.
            - **Analyze Key Influencers:** Offer insightful analysis about which factors or categories are most significant in the plot and discuss why they stand out or what trends they indicate.

            ## Answer Structure and Format
            Your answer **must** follow this structured format:

            ********
            The above plot shows the frequency of elements in the [Elements] column:  
            Element-1 has 50 entries,  
            Element-2 has 60 entries,  
            Element-3 has 30 entries,  
            ... (continue for all relevant elements/categories)

            Key Influencers and Analysis:  
            - Element-2 has the highest count, indicating it is the most frequent.  
            - Element-3 has the lowest count, which might suggest it is the rarest category.  
            ... (include other noteworthy observations)

            Summary: <A brief concluding sentence summarizing the main insight of the plot.>
            ********

            **Important formatting notes:**

            - **Opening Statement:** Always begin with the exact phrase **"The above plot shows..."** followed by a succinct description of what is being counted or measured. For example: *"The above plot shows the frequency of elements in the **Elements** column:"*.
            - **List of Values:** Present the values or categories from the plot and their corresponding counts (or relevant statistics) in a clear, itemized format. You can use bullet points or line breaks as shown, ensuring each item is easy to read.
            - **Analysis Section:** After listing the values, provide a **"Key Influencers and Analysis"** section. Use bullet points to highlight important insights (e.g. which element is highest/lowest and what that implies). This should interpret the data — not just restate it — to explain *why* those values are meaningful.
            - **Summary Line:** End with a **Summary** that concisely wraps up the overall finding or trend observed in the visualization. This should be one sentence that gives the reader a high-level takeaway.

            ## Additional Guidelines
            - **Be Context-Aware:** Tailor your explanation to avoid stating obvious visual details (such as colors or shapes of chart elements) that don’t add insight. Focus on the implications of the data. For example, instead of saying "*the bar for Element-2 is taller*", say "*Element-2 has the highest frequency*," which conveys the meaning behind the visual.
            - **Justify Data Processing Choices:** If you need to perform data manipulation (like sorting or filtering the DataFrame) to get the numbers for your explanation, choose the method that best highlights the important aspects of the plot. If there are multiple ways to describe the data (e.g. absolute counts vs. percentages), pick the most relevant one and briefly mention why it's useful, if appropriate.
            - **Clarity and Reproducibility:** Make sure your explanation is detailed enough that a reader could follow your reasoning. They should be able to understand how you derived each number from the data. Clearly state any calculation or aggregation you performed (for instance, "*counted the occurrences of each element*").
            - **Precision and Accuracy:** Double-check all numbers and facts you mention from the plot. The explanation should accurately reflect the data shown. Misstating a value or trend will confuse the reader, so ensure every detail is correct.

            By following these instructions and format, your answer will be **clean, directive, and unambiguous**, making it easy for any reader (or another AI) to understand the visualization and the insights it provides.

"""
    agent = create_pandas_dataframe_agent(
                llm,
                user_df,
                memory=memory,
                verbose=True,
                allow_dangerous_code=True,
                prompt=detailed_prompt
            )

    answer = agent.run(optimised_query)
    
    return answer