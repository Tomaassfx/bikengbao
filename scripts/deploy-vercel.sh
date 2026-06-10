#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TOOL_DIR="${BIKENGBAO_TOOL_DIR:-$HOME/.cache/bikengbao-tools}"
NODE_BIN="${NODE_BIN:-$HOME/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node}"
NPM_CLI="${NPM_CLI:-$TOOL_DIR/npm/bin/npm-cli.js}"
NPM_TGZ="$TOOL_DIR/npm.tgz"
NPM_REGISTRY="${NPM_REGISTRY:-https://registry.npmmirror.com}"

if [[ ! -x "$NODE_BIN" ]]; then
  if command -v node >/dev/null 2>&1; then
    NODE_BIN="$(command -v node)"
  else
    echo "Missing Node.js. Install Node.js first, or set NODE_BIN to a Node executable." >&2
    exit 1
  fi
fi
export PATH="$(dirname "$NODE_BIN"):$PATH"

if [[ ! -f "$NPM_CLI" ]]; then
  mkdir -p "$TOOL_DIR"
  python3 - "$NPM_TGZ" <<'PY'
from pathlib import Path
import json
import sys
import tarfile
import urllib.request

out = Path(sys.argv[1])
tool_dir = out.parent
meta_url = "https://registry.npmmirror.com/npm/latest"
with urllib.request.urlopen(meta_url, timeout=60) as response:
    meta = json.load(response)
tarball = meta["dist"]["tarball"]
with urllib.request.urlopen(tarball, timeout=120) as response, out.open("wb") as handle:
    while True:
        chunk = response.read(1024 * 1024)
        if not chunk:
            break
        handle.write(chunk)
target = tool_dir / "npm"
if target.exists():
    import shutil
    shutil.rmtree(target)
with tarfile.open(out, "r:gz") as archive:
    archive.extractall(tool_dir)
(tool_dir / "package").rename(target)
PY
fi

if [[ -z "${VERCEL_TOKEN:-}" ]]; then
  echo "VERCEL_TOKEN is not set. The Vercel CLI will open/login interactively if needed." >&2
fi

cd "$ROOT_DIR"
"$NODE_BIN" "$NPM_CLI" exec --yes --registry="$NPM_REGISTRY" vercel@latest -- deploy --prod "$@"
