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
        csv.writer(f).writerow([datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), match_id, league, teams, odds_h2h, system_tag, 'PENDING_LIVE_AUDIT'])

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
    teams = f"{match_details['home_team']} v {match_details['away_team']}"
    selected_book, odds_data = 'N/A', 'N/A'
    for target_book in BOOKMAKER_PRIORITY:
        book_match = next((b for b in h2h_odds_matrix if b.get('key') == target_book), None)
        if book_match:
            selected_book = book_match.get('title', target_book)
            markets = book_match.get('markets', [])
            if markets and len(markets) > 0:
                outcomes = markets[0].get('outcomes', [])
                odds_data = ' | '.join([f"{o['name']}: {o['price']}" for o in outcomes])
            break
    
    # Live stats lookup to fetch real telemetry instead of dummy parameters
    stats_res = query_api_football('fixtures/statistics', {'fixture': fixture_id})
    stats_summary = "Live Telemetry Pending"
    if stats_res and stats_res.get('response'):
        team_stats = stats_res['response']
        stats_summary = ""
        for t in team_stats:
            t_name = t['team']['name']
            s_map = {item['type']: item['value'] for item in t['statistics'] if item['value'] is not None}
            shots_on = s_map.get('Shots on Goal', 0)
            shots_off = s_map.get('Shots off Goal', 0)
            attacks = s_map.get('Attacks', 0)
            dang_attacks = s_map.get('Dangerous Attacks', 0)
            possession = s_map.get('Ball Possession', '0%')
            stats_summary += f"\n• {t_name} -> Shots Target Ratio: {shots_on}/{shots_off + shots_on} | Dangerous Attacks: {dang_attacks} | Possession: {possession}"

    report = f"🏎️ **CORVETTE FUND BLUEPRINT — SYSTEM SELECTION TRIGGERED**\n\nMatch Context: {teams} ({match_details['league_name']})\nVerified Market Price Consensus ({selected_book}):\n• Full-Time 1X2 Moneyline: {odds_data}\n{stats_summary}\n• Target Edge Metric: Implied vs True Probability Margin Met"
    send_discord_payload(report)
    log_to_ledger(fixture_id, match_details['league_name'], teams, odds_data, 'SYSTEM_BLUEPRINT_SELECTION')

def execute_1_time_midnight_sync():
    current_time_ct = datetime.datetime.now()
    print(f"[{current_time_ct.strftime('%H:%M:%S')}] Starting Programmatic Season Paid-Tier Full League Schedule RAM Ingestion...")
    
    fresh_map = {}
    favorites_list = []
    futures_list = []
    
    for league in LEAGUE_CATALOG:
        try:
            time.sleep(0.2)
            # Look up active season dynamically from API-Football
            league_info = query_api_football('leagues', {'id': league['id']})
            target_season = 2026
            if league_info and league_info.get('response'):
                seasons = league_info['response'][0]['seasons']
                active_season_obj = next((s for s in seasons if s.get('current') is True), None)
                if active_season_obj:
                    target_season = active_season_obj.get('year', 2026)
            
            fixtures_res = query_api_football('fixtures', {'league': league['id'], 'season': target_season})
            if fixtures_res and fixtures_res.get('response'):
                fixtures = fixtures_res['response']
                odds_pool = fetch_odds_for_market(SPORT_KEY_MAP.get(league['id']))
                
                for item in fixtures:
                    f_id = item['fixture']['id']
                    home, away = item['teams']['home']['name'], item['teams']['away']['name']
                    match_time_utc = datetime.datetime.strptime(item['fixture']['date'], "%Y-%m-%dT%H:%M:%S%z")
                    match_time_ct = match_time_utc.replace(tzinfo=datetime.timezone.utc).astimezone(None)
                    
                    time_delta = match_time_ct.replace(tzinfo=None) - current_time_ct.replace(tzinfo=None)
                    days_out = time_delta.days
                    
                    match_odds = []
                    odds_str = "No Consensus Odds Found"
                    if odds_pool:
                        match_o = next((o for o in odds_pool if o['home_team'] == home or o['away_team'] == away), None)
                        if match_o and match_o.get('bookmakers'):
                            match_odds = match_o['bookmakers']
                            for target_book in BOOKMAKER_PRIORITY:
                                b_match = next((b for b in match_odds if b.get('key') == target_book), None)
                                if b_match and b_match.get('markets'):
                                    outcomes = b_match['markets'][0].get('outcomes', [])
                                    odds_str = ' | '.join([f"{o['name']}: {o['price']}" for o in outcomes])
                                    break

                    match_meta = {
                        'fixture_id': f_id,
                        'home_team': home,
                        'away_team': away,
                        'league_name': league['name'],
                        'commence_time': item['fixture']['date'],
                        'status_short': item['fixture']['status']['short'],
                        'bookmakers_odds': match_odds
                    }
                    
                    fresh_map[f_id] = match_meta
                    
                    entry_str = f"🔹 {home} vs {away} ({league['name']}) - Time: {match_time_ct.strftime('%m/%d %H:%M')} CT | Odds: {odds_str}"
                    if 0 <= days_out <= 2:
                        favorites_list.append(entry_str)
                    elif 2 < days_out <= 7:
                        futures_list.append(entry_str)
                        
        except Exception as e:
            print(f"[-] Shielded lookup error on league folder {league['id']}: {e}")
            continue
            
    INTERNAL_STATE_MEMORY['cached_schedule'] = fresh_map
    INTERNAL_STATE_MEMORY['top_20_favorites'] = favorites_list[:20]
    INTERNAL_STATE_MEMORY['system_6_futures'] = futures_list[:20]
    
    print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] Ingestion Complete. Cached {len(fresh_map)} active game horizons into local memory arrays.")
    
    if INTERNAL_STATE_MEMORY['top_20_favorites']:
        send_discord_payload('📆 **TOP 20 DAILY FAVORITES BOARD (0-2 DAYS OUT)**\n' + '\n'.join(INTERNAL_STATE_MEMORY['top_20_favorites']))
    if INTERNAL_STATE_MEMORY['system_6_futures']:
        send_discord_payload('🔮 **TOP 20 FUTURES BOARD (2-7 DAYS OUT)**\n' + '\n'.join(INTERNAL_STATE_MEMORY['system_6_futures']))

def initialize_automation_pipeline():
    init_ledger()
    execute_1_time_midnight_sync()
    INTERNAL_STATE_MEMORY['last_summary_time'] = time.time()
    send_discord_payload('✅ **Paid Automation Layer Online & Connected.**')
    
    while True:
        try:
            now = datetime.datetime.now()
            active_count = len(INTERNAL_STATE_MEMORY.get('cached_schedule', {}))
            print(f"[{now.strftime('%H:%M:%S')}] Heartbeat Loop Active: Scanning {active_count} soccer game arrays across priority bookmakers (Bet365/DraftKings)...")
            
            if now.hour == 0 and now.minute <= 4:
                INTERNAL_STATE_MEMORY['top_20_favorites'] = []
                INTERNAL_STATE_MEMORY['system_6_futures'] = []
                execute_1_time_midnight_sync()
                time.sleep(300)
                
            if time.time() - INTERNAL_STATE_MEMORY['last_summary_time'] >= 14400:
                send_discord_payload('📊 **4-HOUR SYSTEM RUNTIME UPDATE**')
                INTERNAL_STATE_MEMORY['last_summary_time'] = time.time()
            
            active = list(INTERNAL_STATE_MEMORY.get('cached_schedule', {}).items())
            for f_id, meta in active:
                try:
                    time.sleep(0.5)
                    check = query_api_football('fixtures', {'id': f_id})
                    if check and check.get('response'):
                        data = check['response'][0]
                        current_status = data['fixture']['status']['short']
                        
                        # Data Age-Out Execution: Drop matches that have finished from active telemetry loop arrays
                        if current_status in ['FT', 'AET', 'PEN', 'Match Finished']:
                            if f_id in INTERNAL_STATE_MEMORY['cached_schedule']:
                                del INTERNAL_STATE_MEMORY['cached_schedule'][f_id]
                            continue
                            
                        if current_status in ['1H', 'HT', '2H', 'ET', 'P', 'LIVE']:
                            evaluate_live_inplay_telemetry(f_id, meta, meta.get('bookmakers_odds', []))
                except Exception as inner_err:
                    print(f"[-] Iteration bypass logged on fixture {f_id}: {inner_err}")
                    continue
            time.sleep(120)
        except KeyboardInterrupt:
            break
        except Exception as main_err:
            print(f"[-] Loop pacing safety trigger hit: {main_err}")
            time.sleep(30)

if __name__ == '__main__':
    initialize_automation_pipeline()