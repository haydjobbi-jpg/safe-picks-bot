"""
SAFE-PICKS-BOT V7 FINAL - ESPN FREE + football-data.org
بلا Quota - يصلح Unknown
"""
import requests, os
from datetime import datetime, timedelta
from collections import Counter

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
FOOTBALL_DATA_KEY = os.environ.get("FOOTBALL_DATA_KEY") or os.environ.get("FOOTBALL_DATA_TOKEN", "")

def espn_fetch_fixed():
    print("\n📌 ESPN FREE - القائمة الحقيقية بلا Quota")
    today = datetime.now().strftime("%Y%m%d")
    url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/all/scoreboard?dates={today}"
    try:
        r = requests.get(url, timeout=20)
        print(f"ESPN Status: {r.status_code}")
        data = r.json()
        events = data.get("events", [])
        real = []
        by_league = Counter()
        for ev in events:
            try:
                if ev.get("competitions"):
                    comp = ev["competitions"][0]
                    lg = comp.get("league", {})
                    league_name = lg.get("name") or lg.get("abbreviation") or "Unknown"
                    if
