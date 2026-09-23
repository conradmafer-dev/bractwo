"""Start an isolated 0.3 server and run browser_smoke.cjs in the same environment.

Set PLAYWRIGHT_MODULE and CHROMIUM_BIN if they are not installed conventionally.
Optionally set QA_DIR to choose the screenshot/report output directory.
Requires Node, Playwright, Chromium and the normal server requirements.
"""
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request


def main():
    root = Path(__file__).resolve().parents[1]
    output = Path(os.environ.get("QA_DIR") or tempfile.mkdtemp(prefix="bractwo-browser-report-"))
    output.mkdir(parents=True, exist_ok=True)
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    url = f"http://127.0.0.1:{port}"
    result = 1
    with tempfile.TemporaryDirectory(prefix="bractwo-browser-world-") as state:
        with (output / "server.log").open("w") as log:
            server = subprocess.Popen(
                [sys.executable, "-u", "server/server.py", "--host", "127.0.0.1",
                 "--port", str(port), "--db", str(Path(state) / "world.sqlite3")],
                cwd=root, stdout=log, stderr=log,
            )
            try:
                for _ in range(100):
                    if server.poll() is not None:
                        raise RuntimeError("Test server exited before startup")
                    try:
                        with urllib.request.urlopen(url + "/health", timeout=1) as response:
                            if response.status == 200:
                                break
                    except OSError:
                        time.sleep(.1)
                else:
                    raise RuntimeError("Test server startup timed out")
                environment = dict(os.environ, GAME_URL=url, QA_DIR=str(output))
                result = subprocess.run(["node", "tools/browser_smoke.cjs"], cwd=root, env=environment,
                                        timeout=600).returncode
            finally:
                server.terminate()
                try:
                    server.wait(timeout=8)
                except subprocess.TimeoutExpired:
                    server.kill()
                    server.wait()
    print(f"Browser result: {result}. Report: {output}")
    return result


if __name__ == "__main__":
    sys.exit(main())
