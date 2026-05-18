import os
import time
import requests
import pandas as pd
import streamlit as st
from dotenv import load_dotenv
import google.generativeai as genai

# --- 1. ALAPBEÁLLÍTÁSOK ---
load_dotenv()
api_key = os.getenv("API_FOOTBALL_KEY")
gemini_key = os.getenv("GEMINI_API_KEY")

genai.configure(api_key=gemini_key)
modell = genai.GenerativeModel('gemini-2.5-flash')

# --- 2. SEGÉDFÜGGVÉNYEK (Gyorsítótárazással / Caching) ---

@st.cache_data(ttl=3600) 
def get_team_id(csapat_nev):
    url = f"https://v3.football.api-sports.io/teams?search={csapat_nev}"
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
    if res.status_code != 200: return None
        
    data = res.json()
    if 'errors' in data and data['errors']:
        st.error(f"API Hiba ({team_name}): {data['errors']}")
        return None
        
    all_fixtures = data.get('response', [])
    if not all_fixtures: return None
        
    
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
                    if stat['type'] == 'Corner Kicks': corners = stat['value'] if stat['value'] else 0
                    elif stat['type'] == 'Yellow Cards': cards = stat['value'] if stat['value'] else 0
                
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

# --- 3. WEBOLDAL GRAFIKUS FELÜLET ---
st.set_page_config(page_title="H2H Elemző", page_icon="⚽", layout="wide") # Szélesebb dizájn
st.title("⚽ AI H2H Meccs Elemző (V2.1 - Caching & RAG)")
st.markdown("Vizsgáld meg a csapatok legfrissebb egyéni formáját, szöglet és lap átlagait valós időben!")

col1, col2 = st.columns(2)
with col1: hazai_csapat = st.text_input("🏠 Hazai csapat (pl. Real Madrid):")
with col2: vendeg_csapat = st.text_input("✈️ Vendég csapat (pl. Barcelona):")

if st.button("Részletes Elemzés Kérése", use_container_width=True):
    if hazai_csapat and vendeg_csapat:
        
        with st.spinner('Adatbányászat és API lekérések folyamatban...'):
            hazai_id, hazai_hivatalos_nev = get_team_id(hazai_csapat)
            vendeg_id, vendeg_hivatalos_nev = get_team_id(vendeg_csapat)
            
            if hazai_id and vendeg_id:
                st.success(f"✅ Rendszerkapcsolat felépítve: {hazai_hivatalos_nev} vs {vendeg_hivatalos_nev}")
                
                hazai_stats = get_team_detailed_stats(hazai_id, hazai_hivatalos_nev)
                vendeg_stats = get_team_detailed_stats(vendeg_id, vendeg_hivatalos_nev)
                
                if hazai_stats and vendeg_stats:
                    st.divider() # Vonalhúzó
                    
                    # A RAG ARCHITEKTÚRA BEMUTATÁSA, HASZNÁLATA
                    st.header("📥 1. Kinyert Tényadatok (Retrieval)")
                    
                    
                    st.subheader("Gólstatisztika összehasonlítás")
                    chart_data = pd.DataFrame(
                        {
                            "Lőtt gólok (Átlag)": [hazai_stats['avg_scored'], vendeg_stats['avg_scored']],
                            "Kapott gólok (Átlag)": [hazai_stats['avg_conceded'], vendeg_stats['avg_conceded']]
                        },
                        index=[hazai_hivatalos_nev, vendeg_hivatalos_nev]
                    )
                    st.bar_chart(chart_data)
                    
                    
                    m_col1, m_col2 = st.columns(2)
                    with m_col1:
                        st.markdown(f"**🏠 {hazai_hivatalos_nev} (Utolsó 3 meccs)**")
                        st.code(f"⚽ Lőtt: {hazai_stats['avg_scored']} | 🛡️ Kapott: {hazai_stats['avg_conceded']}\n📐 Szöglet: {hazai_stats['avg_corners']} | 🟨 Lap: {hazai_stats['avg_cards']}")
                        
                    with m_col2:
                        st.markdown(f"**✈️ {vendeg_hivatalos_nev} (Utolsó 3 meccs)**")
                        st.code(f"⚽ Lőtt: {vendeg_stats['avg_scored']} | 🛡️ Kapott: {vendeg_stats['avg_conceded']}\n📐 Szöglet: {vendeg_stats['avg_corners']} | 🟨 Lap: {vendeg_stats['avg_cards']}")
                    
                    st.divider()
                    
                    
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
                        Hazai ({hazai_hivatalos_nev}): Lőtt:{hazai_stats['avg_scored']}, Kapott:{hazai_stats['avg_conceded']}, Szöglet:{hazai_stats['avg_corners']}, Lap:{hazai_stats['avg_cards']}
                        Vendég ({vendeg_hivatalos_nev}): Lőtt:{vendeg_stats['avg_scored']}, Kapott:{vendeg_stats['avg_conceded']}, Szöglet:{vendeg_stats['avg_corners']}, Lap:{vendeg_stats['avg_cards']}
                        """
                        
                        ai_valasz = modell.generate_content(prompt)
                        st.write(ai_valasz.text)
                else:
                    st.error("Nem sikerült kinyerni a statisztikákat (Lehet, hogy kimerült a napi API limit).")
            else:
                st.error("Nem található meg mindkét csapat. Ellenőrizd a neveket!")
    else:
        st.warning("Kérlek, add meg mindkét csapat nevét!")