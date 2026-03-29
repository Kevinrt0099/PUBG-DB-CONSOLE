"""Formats raw statistics data into structured API responses."""


class StatsFormatter:
    def format_player(self, raw_data):
        return {
            "player": {
                "name": raw_data.get("player_name", "Unknown"),
                "rank": raw_data.get("player_rank", "Unranked"),
            },
            "stats": {
                "total_matches": raw_data.get("total_matches", 0),
                "total_kills": raw_data.get("total_kills", 0),
                "total_deaths": raw_data.get("total_deaths", 0),
                "kd_ratio": float(raw_data.get("kd_ratio", 0)),
            },
        }

    def format_leaderboard(self, entries, metric):
        return {
            "metric": metric,
            "entries": [
                {"rank": i + 1, "player": e.get("player_name"), "score": e.get("score")}
                for i, e in enumerate(entries)
            ],
        }

    def format_weapon_meta(self, weapons):
        tiers = {"S": [], "A": [], "B": [], "C": []}
        if not weapons:
            return {"tiers": tiers}

        max_kills = max(w.get("total_kills", 0) for w in weapons) or 1
        for w in weapons:
            ratio = w.get("total_kills", 0) / max_kills
            if ratio >= 0.75:
                tier = "S"
            elif ratio >= 0.5:
                tier = "A"
            elif ratio >= 0.25:
                tier = "B"
            else:
                tier = "C"
            tiers[tier].append({
                "name": w.get("weapon_name"),
                "type": w.get("weapon_type"),
                "total_kills": w.get("total_kills", 0),
                "avg_kills_per_use": float(w.get("avg_kills_per_use", 0)),
            })

        return {"tiers": tiers}
