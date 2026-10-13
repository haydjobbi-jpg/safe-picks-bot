import os, requests
from datetime import datetime, timedelta
from collections import defaultdict

BOT_TOKEN=os.getenv("BOT_TOKEN")
CHAT_ID=os.getenv("CHAT_ID")
API_KEY=os.getenv("API_FOOTBALL_KEY")

def get_data(url):
    try:
        headers={"x-apisports-key": API_KEY}
        r=requests.get(url, headers=headers, timeout=15)
        j=r.json()
        return j.get("response", [])
    except:
        return []

tomorrow = (datetime.utcnow()+timedelta(hours=3)).strftime("%Y-%m-%d")
fixtures = get_data(f"https://v3.football.api-sports.io/fixtures?date={tomorrow}")
print(f"fixtures {len(fixtures)}")

# نعمل cache باش ما نعاودوش نفس البطولة
stand_cache = {}
all_scored = []

# نلوجو كان على أول 200 ماتش
for m in fixtures[:200]:
    try:
        fid = m["fixture"]["id"]
        home_id = m["teams"]["home"]["id"]
        away_id = m["teams"]["away"]["id"]
        league_id = m["league"]["id"]
        season = m["league"]["season"]

        # 1. Top4 - نجيبوها مرة برك لكل بطولة
        if league_id not in stand_cache:
            st = get_data(f"https://v3.football.api-sports.io/standings?league={league_id}&season={season}")
            stand_cache[league_id] = st
        else:
            st = stand_cache[league_id]

        if not st: continue
        try:
            table = st[0]["league"]["standings"][0]
        except: continue

        home_rank = 99
        for t in table:
            if t["team"]["id"] == home_id:
                home_rank = t["rank"]
                break
        if home_rank > 4:
            continue

        # كان وصلنا هنا يعني Top4 موجود ✅
        # تو نكملو الباقي
        last5 = get_data(f"https://v3.football.api-sports.io/fixtures?team={home_id}&last=5")
        wins = 0
        for g in last5:
            if g["teams"]["home"]["id"] == home_id and g["teams"]["home"]["winner"]: wins+=1
            if g["teams"]["away"]["id"] == home_id and g["teams"]["away"]["winner"]: wins+=1

        stats = get_data(f"https://v3.football.api-sports.io/teams/statistics?team={home_id}&league={league_id}&season={season}")
        rate = 0
        try:
            if stats:
                hw = stats[0]["fixtures"]["wins"]["home"]
                hp = stats[0]["fixtures"]["played"]["home"]
                if hp>0: rate = int((hw/hp)*100)
        except: rate = 0

        h2h = get_data(f"https://v3.football.api-sports.io/fixtures/headtohead?h2h={home_id}-{away_id}&last=3")
        h2w = 0
        for g in h2h:
            if g["teams"]["home"]["id"] == home_id and g["teams"]["home"]["winner"]: h2w+=1
            if g["teams"]["away"]["id"] == home_id and g["teams"]["away"]["winner"]: h2w+=1

        odds = get_data(f"https://v3.football.api-sports.io/odds?fixture={fid}")
        has_odd = len(odds) > 0
        odd_val = "1.x"
        try:
            if has_odd:
                odd_val = odds[0]["bookmakers"][0]["bets"][0]["values"][0]["odd"]
        except: pass

        cond = {
            "Top4": True,
            "دار": True,
            "5/5": wins >= 4,
            "90%": rate >= 70,
            "H2H": h2w >= 1,
            "موجود": has_odd
        }
        score = sum(cond.values())

        cond_text = f"✅Top{home_rank} ✅دار {'✅' if wins>=4 else '❌'}{wins}/5 {'✅' if rate>=70 else '❌'}{rate}% {'✅' if h2w>=1 else '❌'}H2H:{h2w} {'✅' if has_odd else '❌'}{'موجود' if has_odd else 'موش'}"
        pick = "W1" if score>=5 else "1X"

        msg_line = f"⚽ {m['league']['name']}\n{m['teams']['home']['name']} vs {m['teams']['away']['name']}\n👉 {pick} @ {odd_val} | Score {score}/6\n{cond_text}\n"
        all_scored.append((score, rate, wins, msg_line))

    except Exception as e:
        continue

all_scored.sort(key=lambda x: (x[0], x[1], x[2]), reverse=True)
top = all_scored[:10]

if top:
    body = "\n".join([t[3] for t in top])
    header = f"🔥 Safe Picks - {tomorrow} ({len(top)}/10) Top4 أساس - {len(fixtures)} ماتش\n\n"
    final_msg = header + body
else:
    final_msg = f"📭 {tomorrow} - فما {len(fixtures)} ماتش اليوم، فحصت {len(stand_cache)} بطولة، لقيت 0 في Top4 يلعبو في الدار (API quota يمكن خلص)"

requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", data={"chat_id": CHAT_ID, "text": final_msg[:4000]})
