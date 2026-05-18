# AI Football Match Analyzer

A Python-based web application that fetches football statistics (API-Football) and uses Google Gemini to generate value betting analysis. Built to practice API integration, data transformation, caching, and basic RAG concepts.

## Core Features
* **Data Extraction & Transformation:** Fetches season data, filters for completed matches (FT/AET/PEN), and sorts by timestamp using Python to bypass API paywalls on specific parameters.
* **Rate Limit Optimization:** Utilizes `streamlit.cache_data` to minimize network calls and stay within the free tier limits of the API.
* **LLM Integration:** Injects calculated averages (corners, cards, goals) into a strict prompt for Google Gemini to provide objective, data-driven analysis rather than generic sports commentary.
* **UI & Visualization:** Simple interface built with Streamlit, including a Pandas-based bar chart for quick visual comparison of team forms.

## Tech Stack
* Python 3.10+
* Streamlit
* Pandas
* Google Generative AI SDK
* Requests
* Docker

## Local Setup

### Running with Docker
1. Clone the repository.
2. Create a `.env` file in the root directory:
   ```text
   API_FOOTBALL_KEY=your_rapidapi_key
   GEMINI_API_KEY=your_gemini_key