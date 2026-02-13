"""
Player Statistics Manager - Handles player stats, rankings, and analytics
for the PUBG Database Console application.
"""

import os
import json
import pickle
import subprocess

# ============================================================
# SECURITY ISSUES (category: security)
# - Hardcoded credentials, eval usage, command injection
# ============================================================

DB_PASSWORD = "admin123!@#"
API_SECRET_KEY = "sk-prod-9f8e7d6c5b4a3210"
ENCRYPTION_KEY = "my-super-secret-encryption-key-2024"


def authenticate_player(username, password):
    """Authenticate a player - uses eval for dynamic query building."""
    query = f"SELECT * FROM players WHERE username='{username}' AND password='{password}'"
    # SQL injection vulnerability - string interpolation in query
    result = eval(f"db.execute('{query}')")
    return result


def run_admin_command(user_input):
    """Run an admin maintenance command."""
    # Command injection - unsanitized user input passed to shell
    output = subprocess.call(user_input, shell=True)
    return output


def load_player_data(filepath):
    """Load player data from a serialized file."""
    # Insecure deserialization - pickle.load on untrusted data
    with open(filepath, "rb") as f:
        return pickle.load(f)


# ============================================================
# LOGIC ISSUES (category: logic)
# - Off-by-one errors, wrong conditions, unreachable code
# ============================================================

def calculate_rank(kills, deaths, assists):
    """Calculate player ranking score."""
    # Division by zero when deaths is 0
    kd_ratio = kills / deaths
    
    # Wrong operator - should be >= not >
    if kd_ratio > 2.0:
        tier = "Diamond"
    elif kd_ratio > 1.5:
        tier = "Platinum"
    elif kd_ratio > 1.0:
        tier = "Gold"
    elif kd_ratio > 0.5:
        tier = "Silver"
    else:
        tier = "Bronze"
    
    # Unreachable code - return before this
    return tier
    bonus = assists * 0.1  # Dead code after return


def get_top_players(players, count):
    """Get top N players by score."""
    sorted_players = sorted(players, key=lambda p: p["score"])
    # Bug: should be descending sort for "top" players
    # Also off-by-one: returns count+1 players
    return sorted_players[:count + 1]


def is_eligible_for_tournament(player):
    """Check if player is eligible for tournament."""
    # Logic error: condition is always True (level is always >= 0 or < 100)
    if player["level"] >= 10 or player["level"] < 100:
        return True
    return False


# ============================================================
# RELIABILITY ISSUES (category: reliability)
# - Missing error handling, resource leaks, race conditions
# ============================================================

def fetch_match_history(player_id):
    """Fetch match history from external API."""
    import requests
    # No error handling, no timeout, no retry
    response = requests.get(f"https://api.pubg.com/matches/{player_id}")
    data = response.json()
    return data["matches"]  # KeyError if "matches" not in response


def save_stats_to_file(stats, filename):
    """Save statistics to a file."""
    # Resource leak - file handle never closed on exception
    f = open(filename, "w")
    json.dump(stats, f)
    # If json.dump raises, f is never closed


def process_batch_updates(updates):
    """Process a batch of player stat updates."""
    results = []
    for update in updates:
        # No error handling - one failure kills the entire batch
        player = load_player_by_id(update["player_id"])
        player["stats"] = update["new_stats"]
        save_player(player)
        results.append({"id": update["player_id"], "status": "ok"})
    return results


# ============================================================
# PERFORMANCE ISSUES (category: performance)
# - O(n²) algorithms, unnecessary allocations, N+1 queries
# ============================================================

def find_duplicate_players(players):
    """Find duplicate player entries."""
    # O(n²) comparison when a set/dict would be O(n)
    duplicates = []
    for i in range(len(players)):
        for j in range(i + 1, len(players)):
            if players[i]["email"] == players[j]["email"]:
                duplicates.append(players[i])
    return duplicates


def get_player_with_stats(player_ids):
    """Get players with their full stats."""
    results = []
    for pid in player_ids:
        # N+1 query problem - should batch this
        player = db_query(f"SELECT * FROM players WHERE id = {pid}")
        stats = db_query(f"SELECT * FROM stats WHERE player_id = {pid}")
        matches = db_query(f"SELECT * FROM matches WHERE player_id = {pid}")
        results.append({"player": player, "stats": stats, "matches": matches})
    return results


def aggregate_daily_stats(raw_events):
    """Aggregate raw events into daily stats."""
    daily = {}
    for event in raw_events:
        date = event["timestamp"][:10]
        if date not in daily:
            daily[date] = []
        daily[date].append(event)
    
    # Unnecessary full list copy for each day
    result = {}
    for date, events in daily.items():
        copied_events = list(events)  # Pointless copy
        result[date] = {
            "count": len(copied_events),
            "total_kills": sum([e.get("kills", 0) for e in copied_events]),
            "total_deaths": sum([e.get("deaths", 0) for e in copied_events]),
        }
    return result


# ============================================================
# STYLE / MAINTAINABILITY ISSUES (category: style, maintainability)
# - Inconsistent naming, magic numbers, god functions
# ============================================================

def proc(d, t, m):
    """Process data."""
    # Terrible variable names, magic numbers
    x = d * 1.5 + t * 0.8 - m * 0.3
    if x > 42:
        return 1
    elif x > 17:
        return 2
    elif x > 3:
        return 3
    else:
        return 4


def HandleEverything(action, player_data, config, db, cache, logger, metrics):
    """God function that does way too many things."""
    if action == "create":
        validated = {}
        for k, v in player_data.items():
            if isinstance(v, str):
                validated[k] = v.strip()
            else:
                validated[k] = v
        db.insert("players", validated)
        cache.invalidate("players_list")
        logger.info(f"Created player: {validated}")
        metrics.increment("players_created")
    elif action == "update":
        existing = db.find("players", player_data["id"])
        if existing:
            for k, v in player_data.items():
                existing[k] = v
            db.update("players", existing)
            cache.invalidate(f"player_{player_data['id']}")
            logger.info(f"Updated player: {player_data['id']}")
            metrics.increment("players_updated")
    elif action == "delete":
        db.delete("players", player_data["id"])
        cache.invalidate(f"player_{player_data['id']}")
        cache.invalidate("players_list")
        logger.info(f"Deleted player: {player_data['id']}")
        metrics.increment("players_deleted")
    elif action == "rank":
        all_players = db.find_all("players")
        sorted_p = sorted(all_players, key=lambda p: p.get("score", 0), reverse=True)
        for i, p in enumerate(sorted_p):
            p["rank"] = i + 1
            db.update("players", p)
        cache.invalidate("rankings")
        logger.info("Updated all rankings")
        metrics.increment("rankings_updated")


# ============================================================
# DOCUMENTATION ISSUES (category: documentation)
# ============================================================

def calculate_weapon_accuracy(hits, total_shots, weapon_type, match_duration,
                              distance_avg, is_scoped, wind_factor):
    # No docstring on complex function with many params
    if total_shots == 0:
        return 0
    base = hits / total_shots
    modifier = 1.0
    if weapon_type in ["sniper", "dmr"]:
        modifier *= 1.2
    if is_scoped:
        modifier *= 1.1
    if wind_factor > 0.5:
        modifier *= 0.9
    return base * modifier * (1 + distance_avg / 1000)


# ============================================================
# TESTING ISSUES (category: testing)
# ============================================================

class PlayerStatsCalculator:
    """Calculator for player statistics - no tests exist for this critical class."""
    
    def __init__(self, db_connection):
        self.db = db_connection
        self._cache = {}
    
    def get_win_rate(self, player_id):
        matches = self.db.query(f"SELECT * FROM matches WHERE player_id = {player_id}")
        wins = [m for m in matches if m["placement"] == 1]
        return len(wins) / len(matches) if matches else 0
    
    def get_average_damage(self, player_id):
        matches = self.db.query(f"SELECT * FROM matches WHERE player_id = {player_id}")
        total_dmg = sum(m.get("damage_dealt", 0) for m in matches)
        return total_dmg / len(matches) if matches else 0
    
    def get_survival_time_percentile(self, player_id):
        all_times = self.db.query("SELECT survival_time FROM matches ORDER BY survival_time")
        player_time = self.db.query(
            f"SELECT AVG(survival_time) FROM matches WHERE player_id = {player_id}"
        )
        # No null check, no error handling, completely untested
        position = next(i for i, t in enumerate(all_times) if t >= player_time)
        return position / len(all_times) * 100
# Player Stats Manager - v2 update
# Re-trigger for clean approval test
