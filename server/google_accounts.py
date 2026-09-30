"""Google principals own up to four game characters, including offline saves.

Existing Google ownership is retained. New characters are created directly
under a verified account; claiming unlinked legacy saves is no longer offered.
"""
from __future__ import annotations

import json
import re
import secrets
import sqlite3
import sys

try:
    from .google_auth import AuthError
except ImportError:
    from google_auth import AuthError

MAX_CHARACTERS = 4
_NAME = re.compile(r"[\w -]{3,20}", re.UNICODE)


def _game_types():
    # Imported only after server.py has finished defining Game and Player.
    main = sys.modules.get("__main__")
    if main is not None and getattr(main, "GoogleAccountGame", None) is GoogleAccountGame:
        return main.Player, main.CLASSES, main.MAX_PLAYERS
    if __package__:
        from .server import Player, CLASSES, MAX_PLAYERS
    else:
        from server import Player, CLASSES, MAX_PLAYERS
    return Player, CLASSES, MAX_PLAYERS


class GoogleAccountGame:
    def init_google_accounts(self):
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.executescript("""
          CREATE TABLE IF NOT EXISTS google_accounts(
            id INTEGER PRIMARY KEY,
            subject TEXT UNIQUE NOT NULL,
            created_at REAL NOT NULL
          );
          CREATE TABLE IF NOT EXISTS google_characters(
            google_account_id INTEGER NOT NULL REFERENCES google_accounts(id),
            character_id INTEGER UNIQUE NOT NULL REFERENCES accounts(id),
            linked_at REAL NOT NULL,
            PRIMARY KEY(google_account_id, character_id)
          );
          CREATE TRIGGER IF NOT EXISTS google_characters_limit_insert
          BEFORE INSERT ON google_characters
          WHEN (SELECT COUNT(*) FROM google_characters
                WHERE google_account_id=NEW.google_account_id) >= 4
          BEGIN
            SELECT RAISE(ABORT, 'google_character_limit');
          END;
          CREATE TRIGGER IF NOT EXISTS google_characters_owner_immutable
          BEFORE UPDATE OF google_account_id, character_id ON google_characters
          WHEN NEW.google_account_id != OLD.google_account_id
               OR NEW.character_id != OLD.character_id
          BEGIN
            SELECT RAISE(ABORT, 'google_character_owner_immutable');
          END;
          CREATE TRIGGER IF NOT EXISTS google_characters_no_replace
          BEFORE INSERT ON google_characters
          WHEN EXISTS(SELECT 1 FROM google_characters WHERE character_id=NEW.character_id)
          BEGIN
            SELECT RAISE(ABORT, 'google_character_already_owned');
          END;
        """)

    def _google_account_id(self, subject):
        if not isinstance(subject, str) or not 1 <= len(subject) <= 255:
            raise ValueError("Invalid verified Google subject")
        with self.db:
            self.db.execute(
                "INSERT OR IGNORE INTO google_accounts(subject,created_at) VALUES(?,?)",
                (subject, self.now()),
            )
        return self.db.execute("SELECT id FROM google_accounts WHERE subject=?", (subject,)).fetchone()[0]

    def _google_character_count(self, account_id):
        return self.db.execute(
            "SELECT COUNT(*) FROM google_characters WHERE google_account_id=?", (account_id,)
        ).fetchone()[0]

    def google_account_info(self, subject):
        """Private roster, called only after the Google credential is verified."""
        account_id = self._google_account_id(subject)
        characters = []
        for pid, name, encoded in self.db.execute(
            "SELECT a.id,a.name,a.data FROM accounts a JOIN google_characters g "
            "ON g.character_id=a.id WHERE g.google_account_id=? ORDER BY a.id", (account_id,)
        ):
            live = self.players.get(str(pid))
            saved = json.loads(encoded)
            characters.append({
                "id": str(pid), "name": name,
                "class_id": live.class_id if live else saved.get("class_id", "knight"),
                "level": live.level if live else saved.get("level", 1),
                "online": bool(live and not live.disconnected),
            })
        return {"characters": characters, "max_characters": MAX_CHARACTERS}

    async def _google_error(self, ws, text, code="character_error"):
        await self.send(ws, {"type": "error", "code": code, "text": text})

    def _google_session_error(self, ws, pid, max_players):
        if ws.closed:
            return "closed"
        if any(p.ws is ws for p in self.players.values()):
            return "Jesteś już zalogowany."
        live = self.players.get(str(pid)) if pid is not None else None
        if live and not live.disconnected:
            return "Ta postać jest już w grze. Wyloguj ją na drugim urządzeniu."
        if live is None and len(self.players) >= max_players:
            return "Świat jest pełny. Spróbuj za chwilę."
        return None

    async def hello_google(self, ws, data, service, browser_binding, origin):
        """Redeem a single-use, browser-bound ticket for select/create only."""
        if ws.closed:
            return
        if not isinstance(data, dict):
            return await self._google_error(ws, "Nieprawidłowe żądanie logowania.")
        if not service.enabled or origin != service.allowed_origin:
            return await self._google_error(ws, "Zaloguj się przez Google na stronie gry.", "google_retry")
        ticket = data.get("ticket")
        try:
            identity = service.peek_ticket(ticket, browser_binding)
        except AuthError:
            return await self._google_error(ws, "Logowanie wygasło. Wybierz Google ponownie.", "google_retry")
        Player, classes, max_players = _game_types()
        mode = data.get("mode")
        if mode not in ("select", "create"):
            return await self._google_error(ws, "Wybierz lub utwórz postać.")
        account_id = self._google_account_id(identity.sub)
        row = None
        if mode == "select":
            character_id = data.get("character_id")
            if (not isinstance(character_id, str) or not re.fullmatch(r"[1-9][0-9]{0,18}", character_id)
                    or int(character_id) > 9223372036854775807):
                return await self._google_error(ws, "Nie można użyć tej postaci.")
            row = self.db.execute(
                "SELECT a.id,a.name,a.data FROM accounts a JOIN google_characters g "
                "ON g.character_id=a.id WHERE a.id=? AND g.google_account_id=?",
                (int(character_id), account_id),
            ).fetchone()
            if row is None:
                return await self._google_error(ws, "Nie można użyć tej postaci.")
        else:
            if self._google_character_count(account_id) >= MAX_CHARACTERS:
                return await self._google_error(ws, "Na koncie mogą być najwyżej 4 postacie.", "character_limit")
            name = data.get("name")
            if not isinstance(name, str) or not _NAME.fullmatch(name) or name != name.strip():
                return await self._google_error(ws, "Nazwa postaci: 3–20 liter, cyfr, spacji lub znaków - i _.")
            class_id = data.get("class_id")
            if not isinstance(class_id, str) or class_id not in classes:
                return await self._google_error(ws, "Wybierz jedną z czterech klas.")
            if self.db.execute("SELECT 1 FROM accounts WHERE name_key=?", (name.casefold(),)).fetchone():
                return await self._google_error(ws, "Ta nazwa postaci jest zajęta.")

        err = self._google_session_error(ws, row[0] if row else None, max_players)
        if err:
            if err != "closed":
                await self._google_error(ws, err)
            return
        if mode == "create":
            p = Player("", name, ws, class_id=class_id)
            p.hp, p.mana = p.max_hp, p.max_mana
            self.starter(p)
            encoded = json.dumps(p.save_data())
        else:
            p = self.players.get(str(row[0]))
            if p is None:
                p = self.load_player(str(row[0]), row[1], ws, json.loads(row[2]))
        try:
            # No awaits below until complete_login has bound p.ws/self.players.
            # A second request cannot redeem this ticket on another websocket.
            service.consume_ticket(ticket, browser_binding)
            if mode == "create":
                with self.db:
                    if mode == "create":
                        cur = self.db.execute(
                            "INSERT INTO accounts(name,name_key,salt,password_hash,data) VALUES(?,?,?,?,?)",
                            (name, name.casefold(), secrets.token_bytes(16), b"", encoded),
                        )
                        p.id = str(cur.lastrowid)
                    self.db.execute(
                        "INSERT INTO google_characters(google_account_id,character_id,linked_at) VALUES(?,?,?)",
                        (account_id, int(p.id), self.now()),
                    )
        except AuthError:
            return await self._google_error(ws, "Logowanie wygasło. Wybierz Google ponownie.", "google_retry")
        except sqlite3.IntegrityError:
            # A database-level race/cap rejection rolls back the new character
            # as well as its mapping. The consumed ticket cannot be replayed.
            return await self._google_error(ws, "Nie udało się utworzyć postaci. Wybierz Google ponownie.", "google_retry")
        await self.complete_login(ws, p, data)
