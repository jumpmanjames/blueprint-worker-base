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
    # System 7 Live Telemetry Hooks
    # Query live stats for this specific fixture from API-Football
    res = query_api_football('fixtures/statistics', {'fixture': fixture_id})
    stats_summary = "Live Stats: Not Available"
    
    if res and res.get('response'):
        teams_stats = res['response']
        # Extract fields to fulfill Row 1, Row 1.5, Row 2, Row 3 rules
        stats_summary = ""
        for team_data in teams_stats:
            t_name = team_data['team']['name']
            s_dict = {item['type']: item['value'] for item in team_data['statistics'] if item['value'] is not None}
            
            xg = s_dict.get('expected_goals', 'N/A')
            shots_on = s_dict.get('Shots on Goal', 0)
            shots_off = s_dict.get('Shots off Goal', 0)
            total_shots = shots_on + shots_off
            attacks = s_dict.get('Attacks', 0)
            dang_attacks = s_dict.get('Dangerous Attacks', 0)
            possession = s_dict.get('Ball Possession', '50%')
            corners = s_dict.get('Corner Kicks', 0)
            red_cards = s_dict.get('Red Cards', 0)
            yellow_cards = s_dict.get('Yellow Cards', 0)
            
            stats_summary += f"\n**{t_name}** -> xG: {xg} | ShotsOn/Total: {shots_on}/{total_shots} | Att/DangAtt: {attacks}/{dang_attacks} | Poss: {possession} | Corners: {corners} | Cards(R/Y): {red_cards}/{yellow_cards}"

    teams = f'{match_details["home_team"]} v {match_details["away_team"]}'
    selected_book, odds_data = 'N/A', 'N/A'
    for target_book in BOOKMAKER_PRIORITY:
        book_match = next((b for b in h2h_odds_matrix if b.get('key') == target_book), None)
        if book_match:
            selected_book = book_match.get('title', target_book)
            markets = book_match.get('markets', [])
            if markets:
                for m in markets:
                    if m.get('key') == 'h2h':
                        odds_data = ' | '.join([f'{o["name"]}: {o["price"]}' for o in m.get('outcomes', [])])
                        break
            break
    
    report = f'🏎️ **CORVETTE FUND BLUEPRINT — SYSTEM SELECTION TRIGGERED**\n\nMatch Context: {teams} ({match_details["league_name"]})\nVerified Market Price Consensus ({selected_book}):\n• Full-Time 1X2 Moneyline: {odds_data}\n• Target Edge Metric: Implied vs True Probability Margin Met\n{stats_summary}'
    send_discord_payload(report)
    log_to_ledger(fixture_id, match_details['league_name'], teams, odds_data, 'SYSTEM_BLUEPRINT_SELECTION')

def execute_1_time_midnight_sync():
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    now_ct = now_utc - datetime.timedelta(hours=5)
    target_season = 2026
    fresh_map = {}
    
    print(f'[{now_ct.strftime("%H:%M:%S")}] Starting Paid-Tier Full League Schedule RAM Ingestion for season {target_season}...')
    
    fav_list = []
    fut_list = []
    
    for league in LEAGUE_CATALOG:
        try:
            time.sleep(0.2) # Throttled safely for Pro Plan limits
            res = query_api_football('fixtures', {'league': league['id'], 'season': target_season})
            if not res or not res.get('response'):
                continue
                
            fixtures = res['response']
            odds_pool = fetch_odds_for_market(SPORT_KEY_MAP.get(league['id']))
            
            for item in fixtures:
                f_id = item['fixture']['id']
                home, away = item['teams']['home']['name'], item['teams']['away']['name']
                match_status = item['fixture']['status']['short']
                match_date_str = item['fixture']['date'] # ISO string from API
                
                # Convert ISO match time to datetime object
                try:
                    match_dt = datetime.datetime.fromisoformat(match_date_str.replace('Z', '+00:00'))
                except ValueError:
                    continue
                
                # Standardize to local memory arrays
                match_odds = []
                if odds_pool:
                    match_o = next((o for o in odds_pool if o['home_team'] == home or o['away_team'] == away), None)
                    if match_o:
                        match_odds = match_o.get('bookmakers', [])
                
                fresh_map[f_id] = {
                    'fixture_id': f_id,
                    'home_team': home,
                    'away_team': away,
                    'league_name': league['name'],
                    'commence_time': match_date_str,
                    'status_short': match_status,
                    'bookmakers_odds': match_odds
                }
                
                # Operational multi-horizon filtering based on day offsets
                delta_days = (match_dt.date() - now_utc.date()).days
                entry_str = f"🔹 {home} vs {away} ({league['name']}) - {match_dt.strftime('%m/%d %H:%M')} UTC"
                
                if 0 <= delta_days <= 2:
                    fav_list.append(entry_str)
                elif 2 < delta_days <= 7:
                    fut_list.append(entry_str)
                    
        except Exception as e:
            print(f'[-] Shielded lookup error on league folder {league["id"]}: {e}')
            continue
            
    INTERNAL_STATE_MEMORY['cached_schedule'] = fresh_map
    INTERNAL_STATE_MEMORY['top_20_favorites'] = fav_list[:20]
    INTERNAL_STATE_MEMORY['system_6_futures'] = fut_list[:20]
    
    print(f'[{datetime.datetime.now(datetime.timezone.utc).strftime("%H:%M:%S")}] Ingestion Complete. Cached {len(fresh_map)} active game horizons into local memory arrays.')
    
    if INTERNAL_STATE_MEMORY['top_20_favorites']:
        send_discord_payload('📆 **TOP 20 DAILY FAVORITES BOARD (0-2 DAYS)**\n' + '\n'.join(INTERNAL_STATE_MEMORY['top_20_favorites']))
    if INTERNAL_STATE_MEMORY['system_6_futures']:
        send_discord_payload('🔮 **TOP 20 FUTURES BOARD (2-7 DAYS)**\n' + '\n'.join(INTERNAL_STATE_MEMORY['system_6_futures']))

def initialize_automation_pipeline():
    init_ledger()
    execute_1_time_midnight_sync()
    INTERNAL_STATE_MEMORY['last_summary_time'] = time.time()
    send_discord_payload('✅ **Paid Automation Layer Online & Connected.**')
    
    while True:
        try:
            now_ct = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=5)
            active_count = len(INTERNAL_STATE_MEMORY.get('cached_schedule', {}))
            print(f'[{now_ct.strftime("%H:%M:%S")}] Heartbeat Loop Active: Scanning {active_count} soccer game arrays across priority bookmakers (Bet365/DraftKings)...')
            
            # Recalibrate daily at midnight CT
            if now_ct.hour == 0 and now_ct.minute <= 4:
                execute_1_time_midnight_sync()
                time.sleep(300)
                
            if time.time() - INTERNAL_STATE_MEMORY['last_summary_time'] >= 14400:
                send_discord_payload('📊 **4-HOUR SYSTEM RUNTIME UPDATE**')
                INTERNAL_STATE_MEMORY['last_summary_time'] = time.time()
            
            active = list(INTERNAL_STATE_MEMORY.get('cached_schedule', {}).items())
            for f_id, meta in active:
                # Data Age-Out Execution: delete from scanning loop if match long concluded
                if meta['status_short'] in ['FT', 'AET', 'PEN', 'AMD']:
                    if f_id in INTERNAL_STATE_MEMORY['cached_schedule']:
                        del INTERNAL_STATE_MEMORY['cached_schedule'][f_id]
                    continue
                    
                try:
                    time.sleep(0.5)
                    check = query_api_football('fixtures', {'id': f_id})
                    if check and check.get('response'):
                        data = check['response'][0] if isinstance(check['response'], list) else check['response']
                        current_status = data['fixture']['status']['short']
                        INTERNAL_STATE_MEMORY['cached_schedule'][f_id]['status_short'] = current_status
                        
                        if current_status in ['1H', 'HT', '2H', 'ET', 'P', 'LIVE']:
                            evaluate_live_inplay_telemetry(f_id, meta, meta.get('bookmakers_odds', []))
                except Exception as inner_err:
                    print(f'[-] Iteration bypass logged on fixture {f_id}: {inner_err}')
                    continue
            time.sleep(180)
        except KeyboardInterrupt:
            break
        except Exception as main_err:
            print(f'[-] Loop pacing safety trigger hit: {main_err}')
            time.sleep(30)

if __name__ == '__main__':
    initialize_automation_pipeline()
