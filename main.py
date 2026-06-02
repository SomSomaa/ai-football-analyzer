import os
import time
import requests
import streamlit as st
from dotenv import load_dotenv
import google.generativeai as genai
import plotly.graph_objects as go

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
st.set_page_config(page_title="ProMatch AI | Analitika", layout="wide")

def inject_custom_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&family=JetBrains+Mono:wght@400;700&display=swap');

    /* Font globális beállítása */
    html, body, [class*="css"]  {
        font-family: 'Inter', sans-serif !important;
    }

    /* 1. Animáció és Háttér */
    @keyframes fadeinup {
        from { opacity: 0; transform: translateY(15px); }
        to { opacity: 1; transform: translateY(0); }
    }
    .stApp {
        animation: fadeinup 0.8s ease-out;
        background-color: #0E1117;
        background-image: radial-gradient(circle at 50% 0%, #1a202c 0%, #0E1117 70%);
        color: #E0E6ED;
    }

    /* 2. Gyári felesleg eltüntetése */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* 3. Beviteli mezők */
    .stTextInput > div > div > input {
        background-color: #1E2530 !important;
        color: #FFFFFF !important;
        border-radius: 8px;
        border: 1px solid #2D3748 !important;
        padding: 10px 15px;
        font-family: 'Inter', sans-serif;
    }
    .stTextInput > div > div > input:focus {
        border-color: #3B82F6 !important;
        box-shadow: 0 0 10px rgba(59, 130, 246, 0.4) !important;
    }

    /* 4. Gomb dizájn */
    div.stButton > button:first-child {
        background: linear-gradient(90deg, #2563EB 0%, #7C3AED 100%);
        color: white;
        border: none;
        border-radius: 8px !important;
        padding: 12px 24px;
        font-weight: 600;
        letter-spacing: 0.5px;
        transition: all 0.3s ease;
        width: 100%;
    }
    div.stButton > button:first-child:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(139, 92, 246, 0.4);
    }

    /* 5. Címsor (Gradient Text) */
    .custom-title {
        font-size: 2.6rem;
        font-weight: 800;
        background: -webkit-linear-gradient(45deg, #3B82F6, #8B5CF6);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 5px;
        padding-bottom: 0px;
    }
    .custom-subtitle {
        font-size: 1.1rem;
        color: #94A3B8;
        margin-bottom: 35px;
        font-weight: 400;
    }

    /* 6. AI Szöveg és Adatblokkok */
    .stMarkdown p, .stMarkdown li {
        font-size: 1.1rem !important; 
        line-height: 1.7 !important;
        color: #F8FAFC !important;
    }
    
    /* Monospace a statisztikáknak */
    code {
        font-family: 'JetBrains Mono', monospace !important;
        color: #38BDF8 !important;
        background-color: #0F172A !important;
        border: 1px solid #1E293B !important;
        font-size: 0.95rem !important;
    }

    /* 7. Kiemelt idézet blokk (Value Bet) */
    blockquote {
        border-left: 4px solid #8B5CF6;
        background-color: rgba(139, 92, 246, 0.1);
        padding: 15px 20px;
        border-radius: 0 8px 8px 0;
        margin: 20px 0;
    }
    </style>
    """, unsafe_allow_html=True)

inject_custom_css()

# Modern, egyedi formázású címsor HTML/CSS alapon
st.markdown('<h1 class="custom-title">ProMatch AI | RAG-Alapú Sportanalitika</h1>', unsafe_allow_html=True)
st.markdown('<p class="custom-subtitle">Valós idejű statisztikai modellezés és prediktív formaelemzés a Gemini LLM motorjával</p>', unsafe_allow_html=True)

col1, col2 = st.columns(2)
with col1: 
    home_team_input = st.text_input("HAZAI CSAPAT (pl. Real Madrid):")
with col2: 
    away_team_input = st.text_input("VENDÉG CSAPAT (pl. Barcelona):")

if st.button("Mélyelemzés Futtatása", use_container_width=True):
    if home_team_input and away_team_input:
        
        with st.spinner('Adathalmaz letöltése és API kommunikáció folyamatban...'):
            home_id, home_official_name = get_team_id(home_team_input)
            away_id, away_official_name = get_team_id(away_team_input)
            
            if home_id and away_id:
                st.success(f"Adatkapcsolat sikeres: {home_official_name} vs {away_official_name}")
                
                home_stats = get_team_detailed_stats(home_id, home_official_name)
                away_stats = get_team_detailed_stats(away_id, away_official_name)
                
                if home_stats and away_stats:
                    st.divider() 
                    
                    # RAG ARCHITECTURE: RETRIEVAL STEP
                    st.subheader("I. Kinyert Tényadatok (Retrieval)")
                    
                    # Profi Plotly diagram
                    fig = go.Figure(data=[
                        go.Bar(name='Lőtt gólok (Átlag)', x=[home_official_name, away_official_name], y=[home_stats['avg_scored'], away_stats['avg_scored']], marker_color='#3B82F6', text=[home_stats['avg_scored'], away_stats['avg_scored']], textposition='auto'),
                        go.Bar(name='Kapott gólok (Átlag)', x=[home_official_name, away_official_name], y=[home_stats['avg_conceded'], away_stats['avg_conceded']], marker_color='#EF4444', text=[home_stats['avg_conceded'], away_stats['avg_conceded']], textposition='auto')
                    ])
                    fig.update_layout(
                        barmode='group',
                        plot_bgcolor='rgba(0,0,0,0)', 
                        paper_bgcolor='rgba(0,0,0,0)',
                        font=dict(color='#E0E6ED', size=14),
                        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                        margin=dict(l=0, r=0, t=30, b=0),
                        hovermode="x unified"
                    )
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Visszatett statisztikai oszlopok - JetBrains Mono kód stílussal
                    m_col1, m_col2 = st.columns(2)
                    with m_col1:
                        st.markdown(f"**{home_official_name.upper()} (Utolsó 3 mérkőzés)**")
                        st.code(f"LŐTT GÓL: {home_stats['avg_scored']} | KAPOTT: {home_stats['avg_conceded']}\nSZÖGLET:  {home_stats['avg_corners']} | LAPOK:  {home_stats['avg_cards']}")
                        
                    with m_col2:
                        st.markdown(f"**{away_official_name.upper()} (Utolsó 3 mérkőzés)**")
                        st.code(f"LŐTT GÓL: {away_stats['avg_scored']} | KAPOTT: {away_stats['avg_conceded']}\nSZÖGLET:  {away_stats['avg_corners']} | LAPOK:  {away_stats['avg_cards']}")
                    
                    st.divider()
                    
                    # RAG ARCHITECTURE: GENERATION STEP
                    st.subheader("II. Generatív AI Elemzés (Inference)")
                    with st.spinner('Matematikai modellek illesztése és összefüggések keresése...'):
                        prompt = f"""
                        Te egy szigorú, adatalapú sportfogadó elemző matematika szakértő vagy. 
                        Kaptál egy részletes statisztikai adatsort két futballcsapat legutóbbi egyéni mérkőzéseiről.

                        FELADATOD:
                        Hasonlítsd össze a két csapat formáját, és keress matematikai fogadási értéket (value bet).

                        SZIGORÚ FORMÁZÁSI SZABÁLYOK (Ezeket kötelező betartanod a szép webes megjelenéshez):
                        1. Tagold a szöveget rövidebb, levegős bekezdésekre. Semmiképp ne írj egybefüggő, hosszú szövegfalat!
                        2. Használj felsorolásokat (bullet points) a csapatok elemzésénél.
                        3. A kulcsszavakat és a fontos számokat mindig **vastagítsd ki**.
                        4. A legvégén a javasolt 'Value Bet'-et egy idézet blokkba kell tenned. Ezt úgy éred el, hogy a sort egy '>' jellel kezded (pl: > **Value Bet Javaslat:** ...).

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
        st.warning("Kérlek, add meg mindkét csapat nevét a paraméterek beállításához!")