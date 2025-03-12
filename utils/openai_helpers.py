import os
from openai import OpenAI
from typing import List, Dict
from dotenv import load_dotenv
import os
from pathlib import Path
import requests
from typing import Dict, Any, Tuple, Optional


def load_openai_client():
    # Get the project root directory (where .env is located)
    root_dir = Path(__file__).parent.parent
    
    # Load environment variables from .env file
    load_dotenv(root_dir / '.env')
    
    # Initialize and return the OpenAI client
    return OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Create a single client instance to be used throughout the application
client = load_openai_client()




# the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
# do not change this unless explicitly requested by the user
#client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

def get_openai_response(messages: List[Dict[str, str]]) -> str:
    """
    Gets a response from OpenAI API
    """
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            temperature=0,
        )
        return response.choices[0].message.content
    except Exception as e:
        raise Exception(f"Error getting OpenAI response: {str(e)}")




def validate_openai_api_key(api_key: str, check_gpt4: bool = False) -> Tuple[bool, Optional[Dict[Any, Any]]]:
    """
    Validates an OpenAI API key and returns available models if valid.
    
    Args:
        api_key: The OpenAI API key to validate
        check_gpt4: Whether to check if GPT-4 is available
        
    Returns:
        Tuple containing:
        - Boolean indicating if the key is valid
        - Dictionary with model information or error message
    """
    # Basic regex validation (simple check for sk- prefix)
    if not api_key.startswith("sk-"):
        return False, {"error": "Invalid API key format. Must start with 'sk-'"}
    
    # Check key validity by listing models
    headers = {
        "Authorization": f"Bearer {api_key}"
    }
    
    try:
        # Make request to list models
        response = requests.get("https://api.openai.com/v1/models", headers=headers)
        
        if response.status_code == 200:
            models_data = response.json()
            
            # Check for GPT-4 access if requested
            has_gpt4 = False
            if check_gpt4:
                has_gpt4 = any("gpt-4" in model["id"] for model in models_data["data"])
            
            # Test for rate limits with minimal token usage
            test_response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json={
                    "model": "gpt-3.5-turbo",
                    "messages": [{"role": "user", "content": "Hi"}],
                    "max_tokens": 1
                }
            )
            
            rate_limited = False
            if test_response.status_code == 429:
                rate_limited = True
            
            return True, {
                "valid": True,
                "models": models_data["data"],
                "has_gpt4": has_gpt4,
                "rate_limited": rate_limited
            }
        else:
            error_msg = response.json().get("error", {}).get("message", "Unknown error")
            return False, {"error": error_msg}
            
    except Exception as e:
        return False, {"error": str(e)}
