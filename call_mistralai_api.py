# Import the MistralClient classes from the mistralai package
# from mistralai.client import MistralClient
# from mistralai.models.chat_completion import ChatMessage
import requests

# This file contains the function callMistralAPI which is used to call the Mistral API
# The API key and model name are used to authenticate the user and select the model to use

# Retrieve environment variables
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("MISTRAL_API_KEY")
model = "open-mixtral-8x22b"  # mistral-medium-latest  open-mixtral-8x22b  mistral-small-2402 ou latest
url = "https://api.mistral.ai/v1/chat/completions"


## Call MistralAI API via url
## This function can be called from main.py
## It takes a prompt as input and returns the response from the Mistral API

def callMistralAPI(prompt):
    response = requests.post(url,
                             json={
                                 "model": model,
                                 "messages": [
                                     {
                                         "role": "user",
                                         "content": prompt
                                     }
                                 ],
                                 "temperature": 0.3,
                                 "top_p": 1,
                                 "max_tokens": 512,
                                 "stream": False,
                                 "safe_prompt": False,
                                 "random_seed": 1337
                             },
                             headers={"Content-Type": "application/json", "Authorization": f'Bearer {api_key}'})
    if response.status_code == 200:
        return response.json()["choices"][0]["message"]["content"]
    else:
        print(f"Error: Received status code {response.status_code}")
        print(response.text)


if __name__ == "__main__":
    prompt = """DC-3-227B MSN 2198 ex American Airlines NC21793 delivered Feb 24, 1940, impressed by USAAF.  To DSC May 22, 1942,
					returned to American Airlines Mar 28, 1944 as NC21793.  To Douglas Aircraft Co May 10, 1949 
					for sale to Trans Alaska Airlines. Later to CF-HCF (Queen Charlotte Airlines - Pacific 
					Western Airlines May 15, 1953). Rr CF-PWH (PWA Jan 22, 1959 - Queen Charlotte
					Airlines Apr 02, 1962 - Great Northern Airways 1968).  Derelict Terrace, BC. 1973, 
					sold to Pacific Western Airlines Mar 1974 (for spares?), cancelled Feb 1983.
					CF-PWH was bought 1979 by Bob Surman, and in 1987 was under restoration at 
					Cloverdale, BC"""
    response = callMistralAPI(prompt)
    print(response)
