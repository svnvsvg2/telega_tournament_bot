"""
Слой работы с базой данных (SQLite / PostgreSQL).
Хранит зарегистрированных участников турнира, статус подтверждения и турнирную сетку.
Автоматически переключается на PostgreSQL, если задана переменная DATABASE_URL (например, на Heroku).
"""
import os
import sqlite3
import random
from contextlib import closing
from datetime import datetime

DB_PATH = "participants.db"

DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

IS_POSTGRES = bool(DATABASE_URL)

if IS_POSTGRES:
    import psycopg2
    import psycopg2.extras


def get_connection():
    if IS_POSTGRES:
        conn = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)
        conn.autocommit = False
        return conn
    else:
        conn = sqlite3.connect(DB_PATH, timeout=10.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA synchronous = NORMAL")
        return conn


def _format_sql(sql: str) -> str:
    if IS_POSTGRES:
        return sql.replace("?", "%s")
    return sql


def _execute(conn, sql: str, params=None):
    formatted_sql = _format_sql(sql)
    if IS_POSTGRES:
        cur = conn.cursor()
        cur.execute(formatted_sql, params or ())
        return cur
    else:
        if params:
            return conn.execute(formatted_sql, params)
        return conn.execute(formatted_sql)


def _fetchone(conn, sql: str, params=None):
    cur = _execute(conn, sql, params)
    res = cur.fetchone()
    if IS_POSTGRES:
        cur.close()
    return res


def _fetchall(conn, sql: str, params=None):
    cur = _execute(conn, sql, params)
    res = cur.fetchall()
    if IS_POSTGRES:
        cur.close()
    return res


def init_db():
    with closing(get_connection()) as conn:
        if IS_POSTGRES:
            _execute(
                conn,
                """
                CREATE TABLE IF NOT EXISTS participants (
                    telegram_id BIGINT PRIMARY KEY,
                    username TEXT,
                    name TEXT NOT NULL,
                    nickname TEXT NOT NULL,
                    registered_at TEXT NOT NULL,
                    confirmed INTEGER DEFAULT 0,
                    confirmed_at TEXT
                )
                """,
            )
            _execute(
                conn,
                """
                CREATE TABLE IF NOT EXISTS matches (
                    id INTEGER PRIMARY KEY,
                    round INTEGER NOT NULL,
                    match_number INTEGER NOT NULL,
                    player1_name TEXT,
                    player1_nickname TEXT,
                    player2_name TEXT,
                    player2_nickname TEXT,
                    score1 INTEGER DEFAULT 0,
                    score2 INTEGER DEFAULT 0,
                    winner_slot INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'pending',
                    next_match_id INTEGER,
                    next_match_slot INTEGER DEFAULT 1,
                    loser_match_id INTEGER,
                    loser_match_slot INTEGER DEFAULT 1,
                    bracket_type TEXT DEFAULT 'winners'
                )
                """,
            )
        else:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS participants (
                    telegram_id INTEGER PRIMARY KEY,
                    username TEXT,
                    name TEXT NOT NULL,
                    nickname TEXT NOT NULL,
                    registered_at TEXT NOT NULL,
                    confirmed INTEGER DEFAULT 0,
                    confirmed_at TEXT
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS matches (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    round INTEGER NOT NULL,
                    match_number INTEGER NOT NULL,
                    player1_name TEXT,
                    player1_nickname TEXT,
                    player2_name TEXT,
                    player2_nickname TEXT,
                    score1 INTEGER DEFAULT 0,
                    score2 INTEGER DEFAULT 0,
                    winner_slot INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'pending',
                    next_match_id INTEGER,
                    next_match_slot INTEGER DEFAULT 1,
                    loser_match_id INTEGER,
                    loser_match_slot INTEGER DEFAULT 1,
                    bracket_type TEXT DEFAULT 'winners'
                )
                """
            )
        conn.commit()


def count_participants() -> int:
    with closing(get_connection()) as conn:
        row = _fetchone(conn, "SELECT COUNT(*) as cnt FROM participants")
        if row:
            return row["cnt"] if isinstance(row, dict) or hasattr(row, "keys") else row[0]
        return 0


def add_participant(telegram_id: int, username: str, name: str, nickname: str):
    with closing(get_connection()) as conn:
        sql = """
            INSERT INTO participants (telegram_id, username, name, nickname, registered_at, confirmed)
            VALUES (?, ?, ?, ?, ?, 0)
            ON CONFLICT(telegram_id) DO UPDATE SET
                username=EXCLUDED.username,
                name=EXCLUDED.name,
                nickname=EXCLUDED.nickname
        """
        _execute(conn, sql, (telegram_id, username, name, nickname, datetime.now().isoformat()))
        conn.commit()


def get_participant(telegram_id: int):
    with closing(get_connection()) as conn:
        return _fetchone(conn, "SELECT * FROM participants WHERE telegram_id=?", (telegram_id,))


def get_all_participants():
    with closing(get_connection()) as conn:
        return _fetchall(conn, "SELECT * FROM participants ORDER BY registered_at")


def get_unconfirmed():
    with closing(get_connection()) as conn:
        return _fetchall(conn, "SELECT * FROM participants WHERE confirmed=0")


def set_confirmed(telegram_id: int, confirmed: bool):
    with closing(get_connection()) as conn:
        _execute(
            conn,
            "UPDATE participants SET confirmed=?, confirmed_at=? WHERE telegram_id=?",
            (1 if confirmed else 0, datetime.now().isoformat() if confirmed else None, telegram_id),
        )
        conn.commit()


def remove_participant(telegram_id: int):
    with closing(get_connection()) as conn:
        _execute(conn, "DELETE FROM participants WHERE telegram_id=?", (telegram_id,))
        conn.commit()


def reset_all():
    """Полностью очищает таблицу участников и сетку."""
    with closing(get_connection()) as conn:
        _execute(conn, "DELETE FROM participants")
        _execute(conn, "DELETE FROM matches")
        conn.commit()


def seed_test_players():
    """Заполняет базу 16 тестовыми игроками и формирует турнирную сетку."""
    test_players = [
        ("Алексей", "Scorpion_PRO", "alex_mk"),
        ("Дмитрий", "SubZero_Ninja", "dima_frost"),
        ("Игорь", "Raiden_God", "thunder_igor"),
        ("Сергей", "LiuKang_Champ", "monk_sergey"),
        ("Максим", "Johnny_Cage", "star_max"),
        ("Артем", "KungLao_Hat", "hat_artem"),
        ("Евгений", "Smoke_Vapor", "smoke_evg"),
        ("Никита", "Reptile_Acid", "green_nik"),
        ("Владимир", "ShaoKahn_King", "emperor_vova"),
        ("Олег", "ShangTsung_Soul", "soul_oleg"),
        ("Михаил", "Baraka_Blades", "tarkatan_misha"),
        ("Роман", "Jax_Arms", "metal_roma"),
        ("Павел", "Kenshi_Sword", "blind_pavel"),
        ("Илья", "Rain_Water", "prince_ilya"),
        ("Денис", "Geras_Time", "sands_denis"),
        ("Кирилл", "Kabal_Speed", "dash_kirill"),
    ]
    with closing(get_connection()) as conn:
        _execute(conn, "DELETE FROM participants")
        now = datetime.now().isoformat()
        for idx, (name, nick, tg_user) in enumerate(test_players, start=1):
            _execute(
                conn,
                """
                INSERT INTO participants (telegram_id, username, name, nickname, registered_at, confirmed, confirmed_at)
                VALUES (?, ?, ?, ?, ?, 1, ?)
                """,
                (1000 + idx, tg_user, name, nick, now, now),
            )
        conn.commit()

    generate_bracket(shuffle=True)
    return True


def import_players(players_list: list):
    """
    Импортирует пользовательский список игроков и формирует турнирную сетку.
    players_list: список словарей [{"name": "Имя", "nickname": "Никнейм"}, ...]
    """
    with closing(get_connection()) as conn:
        _execute(conn, "DELETE FROM participants")
        now = datetime.now().isoformat()
        for idx, player in enumerate(players_list, start=1):
            name = player.get("name", f"Игрок {idx}").strip() or f"Игрок {idx}"
            nickname = player.get("nickname", f"Player_{idx}").strip() or f"Player_{idx}"
            _execute(
                conn,
                """
                INSERT INTO participants (telegram_id, username, name, nickname, registered_at, confirmed, confirmed_at)
                VALUES (?, ?, ?, ?, ?, 1, ?)
                """,
                (9000 + idx, f"imported_{idx}", name, nickname, now, now),
            )
        conn.commit()

    generate_bracket(shuffle=True)
    return len(players_list)


def export_to_csv(filepath: str = "participants_export.csv") -> str:
    """Экспортирует всех участников в CSV-файл."""
    import csv

    rows = get_all_participants()
    with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerow(["ID Telegram", "Username", "Имя", "Никнейм MK1", "Дата регистрации", "Подтверждён", "Дата подтверждения"])
        for r in rows:
            writer.writerow([
                r["telegram_id"],
                f"@{r['username']}" if r["username"] else "",
                r["name"],
                r["nickname"],
                r["registered_at"],
                "Да" if r["confirmed"] else "Нет",
                r["confirmed_at"] or ""
            ])
    return filepath


def generate_bracket(shuffle: bool = True):
    with closing(get_connection()) as conn:
        _execute(conn, "DELETE FROM matches")

        cur_rows = _fetchall(conn, "SELECT name, nickname FROM participants")
        players = [(r["name"], r["nickname"]) for r in cur_rows]

        if shuffle:
            random.shuffle(players)

        while len(players) < 16:
            players.append(("BYE / TBD", f"Участник {len(players)+1}"))

        for i in range(8):
            p1_name, p1_nick = players[i * 2]
            p2_name, p2_nick = players[i * 2 + 1]
            m_id = i + 1
            next_m = 9 + (i // 2)
            next_slot = 1 if (i % 2 == 0) else 2
            loser_m = 16 + (i // 2)
            loser_slot = 1 if (i % 2 == 0) else 2

            _execute(
                conn,
                """
                INSERT INTO matches (id, round, match_number, player1_name, player1_nickname, player2_name, player2_nickname, status, next_match_id, next_match_slot, loser_match_id, loser_match_slot, bracket_type)
                VALUES (?, 1, ?, ?, ?, ?, ?, 'pending', ?, ?, ?, ?, 'winners')
                """,
                (m_id, i + 1, p1_name, p1_nick, p2_name, p2_nick, next_m, next_slot, loser_m, loser_slot),
            )

        wb_r2_config = [
            (9, 1, 13, 1, 20, 2),
            (10, 2, 13, 2, 21, 2),
            (11, 3, 14, 1, 22, 2),
            (12, 4, 14, 2, 23, 2),
        ]
        for m_id, m_num, next_m, next_s, loser_m, loser_s in wb_r2_config:
            _execute(
                conn,
                """
                INSERT INTO matches (id, round, match_number, status, next_match_id, next_match_slot, loser_match_id, loser_match_slot, bracket_type)
                VALUES (?, 2, ?, 'pending', ?, ?, ?, ?, 'winners')
                """,
                (m_id, m_num, next_m, next_s, loser_m, loser_s),
            )

        _execute(conn, "INSERT INTO matches (id, round, match_number, status, next_match_id, next_match_slot, loser_match_id, loser_match_slot, bracket_type) VALUES (13, 3, 1, 'pending', 15, 1, 26, 2, 'winners')")
        _execute(conn, "INSERT INTO matches (id, round, match_number, status, next_match_id, next_match_slot, loser_match_id, loser_match_slot, bracket_type) VALUES (14, 3, 2, 'pending', 15, 2, 27, 2, 'winners')")
        _execute(conn, "INSERT INTO matches (id, round, match_number, status, next_match_id, next_match_slot, loser_match_id, loser_match_slot, bracket_type) VALUES (15, 4, 1, 'pending', 30, 1, 29, 2, 'winners')")

        for i in range(4):
            m_id = 16 + i
            _execute(
                conn,
                "INSERT INTO matches (id, round, match_number, status, next_match_id, next_match_slot, bracket_type) VALUES (?, 1, ?, 'pending', ?, 1, 'losers')",
                (m_id, i + 1, 20 + i),
            )

        _execute(conn, "INSERT INTO matches (id, round, match_number, status, next_match_id, next_match_slot, bracket_type) VALUES (20, 2, 1, 'pending', 24, 1, 'losers')")
        _execute(conn, "INSERT INTO matches (id, round, match_number, status, next_match_id, next_match_slot, bracket_type) VALUES (21, 2, 2, 'pending', 24, 2, 'losers')")
        _execute(conn, "INSERT INTO matches (id, round, match_number, status, next_match_id, next_match_slot, bracket_type) VALUES (22, 2, 3, 'pending', 25, 1, 'losers')")
        _execute(conn, "INSERT INTO matches (id, round, match_number, status, next_match_id, next_match_slot, bracket_type) VALUES (23, 2, 4, 'pending', 25, 2, 'losers')")

        _execute(conn, "INSERT INTO matches (id, round, match_number, status, next_match_id, next_match_slot, bracket_type) VALUES (24, 3, 1, 'pending', 26, 1, 'losers')")
        _execute(conn, "INSERT INTO matches (id, round, match_number, status, next_match_id, next_match_slot, bracket_type) VALUES (25, 3, 2, 'pending', 27, 1, 'losers')")

        _execute(conn, "INSERT INTO matches (id, round, match_number, status, next_match_id, next_match_slot, bracket_type) VALUES (26, 4, 1, 'pending', 28, 1, 'losers')")
        _execute(conn, "INSERT INTO matches (id, round, match_number, status, next_match_id, next_match_slot, bracket_type) VALUES (27, 4, 2, 'pending', 28, 2, 'losers')")

        _execute(conn, "INSERT INTO matches (id, round, match_number, status, next_match_id, next_match_slot, bracket_type) VALUES (28, 5, 1, 'pending', 29, 1, 'losers')")
        _execute(conn, "INSERT INTO matches (id, round, match_number, status, next_match_id, next_match_slot, bracket_type) VALUES (29, 6, 1, 'pending', 30, 2, 'losers')")

        _execute(conn, "INSERT INTO matches (id, round, match_number, status, next_match_id, next_match_slot, bracket_type) VALUES (30, 1, 1, 'pending', 31, 1, 'grand_final')")
        _execute(conn, "INSERT INTO matches (id, round, match_number, status, bracket_type) VALUES (31, 1, 1, 'pending', 'reset')")

        conn.commit()


def get_all_matches():
    with closing(get_connection()) as conn:
        rows = _fetchall(conn, "SELECT * FROM matches ORDER BY id")
        dict_rows = [dict(r) for r in rows]

        bracket = {
            "winners": {1: [], 2: [], 3: [], 4: []},
            "losers": {1: [], 2: [], 3: [], 4: [], 5: [], 6: []},
            "grand_final": [],
            "reset": [],
        }

        for r in dict_rows:
            b_type = r.get("bracket_type", "winners")
            rnd = r.get("round", 1)
            if b_type == "winners":
                if rnd not in bracket["winners"]:
                    bracket["winners"][rnd] = []
                bracket["winners"][rnd].append(r)
            elif b_type == "losers":
                if rnd not in bracket["losers"]:
                    bracket["losers"][rnd] = []
                bracket["losers"][rnd].append(r)
            elif b_type == "grand_final":
                bracket["grand_final"].append(r)
            elif b_type == "reset":
                bracket["reset"].append(r)

        return bracket


def update_match(
    match_id: int,
    score1: int,
    score2: int,
    status: str,
    winner_slot: int,
    player1_name: str = None,
    player1_nickname: str = None,
    player2_name: str = None,
    player2_nickname: str = None,
):
    with closing(get_connection()) as conn:
        m = _fetchone(conn, "SELECT * FROM matches WHERE id=?", (match_id,))
        if not m:
            return None

        p1_name = player1_name if player1_name is not None else m["player1_name"]
        p1_nick = player1_nickname if player1_nickname is not None else m["player1_nickname"]
        p2_name = player2_name if player2_name is not None else m["player2_name"]
        p2_nick = player2_nickname if player2_nickname is not None else m["player2_nickname"]

        _execute(
            conn,
            """
            UPDATE matches SET
                player1_name=?, player1_nickname=?,
                player2_name=?, player2_nickname=?,
                score1=?, score2=?, status=?, winner_slot=?
            WHERE id=?
            """,
            (p1_name, p1_nick, p2_name, p2_nick, score1, score2, status, winner_slot, match_id),
        )

        m = _fetchone(conn, "SELECT * FROM matches WHERE id=?", (match_id,))

        winner_name, winner_nick = None, None
        loser_name, loser_nick = None, None

        if winner_slot == 1:
            winner_name, winner_nick = m["player1_name"], m["player1_nickname"]
            loser_name, loser_nick = m["player2_name"], m["player2_nickname"]
        elif winner_slot == 2:
            winner_name, winner_nick = m["player2_name"], m["player2_nickname"]
            loser_name, loser_nick = m["player1_name"], m["player1_nickname"]

        if status == "completed" and winner_slot > 0:
            if m["next_match_id"]:
                next_id = m["next_match_id"]
                slot = m["next_match_slot"]
                if slot == 1:
                    _execute(
                        conn,
                        "UPDATE matches SET player1_name=?, player1_nickname=? WHERE id=?",
                        (winner_name, winner_nick, next_id),
                    )
                else:
                    _execute(
                        conn,
                        "UPDATE matches SET player2_name=?, player2_nickname=? WHERE id=?",
                        (winner_name, winner_nick, next_id),
                    )

            if m["loser_match_id"]:
                loser_id = m["loser_match_id"]
                l_slot = m["loser_match_slot"]
                if l_slot == 1:
                    _execute(
                        conn,
                        "UPDATE matches SET player1_name=?, player1_nickname=? WHERE id=?",
                        (loser_name, loser_nick, loser_id),
                    )
                else:
                    _execute(
                        conn,
                        "UPDATE matches SET player2_name=?, player2_nickname=? WHERE id=?",
                        (loser_name, loser_nick, loser_id),
                    )

            if match_id == 30:
                if winner_slot == 1:
                    _execute(conn, "UPDATE matches SET status='not_needed' WHERE id=31")
                elif winner_slot == 2:
                    _execute(
                        conn,
                        """
                        UPDATE matches SET
                            player1_name=?, player1_nickname=?,
                            player2_name=?, player2_nickname=?,
                            status='pending'
                        WHERE id=31
                        """,
                        (winner_name, winner_nick, loser_name, loser_nick),
                    )

        conn.commit()
        return True


def reset_bracket():
    with closing(get_connection()) as conn:
        _execute(conn, "DELETE FROM matches")
        conn.commit()
