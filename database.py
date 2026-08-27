"""
Слой работы с базой данных (SQLite).
Хранит зарегистрированных участников турнира, статус подтверждения и турнирную сетку.
"""
import sqlite3
import random
from contextlib import closing
from datetime import datetime

DB_PATH = "participants.db"


def init_db():
    with closing(sqlite3.connect(DB_PATH)) as conn:
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
        # Миграция колонок для существующей БД
        for col, col_def in [
            ("loser_match_id", "INTEGER"),
            ("loser_match_slot", "INTEGER DEFAULT 1"),
            ("bracket_type", "TEXT DEFAULT 'winners'"),
        ]:
            try:
                conn.execute(f"ALTER TABLE matches ADD COLUMN {col} {col_def}")
            except sqlite3.OperationalError:
                pass
        conn.commit()


def count_participants() -> int:
    with closing(sqlite3.connect(DB_PATH)) as conn:
        cur = conn.execute("SELECT COUNT(*) FROM participants")
        return cur.fetchone()[0]


def add_participant(telegram_id: int, username: str, name: str, nickname: str):
    with closing(sqlite3.connect(DB_PATH)) as conn:
        conn.execute(
            """
            INSERT INTO participants (telegram_id, username, name, nickname, registered_at, confirmed)
            VALUES (?, ?, ?, ?, ?, 0)
            ON CONFLICT(telegram_id) DO UPDATE SET
                username=excluded.username,
                name=excluded.name,
                nickname=excluded.nickname
            """,
            (telegram_id, username, name, nickname, datetime.now().isoformat()),
        )
        conn.commit()


def get_participant(telegram_id: int):
    with closing(sqlite3.connect(DB_PATH)) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.execute("SELECT * FROM participants WHERE telegram_id=?", (telegram_id,))
        return cur.fetchone()


def get_all_participants():
    with closing(sqlite3.connect(DB_PATH)) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.execute("SELECT * FROM participants ORDER BY registered_at")
        return cur.fetchall()


def get_unconfirmed():
    with closing(sqlite3.connect(DB_PATH)) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.execute("SELECT * FROM participants WHERE confirmed=0")
        return cur.fetchall()


def set_confirmed(telegram_id: int, confirmed: bool):
    with closing(sqlite3.connect(DB_PATH)) as conn:
        conn.execute(
            "UPDATE participants SET confirmed=?, confirmed_at=? WHERE telegram_id=?",
            (1 if confirmed else 0, datetime.now().isoformat() if confirmed else None, telegram_id),
        )
        conn.commit()


def remove_participant(telegram_id: int):
    with closing(sqlite3.connect(DB_PATH)) as conn:
        conn.execute("DELETE FROM participants WHERE telegram_id=?", (telegram_id,))
        conn.commit()


def reset_all():
    """Полностью очищает таблицу участников и сетку."""
    with closing(sqlite3.connect(DB_PATH)) as conn:
        conn.execute("DELETE FROM participants")
        conn.execute("DELETE FROM matches")
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
    with closing(sqlite3.connect(DB_PATH)) as conn:
        conn.execute("DELETE FROM participants")
        now = datetime.now().isoformat()
        for idx, (name, nick, tg_user) in enumerate(test_players, start=1):
            conn.execute(
                """
                INSERT INTO participants (telegram_id, username, name, nickname, registered_at, confirmed, confirmed_at)
                VALUES (?, ?, ?, ?, ?, 1, ?)
                """,
                (1000 + idx, tg_user, name, nick, now, now),
            )
        conn.commit()

    generate_bracket(shuffle=True)
    return True


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


# ---------- Логика турнирной сетки (Double Elimination) ----------

def generate_bracket(shuffle: bool = True):
    """
    Генерирует турнирную сетку на 16 участников по системе Double Elimination.
    Все матчи Bo1, Гранд-Финал Bo5.
    Матчи 1..15: Верхняя сетка (WB)
    Матчи 16..29: Сетка Лузеров (LB)
    Матч 30: Гранд-Финал (GF)
    Матч 31: Сброс Сетки (Reset)
    """
    with closing(sqlite3.connect(DB_PATH)) as conn:
        conn.execute("DELETE FROM matches")

        cur = conn.execute("SELECT name, nickname FROM participants")
        players = list(cur.fetchall())

        if shuffle:
            random.shuffle(players)

        while len(players) < 16:
            players.append(("BYE / TBD", f"Участник {len(players)+1}"))

        # --- 1. ВЕРХНЯЯ СЕТКА (WINNERS BRACKET) ---
        # WB R1 (1/8 финала WB): Матчи 1..8
        # Победители -> М9..М12 (slot 1 или 2), Проигравшие -> М16..М19 (slot 1 или 2)
        for i in range(8):
            p1_name, p1_nick = players[i * 2]
            p2_name, p2_nick = players[i * 2 + 1]
            m_id = i + 1
            next_m = 9 + (i // 2)
            next_slot = 1 if (i % 2 == 0) else 2
            loser_m = 16 + (i // 2)
            loser_slot = 1 if (i % 2 == 0) else 2

            conn.execute(
                """
                INSERT INTO matches (id, round, match_number, player1_name, player1_nickname, player2_name, player2_nickname, status, next_match_id, next_match_slot, loser_match_id, loser_match_slot, bracket_type)
                VALUES (?, 1, ?, ?, ?, ?, ?, 'pending', ?, ?, ?, ?, 'winners')
                """,
                (m_id, i + 1, p1_name, p1_nick, p2_name, p2_nick, next_m, next_slot, loser_m, loser_slot),
            )

        # WB R2 (1/4 финала WB): Матчи 9..12
        # Победители -> М13, М14. Проигравшие -> М20..М23 (slot 2)
        wb_r2_config = [
            (9, 1, 13, 1, 20, 2),
            (10, 2, 13, 2, 21, 2),
            (11, 3, 14, 1, 22, 2),
            (12, 4, 14, 2, 23, 2),
        ]
        for m_id, m_num, next_m, next_s, loser_m, loser_s in wb_r2_config:
            conn.execute(
                """
                INSERT INTO matches (id, round, match_number, status, next_match_id, next_match_slot, loser_match_id, loser_match_slot, bracket_type)
                VALUES (?, 2, ?, 'pending', ?, ?, ?, ?, 'winners')
                """,
                (m_id, m_num, next_m, next_s, loser_m, loser_s),
            )

        # WB R3 (1/2 финала WB): Матчи 13, 14
        # Победители -> М15. Проигравшие -> М26, М27 (slot 2)
        conn.execute("INSERT INTO matches (id, round, match_number, status, next_match_id, next_match_slot, loser_match_id, loser_match_slot, bracket_type) VALUES (13, 3, 1, 'pending', 15, 1, 26, 2, 'winners')")
        conn.execute("INSERT INTO matches (id, round, match_number, status, next_match_id, next_match_slot, loser_match_id, loser_match_slot, bracket_type) VALUES (14, 3, 2, 'pending', 15, 2, 27, 2, 'winners')")

        # WB R4 (Финал WB): Матч 15
        # Победитель -> М30 (slot 1). Проигравший -> М29 (slot 2)
        conn.execute("INSERT INTO matches (id, round, match_number, status, next_match_id, next_match_slot, loser_match_id, loser_match_slot, bracket_type) VALUES (15, 4, 1, 'pending', 30, 1, 29, 2, 'winners')")

        # --- 2. СЕТКА ЛУЗЕРОВ (LOSERS BRACKET) ---
        # LB R1: Матчи 16..19 (проигравшие из WB R1) -> ведут в LB R2 (М20..М23 slot 1)
        for i in range(4):
            m_id = 16 + i
            conn.execute(
                "INSERT INTO matches (id, round, match_number, status, next_match_id, next_match_slot, bracket_type) VALUES (?, 1, ?, 'pending', ?, 1, 'losers')",
                (m_id, i + 1, 20 + i),
            )

        # LB R2: Матчи 20..23 (победители LB R1 vs проигравшие WB R2) -> ведут в LB R3 (М24, М25)
        conn.execute("INSERT INTO matches (id, round, match_number, status, next_match_id, next_match_slot, bracket_type) VALUES (20, 2, 1, 'pending', 24, 1, 'losers')")
        conn.execute("INSERT INTO matches (id, round, match_number, status, next_match_id, next_match_slot, bracket_type) VALUES (21, 2, 2, 'pending', 24, 2, 'losers')")
        conn.execute("INSERT INTO matches (id, round, match_number, status, next_match_id, next_match_slot, bracket_type) VALUES (22, 2, 3, 'pending', 25, 1, 'losers')")
        conn.execute("INSERT INTO matches (id, round, match_number, status, next_match_id, next_match_slot, bracket_type) VALUES (23, 2, 4, 'pending', 25, 2, 'losers')")

        # LB R3: Матчи 24, 25 (победители LB R2) -> ведут в LB R4 (М26, М27 slot 1)
        conn.execute("INSERT INTO matches (id, round, match_number, status, next_match_id, next_match_slot, bracket_type) VALUES (24, 3, 1, 'pending', 26, 1, 'losers')")
        conn.execute("INSERT INTO matches (id, round, match_number, status, next_match_id, next_match_slot, bracket_type) VALUES (25, 3, 2, 'pending', 27, 1, 'losers')")

        # LB R4: Матчи 26, 27 (победители LB R3 vs проигравшие WB R3) -> ведут в LB R5 (М28)
        conn.execute("INSERT INTO matches (id, round, match_number, status, next_match_id, next_match_slot, bracket_type) VALUES (26, 4, 1, 'pending', 28, 1, 'losers')")
        conn.execute("INSERT INTO matches (id, round, match_number, status, next_match_id, next_match_slot, bracket_type) VALUES (27, 4, 2, 'pending', 28, 2, 'losers')")

        # LB R5 (Полуфинал LB): Матч 28 -> ведет в LB R6 (М29 slot 1)
        conn.execute("INSERT INTO matches (id, round, match_number, status, next_match_id, next_match_slot, bracket_type) VALUES (28, 5, 1, 'pending', 29, 1, 'losers')")

        # LB R6 (Финал LB): Матч 29 (победитель LB R5 vs проигравший WB Final M15) -> ведет в Гранд-Финал (М30 slot 2)
        conn.execute("INSERT INTO matches (id, round, match_number, status, next_match_id, next_match_slot, bracket_type) VALUES (29, 6, 1, 'pending', 30, 2, 'losers')")

        # --- 3. ГРАНД-ФИНАЛ И СБРОС СЕТКИ ---
        # Гранд-Финал M30 (Bo5)
        conn.execute("INSERT INTO matches (id, round, match_number, status, next_match_id, next_match_slot, bracket_type) VALUES (30, 1, 1, 'pending', 31, 1, 'grand_final')")

        # Сброс Сетки M31 (Bo5) - активен только если финалист лузеров побеждает в M30
        conn.execute("INSERT INTO matches (id, round, match_number, status, bracket_type) VALUES (31, 1, 1, 'pending', 'reset')")

        conn.commit()


def get_all_matches():
    """Возвращает все матчи, разделенные по типам сеток и раундам."""
    with closing(sqlite3.connect(DB_PATH)) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.execute("SELECT * FROM matches ORDER BY id")
        rows = [dict(r) for r in cur.fetchall()]

        bracket = {
            "winners": {1: [], 2: [], 3: [], 4: []},
            "losers": {1: [], 2: [], 3: [], 4: [], 5: [], 6: []},
            "grand_final": [],
            "reset": [],
        }

        for r in rows:
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
    """Обновляет счёт, статус и участников матча. Автоматически продвигает победителя и переводит проигравшего."""
    with closing(sqlite3.connect(DB_PATH)) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.execute("SELECT * FROM matches WHERE id=?", (match_id,))
        m = cur.fetchone()
        if not m:
            return None

        p1_name = player1_name if player1_name is not None else m["player1_name"]
        p1_nick = player1_nickname if player1_nickname is not None else m["player1_nickname"]
        p2_name = player2_name if player2_name is not None else m["player2_name"]
        p2_nick = player2_nickname if player2_nickname is not None else m["player2_nickname"]

        conn.execute(
            """
            UPDATE matches SET
                player1_name=?, player1_nickname=?,
                player2_name=?, player2_nickname=?,
                score1=?, score2=?, status=?, winner_slot=?
            WHERE id=?
            """,
            (p1_name, p1_nick, p2_name, p2_nick, score1, score2, status, winner_slot, match_id),
        )

        cur = conn.execute("SELECT * FROM matches WHERE id=?", (match_id,))
        m = cur.fetchone()

        winner_name, winner_nick = None, None
        loser_name, loser_nick = None, None

        if winner_slot == 1:
            winner_name, winner_nick = m["player1_name"], m["player1_nickname"]
            loser_name, loser_nick = m["player2_name"], m["player2_nickname"]
        elif winner_slot == 2:
            winner_name, winner_nick = m["player2_name"], m["player2_nickname"]
            loser_name, loser_nick = m["player1_name"], m["player1_nickname"]

        # Продвижение участников при завершении матча
        if status == "completed" and winner_slot > 0:
            # 1. Продвижение победителя в следующую стадию
            if m["next_match_id"]:
                next_id = m["next_match_id"]
                slot = m["next_match_slot"]
                if slot == 1:
                    conn.execute(
                        "UPDATE matches SET player1_name=?, player1_nickname=? WHERE id=?",
                        (winner_name, winner_nick, next_id),
                    )
                else:
                    conn.execute(
                        "UPDATE matches SET player2_name=?, player2_nickname=? WHERE id=?",
                        (winner_name, winner_nick, next_id),
                    )

            # 2. Перевод проигравшего из Верхней сетки в Сетку Лузеров
            if m["loser_match_id"]:
                loser_id = m["loser_match_id"]
                l_slot = m["loser_match_slot"]
                if l_slot == 1:
                    conn.execute(
                        "UPDATE matches SET player1_name=?, player1_nickname=? WHERE id=?",
                        (loser_name, loser_nick, loser_id),
                    )
                else:
                    conn.execute(
                        "UPDATE matches SET player2_name=?, player2_nickname=? WHERE id=?",
                        (loser_name, loser_nick, loser_id),
                    )

            # 3. Особая логика Гранд-Финала (Матч 30) -> Сброс Сетки (Матч 31)
            if match_id == 30:
                if winner_slot == 1:
                    conn.execute("UPDATE matches SET status='not_needed' WHERE id=31")
                elif winner_slot == 2:
                    conn.execute(
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
    """Очищает сетку матчей."""
    with closing(sqlite3.connect(DB_PATH)) as conn:
        conn.execute("DELETE FROM matches")
        conn.commit()
