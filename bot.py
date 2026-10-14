import requests, os
from datetime import datetime, timedelta

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

def get_league_and_odds(ev):
    comp = ev.get("competitions", [{}])[0]
    league = "League"
    odds = "غير متوفرة"
    try:
        if ev.get("leagues") and len(ev["leagues"])>0:
            league = ev["leagues"][0].get("name") or "League"
        elif ev.get("season", {}).get("name"):
            league = ev["season"]["name"]
        elif comp.get("notes") and len(comp["notes"])>0:
            league = comp["notes"][0].get("headline") or comp["notes"][0].get("text") or "League"
        else:
            league = ev.get("name","League").split(" - ")[0] if ev.get("name") else "League"

        if comp.get("odds") and len(comp["odds"])>0:
            o = comp["odds"][0]
            details = o.get("details","")
            home = o.get("homeTeamOdds",{}).get("price") or ""
            draw = o.get("drawOdds",{}).get("price") or ""
            away = o.get("awayTeamOdds",{}).get("price") or ""
            if home or away:
                odds = f"{home} / {draw} / {away}".strip("
