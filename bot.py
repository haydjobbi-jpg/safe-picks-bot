"""
Safe Picks Bot — Home-team football match analyzer
Data provider: API-Football (API-Sports), not direct Flashscore scraping.

Setup:
  pip install requests
  macOS/Linux:
    export API_FOOTBALL_KEY="YOUR_API_KEY"
  Windows PowerShell:
    $env:API_FOOTBALL_KEY="YOUR_API_KEY"

Run:
  python safe_picks_bot.py
Optional:
  set DAYS_AHEAD=3   (default 7)
  set MIN_HOME_WIN_PROB=55  (default 55)

Notes:
- "Home team" means the team listed first / playing at home.
- The ranking rule requires the home team to be above the away team in league standings.
- This is a statistical estimate, not a guarantee or betting advice.
"""

import os
import time
from datetime import date, timedelta
from typing import Any, Dict, List, Optional, Tuple

import requests

BASE_URL = "https://v3.football.api-sports.io"
API_KEY = os.getenv("API_FOOTBALL_KEY", "").strip()
DAYS_AHEAD = int(os.getenv("DAYS_AHEAD", "7"))
MIN_HOME_WIN_PROB = float(os.getenv("MIN_HOME_WIN_PROB", "55"))
REQUEST_TIMEOUT = 20

session = requests.Session()
session.headers.update({"x-apisports-key": API_KEY})
_cache: Dict[Tuple[Any, ...], Any] = {}


class APIError(RuntimeError):
    pass


def api_get(endpoint: str, params: dict) -> list:
    """GET an API-Football endpoint and return its response list."""
    cache_key = (endpoint, tuple(sorted(params.items())))
    if cache_key in _cache:
        return _cache[cache_key]

    response = session.get(
        f"{BASE_URL}/{endpoint.lstrip('/')}",
        params=params,
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    payload = response.json()

    errors = payload.get("errors")
    if errors:
        raise APIError(f"API error at {endpoint}: {errors}")

    result = payload.get("response", [])
    _cache[cache_key] = result
    # Small pause to be kinder to API rate limits.
    time.sleep(0.25)
    return result


def get_team_recent(team_id: int, before_date: str, limit: int = 5) -> List[dict]:
    rows = api_get("fixtures", {
        "team": team_id,
        "last": limit,
        "to": before_date,
        "status": "FT",
    })
    finished = []
    for item in rows:
        goals = item.get("goals") or {}
        home_goals, away_goals = goals.get("home"), goals.get("away")
        if home_goals is None or away_goals is None:
            continue
        finished.append({
            "fixture": item,
            "home_goals": home_goals,
            "away_goals": away_goals,
        })
    return finished[-limit:]


def team_form(team_id: int, before_date: str) -> Tuple[float, int, int]:
    """Return recent win percentage, wins, and games sampled."""
    games = get_team_recent(team_id, before_date)
    if not games:
        return 50.0, 0, 0

    wins = 0
    for game in games:
        fixture = game["fixture"]
        is_home = fixture["teams"]["home"]["id"] == team_id
        own = game["home_goals"] if is_home else game["away_goals"]
        opp = game["away_goals"] if is_home else game["home_goals"]
        if own > opp:
            wins += 1

    return (wins / len(games)) * 100.0, wins, len(games)


def head_to_head(home_id: int, away_id: int) -> Tuple[float, int]:
    """Return home team's win percentage in recent H2H games and sample size."""
    rows = api_get("fixtures/headtohead", {
        "h2h": f"{home_id}-{away_id}",
        "last": 5,
        "status": "FT",
    })
    wins = 0
    count = 0
    for item in rows:
        goals = item.get("goals") or {}
        hg, ag = goals.get("home"), goals.get("away")
        if hg is None or ag is None:
            continue
        count += 1
        home_team_id = item["teams"]["home"]["id"]
        home_score = hg if home_team_id == home_id else ag
        away_score = ag if home_team_id == home_id else hg
        if home_score > away_score:
            wins += 1

    # If no H2H data, use a neutral prior rather than inventing results.
    return ((wins / count) * 100.0 if count else 50.0), count


def league_positions(league_id: int, season: int) -> Dict[int, int]:
    rows = api_get("standings", {"league": league_id, "season": season})
    positions: Dict[int, int] = {}
    for item in rows:
        for group in item.get("league", {}).get("standings", []):
            for entry in group:
                team_id = entry.get("team", {}).get("id")
                rank = entry.get("rank")
                if team_id is not None and rank is not None:
                    positions[int(team_id)] = int(rank)
    return positions


def estimate_home_win(
    home_form: float,
    away_form: float,
    h2h_home_win: float,
    home_rank: int,
    away_rank: int,
    home_games: int,
    away_games: int,
    h2h_games: int,
) -> float:
    """
    Transparent heuristic score, NOT a calibrated betting probability.
    Form is weighted most heavily; H2H has less influence due to small samples.
    """
    # Neutral values reduce the impact of missing samples.
    form_difference = home_form - away_form
    h2h_difference = h2h_home_win - 50.0

    # Ranking advantage is bounded so a large league doesn't dominate the score.
    rank_advantage = max(-20.0, min(20.0, (away_rank - home_rank) * 2.0))

    sample_reliability = min(1.0, min(home_games, away_games) / 5.0)
    h2h_reliability = min(1.0, h2h_games / 5.0)

    score = (
        50.0
        + 0.30 * form_difference * sample_reliability
        + 0.15 * h2h_difference * h2h_reliability
        + 0.75 * rank_advantage
        + 5.0  # modest home advantage
    )
    return max(5.0, min(90.0, score))


def analyze_fixture(fixture: dict) -> Optional[dict]:
    teams = fixture.get("teams", {})
    home = teams.get("home", {})
    away = teams.get("away", {})
    league = fixture.get("league", {})
    home_id, away_id = home.get("id"), away.get("id")
    league_id, season = league.get("id"), league.get("season")

    if not all([home_id, away_id, league_id, season]):
        return None

    positions = league_positions(int(league_id), int(season))
    home_rank = positions.get(int(home_id))
    away_rank = positions.get(int(away_id))

    # Enforce the user's condition: home team must rank above the away team.
    if home_rank is None or away_rank is None or home_rank >= away_rank:
        return None

    kickoff = (fixture.get("fixture") or {}).get("date", "")
    before_date = kickoff[:10] or date.today().isoformat()

    home_form, home_wins, home_n = team_form(int(home_id), before_date)
    away_form, away_wins, away_n = team_form(int(away_id), before_date)
    h2h_rate, h2h_n = head_to_head(int(home_id), int(away_id))

    probability = estimate_home_win(
        home_form, away_form, h2h_rate, home_rank, away_rank,
        home_n, away_n, h2h_n,
    )

    # A separate evidence score indicates how complete the underlying sample is.
    evidence = 0
    evidence += 35 if home_n >= 5 else int(35 * home_n / 5)
    evidence += 25 if away_n >= 5 else int(25 * away_n / 5)
    evidence += 20 if h2h_n >= 3 else int(20 * h2h_n / 3)
    evidence += 20  # standings are available, otherwise this candidate was rejected

    return {
        "date": kickoff.replace("T", " ")[:16],
        "league": league.get("name", "Unknown league"),
        "home": home.get("name", "Home"),
        "away": away.get("name", "Away"),
        "home_rank": home_rank,
        "away_rank": away_rank,
        "home_form": round(home_form),
        "away_form": round(away_form),
        "h2h": round(h2h_rate),
        "h2h_n": h2h_n,
        "probability": round(probability),
        "evidence": min(100, evidence),
        "home_wins": home_wins,
        "home_n": home_n,
        "away_wins": away_wins,
        "away_n": away_n,
    }


def main() -> None:
    if not API_KEY:
        print("ERROR: Set the API_FOOTBALL_KEY environment variable first.")
        print("Get an API key from https://www.api-football.com/")
        return

    start = date.today()
    end = start + timedelta(days=max(1, DAYS_AHEAD))
    print(f"Searching fixtures from {start} to {end} ...")

    try:
        fixtures = api_get("fixtures", {
            "from": start.isoformat(),
            "to": end.isoformat(),
            "timezone": "Asia/Qatar",
        })
    except (requests.RequestException, APIError) as exc:
        print(f"Could not fetch fixtures: {exc}")
        return

    picks = []
    seen = set()
    for fixture in fixtures:
        status = ((fixture.get("fixture") or {}).get("status") or {}).get("short")
        if status not in ("NS", "TBD"):
            continue

        fixture_id = (fixture.get("fixture") or {}).get("id")
        if fixture_id in seen:
            continue
        seen.add(fixture_id)

        try:
            result = analyze_fixture(fixture)
            if result and result["probability"] >= MIN_HOME_WIN_PROB:
                picks.append(result)
        except (requests.RequestException, APIError, KeyError, TypeError, ValueError) as exc:
            print(f"Skipping one fixture due to incomplete data: {exc}")

    picks.sort(key=lambda item: (item["probability"], item["evidence"]), reverse=True)
    picks = picks[:10]

    if not picks:
        print("\nNo matches met all conditions.")
        print("Try increasing DAYS_AHEAD or lowering MIN_HOME_WIN_PROB.")
        return

    print("\n" + "=" * 78)
    print("TOP HOME-TEAM PICKS — estimates, not guarantees")
    print("=" * 78)
    for index, item in enumerate(picks, 1):
        print(f"\n{index}. {item['home']} vs {item['away']}")
        print(f"   Kickoff: {item['date']} | {item['league']}")
        print(f"   Estimated home-win score: {item['probability']}%")
        print(f"   League rank: home #{item['home_rank']} | away #{item['away_rank']}")
        print(
            f"   Recent wins: home {item['home_wins']}/{item['home_n']} "
            f"({item['home_form']}%) | away {item['away_wins']}/{item['away_n']} "
            f"({item['away_form']}%)"
        )
        if item["h2h_n"]:
            print(f"   H2H home-team wins: {item['h2h']}% across {item['h2h_n']} games")
        else:
            print("   H2H: no recent data found; neutral value used")
        print(f"   Evidence completeness: {item['evidence']}/100")

    print("\nImportant: the percentage is a heuristic score, not a validated probability.")
    print("Check injuries, lineups, suspensions, and odds before making any decision.")


if __name__ == "__main__":
    main()
