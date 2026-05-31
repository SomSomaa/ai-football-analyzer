import os
import google.generativeai as genai
from dotenv import load_dotenv

# Diagnostic tool for the AI Football Analyzer.
# Use this script to verify your Google Gemini API key connection 
# and list the currently supported generative AI models.

load_dotenv()
gemini_key = os.getenv("GEMINI_API_KEY")

print("--- STARTING DIAGNOSTICS ---")

if not gemini_key:
    print("Critical Error: 'GEMINI_API_KEY' not found in the .env file!")
    print("Check if the file is saved and the variable name is correct.")
else:
    print(f"Success: API key loaded. (First 5 characters: {gemini_key[:5]}...)")
    
    genai.configure(api_key=gemini_key)
    
    print("\nFetching available models from Google servers...")
    print("You can use these model names in your code:\n")
    
    try:
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                print(f"- {m.name}")
    except Exception as e:
        print(f"\nError communicating with Google servers: {e}")

print("\n--- DIAGNOSTICS COMPLETE ---")