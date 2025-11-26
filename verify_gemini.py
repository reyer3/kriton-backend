import os
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
model_name = os.getenv("GEMINI_MODEL", "gemini-pro")

print(f"Checking Gemini configuration...")
print(f"API Key present: {'Yes' if api_key else 'No'}")
print(f"Model: {model_name}")

if not api_key:
    print("Skipping actual API call because GEMINI_API_KEY is missing.")
    exit(0)

try:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_name)
    
    print("\nSending test prompt to Gemini...")
    response = model.generate_content("Say 'Hello from Gemini!' if you can hear me.")
    
    print(f"\nResponse:\n{response.text}")
    print("\nSUCCESS: Gemini integration is working.")

except Exception as e:
    print(f"\nERROR: Failed to connect to Gemini.\n{e}")
