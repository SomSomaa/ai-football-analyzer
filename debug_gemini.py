import os
import google.generativeai as genai
from dotenv import load_dotenv

"""
Diagnostic tool for the AI Football Analyzer.
Use this script to verify your Google Gemini API key connection 
and list the currently supported generative AI models.
"""


load_dotenv()
gemini_key = os.getenv("GEMINI_API_KEY")

print("--- DIAGNOSZTIKA INDÍTÁSA ---")


if not gemini_key:
    print("Kritikus Hiba: Nem találom a 'GEMINI_API_KEY' változót a .env fájlban!")
    print("Ellenőrizd, hogy elmentetted-e a fájlt, és pontosan így írtad-e a nevét.")
else:
    print(f"Siker: API kulcs betöltve. (Első 5 karakter: {gemini_key[:5]}...)")
    
    
    genai.configure(api_key=gemini_key)
    
    print("\nLekérdezem a Google szerverétől az elérhető modelleket...")
    print("Ezeket a neveket használhatod a kódban:\n")
    
    try:
        
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                print(f"- {m.name}")
    except Exception as e:
        print(f"\nHiba a Google szerverrel való kommunikációban: {e}")

print("\n--- DIAGNOSZTIKA VÉGE ---")