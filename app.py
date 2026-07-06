import streamlit as st
import requests
import pandas as pd

st.set_page_config(page_title="Pinnacle True Probability Scanner", layout="wide")

st.title("🧠 Pinnacle True Probability Edge Scanner")
st.write("Using Pinnacle's sharp market pricing as the absolute source of truth to exploit FanDuel lines.")

API_KEY = "1069eccbb7b9bbabe99b4dfa886e5a39"

# Core high-volume boards for professional sharp parsing
SPORTS_TO_SCAN = {
    "baseball_mlb": "⚾ MLB Baseball",
    "tennis_atp_wimbledon": "🎾 Men's ATP Tennis"
}

def to_american(dec):
    if dec >= 2.0:
        return f"+{round((dec - 1) * 100)}"
    else:
        return f"-{round(100 / (dec - 1))}"

st.info("🔄 Streaming raw board matrices from both US (FanDuel) and EU (Pinnacle) endpoints...")

arbitrage_roster = []

for sport_key, sport_label in SPORTS_TO_SCAN.items():
    # Query both US and EU regions to hook both books simultaneously
    url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds/?apiKey={API_KEY}&regions=us,eu&markets=h2h"
    
    try:
        response = requests.get(url)
        if response.status_code == 200:
            games = response.json()
            
            for game in games:
                matchup_name = f"{game.get('away_team')} @ {game.get('home_team')}"
                bookmakers = game.get('bookmakers', [])
                
                # Extract individual dictionary footprints for both bookmakers
                pin_odds = {}
                fd_odds = {}
                
                for b in bookmakers:
                    if b['key'] == 'pinnacle':
                        outcomes = b['markets'][0]['outcomes']
                        pin_odds = {o['name']: o['price'] for o in outcomes}
                    elif b['key'] == 'fanduel':
                        outcomes = b['markets'][0]['outcomes']
                        fd_odds = {o['name']: o['price'] for o in outcomes}
                
                # Process only if BOTH books have dropped active lines for the matchup
                if pin_odds and fd_odds and len(pin_odds) == 2:
                    players = list(pin_odds.keys())
                    p1, p2 = players[0], players[1]
                    
                    # --- CORE HANDICAPPING MATHEMATICS: THE PINNACLE DE-VIG ---
                    pin_dec1, pin_dec2 = pin_odds[p1], pin_odds[p2]
                    raw_p1, raw_p2 = 1/pin_dec1, 1/pin_dec2
                    total_pin_prob = raw_p1 + raw_p2
                    
                    # TRUE PROBABILITY (Pinnacle's zero-vig baseline market truth)
                    true_prob1 = raw_p1 / total_pin_prob
                    true_prob2 = raw_p2 / total_pin_prob
                    
                    # Extract corresponding commercial prices on FanDuel
                    fd_dec1 = fd_odds.get(p1)
                    fd_dec2 = fd_odds.get(p2)
                    
                    if fd_dec1 and fd_dec2:
                        # Calculate exactly how much FanDuel's implied price deviates from Pinnacle's truth
                        fd_implied1 = 1 / fd_dec1
                        fd_implied2 = 1 / fd_dec2
                        
                        # EV Edge = True Probability (Pinnacle) - What you are forced to pay (FanDuel)
                        edge1 = true_prob1 - fd_implied1
                        edge2 = true_prob2 - fd_implied2
                        
                        # Format into the array if an asymmetric value gap is detected
                        for player, true_p, fd_dec, edge in [(p1, true_prob1, fd_dec1, edge1), (p2, true_prob2, fd_dec2, edge2)]:
                            
                            # Standard scale: Anything over a +1.0% pure probability advantage is highly exploitable
                            if edge > 0.01:
                                confidence_score = round((true_p * 60) + (edge * 400), 1)
                                confidence_score = min(99.0, max(50.0, confidence_score))
                                
                                arbitrage_roster.append({
                                    "Confidence Score": confidence_score,
                                    "Sport": sport_label,
                                    "Matchup": matchup_name,
                                    "Target Value Bet": player,
                                    "True Probability": f"{true_p*100:.1f}%",
                                    "Pinnacle Sharp Price": to_american(pin_odds[player]),
                                    "FanDuel Line Available": to_american(fd_dec),
                                    "Pure Mathematical Edge": f"{edge*100:+.2f}%"
                                })
                                
    except Exception as e:
        st.error(f"Error compiling sharp metrics for {sport_label}: {e}")

# --- RENDER DATA MATRICES ---
if arbitrage_roster:
    df = pd.DataFrame(arbitrage_roster)
    df_sorted = df.sort_values(by="Confidence Score", ascending=False)
    
    st.subheader("🚀 Discovered Sharp Value Opportunities")
    st.write("These bets represent structural mispricings where FanDuel is charging less than what Pinnacle's true probability dictates:")
    
    st.dataframe(
        df_sorted[["Confidence Score", "Sport", "Matchup", "Target Value Bet", "True Probability", "Pinnacle Sharp Price", "FanDuel Line Available", "Pure Mathematical Edge"]],
        use_container_width=True,
        hide_index=True
    )
else:
    st.warning("⚖️ Complete Market Efficiency: FanDuel's board currently mirrors Pinnacle's lines perfectly across active slots.")
