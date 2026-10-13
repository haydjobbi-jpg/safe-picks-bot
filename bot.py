import os, requests
from datetime import datetime, timedelta

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
API_KEY = os.getenv("API_FOOTBALL_KEY")

def get_data(url):
    try:
        r = requests.get(url, headers={"x-apisports-key": API_KEY}, timeout=15)
        return r.json().get("response", [])
    except:
        return []

# تاريخ اليوم بتوقيت الدوحة
tomorrow = (datetime.utcnow() + timedelta(hours=3)).strftime("%Y-%m-%d")
fixtures = get_data(f"https://v3.football.api-sports.io/fixtures?date={tomorrow}")

stand_cache = {}
picks = {6: [], 5: [], 4: [], 3: [], 2: [], 1: []}

for m in fixtures[:200]:
    try:
        fid = m["fixture"]["id"]
        home_id = m["teams"]["home"]["id"]
        away_id = m["teams"]["away"]["id"]
        league_id = m["league"]["id"]
        season = m["league"]["season"]

        # --- الشرط الأساسي: Top4 ---
        if league_id not in stand_cache:
            stand_cache[league_id] = get_data(
                f"https://v3.football.api-sports.io/standings?league={league_id}&season={season}"
            )
        st = stand_cache[league_id]
        if not st: continue
        try: table = st[0]["league"]["standings"][0]
        except: continue

        rank = 99
        for t in table:
            if t["team"]["id"] == home_id:
                rank = t["rank"]
                break
        if rank > 4: # موش Top4 -> نتعداه
            continue

        # --- باقي الشروط ---
        last5 = get_data(f"https://v3.football.api-sports.io/fixtures?team={home_id}&last=5")
        wins = 0
        for g in last5:
            if g["teams"]["home"]["id"] == home_id and g["teams"]["home"]["winner"]: wins += 1
            if g["teams"]["away"]["id"] == home_id and g["teams"]["away"]["winner"]: wins += 1

        stats = get_data(f"https://v3.football.api-sports.io/teams/statistics?team={home_id}&league={league_id}&season={season}")
        rate = 0
        try:
            if stats:
                hw = stats[0]["fixtures"]["wins"]["home"]
                hp = stats[0]["fixtures"]["played"]["home"]
                if hp > 0: rate = int((hw/hp)*100)
        except: pass

        h2h = get_data(f"https://v3.football.api-sports.io/fixtures/headtohead?h2h={home_id}-{away_id}&last=3")
        h2w = 0
        for g in h2h:
            if g["teams"]["home"]["id"] == home_id and g["teams"]["home"]["winner"]: h2w += 1
            if g["teams"]["away"]["id"] == home_id and g["teams"]["away"]["winner"]: h2w += 1

        odds = get_data(f"https://v3.football.api-sports.io/odds?fixture={fid}")
        has_odd = len(odds) > 0
        odd_val = "1.x"
        try:
            if has_odd: odd_val = odds[0]["bookmakers"][0]["bets"][0]["values"][0]["odd"]
        except: pass

        # --- حساب Score ---
        score = 2 # Top4 + دار ديما 2
        txt = f"✅Top{rank} ✅دار "
        if wins >= 4: txt += f"✅{wins}/5 "; score += 1
        else: txt += f"❌{wins}/5 "
        if rate >= 70: txt += f"✅{rate}% "; score += 1
        else: txt += f"❌{rate}% "
        if h2w >= 1: txt += f"✅H2H:{h2w} "; score += 1
        else: txt += f"❌H2H:{h2w} "
        if has_odd: txt += f"✅موجود"; score += 1
        else: txt += f"❌موش"

        pick = "W1" if score >= 5 else "1X"
        line = f"⚽ {m['league']['name']}\n{m['teams']['home']['name']} vs {m['teams']['away']['name']}\n👉 {pick} @ {odd_val} | Score {score}/6\n{txt}\n"

        picks[score].append((rate, wins, line))
    except:
        continue

# --- نلوج من 6 لـ 1: أول سكور موجود نبعثوه ---
final = []
best_score = 0
for s in [6,5,4,3,2,1]:
    if picks[s]:
        picks[s].sort(key=lambda x: (x[0], x[1]), reverse=True)
        final = [x[2] for x in picks[s][:10]]
        best_score = s
        break

if final:
    body = "\n".join(final)
    header = f"🔥 Safe Picks - {tomorrow} | أفضل موجود Score {best_score}/6\nالشرط الأساسي Top4 + نهبطو من 6 لـ 1\nفحصت {len(fixtures)} ماتش / {len(stand_cache)} بطولة\n\n"
    msg = header + body
else:
    msg = f"📭 {tomorrow} - فما {len(fixtures)} ماتش، فحصت {len(stand_cache)} بطولة، 0 Top4 يلعب في الدار\n(Quota خلص اليوم، يرجع غدوة 00:00 UTC)"

requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", data={"chat_id": CHAT_ID, "text": msg[:4000]})
