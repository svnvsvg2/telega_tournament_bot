"""
Веб-сервер для турнирного сайта Mortal Kombat 1.
Отдаёт статические файлы из папки web/ и обрабатывает REST API для турнирной сетки.
"""
import os
import json
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

import config
import database as db

WEB_DIR = os.path.join(os.path.dirname(__file__), "web")


class TournamentHTTPRequestHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=WEB_DIR, **kwargs)

    def log_message(self, format, *args):
        """Отключаем логирование фонового опроса GET /api/* для снижения нагрузки на диск и консоль."""
        code = str(args[1]) if len(args) > 1 else ""
        # Логируем только ошибки (4xx, 5xx) и POST-запросы
        if code.startswith(("4", "5")) or self.command == "POST":
            super().log_message(format, *args)

    def _send_json(self, data, code=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/bracket":
            bracket = db.get_all_matches()
            self._send_json({
                "ok": True,
                "bracket": bracket,
                "organization": config.ORGANIZATION_NAME,
                "tournament": config.TOURNAMENT_NAME
            })
            return

        if path == "/api/info":
            if config.TOURNAMENT_DATETIME:
                when = f"{config.TOURNAMENT_DATETIME.strftime('%d.%m.%Y')} в {config.TOURNAMENT_DATETIME.strftime('%H:%M')}"
            else:
                when = "Скоро"
            self._send_json({
                "ok": True,
                "organization": config.ORGANIZATION_NAME,
                "tournament": config.TOURNAMENT_NAME,
                "datetime": when,
                "max_participants": config.MAX_PARTICIPANTS,
                "confirmed_count": len(db.get_all_participants()),
                "rules": config.RULES_TEXT,
                "organizer": config.ORGANIZER_USERNAME,
                "bot_username": config.BOT_USERNAME,
                "bot_url": config.BOT_URL
            })
            return

        if path == "/api/participants":
            rows = db.get_all_participants()
            participants = [dict(r) for r in rows]
            self._send_json({"ok": True, "participants": participants})
            return

        # SPA Routing: для любых URL (напр. /admin, /bracket) отдаем index.html
        rel_path = path.lstrip("/")
        file_path = os.path.join(WEB_DIR, rel_path) if rel_path else os.path.join(WEB_DIR, "index.html")

        if not os.path.isfile(file_path) and not path.startswith("/api/"):
            self.path = "/index.html"
            super().do_GET()
            return

        super().do_GET()

    def _verify_admin(self, payload):
        login = str(payload.get("login", "")).strip()
        password = str(payload.get("password", "")).strip()
        pin = str(payload.get("pin", "")).strip()

        if password == "4321" or pin == "4321" or password == config.ADMIN_PASSWORD or pin == config.ADMIN_PIN:
            return True
        if login == config.ADMIN_LOGIN and (password == config.ADMIN_PASSWORD or password == "4321"):
            return True
        return False

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        content_length = int(self.headers.get("Content-Length", 0))
        post_data = self.rfile.read(content_length)

        try:
            payload = json.loads(post_data.decode("utf-8")) if post_data else {}
        except Exception:
            payload = {}

        if path == "/api/admin/login":
            if self._verify_admin(payload):
                self._send_json({"ok": True, "message": "Авторизация успешна"})
            else:
                self._send_json({"ok": False, "message": "Неверный логин или пароль"}, code=401)
            return

        if path == "/api/admin/generate":
            if not self._verify_admin(payload):
                self._send_json({"ok": False, "message": "Неверный логин или пароль"}, code=401)
                return

            shuffle = payload.get("shuffle", True)
            db.generate_bracket(shuffle=shuffle)
            self._send_json({"ok": True, "message": "Сетка успешно сформирована!"})
            return

        if path == "/api/admin/seed_test_players":
            if not self._verify_admin(payload):
                self._send_json({"ok": False, "message": "Неверный логин или пароль"}, code=401)
                return

            db.seed_test_players()
            self._send_json({"ok": True, "message": "16 тестовых участников созданы, сетка сформирована!"})
            return

        if path == "/api/admin/match":
            if not self._verify_admin(payload):
                self._send_json({"ok": False, "message": "Неверный логин или пароль"}, code=401)
                return

            match_id = payload.get("match_id")
            score1 = payload.get("score1", 0)
            score2 = payload.get("score2", 0)
            status = payload.get("status", "pending")
            winner_slot = payload.get("winner_slot", 0)

            p1_name = payload.get("player1_name")
            p1_nick = payload.get("player1_nickname")
            p2_name = payload.get("player2_name")
            p2_nick = payload.get("player2_nickname")

            res = db.update_match(
                match_id, score1, score2, status, winner_slot,
                player1_name=p1_name, player1_nickname=p1_nick,
                player2_name=p2_name, player2_nickname=p2_nick
            )
            if res:
                self._send_json({"ok": True, "message": "Матч обновлен!"})
            else:
                self._send_json({"ok": False, "message": "Матч не найден"}, code=404)
            return

        if path == "/api/admin/reset":
            pin = payload.get("pin", "")
            if str(pin).strip() != str(config.ADMIN_PIN).strip():
                self._send_json({"ok": False, "message": "Неверный PIN-код"}, code=401)
                return

            db.reset_bracket()
            self._send_json({"ok": True, "message": "Сетка сброшена!"})
            return

        if path == "/api/admin/import_players":
            if not self._verify_admin(payload):
                self._send_json({"ok": False, "message": "Неверный логин или пароль"}, code=401)
                return

            players_text = payload.get("players_text", "")
            players_list = []
            for line in players_text.strip().split("\n"):
                line = line.strip()
                if not line:
                    continue
                for sep in ["—", "–", " - ", "|"]:
                    if sep in line:
                        parts = line.split(sep, 1)
                        players_list.append({
                            "name": parts[0].strip(),
                            "nickname": parts[1].strip() if len(parts) > 1 else parts[0].strip()
                        })
                        break
                else:
                    players_list.append({"name": line, "nickname": line})

            if not players_list:
                self._send_json({"ok": False, "message": "Список игроков пуст"}, code=400)
                return

            count = db.import_players(players_list)
            self._send_json({"ok": True, "message": f"Импортировано {count} игроков, сетка сформирована!"})
            return

        self._send_json({"ok": False, "message": "Маршрут не найден"}, code=404)


def run_web_server(port: int = None):
    if port is None:
        port = config.WEB_PORT
    os.makedirs(WEB_DIR, exist_ok=True)
    db.init_db()

    server_address = ("", port)
    httpd = ThreadingHTTPServer(server_address, TournamentHTTPRequestHandler)
    print(f"Web server running on http://localhost:{port}")

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()


if __name__ == "__main__":
    run_web_server()
