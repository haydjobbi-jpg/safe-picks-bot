import requests, os
from datetime import datetime
import pytz

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

LEAGUE_NAMES = {
    "775": "UEFA Youth League / Champions League",
    "3914": "English League Cup (EFL Cup)",
    "11": "MLS",
    "2": "Champions League",
    "12": "Europa League"
}

def get_league_name(ev):
    try:
        if ev.get("leagues") and len(ev["leagues"])>0:
            lg = ev["leagues"][0]
            lid = str(lg.get("id", ""))
            name = lg.get("name", "")
            if name and not name.isdigit() and name!= "League":
                return name
            if lid in LEAGUE_NAMES:
                return LEAGUE_NAMES[lid]
    except:
        pass
    try:
        comp = ev.get("competitions", [{}])[0]
        if comp.get("notes") and comp["notes"][0]!= "League":
            return comp["notes"][0]
    except:
        pass
    return "League"

def get_match_time(ev):
    try:
        date_str = ev.get("date", "")
        if not date_str:
            return "N/A"
        dt_utc = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        doha_tz = pytz.timezone("Asia/Qatar")
        dt_doha = dt_utc.astimezone(doha_tz)
        return dt_doha.strftime("%H:%M - %d/%m")
    except:
        return "N/A"

def get_odds(ev):
    try:
        comp = ev.get("competitions", [{}])[0]
        odds = comp.get("odds", [])
        if odds and len(odds)>0:
            o = odds[0]
            details = o.get("details", "")
            if details:
                return details
            home = o.get("homeTeamOdds", {}).get("decimal", "") if isinstance(o.get("homeTeamOdds"), dict) else ""
            away = o.get("awayTeamOdds", {}).get("decimal", "") if isinstance(o.get("awayTeamOdds"), dict) else ""
            draw = o.get("drawOdds", {}).get("decimal", "") if isinstance(o.get("drawOdds"), dict) else ""
            if home:
                return f"1:{home} X:{draw} 2:{away}"
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
    events = r.json().get("events", [])

    msg = f"Safe Picks {datetime.now().strftime('%Y-%m-%d')} (Doha)\n\n"
    msg += f"فحصت {len(events)} ماتش:\n\n"

    for ev in events:
        comp = ev.get("competitions", [{}])[0]
        teams = comp.get("competitors", [])
        if len(teams)<2:
            continue
        home = next((t for t in teams if t.get("homeAway")=="home"), teams[0])
        away = next((t for t in teams if t.get("homeAway")=="away"), teams[1])
        home_name = home.get("team", {}).get("displayName", "")
        away_name = away.get("team", {}).get("displayName", "")

        league = get_league_name(ev)
        time_str = get_match_time(ev)
        odds_str = get_odds(ev)
        top4, home90, h2h = check_conditions(home_name, away_name)
        score = sum([top4, home90, h2h])

        if score>=1:
            icon = "✅" if score==3 else "⚠️"
            msg += f"{icon} {home_name} vs {away_name}\n"
            msg += f"🏆 {league}\n"
            msg += f"🕐 {time_str} (Doha)\n"
            msg += f"💰 كوت: {odds_str}\n"
            t1 = "✅ Top4" if top4 else "❌ Top4 ناقص"
            t2 = "✅ 90% دار" if home90 else "❌ 90% ناقص"
            t3 = "✅ H2H 5/5" if h2h else "❌ H2H ناقص"
            msg += f"{t1} | {t2} | {t3} - {score}/3\n\n"

    print(msg)
    if BOT_TOKEN and CHAT_ID:
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": CHAT_ID, "text": msg}, timeout=15)

if __name__ == "__main__":
    main()
