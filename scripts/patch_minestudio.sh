#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

LAUNCH_CLIENT="./.venv/lib/python3.10/site-packages/minestudio/simulator/minerl/env/launchClient.sh"

if grep -Fq 'xvfb-run -a -s "+extension GLX +render"' "$LAUNCH_CLIENT"; then
  exit 0
fi

python - <<'PY'
from pathlib import Path

path = Path(".venv/lib/python3.10/site-packages/minestudio/simulator/minerl/env/launchClient.sh")
text = path.read_text()
old = "        xvfb-run -a java -Xmx$maxMem -jar $fatjar --envPort=$port\n"
new = (
    '        export LD_LIBRARY_PATH="$HOME/opt/openssl10/lib:$LD_LIBRARY_PATH"\n'
    "        export LIBGL_DRIVERS_PATH=/usr/lib/x86_64-linux-gnu/dri\n"
    '        xvfb-run -a -s "+extension GLX +render" java -Xmx$maxMem -jar $fatjar --envPort=$port\n'
)
if old not in text:
    raise SystemExit(f"expected xvfb-run line not found in {path}")
path.write_text(text.replace(old, new))
PY
