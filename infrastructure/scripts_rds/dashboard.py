import http.server
import socketserver
import json
import os
import urllib.parse
import boto3
import psycopg2
from threading import Thread

# Config
PORT = 5000
AURORA_ENDPOINT = os.environ.get("AURORA_ENDPOINT")
DB_REGION = os.environ.get("DB_REGION", "us-east-1")
DB_USER = os.environ.get("DB_USER", "postgres")
DB_NAME = os.environ.get("DB_NAME", "postgres")

class DashboardHandler(http.server.SimpleHTTPRequestHandler):
    def get_conn(self):
        rds_client = boto3.client('rds', region_name=DB_REGION)
        token = rds_client.generate_db_auth_token(DBHostname=AURORA_ENDPOINT, Port=5432, DBUsername=DB_USER)
        return psycopg2.connect(host=AURORA_ENDPOINT, port=5432, database=DB_NAME, user=DB_USER, password=token, sslmode='require')

    def do_GET(self):
        parsed_path = urllib.parse.urlparse(self.path)
        if parsed_path.path == "/":
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(HTML_CONTENT.encode())
        elif parsed_path.path == "/api/tables":
            self.handle_api_tables()
        elif parsed_path.path == "/api/data":
            query = urllib.parse.parse_qs(parsed_path.query)
            table = query.get("table", ["stops"])[0]
            self.handle_api_data(table)
        else:
            self.send_error(404)

    def handle_api_tables(self):
        try:
            conn = self.get_conn()
            cur = conn.cursor()
            cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
            tables = [row[0] for row in cur.fetchall()]
            counts = {}
            for t in tables:
                cur.execute(f"SELECT COUNT(*) FROM {t}")
                counts[t] = cur.fetchone()[0]
            cur.close()
            conn.close()
            self.send_json({"tables": tables, "counts": counts})
        except Exception as e:
            self.send_json({"error": str(e)}, 500)

    def handle_api_data(self, table):
        try:
            conn = self.get_conn()
            cur = conn.cursor()
            allowed = ["stops", "routes", "calendar", "trips", "stop_times"]
            if table not in allowed: raise Exception("Invalid table")
            cur.execute(f"SELECT * FROM {table} LIMIT 100")
            colnames = [desc[0] for desc in cur.description]
            rows = [dict(zip(colnames, row)) for row in cur.fetchall()]
            cur.close()
            conn.close()
            self.send_json({"columns": colnames, "rows": data if 'data' in locals() else rows})
        except Exception as e:
            self.send_json({"error": str(e)}, 500)

    def send_json(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, default=str).encode())

HTML_CONTENT = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Aurora GTFS Explorer</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg: #0f172a;
            --sidebar: #1e293b;
            --card: #1e293b;
            --accent: #38bdf8;
            --text: #f8fafc;
            --text-muted: #94a3b8;
            --border: #334155;
            --glass: rgba(30, 41, 59, 0.7);
        }

        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: 'Inter', sans-serif; 
            background: var(--bg); 
            color: var(--text);
            display: flex;
            height: 100vh;
            overflow: hidden;
        }

        /* Sidebar */
        aside {
            width: 280px;
            background: var(--sidebar);
            border-right: 1px solid var(--border);
            display: flex;
            flex-direction: column;
            padding: 2rem 1.5rem;
        }

        h1 {
            font-size: 1.25rem;
            font-weight: 700;
            margin-bottom: 2.5rem;
            display: flex;
            align-items: center;
            gap: 0.75rem;
            color: var(--accent);
        }

        .nav-item {
            padding: 0.75rem 1rem;
            border-radius: 0.5rem;
            cursor: pointer;
            transition: all 0.2s;
            margin-bottom: 0.5rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
            color: var(--text-muted);
        }

        .nav-item:hover {
            background: rgba(56, 189, 248, 0.1);
            color: var(--text);
        }

        .nav-item.active {
            background: var(--accent);
            color: var(--bg);
            font-weight: 600;
        }

        .count-badge {
            font-size: 0.7rem;
            background: rgba(0,0,0,0.2);
            padding: 0.2rem 0.5rem;
            border-radius: 1rem;
        }

        /* Main Content */
        main {
            flex: 1;
            padding: 2rem;
            overflow-y: auto;
            background: radial-gradient(circle at top right, #1e293b, #0f172a);
        }

        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 2rem;
        }

        .card {
            background: var(--glass);
            backdrop-filter: blur(12px);
            border: 1px solid var(--border);
            border-radius: 1rem;
            padding: 1.5rem;
            box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.3);
        }

        /* Table Styles */
        .table-container {
            width: 100%;
            overflow-x: auto;
            border-radius: 0.5rem;
        }

        table {
            width: 100%;
            border-collapse: collapse;
            text-align: left;
            font-size: 0.875rem;
        }

        th {
            background: rgba(255,255,255,0.05);
            padding: 1rem;
            font-weight: 600;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.05em;
            border-bottom: 1px solid var(--border);
        }

        td {
            padding: 1rem;
            border-bottom: 1px solid var(--border);
            color: var(--text);
            max-width: 200px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }

        tr:hover td {
            background: rgba(255,255,255,0.02);
        }

        /* Loading Animation */
        .loader {
            width: 24px;
            height: 24px;
            border: 3px solid rgba(56, 189, 248, 0.3);
            border-radius: 50%;
            border-top-color: var(--accent);
            animation: spin 1s linear infinite;
        }

        @keyframes spin {
            to { transform: rotate(360deg); }
        }

        .status-pill {
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            padding: 0.4rem 0.8rem;
            background: rgba(34, 197, 94, 0.1);
            color: #4ade80;
            border-radius: 2rem;
            font-size: 0.75rem;
            font-weight: 600;
        }

        ::-webkit-scrollbar { width: 8px; height: 8px; }
        ::-webkit-scrollbar-track { background: var(--bg); }
        ::-webkit-scrollbar-thumb { background: var(--border); border-radius: 4px; }
        ::-webkit-scrollbar-thumb:hover { background: var(--text-muted); }

    </style>
</head>
<body>
    <aside>
        <h1>
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
            DSQL Explorer
        </h1>
        <div id="table-list">
            <div class="nav-item">Loading tables...</div>
        </div>
    </aside>

    <main>
        <div class="header">
            <div>
                <h2 id="current-table-name">Select a table</h2>
                <p style="color: var(--text-muted); font-size: 0.9rem; margin-top: 0.25rem;">Showing latest 100 records from AWS Aurora DSQL</p>
            </div>
            <div class="status-pill">
                <span style="width: 8px; height: 8px; background: #22c55e; border-radius: 50%;"></span>
                Connected to {region}
            </div>
        </div>

        <div class="card">
            <div id="data-view" class="table-container">
                <div style="display: flex; flex-direction: column; align-items: center; padding: 4rem; color: var(--text-muted);">
                    <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1" stroke-linecap="round" stroke-linejoin="round" style="margin-bottom: 1rem; opacity: 0.5;"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/></svg>
                    <p>Select a table from the sidebar to explore your GTFS data</p>
                </div>
            </div>
        </div>
    </main>

    <script>
        let currentTable = '';

        async function fetchTables() {
            const res = await fetch('/api/tables');
            const data = await res.json();
            const list = document.getElementById('table-list');
            list.innerHTML = '';
            
            const tableOrder = ['stops', 'routes', 'calendar', 'trips', 'stop_times'];
            
            tableOrder.forEach(name => {
                if (!data.counts.hasOwnProperty(name)) return;
                const item = document.createElement('div');
                item.className = 'nav-item' + (currentTable === name ? ' active' : '');
                item.innerHTML = `
                    <span>${name}</span>
                    <span class="count-badge">${data.counts[name].toLocaleString()}</span>
                `;
                item.onclick = () => loadTable(name);
                list.appendChild(item);
            });
        }

        async function loadTable(name) {
            currentTable = name;
            document.getElementById('current-table-name').innerText = name.toUpperCase();
            document.getElementById('data-view').innerHTML = '<div style="padding: 4rem; display: flex; justify-content: center;"><div class="loader"></div></div>';
            
            // Update active state in sidebar
            document.querySelectorAll('.nav-item').forEach(el => {
                el.classList.toggle('active', el.querySelector('span').innerText === name);
            });

            try {
                const res = await fetch(`/api/data?table=${name}`);
                const data = await res.json();
                
                if (data.error) {
                    document.getElementById('data-view').innerHTML = `<div style="color: #ef4444; padding: 2rem;">Error: ${data.error}</div>`;
                    return;
                }

                let html = '<table><thead><tr>';
                data.columns.forEach(col => html += `<th>${col}</th>`);
                html += '</tr></thead><tbody>';
                
                data.rows.forEach(row => {
                    html += '<tr>';
                    data.columns.forEach(col => {
                        html += `<td>${row[col] === null ? '<span style="opacity:0.3">null</span>' : row[col]}</td>`;
                    });
                    html += '</tr>';
                });
                
                html += '</tbody></table>';
                document.getElementById('data-view').innerHTML = html;
            } catch (e) {
                document.getElementById('data-view').innerHTML = `<div style="color: #ef4444; padding: 2rem;">Error connecting to DSQL: ${e}</div>`;
            }
        }

        fetchTables();
    </script>
</body>
</html>
""".replace("{region}", DB_REGION)

if __name__ == "__main__":
    if not DSQL_ENDPOINT:
        print("Error: DSQL_ENDPOINT environment variable not set.")
    else:
        print(f"Starting GTFS Explorer on http://localhost:{PORT}")
        with socketserver.TCPServer(("", PORT), DashboardHandler) as httpd:
            try:
                httpd.serve_forever()
            except KeyboardInterrupt:
                pass
            finally:
                httpd.server_close()
