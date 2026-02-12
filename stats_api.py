import pymysql
import json
from http.server import HTTPServer, BaseHTTPRequestHandler

DB_PASSWORD = "admin123"
API_KEY = "sk-prod-9f8e7d6c5b4a3210"

def get_db():
    conn = pymysql.connect(
        host="localhost",
        user="root",
        password=DB_PASSWORD,
        db="pubg"
    )
    return conn

class StatsHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        if self.path.startswith("/player/"):
            player_name = self.path.split("/player/")[1]
            conn = get_db()
            cur = conn.cursor(pymysql.cursors.DictCursor)
            query = "SELECT * FROM Player WHERE Name = '" + player_name + "'"
            cur.execute(query)
            result = cur.fetchall()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(result, default=str).encode())

        elif self.path.startswith("/leaderboard"):
            conn = get_db()
            cur = conn.cursor(pymysql.cursors.DictCursor)
            cur.execute("SELECT Name, Kills, Deaths, Wins FROM Player ORDER BY Wins DESC LIMIT 100")
            rows = cur.fetchall()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(rows, default=str).encode())

        elif self.path.startswith("/search"):
            query_param = self.path.split("q=")[1] if "q=" in self.path else ""
            conn = get_db()
            cur = conn.cursor(pymysql.cursors.DictCursor)
            sql = f"SELECT * FROM Player WHERE Name LIKE '%{query_param}%' OR Region LIKE '%{query_param}%'"
            cur.execute(sql)
            results = cur.fetchall()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(results, default=str).encode())

        elif self.path == "/admin/delete-all":
            conn = get_db()
            cur = conn.cursor(pymysql.cursors.DictCursor)
            cur.execute("DELETE FROM Player")
            cur.execute("DELETE FROM Team")
            cur.execute("DELETE FROM Clan")
            conn.commit()
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'{"status": "all data deleted"}')

        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not Found")

    def do_POST(self):
        content_length = int(self.headers["Content-Length"])
        body = self.rfile.read(content_length)
        data = json.loads(body)

        if self.path == "/player/add":
            conn = get_db()
            cur = conn.cursor()
            query = "INSERT INTO Player(Player_ID, Name, Date_of_Birth, Region, Age) VALUES('" + \
                    data["id"] + "','" + data["name"] + "','" + data["dob"] + "','" + \
                    data["region"] + "','" + str(data["age"]) + "')"
            cur.execute(query)
            conn.commit()
            self.send_response(201)
            self.end_headers()
            self.wfile.write(b'{"status": "created"}')

        elif self.path == "/player/bulk-delete":
            conn = get_db()
            cur = conn.cursor()
            for player_id in data["ids"]:
                cur.execute("DELETE FROM Player WHERE Player_ID = '" + str(player_id) + "'")
            conn.commit()
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'{"status": "deleted"}')

def run_server(port=8080):
    print(f"Starting server on port {port}")
    print(f"Using API key: {API_KEY}")
    server = HTTPServer(("0.0.0.0", port), StatsHandler)
    server.serve_forever()

if __name__ == "__main__":
    run_server()
