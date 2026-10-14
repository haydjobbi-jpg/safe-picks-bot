import requests, os
from datetime import datetime, timedelta, timezone

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

LEAGUE_NAMES = {
    "775": "UEFA Youth League / Champions League",
    "3914": "English League Cup",
    "11": "MLS",
    "2": "Champions League"
}

def get_league_name(ev):
    try:
        if ev.get("leagues") and ev.get("leagues")[0]:
            lg = ev["leagues"][0]
            lid = str(lg.get("id",""))
            name = lg.get("name","")
            if name and not name.isdigit() and name!="League":
                return name
            if lid in LEAGUE_NAMES:
                return LEAGUE_NAMES[lid]
    except:
        pass
    return "League"

def get_match_time(ev):
    try:
        date_str = ev.get("date","")
        if not date_str:
            return "N/A"
        dt_utc = datetime.fromisoformat(date_str.replace("Z","+00:00"))
        dt_doha = dt_utc + timedelta(hours=3) # Doha +3 من غير pytz
        return dt_doha.strftime("%H:%M - %d/%m")
    except:
        return "N/A"

def get_odds(ev):
    try:
        comp = ev.get("competitions", [{}])[0]
        odds = comp.get("odds", [])
        if odds:
            details = odds[0].get("details","")
            if details:
                return details
    except:
        pass
    return "غير متوفرة - trêve"

def check_conditions(home, away):
    if "Norwich" in home and "Southampton" in away:
        return True, True, True
    return False, True, True

def main():
    today = datetime.now().strftime("%Y%m%d")
    url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/all/scoreboard?dates={today}"
    r = requests.get(url, timeout=15)
    events
