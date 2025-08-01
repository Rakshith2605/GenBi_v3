from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
import os
from pathlib import Path
from langchain_experimental.agents import create_pandas_dataframe_agent
import pandas as pd


root_dir = Path(__file__).parent.parent
load_dotenv(root_dir / '.env')
api_key=os.getenv("OPENAI_API_KEY")
llm = ChatOpenAI(
    api_key=api_key,
    temperature=0,
    model_name="gpt-4"
)

def generate_table(df,memory,optimised_query):
    agent = create_pandas_dataframe_agent(
            llm, df, memory=memory, verbose=False, allow_dangerous_code=True,
            handle_parsing_errors=True
            )
    
    agent_prompt = (
        f"{optimised_query.strip()}\n"
        "Return only valid Python code that defines a DataFrame named `result_df`. "
        "Do not include comments, markdown, or explanation."
            )

    generated_code = agent.run(agent_prompt).strip()
    print("📦 Generated Code:\n", generated_code)

    # ✅ Clean accidental markdown/code fences
    if "```" in generated_code:
        generated_code = generated_code.replace("```python", "").replace("```", "").strip()
        
    print("🧪 Cleaned Code to Execute:\n", generated_code)
    # ✅ Execute safely
    exec_env = {'df': df, 'pd': pd}
    exec(generated_code, {}, exec_env)

    # ✅ Retrieve the result
    result_df = exec_env.get("result_df") 
    return result_df


'''
                agent = create_pandas_dataframe_agent(
                    llm, df, memory=memory, verbose=False, allow_dangerous_code=True,
                    handle_parsing_errors=True
                )


                agent_prompt = (
                    f"{optimised_query.strip()}\n"
                    "Return only valid Python code that defines a DataFrame named `result_df`. "
                    "Do not include comments, markdown, or explanation."
                )

                generated_code = agent.run(agent_prompt).strip()
                print("📦 Generated Code:\n", generated_code)

                # ✅ Clean accidental markdown/code fences
                if "```" in generated_code:
                    generated_code = generated_code.replace("```python", "").replace("```", "").strip()

                print("🧪 Cleaned Code to Execute:\n", generated_code)

                # ✅ Execute safely
                exec_env = {'df': df, 'pd': pd}
                exec(generated_code, {}, exec_env)

                # ✅ Retrieve the result
                result_df = exec_env.get("result_df")
                if not isinstance(result_df, pd.DataFrame):
                    raise ValueError("The code did not define a valid DataFrame named `result_df`.")

'''