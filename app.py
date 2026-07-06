import streamlit as st
import requests
import pandas as pd

st.set_page_config(page_title="Pinnacle Precision Scanner", layout="wide")

st.title("🧠 Pinnacle Precision Sweet-Spot Scanner")
st.write("Filtering Pinnacle's sharp board within optimized risk brackets to highlight FanDuel edges.")

# --- USER CONTROL PANEL ---
st.sidebar.header("🎯 Target Odds Bracket Settings")
st.sidebar.write("Filter out heavy favorites and high-variance longshots.")
min_odds = st.sidebar.number_input("Minimum American Odds (e.g. -200)", value=-200)
max_odds = st.sidebar.number_input("Maximum American Odds (e.g. +150)", value=150)

API_KEY = "1069eccbb7b9bbabe99b4dfa886e5a39"

SPORTS_TO_SCAN = {
    "baseball_mlb": "⚾ MLB Baseball",
    "tennis_atp_wimbledon": "🎾 Men's ATP Tennis"
}

def to_american(dec):
    if dec >= 2.0:
        return f"+{round((dec - 1) * 100)}"
    else:
        return f"-{round(100 / (dec - 1))}"

def american_to_numeric(ame_str):
    """Converts string American odds into a raw integer for numerical filtering."""
    try:
        val = int(ame_str.replace("+", ""))
        return val
    except:
        return 0

st.info("🔄 Streaming active boards and mapping sweet-spot parameters...")

arbitrage_roster = []

for sport_key, sport_label in SPORTS_TO_SCAN.items():
    url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds/?apiKey={API_KEY}&regions=us,eu&markets=h2h"
    
    try:
        response = requests.get(url)
        if response.status_code == 200:
            games = response.json()
            
            for game in games:
                matchup_name = f"{game.get('away_team')} @ {game.get('home_team')}"
                bookmakers = game.get('bookmakers', [])
                
                pin_odds = {}
                fd_odds = {}
                
                for b in bookmakers:
                    if b['key'] == 'pinnacle':
                        outcomes = b['markets'][0]['outcomes']
                        pin_odds = {o['name']: o['price'] for o in outcomes}
                    elif b['key'] == 'fanduel':
                        outcomes = b['markets'][0]['outcomes']
                        fd_odds = {o['name']: o['price'] for o in outcomes}
                
                if pin_odds and fd_odds and len(pin_odds) == 2:
                    players = list(pin_odds.keys())
                    p1, p2 = players[0], players[1]
                    
                    # De-vig Pinnacle metrics
                    pin_dec1, pin_dec2 = pin_odds[p1], pin_odds[p2]
                    raw_p1, raw_p2 = 1/pin_dec1, 1/pin_dec2
                    total_pin_prob = raw_p1 + raw_p2
                    
                    true_prob1 = raw_p1 / total_pin_prob
                    true_prob2 = raw_p2 / total_pin_prob
                    
                    fd_dec1 = fd_odds.get(p1)
                    fd_dec2 = fd_odds.get(p2)
                    
                    if fd_dec1 and fd_dec2:
                        fd_implied1 = 1 / fd_dec1
                        fd_implied2 = 1 / fd_dec2
                        
                        edge1 = true_prob1 - fd_implied1
                        edge2 = true_prob2 - fd_implied2
                        
                        for player, true_p, fd_dec, edge, pin_dec in [(p1, true_prob1, fd_dec1, edge1, pin_dec1), (p2, true_prob2, fd_dec2, edge2, pin_dec2)]:
                            pin_american = to_american(pin_dec)
                            pin_numeric = american_to_numeric(pin_american)
                            
                            # --- BRACKET ODDS FILTER FILTERING ---
                            # Ensure the sharp line falls completely inside your custom risk parameters
                            is_valid_odds = False
                            if pin_numeric < 0 and pin_numeric >= min_odds:
                                is_valid_odds = True # Inside favorite limit
                            elif pin_numeric > 0 and pin_numeric <= max_odds:
                                is_valid_odds = True # Inside underdog limit
                            elif pin_numeric == 0:
                                is_valid_odds = True
                                
                            if is_valid_odds:
                                signal = "🟢 +EV EDGE FOUND" if edge > 0.005 else "⚪ NO EDGE"
                                
                                arbitrage_roster.append({
                                    "Status": signal,
                                    "Sport": sport_label,
                                    "Matchup": matchup_name,
                                    "Target Team/Player": player,
                                    "True Probability": f"{true_p*100:.1f}%",
                                    "Pinnacle Sharp Line": pin_american,
                                    "FanDuel Line": to_american(fd_dec),
                                    "Edge Magnitude": round(edge * 100, 2),
                                    "Edge Display": f"{edge*100:+.2f}%"
                                })
                                
    except Exception as e:
        st.error(f"Error compiling metrics: {e}")

# --- DISPLAY MATRIX ---
if arbitrage_roster:
    df = pd.DataFrame(arbitrage_roster)
    df_sorted = df.sort_values(by="Edge Magnitude", ascending=False)
    
    # Custom Row Highlighting Color Function
    def highlight_ev(row):
        if "🟢" in row["Status"]:
            return ['background-color: #155e75; color: #ffffff'] * len(row)
        return [''] * len(row)
    
    st.subheader("📊 Complete Sweet-Spot Multi-Sport Grid")
    st.write("All active matchups inside your risk range. High-value +EV targets are highlighted instantly in teal:")
    
    # Apply dynamic style matrix pipeline
    styled_df = df_sorted.style.apply(highlight_ev, axis=1)
    
    st.dataframe(
        styled_df,
        column_order=["Status", "Sport", "Matchup", "Target Team/Player", "True Probability", "Pinnacle Sharp Line", "FanDuel Line", "Edge Display"],
        use_container_width=True,
        hide_index=True
    )
else:
    st.warning("⚖️ No upcoming games match your custom odds filters on the board right now.")
