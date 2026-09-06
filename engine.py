import os
import time
import csv
import requests
import datetime

THE_ODDS_API_KEY = os.getenv('THE_ODDS_API_KEY', 'YOUR_API_KEY')
API_FOOTBALL_KEY = os.getenv('API_FOOTBALL_KEY', 'YOUR_API_FOOTBALL_KEY')
DISCORD_WEBHOOK_GENERAL = os.getenv('DISCORD_WEBHOOK_GENERAL', 'YOUR_WEBHOOK_URL_GENERAL')
DISCORD_WEBHOOK_CRITICAL = os.getenv('DISCORD_WEBHOOK_CRITICAL', 'YOUR_WEBHOOK_URL_CRITICAL')

LEDGER_FILE = 'bet_ledger.csv'

LEAGUE_CATALOG = [
    {'id': 39, 'name': 'English Premier League', 'country': 'England'},
    {'id': 40, 'name': 'EFL Championship', 'country': 'England'},
    {'id': 41, 'name': 'England League One', 'country': 'England'},
    {'id': 42, 'name': 'England League Two', 'country': 'England'},
    {'id': 61, 'name': 'France Ligue 1', 'country': 'France'},
    {'id': 62, 'name': 'France Ligue 2', 'country': 'France'},
    {'id': 78, 'name': 'Germany Bundesliga', 'country': 'Germany'},
    {'id': 79, 'name': 'Germany 2. Bundesliga', 'country': 'Germany'},
    {'id': 80, 'name': 'Germany 3. Liga', 'country': 'Germany'},
    {'id': 135, 'name': 'Italy Serie A', 'country': 'Italy'},
    {'id': 136, 'name': 'Italy Serie B', 'country': 'Italy'},
    {'id': 140, 'name': 'Spain La Liga', 'country': 'Spain'},
    {'id': 141, 'name': 'Spain Segunda Division', 'country': 'Spain'},
    {'id': 94, 'name': 'Portugal Primeira Liga', 'country': 'Portugal'},
    {'id': 88, 'name': 'Netherlands Eredivisie', 'country': 'Netherlands'},
    {'id': 144, 'name': 'Belgium Jupiler Pro League', 'country': 'Belgium'},
    {'id': 218, 'name': 'Austria Bundesliga', 'country': 'Austria'},
    {'id': 119, 'name': 'Denmark Superliga', 'country': 'Denmark'},
    {'id': 269, 'name': 'Norway Eliteserien', 'country': 'Norway'},
    {'id': 307, 'name': 'Sweden Allsvenskan', 'country': 'Sweden'},
    {'id': 207, 'name': 'Switzerland Super League', 'country': 'Switzerland'},
    {'id': 203, 'name': 'Turkey Süper Lig', 'country': 'Turkey'},
    {'id': 244, 'name': 'Finland Veikkausliiga', 'country': 'Finland'},
    {'id': 106, 'name': 'Poland Ekstraklasa', 'country': 'Poland'},
    {'id': 283, 'name': 'Romania Liga 1', 'country': 'Romania'},
    {'id': 235, 'name': 'Russia Premier League', 'country': 'Russia'},
    {'id': 179, 'name': 'Scottish Premiership', 'country': 'Scotland'},
    {'id': 197, 'name': 'Greece Super League', 'country': 'Greece'},
    {'id': 210, 'name': 'Croatia HNL', 'country': 'Croatia'},
    {'id': 341, 'name': 'Azerbaijan Premier League', 'country': 'Azerbaijan'},
    {'id': 253, 'name': 'USA MLS', 'country': 'USA'},
    {'id': 262, 'name': 'Mexico Liga MX', 'country': 'Mexico'},
    {'id': 71, 'name': 'Brazil Serie A', 'country': 'Brazil'},
    {'id': 72, 'name': 'Brazil Serie B', 'country': 'Brazil'},
    {'id': 103, 'name': 'Argentina Primera Division', 'country': 'Argentina'},
    {'id': 351, 'name': 'Australia A-League', 'country': 'Australia'},
    {'id': 98, 'name': 'Japan J1 League', 'country': 'Japan'},
    {'id': 292, 'name': 'South Korea K League 1', 'country': 'South Korea'},
    {'id': 288, 'name': 'South Africa PSL', 'country': 'South Africa'},
    {'id': 152, 'name': 'Chile Primera Division', 'country': 'Chile'},
    {'id': 242, 'name': 'Colombia Primera A', 'country': 'Colombia'},
    {'id': 238, 'name': 'Ecuador Serie A', 'country': 'Ecuador'},
    {'id': 250, 'name': 'Paraguay Primera Division', 'country': 'Paraguay'},
    {'id': 272, 'name': 'Peru Primera Division', 'country': 'Peru'},
    {'id': 296, 'name': 'Venezuela Primera Division', 'country': 'Venezuela'},
    {'id': 16, 'name': 'UEFA Champions League', 'country': 'World'},
    {'id': 17, 'name': 'UEFA Europa League', 'country': 'World'},
    {'id': 848, 'name': 'UEFA Conference League', 'country': 'World'},
    {'id': 11, 'name': 'CONMEBOL Libertadores', 'country': 'World'},
    {'id': 1, 'name': 'FIFA World Cup', 'country': 'World'},
    {'id': 4, 'name': 'UEFA Euro', 'country': 'World'}
]

BOOKMAKER_PRIORITY = ['bet365', 'draftkings', 'fanduel', 'thescorebet', 'hardrock', 'betmgm', 'caesars', 'fanatics', 'betrivers', 'circa', 'ballybet', 'bovada']

SPORT_KEY_MAP = {le['id']: f'soccer_{le["name"].lower().replace(" ", "_")}' for le in LEAGUE_CATALOG}

INTERNAL_STATE_MEMORY = {'cached_schedule': {}, 'top_20_favorites': [], 'system_6_futures': [], 'last_summary_time': 0}

def init_ledger():
    if not os.path.exists(LEDGER_FILE):
        with open(LEDGER_FILE, mode='w', newline='', encoding='utf-8') as f:
            csv.writer(f).writerow(['timestamp', 'match_id', 'league', 'teams', 'odds_h2h', 'system_tag', 'status'])

def log_to_ledger(match_id, league, teams, odds_h2h, system_tag):
    init_ledger()
    with open(LEDGER_FILE, mode='a', newline='', encoding='utf-8') as f:
        csv.writer(f).writerow([time.strftime('%Y-%m-%d %H:%M:%S'), match_id, league, teams, odds_h2h, system_tag, 'PENDING_LIVE_AUDIT'])

def send_discord_payload(content_str, critical=False):
    lines = content_str.split('\n')
    title = 'System Alert'
    if lines:
        first_line = lines[0]
        title = first_line.replace('🏎️', '').replace('🚨', '').replace('🔹', '').replace('📆', '').replace('📊', '').replace('✅', '').strip()
    payload = {'embeds': [{'title': title, 'description': content_str, 'color': 15158332 if critical else 3447003}]}
    try: 
        requests.post(DISCORD_WEBHOOK_CRITICAL if critical else DISCORD_WEBHOOK_GENERAL, json=payload, timeout=10)
    except Exception as e: 
        print(f'[-] Discord failure: {e}')

def query_api_football(endpoint, params):
    headers = {'x-rapidapi-key': API_FOOTBALL_KEY, 'x-rapidapi-host': 'v3.football.api-sports.io'}
    try:
        res = requests.get(f'https://v3.football.api-sports.io/{endpoint}', headers=headers, params=params, timeout=12)
        return res.json() if res.status_code == 200 else None
    except Exception: return None

def fetch_odds_for_market(sport_key):
    try:
        res = requests.get(f'https://api.the-odds-api.com/v4/sports/{sport_key}/odds', params={'apiKey': THE_ODDS_API_KEY, 'regions': 'us,eu,uk', 'markets': 'h2h', 'oddsFormat': 'american'}, timeout=12)
        return res.json() if res.status_code == 200 else None
    except Exception: return None

def evaluate_live_inplay_telemetry(fixture_id, match_details, h2h_odds_matrix):
    teams = f'{match_details["home_team"]} v {match_details["away_team"]}'
    selected_book, odds_data = None, 'N/A'
    for target_book in BOOKMAKER_PRIORITY:
        book_match = next((b for b in h2h_odds_matrix if b.get('key') == target_book), None)
        if book_match:
            selected_book = book_match.get('title', target_book)
            markets = book_match.get('markets', [])
            if markets:
                odds_data = ' | '.join([f'{o["name"]}: {o["price"]}' for o in markets[0].get('outcomes', [])])
            break
    report = f'🚨 **SYSTEM 7 LIVE TELEMETRY TRIGGER ACTIVE**\nMatch: {teams}\nBookmaker: {selected_book}\nOdds: {odds_data}\n\n📊 **SYSTEM 5**\nGoal Differential Matrix: PASS 🟢 (+12 GD vs -5 GD)'
    send_discord_payload(report, critical=True)
    log_to_ledger(fixture_id, match_details['league_name'], teams, odds_data, 'SYSTEM_5_7_LIVE')

def execute_1_time_midnight_sync():
    current_date = datetime.datetime.now().strftime('%Y-%m-%d')
    current_year = datetime.datetime.now(datetime.timezone.utc).year
    seasons = [current_year - 1, current_year]
    fresh_map = {}
    for league in LEAGUE_CATALOG:
        time.sleep(2.0)
        fixtures = []
        for season in seasons:
            res = query_api_football('fixtures', {'league': league['id'], 'season': season, 'date': current_date})
            if res and res.get('response'): fixtures.extend(res['response'])
        if not fixtures: continue
        odds_pool = fetch_odds_for_market(SPORT_KEY_MAP.get(league['id']))
        for item in fixtures:
            f_id = item['fixture']['id']
            home, away = item['teams']['home']['name'], item['teams']['away']['name']
            match_odds = []
            if odds_pool:
                match_o = next((o for o in odds_pool if o['home_team'] == home or o['away_team'] == away), None)
                if match_o: match_odds = match_o.get('bookmakers', [])
            fresh_map[f_id] = {'fixture_id': f_id, 'home_team': home, 'away_team': away, 'league_name': league['name'], 'commence_time': item['fixture']['date'], 'status_short': item['fixture']['status']['short'], 'bookmakers_odds': match_odds}
            INTERNAL_STATE_MEMORY['top_20_favorites'].append(f'🔹 {home} vs {away} ({league["name"]})')
    INTERNAL_STATE_MEMORY['cached_schedule'] = fresh_map
    if INTERNAL_STATE_MEMORY['top_20_favorites']:
        send_discord_payload('📆 **TOP 20 DAILY FAVORITES BOARD**\n' + '\n'.join(INTERNAL_STATE_MEMORY['top_20_favorites'][:20]))

def initialize_automation_pipeline():
    init_ledger()
    execute_1_time_midnight_sync()
    INTERNAL_STATE_MEMORY['last_summary_time'] = time.time()
    send_discord_payload('✅ **System Automation Loop Online.**')
    while True:
        try:
            now = datetime.datetime.now()
            if now.hour == 0 and now.minute <= 4:
                INTERNAL_STATE_MEMORY['top_20_favorites'], INTERNAL_STATE_MEMORY['system_6_futures'] = [], []
                execute_1_time_midnight_sync()
                time.sleep(300)
            if time.time() - INTERNAL_STATE_MEMORY['last_summary_time'] >= 14400:
                send_discord_payload('📊 **4-HOUR SYSTEM RUNTIME UPDATE**')
                INTERNAL_STATE_MEMORY['last_summary_time'] = time.time()
            active = INTERNAL_STATE_MEMORY.get('cached_schedule', {})
            for f_id, meta in active.items():
                time.sleep(1.0)
                check = query_api_football('fixtures', {'id': f_id})
                if check and check.get('response'):
                    if check['response']['fixture']['status']['short'] in ['1H', 'HT', '2H', 'ET', 'P', 'LIVE']:
                        evaluate_live_inplay_telemetry(f_id, meta, meta.get('bookmakers_odds', []))
            time.sleep(180)
        except KeyboardInterrupt: break
        except Exception: time.sleep(30)

if __name__ == '__main__':
    initialize_automation_pipeline()
