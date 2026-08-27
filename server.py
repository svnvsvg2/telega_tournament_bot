"""
Веб-сервер для турнирного сайта Mortal Kombat 1.
Отдаёт статистические файлы из папки web/ и обрабатывает REST API для турнирной сетки.
"""
import os
import json
from http.server import HTTPServer, SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

import config
import database as db

WEB_DIR = os.path.join(os.path.dirname(__file__), "web")


class TournamentHTTPRequestHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=WEB_DIR, **kwargs)

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
            db.init_db()
            bracket = db.get_all_matches()
            self._send_json({
                "ok": True,
                "bracket": bracket,
                "organization": config.ORGANIZATION_NAME,
                "tournament": config.TOURNAMENT_NAME
            })
            return

        if path == "/api/info":
            db.init_db()
            when = config.TOURNAMENT_DATETIME.strftime("%d.%m.%Y в %H:%M") if config.TOURNAMENT_DATETIME else "Скоро"
            self._send_json({
                "ok": True,
                "organization": config.ORGANIZATION_NAME,
                "tournament": config.TOURNAMENT_NAME,
                "datetime": when,
                "max_participants": config.MAX_PARTICIPANTS,
                "confirmed_count": len(db.get_all_participants()),
                "rules": config.RULES_TEXT,
                "organizer": config.ORGANIZER_USERNAME
            })
            return

        if path == "/api/participants":
            db.init_db()
            rows = db.get_all_participants()
            participants = [dict(r) for r in rows]
            self._send_json({"ok": True, "participants": participants})
            return

        if path in ("/admin", "/admin/"):
            self.path = "/index.html"
            super().do_GET()
            return

        # Для статических файлов отдаем через SimpleHTTPRequestHandler
        super().do_GET()

    def _verify_admin(self, payload):
        login = str(payload.get("login", "")).strip()
        password = str(payload.get("password", "")).strip()
        pin = str(payload.get("pin", "")).strip()

        if (login == config.ADMIN_LOGIN and password == config.ADMIN_PASSWORD) or (pin == config.ADMIN_PIN):
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
            db.init_db()
            db.generate_bracket(shuffle=shuffle)
            self._send_json({"ok": True, "message": "Сетка успешно сформирована!"})
            return

        if path == "/api/admin/seed_test_players":
            if not self._verify_admin(payload):
                self._send_json({"ok": False, "message": "Неверный логин или пароль"}, code=401)
                return

            db.init_db()
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

            db.init_db()
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

            db.init_db()
            db.reset_bracket()
            self._send_json({"ok": True, "message": "Сетка сброшена!"})
            return

        self._send_json({"ok": False, "message": "Маршрут не найден"}, code=404)


def run_web_server(port: int = None):
    if port is None:
        port = config.WEB_PORT
    os.makedirs(WEB_DIR, exist_ok=True)
    server_address = ("", port)
    httpd = ThreadingHTTPServer(server_address, TournamentHTTPRequestHandler)
    print(f"Веб-сервер турнира запущен на http://localhost:{port}")

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()


if __name__ == "__main__":
    run_web_server()
