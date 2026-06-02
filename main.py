import os
import time
import requests
import pandas as pd
import streamlit as st
from dotenv import load_dotenv
import google.generativeai as genai

# --- 1. CONFIGURATION & SETUP ---
load_dotenv()
api_key = os.getenv("API_FOOTBALL_KEY")
gemini_key = os.getenv("GEMINI_API_KEY")

genai.configure(api_key=gemini_key)
model = genai.GenerativeModel('gemini-2.5-flash')

# --- 2. HELPER FUNCTIONS (WITH CACHING) ---

@st.cache_data(ttl=3600) 
def get_team_id(team_name):
    url = f"https://v3.football.api-sports.io/teams?search={team_name}"
    headers = {"x-apisports-key": api_key}
    try:
        res = requests.get(url, headers=headers)
        if res.status_code == 200:
            data = res.json()
            if len(data.get('response', [])) > 0:
                return data['response'][0]['team']['id'], data['response'][0]['team']['name']
    except Exception:
        pass
    return None, None

@st.cache_data(ttl=3600)
def get_team_detailed_stats(team_id, team_name):
    url = f"https://v3.football.api-sports.io/fixtures?team={team_id}&season=2024"
    headers = {"x-apisports-key": api_key}
    
    res = requests.get(url, headers=headers)
    if res.status_code != 200: 
        return None
        
    data = res.json()
    if 'errors' in data and data['errors']:
        st.error(f"API Hiba ({team_name}): {data['errors']}")
        return None
        
    all_fixtures = data.get('response', [])
    if not all_fixtures: 
        return None
        
    finished_matches = [m for m in all_fixtures if m['fixture']['status']['short'] in ['FT', 'AET', 'PEN']]
    finished_matches.sort(key=lambda x: x['fixture']['timestamp'], reverse=True)
    fixtures = finished_matches[:3] 
        
        
    total_goals_scored = 0
    total_goals_conceded = 0
    total_corners = 0
    total_cards = 0
    valid_stats_count = 0
    match_summaries = []
    
    for match in fixtures:
        fixture_id = match['fixture']['id']
        home_team = match['teams']['home']['name']
        away_team = match['teams']['away']['name']
        
        g_home = match['goals']['home'] if match['goals']['home'] is not None else 0
        g_away = match['goals']['away'] if match['goals']['away'] is not None else 0
        
        if match['teams']['home']['id'] == team_id:
            scored, conceded = g_home, g_away
        else:
            scored, conceded = g_away, g_home
            
        total_goals_scored += scored
        total_goals_conceded += conceded
        
        time.sleep(1)
        
        stats_url = f"https://v3.football.api-sports.io/fixtures/statistics?fixture={fixture_id}&team={team_id}"
        stats_res = requests.get(stats_url, headers=headers)
        corners, cards = 0, 0
        
        if stats_res.status_code == 200:
            stats_data = stats_res.json()
            if 'errors' in stats_data and stats_data['errors']:
                st.warning(f"Limit Hiba a statisztikáknál: {stats_data['errors']}")
                break
                
            stats_resp = stats_data.get('response', [])
            if stats_resp:
                for stat in stats_resp[0].get('statistics', []):
                    if stat['type'] == 'Corner Kicks': 
                        corners = stat['value'] if stat['value'] else 0
                    elif stat['type'] == 'Yellow Cards': 
                        cards = stat['value'] if stat['value'] else 0
                
                total_corners += corners
                total_cards += cards
                valid_stats_count += 1
        
        match_summaries.append(f"- {home_team} {g_home}-{g_away} {away_team} (Szöglet: {corners}, Lap: {cards})")
        
    count = len(fixtures)
    stats_count = valid_stats_count if valid_stats_count > 0 else 1
    
    return {
        'avg_scored': round(total_goals_scored / count, 2),
        'avg_conceded': round(total_goals_conceded / count, 2),
        'avg_corners': round(total_corners / stats_count, 2),
        'avg_cards': round(total_cards / stats_count, 2),
        'history': "\n".join(match_summaries)
    }

# --- 3. WEB USER INTERFACE (STREAMLIT) ---
st.set_page_config(page_title="H2H Elemző", page_icon="⚽", layout="wide")

def inject_custom_css():
    st.markdown("""
    <style>
    /* 1. Teljes háttér és betűtípus - Mély sötét, modern színvilág */
    .stApp {
        background-color: #0E1117;
        background-image: radial-gradient(circle at 50% 0%, #1a202c 0%, #0E1117 70%);
        color: #E0E6ED;
    }

    /* 2. Streamlit gyári felesleg (hamburger menü, lábléc) eltüntetése */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* 3. Beviteli mezők (Input boxes) modernizálása */
    .stTextInput > div > div > input {
        background-color: #1E2530 !important;
        color: #FFFFFF !important;
        border-radius: 10px;
        border: 1px solid #2D3748 !important;
        padding: 10px 15px;
        box-shadow: inset 0 1px 4px rgba(0,0,0,0.5);
        transition: border-color 0.3s ease, box-shadow 0.3s ease;
    }
    .stTextInput > div > div > input:focus {
        border-color: #3B82F6 !important; /* Kék neon fókusz */
        box-shadow: 0 0 10px rgba(59, 130, 246, 0.4) !important;
    }

    /* 4. Gomb (Button) dizájn - Fókuszált, gradient "Call to Action" */
    div.stButton > button:first-child {
        background: linear-gradient(90deg, #3B82F6 0%, #8B5CF6 100%);
        color: white;
        border: none;
        border-radius: 10px;
        padding: 10px 24px;
        font-weight: 600;
        letter-spacing: 0.5px;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(139, 92, 246, 0.4);
        width: 100%;
        border-radius: 8px !important;
    }
    div.stButton > button:first-child:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(139, 92, 246, 0.6);
        background: linear-gradient(90deg, #2563EB 0%, #7C3AED 100%);
    }

    /* 5. Sikeres üzenet (st.success) modernizálása */
    div[data-testid="stAlert"] {
        background-color: rgba(16, 185, 129, 0.1) !important;
        border: 1px solid rgba(16, 185, 129, 0.4) !important;
        color: #10B981 !important;
        border-radius: 10px;
    }

    /* 6. Elválasztó vonalak finomítása */
    hr {
        border-color: rgba(255, 255, 255, 0.1) !important;
    }
    </style>
    """, unsafe_allow_html=True)

inject_custom_css()

st.title("⚽ AI H2H Meccs Elemző (V2.1 - Caching & RAG)")
st.markdown("Vizsgáld meg a csapatok legfrissebb egyéni formáját, szöglet és lap átlagait valós időben!")

col1, col2 = st.columns(2)
with col1: 
    home_team_input = st.text_input("🏠 Hazai csapat (pl. Real Madrid):")
with col2: 
    away_team_input = st.text_input("✈️ Vendég csapat (pl. Barcelona):")

if st.button("Részletes Elemzés Kérése", use_container_width=True):
    if home_team_input and away_team_input:
        
        with st.spinner('Adatbányászat és API lekérések folyamatban...'):
            home_id, home_official_name = get_team_id(home_team_input)
            away_id, away_official_name = get_team_id(away_team_input)
            
            if home_id and away_id:
                st.success(f"✅ Rendszerkapcsolat felépítve: {home_official_name} vs {away_official_name}")
                
                home_stats = get_team_detailed_stats(home_id, home_official_name)
                away_stats = get_team_detailed_stats(away_id, away_official_name)
                
                if home_stats and away_stats:
                    st.divider() 
                    
                    # RAG ARCHITECTURE: RETRIEVAL STEP
                    st.header("📥 1. Kinyert Tényadatok (Retrieval)")
                    
                    st.subheader("Gólstatisztika összehasonlítás")
                    chart_data = pd.DataFrame(
                        {
                            "Lőtt gólok (Átlag)": [home_stats['avg_scored'], away_stats['avg_scored']],
                            "Kapott gólok (Átlag)": [home_stats['avg_conceded'], away_stats['avg_conceded']]
                        },
                        index=[home_official_name, away_official_name]
                    )
                    st.bar_chart(chart_data)
                    
                    m_col1, m_col2 = st.columns(2)
                    with m_col1:
                        st.markdown(f"**🏠 {home_official_name} (Utolsó 3 meccs)**")
                        st.code(f"⚽ Lőtt: {home_stats['avg_scored']} | 🛡️ Kapott: {home_stats['avg_conceded']}\n📐 Szöglet: {home_stats['avg_corners']} | 🟨 Lap: {home_stats['avg_cards']}")
                        
                    with m_col2:
                        st.markdown(f"**✈️ {away_official_name} (Utolsó 3 meccs)**")
                        st.code(f"⚽ Lőtt: {away_stats['avg_scored']} | 🛡️ Kapott: {away_stats['avg_conceded']}\n📐 Szöglet: {away_stats['avg_corners']} | 🟨 Lap: {away_stats['avg_cards']}")
                    
                    st.divider()
                    
                    # RAG ARCHITECTURE: GENERATION STEP
                    st.header("🧠 2. AI Elemzés (Generation)")
                    with st.spinner('Matematikai összefüggések keresése az adatokban...'):
                        prompt = f"""
                        Te egy szigorú, adatalapú sportfogadó elemző matematika szakértő vagy. 
                        Kaptál egy részletes statisztikai adatsort két futballcsapat legutóbbi egyéni mérkőzéseiről.
                        
                        FELADATOD:
                        Hasonlítsd össze a két csapat formáját, és keress matematikai fogadási értéket (value bet).
                        
                        SZABÁLYOK:
                        - NE használj bevezető sallangokat. Térj közvetlenül a tárgyra.
                        - Maradj végig hűvös, matematikai és tárgyilagos.
                        
                        STATISZTIKÁK:
                        Hazai ({home_official_name}): Lőtt:{home_stats['avg_scored']}, Kapott:{home_stats['avg_conceded']}, Szöglet:{home_stats['avg_corners']}, Lap:{home_stats['avg_cards']}
                        Vendég ({away_official_name}): Lőtt:{away_stats['avg_scored']}, Kapott:{away_stats['avg_conceded']}, Szöglet:{away_stats['avg_corners']}, Lap:{away_stats['avg_cards']}
                        """
                        
                        ai_response = model.generate_content(prompt)
                        st.write(ai_response.text)
                else:
                    st.error("Nem sikerült kinyerni a statisztikákat (Lehet, hogy kimerült a napi API limit).")
            else:
                st.error("Nem található meg mindkét csapat. Ellenőrizd a neveket!")
    else:
        st.warning("Kérlek, add meg mindkét csapat nevét!")