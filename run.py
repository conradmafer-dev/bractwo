"""Railway launcher for Bractwo 0.8.14. Does not alter game balance or saves.

One simulation process, one SQLite database, one persistent volume.
"""
from __future__ import annotations

import asyncio
from contextlib import closing, contextmanager, suppress
from dataclasses import dataclass
from datetime import datetime, timezone
import logging
import os
from pathlib import Path
import sqlite3
import sys
from typing import Mapping

from aiohttp import web
from server.server import create_app
from server.world_content import VERSION

ROOT = Path(__file__).resolve().parent
LOG = logging.getLogger("bractwo.hosting")


class StartupError(RuntimeError):
    """Configuration or save validation failed before opening the game database."""


@dataclass(frozen=True)
class Settings:
    port: int
    database: Path
    railway: bool


def settings_from_env(env: Mapping[str, str]) -> Settings:
    try:
        port = int(env.get("PORT", "8080"))
    except (TypeError, ValueError) as exc:
        raise StartupError("PORT musi byc liczba calkowita, np. 8080.") from exc
    if not 1 <= port <= 65535:
        raise StartupError("PORT musi miescic sie w zakresie 1-65535.")
    railway = any(env.get(k) for k in (
        "RAILWAY_SERVICE_ID", "RAILWAY_PROJECT_ID", "RAILWAY_ENVIRONMENT_ID"))
    mount_raw = env.get("RAILWAY_VOLUME_MOUNT_PATH", "").strip()
    if railway and not mount_raw:
        raise StartupError(
            "Brak trwalego dysku Railway. Dolacz Volume do uslugi Bractwo "
            "i ustaw Mount Path /data. Nie wpisuj RAILWAY_VOLUME_MOUNT_PATH recznie.")
    mount = Path(mount_raw).resolve() if mount_raw else None
    if railway and (not Path(mount_raw).is_absolute() or not mount.is_dir()):
        raise StartupError("Wolumen Railway nie jest dostepny pod wskazana sciezka.")
    raw = env.get("BRACTWO_DB_PATH", "").strip()
    database = Path(raw) if raw else (mount or ROOT / "data") / "world.sqlite3"
    if str(database) == ":memory:":
        raise StartupError("Hosting wymaga pliku bazy, nie :memory:.")
    database = database.resolve()
    if railway and (database == mount or not database.is_relative_to(mount)):
        raise StartupError("BRACTWO_DB_PATH musi wskazywac plik na wolumenie Railway.")
    return Settings(port, database, railway)


@contextmanager
def exclusive_database(database: Path):
    """Advisory Linux lock prevents two copies of the simulation on one save."""
    database.parent.mkdir(parents=True, exist_ok=True)
    with database.with_name(database.name + ".lock").open("a+b") as lock:
        try:
            import fcntl
        except ImportError:
            # The deployment image is Linux. This branch only supports local Windows tests.
            LOG.warning("Brak blokady fcntl: lokalnie uruchamiaj tylko jeden serwer.")
            yield
            return
        try:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise StartupError("Ta baza jest juz uzywana przez inny serwer. Ustaw jedna replike.") from exc
        try:
            yield
        finally:
            fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


def backup_existing_database(database: Path, keep: int = 5) -> Path | None:
    """Validate and snapshot an existing Bractwo database before game migrations.

    Use SQLite's backup API, not a raw copy (which could miss WAL transactions).
    Backups live on the same volume; they do not replace independent backups.
    """
    if not database.exists():
        return None
    if not database.is_file() or database.stat().st_size == 0:
        raise StartupError("Istniejaca baza jest pusta lub nie jest plikiem. Nie zostala nadpisana.")
    temporary = None
    try:
        with closing(sqlite3.connect(database.as_uri() + "?mode=ro", uri=True, timeout=5)) as source:
            columns = {row[1] for row in source.execute("PRAGMA table_info(accounts)")}
            expected = {"id", "name", "name_key", "salt", "password_hash", "data"}
            tables = {row[0] for row in source.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if not expected.issubset(columns) or "shared" not in tables:
                raise StartupError("To nie jest rozpoznana baza Bractwa. Nie zostala zmieniona.")
            if source.execute("PRAGMA quick_check").fetchone() != ("ok",):
                raise StartupError("Kontrola bazy nie powiodla sie. Przywroc sprawna kopie zapisu.")
            folder = database.parent / "backups"
            folder.mkdir(exist_ok=True)
            stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
            target = folder / ("bractwo-" + stamp + ".sqlite3")
            temporary = target.with_suffix(".partial")
            with closing(sqlite3.connect(temporary)) as destination:
                source.backup(destination)
            temporary.replace(target)
        for old in sorted(folder.glob("bractwo-*.sqlite3"), reverse=True)[max(1, keep):]:
            old.unlink()
        LOG.info("Kopia przed startem: %s", target)
        return target
    except sqlite3.Error as exc:
        raise StartupError("Nie mozna odczytac lub skopiowac bazy. Plik nie zostal zastapiony.") from exc
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


async def graceful_shutdown(app: web.Application) -> None:
    """Save before draining sockets, rather than waiting for long-lived connections."""
    game = app["game"]
    if game.task is not None:
        game.task.cancel()
        try:
            await game.task
        except asyncio.CancelledError:
            pass
        except Exception:
            LOG.exception("Petla gry zakonczyla sie bledem; zapisuje stan przed zamknieciem.")
    game.persist()
    LOG.info("Zapisano stan gry; zamykam polaczenia.")
    sockets = tuple(game.connections)
    if sockets:
        with suppress(asyncio.TimeoutError):
            await asyncio.wait_for(asyncio.gather(
                *(ws.close(code=1001, message=b"Server restart") for ws in sockets),
                return_exceptions=True), timeout=3)


@web.middleware
async def readiness(request: web.Request, handler):
    if request.path == "/health":
        task = request.app["game"].task
        if task is None or task.done():
            return web.json_response({"ok": False, "version": VERSION}, status=503,
                                     headers={"Cache-Control": "no-store"})
    return await handler(request)


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    try:
        config = settings_from_env(os.environ)
        with exclusive_database(config.database):
            backup_existing_database(config.database)
            app = create_app(str(config.database))
            app.middlewares.append(readiness)
            app.on_shutdown.append(graceful_shutdown)
            LOG.info("Bractwo %s | 0.0.0.0:%d | baza: %s", VERSION, config.port, config.database)
            web.run_app(app, host="0.0.0.0", port=config.port, access_log=None,
                        shutdown_timeout=5)
    except (StartupError, OSError) as exc:
        LOG.error("START WSTRZYMANY: %s", exc)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
