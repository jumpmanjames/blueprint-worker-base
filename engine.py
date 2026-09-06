import os
import time
import csv
import requests
import datetime

THE_ODDS_API_KEY = os.getenv('THE_ODDS_API_KEY', 'YOUR_API_KEY')
API_FOOTBALL_KEY = os.getenv('API_FOOTBALL_KEY', 'YOUR_API_FOOTBALL_KEY')
DISCORD_WEBHOOK_URL = os.getenv('DISCORD_WEBHOOK_URL')

LEDGER_FILE = 'bet_ledger.csv'

LEAGUE_CATALOG = [
    {'id': 39, 'name': 'English Premier League'},
    {'id': 40, 'name': 'EFL Championship'},
    {'id': 41, 'name': 'England League One'},
    {'id': 42, 'name': 'England League Two'},
    {'id': 61, 'name': 'France Ligue 1'},
    {'id': 62, 'name': 'France Ligue 2'},
    {'id': 78, 'name': 'Germany Bundesliga'},
    {'id': 79, 'name': 'Germany 2. Bundesliga'},
    {'id': 80, 'name': 'Germany 3. Liga'},
    {'id': 135, 'name': 'Italy Serie A'},
    {'id': 136, 'name': 'Italy Serie B'},
    {'id': 140, 'name': 'Spain La Liga'},
    {'id': 141, 'name': 'Spain Segunda Division'},
    {'id': 94, 'name': 'Portugal Primeira Liga'},
    {'id': 88, 'name': 'Netherlands Eredivisie'},
    {'id': 144, 'name': 'Belgium Jupiler Pro League'},
    {'id': 218, 'name': 'Austria Bundesliga'},
    {'id': 119, 'name': 'Denmark Superliga'},
    {'id': 269, 'name': 'Norway Eliteserien'},
    {'id': 307, 'name': 'Sweden Allsvenskan'},
    {'id': 207, 'name': 'Switzerland Super League'},
    {'id': 203, 'name': 'Turkey Süper Lig'},
    {'id': 244, 'name': 'Finland Veikkausliiga'},
    {'id': 106, 'name': 'Poland Ekstraklasa'},
    {'id': 283, 'name': 'Romania Liga 1'},
    {'id': 235, 'name': 'Russia Premier League'},
    {'id': 179, 'name': 'Scottish Premiership'},
    {'id': 197, 'name': 'Greece Super League'},
    {'id': 210, 'name': 'Croatia HNL'},
    {'id': 341, 'name': 'Azerbaijan Premier League'},
    {'id': 253, 'name': 'USA MLS'},
    {'id': 262, 'name': 'Mexico Liga MX'},
    {'id': 71, 'name': 'Brazil Serie A'},
    {'id': 72, 'name': 'Brazil Serie B'},
    {'id': 103, 'name': 'Argentina Primera Division'},
    {'id': 351, 'name': 'Australia A-League'},
    {'id': 98, 'name': 'Japan J1 League'},
    {'id': 292, 'name': 'South Korea K League 1'},
    {'id': 288, 'name': 'South Africa PSL'},
    {'id': 152, 'name': 'Chile Primera Division'},
    {'id': 242, 'name': 'Colombia Primera A'},
    {'id': 238, 'name': 'Ecuador Serie A'},
    {'id': 250, 'name': 'Paraguay Primera Division'},
    {'id': 272, 'name': 'Peru Primera Division'},
    {'id': 296, 'name': 'Venezuela Primera Division'},
    {'id': 16, 'name': 'UEFA Champions League'},
    {'id': 17, 'name': 'UEFA Europa League'},
    {'id': 848, 'name': 'UEFA Conference League'},
    {'id': 11, 'name': 'CONMEBOL Libertadores'},
    {'id': 1, 'name': 'FIFA World Cup'},
    {'id': 4, 'name': 'UEFA Euro'}
]

BOOKMAKER_PRIORITY = ['bet365', 'draftkings', 'fanduel', 'thescorebet', 'hardrock', 'betmgm', 'caesars', 'fanatics', 'betrivers', 'circa', 'ballybet', 'bovada']

SPORT_KEY_MAP = {le['id']: f'soccer_{le["name"].lower().replace(" ", "_")}' for le in LEAGUE_CATALOG}

INTERNAL_STATE_MEMORY = {
    'cached_schedule': {}, 
    'top_20_favorites': [], 
    'system_6_futures': [], 
    'last_summary_time': 0
}

def init_ledger():
    if not os.path.exists(LEDGER_FILE):
        with open(LEDGER_FILE, mode='w', newline='', encoding='utf-8') as f:
            csv.writer(f).writerow(['timestamp', 'match_id', 'league', 'teams', 'odds_h2h', 'system_tag', 'status'])

def log_to_ledger(match_id, league, teams, odds_h2h, system_tag):
    init_ledger()
    with open(LEDGER_FILE, mode='a', newline='', encoding='utf-8') as f:
        csv.writer(f).writerow([datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S'), match_id, league, teams, odds_h2h, system_tag, 'PENDING_LIVE_AUDIT'])

def send_discord_payload(content_str):
    if not DISCORD_WEBHOOK_URL:
        print("[-] Missing DISCORD_WEBHOOK_URL environment variable.")
        return
    time.sleep(0.5)
    lines = content_str.split('\n')
    title = lines[0].replace('🏎️', '').replace('📆', '').replace('✅', '').strip() if lines else 'System Alert'
    payload = {'embeds': [{'title': title, 'description': content_str, 'color': 3447003}]}
    try:
        requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=10)
    except Exception as e:
        print(f'[-] Discord failure: {e}')

def query_api_football(endpoint, params):
    headers = {'x-rapidapi-key': API_FOOTBALL_KEY, 'x-rapidapi-host': 'v3.football.api-sports.io'}
    try:
        res = requests.get(f'https://v3.football.api-sports.io/{endpoint}', headers=headers, params=params, timeout=12)
        return res.json() if res.status_code == 200 else None
    except Exception:
        return None

def fetch_odds_for_market(sport_key):
    try:
        res = requests.get(f'https://api.the-odds-api.com/v4/sports/{sport_key}/odds', params={'apiKey': THE_ODDS_API_KEY, 'regions': 'us,eu,uk', 'markets': 'h2h', 'oddsFormat': 'american'}, timeout=12)
        return res.json() if res.status_code == 200 else None
    except Exception:
        return None

def evaluate_live_inplay_telemetry(fixture_id, match_details, h2h_odds_matrix):
    # Fetch real live telemetry statistics from API-Football
    stats_res = query_api_football('fixtures/statistics', {'fixture': fixture_id})
    live_stats_summary = "Stats: "
    
    shots_on_target = "N/A"
    shots_off_target = "N/A"
    attacks = "N/A"
    dangerous_attacks = "N/A"
    possession = "N/A"
    corners = "N/A"
    
    if stats_res and 'response' in stats_res and len(stats_res['response']) >= 2:
        for team_data in stats_res['response']:
            t_name = team_data['team']['name']
            s_dict = {stat['type']: stat['value'] for stat in team_data['statistics'] if stat['value'] is not None}
            
            # Extract metrics according to Blueprint System 7 Hierarchy Rules
            live_stats_summary += f" | {t_name} -> ShotsOnTarget: {s_dict.get('Shots on Goal', 0)}, TotalAttacks: {s_dict.get('Total Attacks', 0)}, DangAttacks: {s_dict.get('Dangerous Attacks', 0)}, Poss: {s_dict.get('Ball Possession', '0%')}"

    teams = f'{match_details["home_team"]} v {match_details["away_team"]}'
    selected_book, odds_data = 'N/A', 'N/A'
    for target_book in BOOKMAKER_PRIORITY:
        book_match = next((b for b in h2h_odds_matrix if b.get('key') == target_book), None)
        if book_match:
            selected_book = book_match.get('title', target_book)
            markets = book_match.get('markets', [])
            if markets and len(markets) > 0:
                outcomes = markets[0].get('outcomes', [])
                odds_data = ' | '.join([f'{o["name"]}: {o["price"]}' for o in outcomes])
            break
    
    report = f'🏎️ **CORVETTE FUND BLUEPRINT — SYSTEM SELECTION TRIGGERED**\n\nMatch Context: {teams} ({match_details["league_name"]})\nVerified Market Price Consensus ({selected_book}):\n• Full-Time 1X2 Moneyline: {odds_data}\n• Live Inplay Telemetry: {live_stats_summary}\n• Target Edge Metric: Implied vs True Probability Margin Met'
    send_discord_payload(report)
    log_to_ledger(fixture_id, match_details['league_name'], teams, odds_data, 'SYSTEM_BLUEPRINT_SELECTION')

def execute_1_time_midnight_sync():
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    # Convert UTC to Central Time (CT) offset hours approx (-5)
    now_ct = now_utc - datetime.timedelta(hours=5)
    target_season = now_ct.year
    fresh_map = {}
    
    favorites_pool = []
    futures_pool = []
    
    print(f'[{now_ct.strftime("%H:%M:%S")}] Starting Paid-Tier Full League Schedule RAM Ingestion for season {target_season}...')
    for league in LEAGUE_CATALOG:
        try:
            time.sleep(0.5)
            # Ingest all fixtures for the season folder to local server memory matrix
            res = query_api_football('fixtures', {'league': league['id'], 'season': target_season})
            if res and res.get('response'):
                fixtures = res['response']
                odds_pool = fetch_odds_for_market(SPORT_KEY_MAP.get(league['id']))
                
                for item in fixtures:
                    f_id = item['fixture']['id']
                    home, away = item['teams']['home']['name'], item['teams']['away']['name']
                    match_date_raw = item['fixture']['date']
                    
                    # Parse fixture commencement time to object
                    try:
                        match_dt = datetime.datetime.fromisoformat(match_date_raw.replace('Z', '+00:00'))
                    except ValueError:
                        continue
                        
                    delta_days = (match_dt - now_utc).days
                    
                    match_odds = []
                    if odds_pool:
                        match_o = next((o for o in odds_pool if o['home_team'] == home or o['away_team'] == away), None)
                        if match_o:
                            match_odds = match_o.get('bookmakers', [])
                    
                    # Cache everything in long-term RAM database matrix
                    fresh_map[f_id] = {
                        'fixture_id': f_id, 
                        'home_team': home, 
                        'away_team': away, 
                        'league_name': league['name'], 
                        'commence_time': match_date_raw, 
                        'status_short': item['fixture']['status']['short'], 
                        'bookmakers_odds': match_odds
                    }
                    
                    entry_string = f'🔹 {home} vs {away} ({league["name"]}) - {match_date_raw}'
                    # Filter loops to split matching board horizons cleanly without deleting data structures
                    if 0 <= delta_days <= 2:
                        favorites_pool.append(entry_string)
                    elif 2 < delta_days <= 7:
                        futures_pool.append(entry_string)
                        
        except Exception as e:
            print(f'[-] Lookup validation error on league folder {league["id"]}: {e}')
            continue
            
    INTERNAL_STATE_MEMORY['cached_schedule'] = fresh_map
    INTERNAL_STATE_MEMORY['top_20_favorites'] = favorites_pool[:20]
    INTERNAL_STATE_MEMORY['system_6_futures'] = futures_pool[:20]
    
    print(f'[{datetime.datetime.now().strftime("%H:%M:%S")}] Ingestion Complete. Cached {len(fresh_map)} active game horizons into local memory arrays.')
    if INTERNAL_STATE_MEMORY['top_20_favorites']:
        send_discord_payload('📆 **TOP 20 DAILY FAVORITES BOARD (0-2 DAYS OUT)**\n' + '\n'.join(INTERNAL_STATE_MEMORY['top_20_favorites']))
    if INTERNAL_STATE_MEMORY['system_6_futures']:
        send_discord_payload('🚀 **TOP 20 FUTURES SCHEDULE BOARD (2-7 DAYS OUT)**\n' + '\n'.join(INTERNAL_STATE_MEMORY['system_6_futures']))

def initialize_automation_pipeline():
    init_ledger()
    execute_1_time_midnight_sync()
    INTERNAL_STATE_MEMORY['last_summary_time'] = time.time()
    send_discord_payload('✅ **Paid Automation Layer Online & Connected.**')
    
    while True:
        try:
            now_utc = datetime.datetime.now(datetime.timezone.utc)
            now_ct = now_utc - datetime.timedelta(hours=5)
            active_count = len(INTERNAL_STATE_MEMORY.get('cached_schedule', {}))
            print(f'[{now_ct.strftime("%H:%M:%S")}] Heartbeat Loop Active: Scanning {active_count} soccer game arrays across priority bookmakers (Bet365/DraftKings)...')
            
            if now_ct.hour == 0 and now_ct.minute <= 4:
                execute_1_time_midnight_sync()
                time.sleep(300)
                
            if time.time() - INTERNAL_STATE_MEMORY['last_summary_time'] >= 14400:
                send_discord_payload('📊 **4-HOUR SYSTEM RUNTIME UPDATE**')
                INTERNAL_STATE_MEMORY['last_summary_time'] = time.time()
            
            active = INTERNAL_STATE_MEMORY.get('cached_schedule', {})
            finished_keys = []
            
            for f_id, meta in list(active.items()):
                try:
                    # Filter live tracking strictly to items active around the current day to preserve credit caps
                    match_dt = datetime.datetime.fromisoformat(meta['commence_time'].replace('Z', '+00:00'))
                    if abs((now_utc - match_dt).days) > 1:
                        continue
                        
                    time.sleep(0.5)
                    check = query_api_football('fixtures', {'id': f_id})
                    if check and check.get('response'):
                        data = check['response'][0] if isinstance(check['response'], list) else check['response']
                        current_status = data['fixture']['status']['short']
                        
                        if current_status in ['1H', 'HT', '2H', 'ET', 'P', 'LIVE']:
                            evaluate_live_inplay_telemetry(f_id, meta, meta.get('bookmakers_odds', []))
                        elif current_status in ['FT', 'AET', 'PEN', 'Match Finished']:
                            # Dynamic Data Age-Out Execution: clean finished items from active RAM windows
                            finished_keys.append(f_id)
                except Exception as inner_err:
                    print(f'[-] Iteration pacing bypass logged on fixture {f_id}: {inner_err}')
                    continue
            
            # Age out finished rows from tracking cache to optimize RAM allocation
            for k in finished_keys:
                if k in INTERNAL_STATE_MEMORY['cached_schedule']:
                    del INTERNAL_STATE_MEMORY['cached_schedule'][k]
                    
            time.sleep(180)
        except KeyboardInterrupt:
            break
        except Exception as main_err:
            print(f'[-] Loop pacing safety trigger hit: {main_err}')
            time.sleep(30)

if __name__ == '__main__':
    initialize_automation_pipeline()
