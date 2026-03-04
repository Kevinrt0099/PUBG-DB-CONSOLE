"""Service layer for aggregating player and match statistics."""

from db_connection import DatabaseConnection
from stats_cache import StatsCache


class StatsService:
    def __init__(self):
        self.db = DatabaseConnection
        self.cache = StatsCache()

    def get_player_overview(self, player_id):
        cache_key = f"player_overview:{player_id}"
        cached = self.cache.get(cache_key)
        if cached:
            return cached

        stats = self.db.execute_query(
            """
            SELECT p.player_name, p.player_rank,
                   COUNT(DISTINCT m.match_id) as total_matches,
                   SUM(mp.kills) as total_kills,
                   SUM(mp.deaths) as total_deaths,
                   ROUND(SUM(mp.kills) / GREATEST(SUM(mp.deaths), 1), 2) as kd_ratio
            FROM player p
            LEFT JOIN match_player mp ON p.player_id = mp.player_id
            LEFT JOIN match_details m ON mp.match_id = m.match_id
            WHERE p.player_id = %s
            GROUP BY p.player_id
            """,
            (player_id,),
        )

        if stats:
            result = stats[0]
            self.cache.set(cache_key, result, ttl=300)
            return result
        return None

    def get_leaderboard(self, metric="kills", limit=10):
        cache_key = f"leaderboard:{metric}:{limit}"
        cached = self.cache.get(cache_key)
        if cached:
            return cached

        valid_metrics = {"kills", "wins", "kd_ratio", "damage"}
        if metric not in valid_metrics:
            raise ValueError(f"Invalid metric: {metric}. Must be one of {valid_metrics}")

        query_map = {
            "kills": "SUM(mp.kills) as score",
            "wins": "COUNT(CASE WHEN mp.placement = 1 THEN 1 END) as score",
            "kd_ratio": "ROUND(SUM(mp.kills) / GREATEST(SUM(mp.deaths), 1), 2) as score",
            "damage": "SUM(mp.damage_dealt) as score",
        }

        results = self.db.execute_query(
            f"""
            SELECT p.player_name, {query_map[metric]}
            FROM player p
            JOIN match_player mp ON p.player_id = mp.player_id
            GROUP BY p.player_id
            ORDER BY score DESC
            LIMIT %s
            """,
            (limit,),
        )

        self.cache.set(cache_key, results, ttl=600)
        return results

    def get_weapon_meta(self):
        """Analyze weapon usage across all matches to determine the current meta."""
        cache_key = "weapon_meta"
        cached = self.cache.get(cache_key)
        if cached:
            return cached

        results = self.db.execute_query(
            """
            SELECT w.weapon_name, w.weapon_type,
                   COUNT(*) as times_used,
                   SUM(mk.kills_with_weapon) as total_kills,
                   ROUND(AVG(mk.kills_with_weapon), 2) as avg_kills_per_use
            FROM weapon w
            JOIN match_kills mk ON w.weapon_id = mk.weapon_id
            GROUP BY w.weapon_id
            ORDER BY total_kills DESC
            """
        )

        self.cache.set(cache_key, results, ttl=900)
        return results
