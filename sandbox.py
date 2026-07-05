import google.genai as genai
from dotenv import load_dotenv
load_dotenv()
client = genai.Client(api_key="GEMINI_API")
print(type(client))

# Очікуваний вивід:
# <class 'google.genai.client.Client'>j