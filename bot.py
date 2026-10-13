import os, requests
from datetime import datetime, timedelta

BOT_TOKEN=os.getenv("BOT_TOKEN")
CHAT_ID=os.getenv("CHAT_ID")
API_KEY=os.getenv("API_FOOTBALL_KEY")

def get_data(url):
    try:
        headers={"x-apisports-key": API_KEY}
        r=requests.get(url, headers=headers, timeout=20)
        j=r.json()
        return j.get("response", [])
    except:
        return []

tomorrow = (datetime.utcnow()+timedelta(hours=3)).strftime("%Y-%m-%d")
fixtures = get_data(f"https://v3.football.api-sports.io/fixtures?date={tomorrow}")

all_scored = []

for m in fixtures[:120]:
    try:
        fid = m["fixture"]["id"]
        home_id = m["teams"]["home"]["id"]
        away_id = m["teams"]["away"]["id"]
        league_id = m["league"]["id"]
        season = m["league"]["season"]

        cond = {}
        details = {}

        # 1. شرط أساسي Top4
        standings = get_data(f"https://v3.football.api-sports.io/standings?league={league_id}&season={season}")
        if not standings: continue
        table = standings[0]["league"]["standings"][0]
        home_rank = 99
        for t in table:
            if t["team"]["id"] == home_id:
                home_rank = t["rank"]
                break
        cond["Top4"] = home_rank <= 4
        details["Top4"] = f"Top{home_rank}"
        if not cond["Top4"]:
            continue

        cond["دار"] = True
        details["دار"] = "دار"

        last5 = get_data(f"https://v3.football.api-sports.io/fixtures?team={home_id}&last=5")
        wins = 0
        for g in last5:
            if g["teams"]["home"]["id"] == home_id and g["teams"]["home"]["winner"]: wins+=1
            if g["teams"]["away"]["id"] == home_id and g["teams"]["away"]["winner"]: wins+=1
        cond["5/5"] = wins >= 4
        details["5/5"] = f"{wins}/5"

        stats = get_data(f"https://v3.football.api-sports.io/teams/statistics?team={home_id}&league={league_id}&season={season}")
        rate = 0
        try:
            if stats:
                hw = stats[0]["fixtures"]["wins"]["home"]
                hp = stats[0]["fixtures"]["played"]["home"]
                if hp>0: rate = int((hw/hp)*100)
        except: rate = 0
        cond["90%"] = rate >= 75
        details["90%"] = f"{rate}% دار"

        h2h = get_data(f"https://v3.football.api-sports.io/fixtures/headtohead?h2h={home_id}-{away_id}&last=3")
        h2w = 0
        for g in h2h:
            if g["teams"]["home"]["id"] == home_id and g["teams"]["home"]["winner"]: h2w+=1
            if g["teams"]["away"]["id"] == home_id and g["teams"]["away"]["winner"]: h2w+=1
        cond["H2H"] = h2w >= 1
        details["H2H"] = f"H2H:{h2w}"

        odds = get_data(f"https://v3.football.api-sports.io/odds?fixture={fid}")
        has_odd = len(odds) > 0
        odd_val = "1.x"
        try:
            if has_odd:
                odd_val = odds[0]["bookmakers"][0]["bets"][0]["values"][0]["odd"]
        except: pass
        cond["موجود"] = has_odd
        details["موجود"] = "موجود" if has_odd else "موش موجود"

        score = sum(cond.values())
        pick = "W1" if score >=5 and rate>=75 else "1X"

        cond_text = ""
        for k in ["Top4","دار","5/5","90%","H2H","موجود"]:
            icon = "✅" if cond[k] else "❌"
            cond_text += f"{icon}{details[k]} "

        msg_line = f"⚽ {m['league']['name']}\n{m['teams']['home']['name']} vs {m['teams']['away']['name']}\n👉 {pick} @ {odd_val} | Score {score}/6\n{cond_text}\n"
        all_scored.append((score, rate, wins, msg_line))
    except: continue

all_scored.sort(key=lambda x: (x[0], x[1], x[2]), reverse=True)
top = all_scored[:10]

if top:
    body = "\n".join([t[3] for t in top])
    header = f"🔥 Safe Picks - {tomorrow} ({len(top)}/10)\nالشرط الأساسي Top4\n\n"
    final_msg = header + body
else:
    final_msg = f"📭 {tomorrow} - اليوم {len(fixtures)} ماتش، حتى واحد ما فيه Top4"

requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", data={"chat_id": CHAT_ID, "text": final_msg[:4000]})
