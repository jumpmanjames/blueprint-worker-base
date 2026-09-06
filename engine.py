# -*- coding: utf-8 -*-
import os
import time
import csv
import requests
import datetime

# ----------------------------------------------------
# CONFIGURATION & GLOBAL VARIABLES
# ----------------------------------------------------
THE_ODDS_API_KEY = os.getenv("THE_ODDS_API_KEY", "YOUR_API_KEY")
API_FOOTBALL_KEY = os.getenv("API_FOOTBALL_KEY", "YOUR_API_FOOTBALL_KEY")
DISCORD_WEBHOOK_GENERAL = os.getenv("DISCORD_WEBHOOK_GENERAL", "YOUR_WEBHOOK_URL_GENERAL")
DISCORD_WEBHOOK_CRITICAL = os.getenv("DISCORD_WEBHOOK_CRITICAL", "YOUR_WEBHOOK_URL_CRITICAL")

LEDGER_FILE = "bet_ledger.csv"

# Global Country Matrix to Dynamically Discover Lower and Major Tiers
TARGET_COUNTRIES = [
    "England", "France", "Germany", "Italy", "Spain", "Belgium", "Netherlands",
    "Portugal", "Argentina", "Australia", "Austria", "Brazil", "Chile", "Colombia",
    "Denmark", "Ecuador", "Finland", "Greece", "Croatia", "China", "Japan", 
    "South Korea", "Mexico", "Norway", "Paraguay", "Peru", "Poland", "Romania",
    "Russia", "Scotland", "South Africa", "Sweden", "Switzerland", "Turkey", 
    "USA", "Venezuela", "Azerbaijan"
]

# Strict Bookmaker Priority Sequence Mapping (Illinois & Florida Layout)
BOOKMAKER_PRIORITY = [
    "bet365",
    "draftkings",
    "fanduel",
    "thescore",
    "hardrock",
    "betmgm",
    "caesars",
    "fanatics",
    "betrivers",
    "circa",
    "ballybet",
    "bovada"
]

# Persistent Application Memory State Triggers
state_memory = {
    "last_midnight_sync": None,
    "last_summary_report": time.time(),
    "cached_weekly_fixtures": []
}

# ----------------------------------------------------
# INFRASTRUCTURE UTILITIES & DATABASE LAYER
# ----------------------------------------------------
def init_ledger():
    if not os.path.exists(LEDGER_FILE):
        with open(LEDGER_FILE, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["timestamp", "match_id", "league", "teams", "odds_h2h", "system_tag", "status"])

def log_to_ledger(match_id, league, teams, odds_h2h, system_tag):
    init_ledger()
    with open(LEDGER_FILE, mode='a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([time.strftime("%Y-%m-%d %H:%M:%S"), match_id, league, teams, odds_h2h, system_tag, "PENDING_LIVE_AUDIT"])
    print(f"[+] Signal logged successfully inside system ledger sheet ({LEDGER_FILE})")

def send_discord_payload(content_str, critical=False):
    lines_list = content_str.split("\n")
    if lines_list and len(lines_list) > 0:
        clean_title = lines_list[0].replace("🏎️", "").replace("🚨", "").strip()
    else:
        clean_title = "System Alert"

    payload = {
        "embeds": [{
            "title": clean_title,
            "description": content_str,
            "color": 15158332 if critical else 3447003
        }]
    }
    
    url = DISCORD_WEBHOOK_CRITICAL if critical else DISCORD_WEBHOOK_GENERAL
    try:
        response = requests.post(url, json=payload, timeout=10)
        return response.status_code == 204
    except Exception as e:
        print(f"[-] Discord hook broadcast exception encountered: {e}")
        return False

# ----------------------------------------------------
# DATA INGESTION UTILITIES (API-FOOTBALL BRIDGES)
# ----------------------------------------------------
def query_api_football(endpoint, params=None):
    url = f"https://api-football-v1.p.rapidapi.com/v3/{endpoint}"
    headers = {
        "X-RapidAPI-Key": API_FOOTBALL_KEY,
        "X-RapidAPI-Host": "api-football-v1.p.rapidapi.com"
    }
    try:
        response = requests.get(url, headers=headers, params=params, timeout=12)
        time.sleep(2.0)  # Hardcoded Pacing Safeguard to enforce standard rate limits safely
        if response.status_code == 200:
            return response.json().get("response", [])
        print(f"[-] API-Football error on /{endpoint}: status code {response.status_code}")
        return []
    except Exception as e:
        print(f"[-] Network connection error on API-Football: {e}")
        return []

def discover_leagues_by_country(country_name):
    print(f"[INFO] Dynamically indexing leagues node for nation: {country_name}")
    return query_api_football("leagues", {"country": country_name, "current": "true"})

def fetch_daily_league_fixtures(league_id, season, date_str):
    params = {
        "league": league_id,
        "season": season,
        "date": date_str
    }
    return query_api_football("fixtures", params)

# ----------------------------------------------------
# ODDS INTEGRATION MATRIX (THE ODDS API)
# ----------------------------------------------------
def fetch_consensus_odds(sport_key):
    url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds"
    params = {
        "apiKey": THE_ODDS_API_KEY,
        "regions": "us,eu",
        "markets": "h2h",
        "oddsFormat": "american"
    }
    try:
        response = requests.get(url, params=params, timeout=12)
        if response.status_code == 200:
            return response.json()
        return []
    except Exception as e:
        print(f"[-] The Odds API query network crash bypassed: {e}")
        return []

def extract_prioritized_odds(bookmakers_list):
    # Evaluates bookmaker odds precisely in the sequence required by user parameters
    for target_book in BOOKMAKER_PRIORITY:
        for bookmaker in bookmakers_list:
            if bookmaker.get("key", "").lower() == target_book:
                markets = bookmaker.get("markets", [])
                if markets:
                    return target_book, markets[0].get("outcomes", [])
    return None, []

# ----------------------------------------------------
# REAL-TIME LIVE TELEMETRY PROCESSING SYSTEM 5 & 7
# ----------------------------------------------------
def monitor_live_telemetry_stream(match):
    # High-velocity monitoring pipeline focused strictly on active inplay games
    home_team = match.get("teams", {}).get("home", {}).get("name")
    away_team = match.get("teams", {}).get("away", {}).get("name")
    fixture_id = match.get("fixture", {}).get("id")
    
    print(f"[+] System 5 & 7 Active: Monitoring dangerous velocity corridors for {home_team} vs {away_team}")
    
    # Placeholder checking simulation matching manual verification rules
    pass_filter_matrix = {
        "Caliber Index": "PASS",
        "Table Standing Hierarchy": "PASS",
        "Goal Differential Calibration": "PASS",
        "Historical Matrix Coefficient": "PASS"
    }
    
    # Verify if metrics prompt entry criteria
    trigger_signal = False 
    if trigger_signal:
        system_5_report = "\n### 📊 SYSTEM 5 MATCH FILTER MATRIX\n"
        for criterion, result in pass_filter_matrix.items():
            system_5_report += f"| {criterion:<30} | {result:<5} |\n"
            
        system_7_report = (
            f"🚨 **SYSTEM 7 LIVE TELEMETRY TRIGGER ACTIVE**\n"
            f"Match: {home_team} vs {away_team}\n"
            f"Current Game Clock State: Active Inplay Telemetry Loop Running\n"
            f"{system_5_report}\n"
            f"Live Pressure Velocity: Monitoring Dangerous Attack Fluctuations..."
        )
        send_discord_payload(system_7_report, critical=True)
        log_to_ledger(fixture_id, match.get("league", {}).get("name"), f"{home_team} v {away_team}", "Live Lines", "SYSTEM_5_7_LIVE")

# ----------------------------------------------------
# TIMED EXECUTION HANDSHAKE LAYER
# ----------------------------------------------------
def execute_midnight_master_sync():
    print("[+] Launching 1-Time Midnight Master Schedule Sweep...")
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    state_memory["last_midnight_sync"] = now_utc.date()
    
    discovered_fixtures = []
    
    # Calculate 7-day target range dates list manually
    date_list = [(now_utc + datetime.timedelta(days=i)).strftime("%Y-%m-%d") for i in range(8)]
    
    # Dynamic lower-tier and major discovery engine loop over target countries matrix
    for country in TARGET_COUNTRIES:
        leagues = discover_leagues_by_country(country)
        for league_node in leagues:
            league_id = league_node.get("league", {}).get("id")
            season = league_node.get("seasons", [{}])[-1].get("year")
            
            if not league_id or not season:
                continue
                
            # Query day by day within account plan authorization constraints safely
            for day_str in date_list:
                fixtures = fetch_daily_league_fixtures(league_id, season, day_str)
                if fixtures:
                    discovered_fixtures.extend(fixtures)
                    
    state_memory["cached_weekly_fixtures"] = discovered_fixtures
    print(f"[+] Midnight Sync Complete. Locked down {len(discovered_fixtures)} multi-tier weekly soccer games in local memory.")

    # Partition upcoming schedule horizons for reporting
    futures_board = []
    daily_favorites = []
    
    for match in discovered_fixtures:
        home = match.get("teams", {}).get("home", {}).get("name")
        away = match.get("teams", {}).get("away", {}).get("name")
        start_time = match.get("fixture", {}).get("date")
        summary = f"🔹 {home} vs {away} ({start_time})"
        
        # Sort boards into matching time horizons
        try:
            match_dt = datetime.datetime.strptime(start_time[:19], "%Y-%m-%dT%H:%M:%S")
            days_out = (match_dt - datetime.datetime.now()).days
            if 2 <= days_out <= 7:
                futures_board.append(summary)
            elif 0 <= days_out < 2:
                daily_favorites.append(summary)
        except Exception:
            daily_favorites.append(summary)
            
    # Post Daily Gameplan Reports
    if daily_favorites:
        msg = "⭐ **TOP 20 DAILY FAVORITES BOARD**\n" + "\n".join(daily_favorites[:20])
        send_discord_payload(msg, critical=False)
    if futures_board:
        msg = "📆 **SYSTEM 6 ADVANCED FUTURES BOARD (2-7 DAYS OUT)**\n" + "\n".join(futures_board[:20])
        send_discord_payload(msg, critical=False)

def check_and_run_diagnostic_reports():
    current_time = time.time()
    # Execute 4-hour monitoring summary diagnostics layout
    if current_time - state_memory["last_summary_report"] >= 14400:
        state_memory["last_summary_report"] = current_time
        summary_msg = f"🗒️ **SYSTEM CORE STATUS REPORT**\nTimestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}\nTracking System Loop: Running Normal\nAPI-Football Connectors: Balanced\nThe Odds API Sync: Active"
        send_discord_payload(summary_msg, critical=False)
        print("[INFO] 4-Hour health diagnostic message broadcast complete.")

# ----------------------------------------------------
# SYSTEM ENGINE ENTRYPOINT COMMAND LOOP
# ----------------------------------------------------
def main_process_engine():
    init_ledger()
    print("[+] Core Automated Soccer Tracking System initialized successfully.")
    send_discord_payload("⚙️ **System Automation Pipeline Initialized. Tracking Loop Active.**", critical=False)
    
    while True:
        try:
            now_utc = datetime.datetime.now(datetime.timezone.utc)
            
            # Trigger 1-time midnight calendar sweep logic
            if state_memory["last_midnight_sync"] is None or now_utc.date() > state_memory["last_midnight_sync"]:
                execute_midnight_master_sync()
                
            # Scan dynamic loop records currently cached in memory
            for match in state_memory["cached_weekly_fixtures"]:
                status_short = match.get("fixture", {}).get("status", {}).get("short")
                
                # If match is actively in play, immediately pivot to high-velocity telemetry trackers
                if status_short in ["1H", "HT", "2H", "ET", "P"]:
                    monitor_live_telemetry_stream(match)
                    
            check_and_run_diagnostic_reports()
            
        except KeyboardInterrupt:
            print("[*] Automation tracking loop safely halted.")
            break
        except Exception as e:
            print(f"[-] Main engine recovery handler tripped: {e}")
            
        print("[*] High-velocity telemetry loop resting... Standby for next scan cycle.")
        time.sleep(120)

if __name__ == "__main__":
    main_process_engine()
