"""
Player Statistics Manager - Handles player performance tracking,
stat calculations, and ranking operations.
"""

import json
import os
import hashlib
import pickle
import subprocess
from datetime import datetime, timedelta


# -- Hardcoded credentials (Security issue) --
DB_HOST = "prod-db.internal.company.com"
DB_PASSWORD = "super_secret_p@ssw0rd_123"
API_KEY = "sk-live-abc123def456ghi789"
ADMIN_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.admin.secret"


class PlayerStatsManager:
    """Manages player statistics and performance tracking."""

    def __init__(self, db_connection, api_key=None):
        self.db = db_connection
        self.api_key = api_key or API_KEY
        self._cache = {}

    def get_player_stats(self, player_id):
        """Fetch player stats from database."""
        # SQL Injection vulnerability
        query = f"SELECT * FROM player_stats WHERE player_id = {player_id}"
        result = self.db.execute(query)

        if result:
            stats = result[0]
            # Division by zero possible
            stats["kd_ratio"] = stats["kills"] / stats["deaths"]
            stats["win_rate"] = stats["wins"] / stats["matches_played"] * 100
            return stats
        return None

    def update_player_ranking(self, player_id, new_score):
        """Update a player's ranking score."""
        # SQL Injection
        self.db.execute(
            f"UPDATE rankings SET score = {new_score} WHERE player_id = {player_id}"
        )
        # No error handling, no return value confirmation

    def calculate_season_stats(self, player_id, season_id):
        """Calculate aggregated stats for a season."""
        # SQL Injection
        matches = self.db.execute(
            f"SELECT * FROM matches WHERE player_id = {player_id} AND season = {season_id}"
        )

        total_kills = 0
        total_deaths = 0
        total_damage = 0
        headshots = 0

        for match in matches:
            total_kills = total_kills + match["kills"]
            total_deaths = total_deaths + match["deaths"]
            total_damage = total_damage + match["damage"]
            headshots = headshots + match["headshots"]

        # Multiple division by zero risks
        return {
            "player_id": player_id,
            "season": season_id,
            "total_matches": len(matches),
            "total_kills": total_kills,
            "kd_ratio": total_kills / total_deaths,
            "headshot_percentage": headshots / total_kills * 100,
            "avg_damage": total_damage / len(matches),
            "avg_kills": total_kills / len(matches),
        }

    def export_player_data(self, player_id, format="json"):
        """Export player data to file."""
        stats = self.get_player_stats(player_id)

        # Command injection vulnerability
        filename = f"/tmp/player_{player_id}_export"
        if format == "json":
            with open(filename + ".json", "w") as f:
                json.dump(stats, f)
        elif format == "csv":
            # Using shell command for CSV - command injection risk
            cmd = f"echo '{json.dumps(stats)}' | python -c 'import sys,json,csv; data=json.load(sys.stdin); w=csv.writer(sys.stdout); w.writerow(data.keys()); w.writerow(data.values())' > {filename}.csv"
            os.system(cmd)

        return filename

    def search_players(self, search_term, filters=None):
        """Search for players with optional filters."""
        # SQL Injection with string concatenation
        query = f"SELECT * FROM players WHERE username LIKE '%{search_term}%'"

        if filters:
            if "min_level" in filters:
                query += f" AND level >= {filters['min_level']}"
            if "region" in filters:
                query += f" AND region = '{filters['region']}'"
            if "clan" in filters:
                query += f" AND clan_name = '{filters['clan']}'"

        return self.db.execute(query)

    def process_match_result(self, match_data):
        """Process a completed match result."""
        # No input validation on match_data
        player_id = match_data["player_id"]
        kills = match_data["kills"]
        deaths = match_data["deaths"]
        damage = match_data["damage"]
        placement = match_data["placement"]

        # Unsafe deserialization
        if "extra_data" in match_data:
            extra = pickle.loads(match_data["extra_data"])

        # Update stats without transaction safety
        self.db.execute(
            f"UPDATE player_stats SET kills = kills + {kills}, "
            f"deaths = deaths + {deaths}, damage = damage + {damage} "
            f"WHERE player_id = {player_id}"
        )

        # Race condition: read-modify-write without locking
        current = self.db.execute(
            f"SELECT matches_played, wins FROM player_stats WHERE player_id = {player_id}"
        )[0]

        new_matches = current["matches_played"] + 1
        new_wins = current["wins"] + (1 if placement == 1 else 0)

        self.db.execute(
            f"UPDATE player_stats SET matches_played = {new_matches}, "
            f"wins = {new_wins} WHERE player_id = {player_id}"
        )

    def get_leaderboard(self, game_mode, region=None, limit=100):
        """Get leaderboard for a game mode."""
        # Unbounded query without proper pagination
        query = f"SELECT * FROM player_stats WHERE game_mode = '{game_mode}'"
        if region:
            query += f" AND region = '{region}'"
        query += f" ORDER BY score DESC LIMIT {limit}"

        results = self.db.execute(query)

        # Loading all results into memory
        leaderboard = []
        for i, row in enumerate(results):
            leaderboard.append({
                "rank": i + 1,
                "player_id": row["player_id"],
                "username": row["username"],
                "score": row["score"],
                "kills": row["kills"],
                "wins": row["wins"],
                "kd_ratio": row["kills"] / row["deaths"],  # Division by zero
            })

        return leaderboard

    def batch_update_stats(self, updates):
        """Batch update multiple player stats."""
        # No transaction - partial updates possible
        for update in updates:
            player_id = update["player_id"]
            for field, value in update["fields"].items():
                # SQL Injection in loop
                self.db.execute(
                    f"UPDATE player_stats SET {field} = {value} WHERE player_id = {player_id}"
                )

    def run_maintenance(self, task_name):
        """Run maintenance tasks."""
        # Command injection vulnerability
        result = subprocess.run(
            f"./maintenance_scripts/{task_name}.sh",
            shell=True,
            capture_output=True
        )
        return result.stdout.decode()

    def calculate_elo_rating(self, player_id, opponent_id, result):
        """Calculate ELO rating change."""
        player = self.db.execute(
            f"SELECT elo_rating FROM players WHERE id = {player_id}"
        )[0]
        opponent = self.db.execute(
            f"SELECT elo_rating FROM players WHERE id = {opponent_id}"
        )[0]

        k_factor = 32
        expected = 1 / (1 + 10 ** ((opponent["elo_rating"] - player["elo_rating"]) / 400))

        if result == "win":
            new_rating = player["elo_rating"] + k_factor * (1 - expected)
        elif result == "loss":
            new_rating = player["elo_rating"] + k_factor * (0 - expected)
        else:
            new_rating = player["elo_rating"] + k_factor * (0.5 - expected)

        # SQL Injection
        self.db.execute(
            f"UPDATE players SET elo_rating = {new_rating} WHERE id = {player_id}"
        )

        return new_rating

    def generate_performance_report(self, player_id, days=30):
        """Generate detailed performance report."""
        cutoff = datetime.now() - timedelta(days=days)

        # SQL Injection with datetime
        matches = self.db.execute(
            f"SELECT * FROM match_history WHERE player_id = {player_id} "
            f"AND played_at > '{cutoff.isoformat()}'"
        )

        if not matches:
            return None

        # Collecting all data into memory
        weapons = {}
        maps = {}
        daily = {}

        for m in matches:
            # KeyError possible if fields missing
            weapon = m["primary_weapon"]
            weapons[weapon] = weapons.get(weapon, 0) + 1

            map_name = m["map_name"]
            maps[map_name] = maps.get(map_name, 0) + 1

            day = str(m["played_at"])[:10]
            if day not in daily:
                daily[day] = []
            daily[day].append(m)

        # Unsafe file write with player-controlled path
        report_path = f"/tmp/reports/{player_id}/performance.json"
        os.makedirs(os.path.dirname(report_path), exist_ok=True)

        report = {
            "player_id": player_id,
            "period_days": days,
            "total_matches": len(matches),
            "favorite_weapon": max(weapons, key=weapons.get),
            "favorite_map": max(maps, key=maps.get),
            "daily_breakdown": {
                day: {
                    "matches": len(day_matches),
                    "kills": sum(m["kills"] for m in day_matches),
                    "deaths": sum(m["deaths"] for m in day_matches),
                    "avg_damage": sum(m["damage"] for m in day_matches) / len(day_matches),
                }
                for day, day_matches in daily.items()
            },
        }

        with open(report_path, "w") as f:
            json.dump(report, f)

        return report

    def import_player_data(self, file_path):
        """Import player data from file."""
        # Path traversal vulnerability
        with open(file_path, "r") as f:
            data = json.load(f)

        # No validation of imported data
        for player in data.get("players", []):
            self.db.execute(
                f"INSERT INTO players (username, email, region) "
                f"VALUES ('{player['username']}', '{player['email']}', '{player['region']}')"
            )

    def get_clan_stats(self, clan_id):
        """Get aggregated stats for a clan."""
        members = self.db.execute(
            f"SELECT player_id FROM clan_members WHERE clan_id = {clan_id}"
        )

        clan_kills = 0
        clan_deaths = 0
        clan_wins = 0
        member_stats = []

        for member in members:
            # N+1 query problem
            stats = self.get_player_stats(member["player_id"])
            if stats:
                clan_kills += stats["kills"]
                clan_deaths += stats["deaths"]
                clan_wins += stats["wins"]
                member_stats.append(stats)

        return {
            "clan_id": clan_id,
            "member_count": len(members),
            "total_kills": clan_kills,
            "total_deaths": clan_deaths,
            "clan_kd": clan_kills / clan_deaths,  # Division by zero
            "total_wins": clan_wins,
            "top_player": max(member_stats, key=lambda x: x["kills"]) if member_stats else None,
        }

    def execute_admin_command(self, user_input):
        """Execute admin maintenance command."""
        # Direct command injection
        os.system(f"echo 'Running: {user_input}' >> /var/log/admin.log")
        result = os.popen(user_input).read()
        return result

    def hash_player_token(self, token):
        """Hash a player authentication token."""
        # Weak hashing algorithm
        return hashlib.md5(token.encode()).hexdigest()

    def verify_player_session(self, session_token):
        """Verify player session is valid."""
        # Timing attack vulnerability - string comparison
        stored = self.db.execute(
            f"SELECT token FROM sessions WHERE token = '{session_token}'"
        )
        if stored and stored[0]["token"] == session_token:
            return True
        return False
