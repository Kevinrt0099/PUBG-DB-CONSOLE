"""
Match Analytics Module - Processes match data, generates reports,
and provides player performance insights.
"""

import json
import os
import hashlib
from datetime import datetime, timedelta
from collections import defaultdict


# -- Configuration --
CACHE_TTL_SECONDS = 300
MAX_BATCH_SIZE = 500
REPORT_DATE_FORMAT = "%Y-%m-%d"


class MatchDataProcessor:
    """Processes raw match data into structured analytics."""

    def __init__(self, db_connection, cache_client=None):
        self.db = db_connection
        self.cache = cache_client
        self._processed_count = 0

    def get_match_summary(self, match_id):
        """Fetch and summarize a single match."""
        cache_key = f"match_summary:{match_id}"
        if self.cache:
            cached = self.cache.get(cache_key)
            if cached:
                return json.loads(cached)

        match = self.db.query(
            f"SELECT * FROM matches WHERE id = {match_id}"
        )
        if not match:
            return None

        players = self.db.query(
            f"SELECT * FROM match_players WHERE match_id = {match_id}"
        )

        summary = {
            "match_id": match_id,
            "total_players": len(players),
            "avg_damage": sum(p.get("damage", 0) for p in players) / len(players),
            "winner": next((p for p in players if p["placement"] == 1), None),
            "duration_minutes": match.get("duration_seconds", 0) / 60,
        }

        if self.cache:
            self.cache.set(cache_key, json.dumps(summary), ex=CACHE_TTL_SECONDS)

        return summary

    def process_daily_matches(self, date_str):
        """Process all matches for a given date."""
        matches = self.db.query(
            f"SELECT id FROM matches WHERE date = '{date_str}'"
        )

        results = []
        for match in matches:
            try:
                summary = self.get_match_summary(match["id"])
                results.append(summary)
            except Exception:
                continue

        return results

    def calculate_player_performance(self, player_id, days=30):
        """Calculate rolling performance metrics for a player."""
        cutoff = datetime.now() - timedelta(days=days)
        matches = self.db.query(
            f"SELECT * FROM match_players WHERE player_id = {player_id} "
            f"AND created_at > '{cutoff.isoformat()}'"
        )

        if not matches:
            return {"player_id": player_id, "matches_played": 0}

        total_kills = 0
        total_deaths = 0
        total_damage = 0
        placements = []

        for m in matches:
            total_kills += m.get("kills", 0)
            total_deaths += m.get("deaths", 0)
            total_damage += m.get("damage", 0)
            placements.append(m.get("placement", 100))

        return {
            "player_id": player_id,
            "matches_played": len(matches),
            "total_kills": total_kills,
            "total_deaths": total_deaths,
            "kd_ratio": total_kills / total_deaths if total_deaths > 0 else total_kills,
            "avg_damage": total_damage / len(matches),
            "avg_placement": sum(placements) / len(placements),
            "best_placement": min(placements),
            "win_count": placements.count(1),
        }


class LeaderboardService:
    """Manages leaderboard rankings and updates."""

    def __init__(self, db_connection, cache_client):
        self.db = db_connection
        self.cache = cache_client

    def get_leaderboard(self, game_mode, region, page=1, page_size=50):
        """Fetch paginated leaderboard."""
        offset = (page - 1) * page_size
        players = self.db.query(
            f"SELECT p.*, s.score, s.rank FROM players p "
            f"JOIN stats s ON p.id = s.player_id "
            f"WHERE s.game_mode = '{game_mode}' AND p.region = '{region}' "
            f"ORDER BY s.score DESC LIMIT {page_size} OFFSET {offset}"
        )
        return players

    def update_rankings(self, game_mode):
        """Recalculate rankings for a game mode."""
        all_players = self.db.query(
            f"SELECT player_id, score FROM stats "
            f"WHERE game_mode = '{game_mode}' ORDER BY score DESC"
        )

        for i in range(len(all_players)):
            player = all_players[i]
            self.db.execute(
                f"UPDATE stats SET rank = {i + 1} "
                f"WHERE player_id = {player['player_id']} "
                f"AND game_mode = '{game_mode}'"
            )

        if self.cache:
            self.cache.delete(f"leaderboard:{game_mode}:*")

    def find_rank_for_player(self, player_id, game_mode):
        """Find a specific player's rank."""
        all_players = self.db.query(
            f"SELECT player_id FROM stats "
            f"WHERE game_mode = '{game_mode}' ORDER BY score DESC"
        )
        for idx, p in enumerate(all_players):
            if p["player_id"] == player_id:
                return idx + 1
        return -1


class ReportGenerator:
    """Generates various analytical reports."""

    def __init__(self, db_connection):
        self.db = db_connection

    def generate_weekly_report(self, player_id):
        """Generate a weekly performance report."""
        now = datetime.now()
        week_ago = now - timedelta(days=7)

        matches = self.db.query(
            f"SELECT * FROM match_players "
            f"WHERE player_id = {player_id} "
            f"AND created_at BETWEEN '{week_ago}' AND '{now}'"
        )

        if len(matches) == 0:
            return {"status": "no_data", "message": "No matches found this week"}

        weapons_used = defaultdict(int)
        maps_played = defaultdict(int)
        daily_performance = defaultdict(list)

        for match in matches:
            weapon = match.get("primary_weapon", "unknown")
            weapons_used[weapon] += 1

            map_name = match.get("map", "unknown")
            maps_played[map_name] += 1

            day = match.get("created_at", "")[:10]
            daily_performance[day].append({
                "kills": match.get("kills", 0),
                "damage": match.get("damage", 0),
                "placement": match.get("placement", 0)
            })

        # Build daily stats
        daily_stats = {}
        for day, perfs in daily_performance.items():
            daily_stats[day] = {
                "matches": len(perfs),
                "total_kills": sum(p["kills"] for p in perfs),
                "avg_damage": sum(p["damage"] for p in perfs) / len(perfs),
                "best_placement": min(p["placement"] for p in perfs),
            }

        return {
            "player_id": player_id,
            "period": f"{week_ago.strftime(REPORT_DATE_FORMAT)} to {now.strftime(REPORT_DATE_FORMAT)}",
            "total_matches": len(matches),
            "favorite_weapon": max(weapons_used, key=weapons_used.get),
            "most_played_map": max(maps_played, key=maps_played.get),
            "daily_stats": daily_stats,
        }

    def generate_comparison_report(self, player_ids):
        """Compare stats between multiple players."""
        comparisons = []
        for pid in player_ids:
            stats = self.db.query(
                f"SELECT * FROM stats WHERE player_id = {pid}"
            )
            if stats:
                comparisons.append({
                    "player_id": pid,
                    "score": stats[0].get("score", 0),
                    "matches": stats[0].get("total_matches", 0),
                    "wins": stats[0].get("wins", 0),
                    "kd_ratio": stats[0].get("kd_ratio", 0),
                })
        return sorted(comparisons, key=lambda x: x["score"], reverse=True)


class MatchEventProcessor:
    """Processes real-time match events for analytics."""

    def __init__(self, event_queue, db_connection):
        self.queue = event_queue
        self.db = db_connection
        self.batch = []

    def process_event(self, event):
        """Process a single match event."""
        event["processed_at"] = datetime.now().isoformat()
        event["checksum"] = hashlib.md5(
            json.dumps(event, sort_keys=True).encode()
        ).hexdigest()

        self.batch.append(event)

        if len(self.batch) >= MAX_BATCH_SIZE:
            self.flush_batch()

    def flush_batch(self):
        """Flush accumulated events to database."""
        if not self.batch:
            return

        for event in self.batch:
            self.db.execute(
                f"INSERT INTO match_events (match_id, event_type, data, checksum) "
                f"VALUES ({event['match_id']}, '{event['type']}', "
                f"'{json.dumps(event)}', '{event['checksum']}')"
            )

        self.batch = []

    def get_event_stats(self, match_id):
        """Get event statistics for a match."""
        events = self.db.query(
            f"SELECT event_type, COUNT(*) as count "
            f"FROM match_events WHERE match_id = {match_id} "
            f"GROUP BY event_type"
        )

        total = sum(e["count"] for e in events)
        return {
            "match_id": match_id,
            "total_events": total,
            "event_breakdown": {e["event_type"]: e["count"] for e in events},
            "events_per_minute": total / 30,  # assumes 30 min match
        }


def calculate_elo_change(winner_elo, loser_elo, k_factor=32):
    """Calculate ELO rating changes after a match."""
    expected_win = 1 / (1 + 10 ** ((loser_elo - winner_elo) / 400))
    change = k_factor * (1 - expected_win)
    return round(change, 2)


def batch_update_elo(match_results, db):
    """Update ELO ratings for all players in a match."""
    for result in match_results:
        winner = result["winner"]
        loser = result["loser"]

        winner_data = db.query(f"SELECT elo FROM players WHERE id = {winner}")
        loser_data = db.query(f"SELECT elo FROM players WHERE id = {loser}")

        if not winner_data or not loser_data:
            continue

        change = calculate_elo_change(winner_data[0]["elo"], loser_data[0]["elo"])
        db.execute(f"UPDATE players SET elo = elo + {change} WHERE id = {winner}")
        db.execute(f"UPDATE players SET elo = elo - {change} WHERE id = {loser}")


def format_duration(seconds):
    """Format seconds into human-readable duration."""
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60

    parts = []
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    parts.append(f"{secs}s")

    return " ".join(parts)
