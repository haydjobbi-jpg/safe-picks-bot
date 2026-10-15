import os
import requests
import random
from datetime import datetime, timezone, timedelta

# ========== الإعدادات ==========
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
DOHA = timezone(timedelta(hours=3))

# قاموس قوة الفرق - محترف
TEAM_POWER = {
    # فرق قوية 85-90
    "leverkusen": 90, "milan": 88, "benfica": 87, "real sociedad": 86,
    "bologna": 85, "celtic": 84, "az alkmaar": 83, "lyon": 83,
    "salzburg": 81, "bournemouth": 80, "union": 78, "sunderland": 78,
    # فرق متوسطة 65-75
    "poznan": 65, "sparta": 72, "celje": 68, "omonia": 66,
    "lillestrom": 60, "hapoel": 62, "torreense": 62, "sturm graz": 70
}

def get_power(name):
    n = name.lower()
    for k, v in TEAM_POWER.items():
        if k in n:
            return v
    return 70 # متوسط

def get_today_matches():
    """يجيب ماتشات اليوم - يخدم مع أي عدد"""
    today = datetime.now(DOHA).strftime("%Y%m%d")
    url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/all/scoreboard?dates={today}"
    try:
        data = requests.get(url, timeout=20).json()
        games = []
        for ev in data.get("events", []):
            if ev.get("status", {}).get("type", {}).get("state")!= "pre":
                continue

            comp = ev.get("competitions", [{}])[0]
            competitors = comp.get("competitors", [])
            if len(competitors) < 2:
                continue

            home = competitors[0]["team"]["displayName"]
            away = competitors[1]["team"]["displayName"]
            if competitors[0].get("homeAway") == "away":
                home, away = away, home

            # اسم البطولة - مصحح
            league = "UEFA League"
            if ev.get("leagues") and len(ev["leagues"]) > 0:
                league = ev["leagues"][0].get("name", "UEFA League")

            dt = datetime.fromisoformat(ev["date"].replace("Z", "+00:00")).astimezone(DOHA)

            games.append({
                "home": home,
                "away": away,
                "league": league,
                "time": dt.strftime("%H:%M"),
                "power_h": get_power(home),
                "power_a": get_power(away)
            })
        return games
    except Exception as e:
        print(f"Error: {e}")
        return []

def intelligent_pick(game):
    """تحليل ذكي ومتنوع - موش 1X برك"""
    h, a = game["home"], game["away"]
    ph, pa = game["power_h"], game["power_a"]
    diff = ph - pa
    hl, al = h.lower(), a.lower()

    # حالات خاصة - باش ما يغلطش
    if "poznan" in hl and "leverkusen" in al:
        return "X2 - Leverkusen بطل ألمانيا 90 vs 65", 12
    if "salzburg" in hl and "milan" in al:
        return "X2 - Milan خبرة أوروبية 88 vs 81", 14
    if "union" in hl and "sociedad" in al:
        return "X2 - Real Sociedad أقوى 86 vs 78", 15
    if "hapoel" in al and "alkmaar" in hl:
        return "1W - AZ قوي في دارو 83 vs 62", 12
    if "torreense" in hl and "sunderland" in al:
        return "X2 - Sunderland أقوى 78 vs 62", 13

    # منطق عام حسب الفارق
    if diff >= 18: # المحلي أقوى برشا
        picks = [
            (f"1W - {h} يربح", 12),
            (f"Home Over 1.5 - {h} يمركي برشا", 13),
            (f"Over 1.5 - سيطرة {h}", 14)
        ]
        return random.choice(picks)

    elif diff <= -18: # الضيف أقوى برشا
        picks = [
            (f"X2 - {a} أقوى ({pa} vs {ph})", 12),
            (f"2W - {a} يربح خارج دارو", 13),
            (f"Away Over 0.5 - {a} يمركي", 14)
        ]
        return random.choice(picks)

    elif abs(diff) <= 6: # متقاربين
        picks = [
            (f"Over 1.5 - ماتش متوازن", 17),
            (f"BTTS Yes - الزوز يمركيو", 18),
            (f"Over 0.5 HT - هدف شوط أول", 16),
            (f"Over 2.5 - ماتش مفتوح", 19)
        ]
        return random.choice(picks)

    else: # فارق متوسط
        picks = [
            (f"1X - {h} ما يخسرش في دارو", 15),
            (f"Home Over 0.5 - {h} يمركي", 14),
            (f"Under 3.5 - ماتش تكتيكي", 16),
            (f"1X + Over 1.5 - أمان + أهداف", 15)
        ]
        return random.choice(picks)

def main():
    games = get_today_matches()

    if not games:
        text = f"🔥 {datetime.now(DOHA).strftime('%d/%m')} - ما فماش ماتشات اليوم"
    else:
        random.shuffle(games) # تنوع كل يوم
        text = f"🔥 TOP 10 - {datetime.now(DOHA).strftime('%d/%m %H:%M')} Doha\nمن {len(games)} ماتش اليوم - تحليل محترف:\n\n"

        for i, g in enumerate(games[:10], 1):
            pick, risk = intelligent_pick(g)
            text += f"{i}. {g['home']} vs {g['away']}\n"
            text += f" 🏆 {g['league']} | 🕐 {g['time']} | ⚡ {g['power_h']} vs {g['power_a']}\n"
            text += f" 💡 {pick}\n 📊 ريسك: {risk}%\n\n"

    print(text)

    if BOT_TOKEN and CHAT_ID:
        try:
            requests.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                json={"chat_id": CHAT_ID, "text": text[:4000]},
                timeout=15
            )
            print("✅ تبعث في Telegram")
        except Exception as e:
            print(f"❌ Telegram Error: {e}")

if __name__ == "__main__":
    main()
