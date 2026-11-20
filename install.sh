#!/bin/sh
# Newton installer. Run it from the unzipped folder:   sh install.sh
# Works in any POSIX shell (sh, dash, bash, zsh, busybox) and needs only Python 3.9+.
# Options: --no-setup (skip the guided setup)  --no-path (don't edit shell config)  --bin-dir DIR
#
# To install from a download address instead:  NEWTON_URL=https://…/newton.zip sh install.sh
set -eu

say() { printf '  %s\n' "$*"; }
die() { printf '\n  ✗ %s\n\n' "$*" >&2; exit 1; }

find_python() {
  for c in python3 python3.13 python3.12 python3.11 python3.10 python3.9 python; do
    if p=$(command -v "$c" 2>/dev/null) && "$p" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)' 2>/dev/null; then
      printf '%s' "$p"; return 0
    fi
  done
  return 1
}

python_help() {
  printf '\n  ✗ Newton needs Python 3.9 or newer, and I could not find it.\n\n  Install it, then run this again:\n\n' >&2
  os=$(uname -s 2>/dev/null || echo unknown)
  id=""; [ -r /etc/os-release ] && id=$(. /etc/os-release 2>/dev/null; echo "${ID:-} ${ID_LIKE:-}")
  if [ -e /dev/.cros_milestone ] || [ "${id#*debian}" != "$id" ] || [ "${id#*ubuntu}" != "$id" ]; then
    printf '    sudo apt update && sudo apt install -y python3\n' >&2
    [ -e /dev/.cros_milestone ] && printf '\n  (Chromebook: run this in the Linux terminal, the "Terminal" app.)\n' >&2
  elif [ "$os" = Darwin ]; then
    printf '    xcode-select --install        # or:  brew install python\n' >&2
  elif [ "${id#*fedora}" != "$id" ] || [ "${id#*rhel}" != "$id" ]; then
    printf '    sudo dnf install -y python3\n' >&2
  elif [ "${id#*arch}" != "$id" ]; then
    printf '    sudo pacman -S python\n' >&2
  elif [ "${id#*alpine}" != "$id" ]; then
    printf '    sudo apk add python3\n' >&2
  else
    printf '    https://www.python.org/downloads/\n' >&2
  fi
  printf '\n' >&2
  exit 1
}

PY=$(find_python) || python_help

DIR=$(CDPATH= cd -- "$(dirname -- "$0")" 2>/dev/null && pwd) || DIR=$(pwd)

# Not run from an unzipped folder (e.g. piped from curl): fetch the package first.
if [ ! -f "$DIR/newton/installer.py" ]; then
  [ -n "${NEWTON_URL:-}" ] || die "Run this from the unzipped Newton folder (the one that contains the 'newton' directory)."
  TMP=$(mktemp -d "${TMPDIR:-/tmp}/newton-install.XXXXXX")
  trap 'rm -rf "$TMP"' EXIT
  say "downloading $NEWTON_URL"
  DIR=$("$PY" - "$NEWTON_URL" "$TMP" <<'PYEOF'
import sys, os, urllib.request, zipfile
url, tmp = sys.argv[1], sys.argv[2]
if not url.startswith(("https://", "file://")):
    sys.exit("only https:// addresses are accepted")
zpath = os.path.join(tmp, "newton.zip")
with urllib.request.urlopen(url, timeout=60) as r, open(zpath, "wb") as f:
    f.write(r.read(40 * 1024 * 1024 + 1))
if os.path.getsize(zpath) > 40 * 1024 * 1024:
    sys.exit("download is unexpectedly large")
root = os.path.realpath(os.path.join(tmp, "src"))
with zipfile.ZipFile(zpath) as z:
    for m in z.infolist():
        if not os.path.realpath(os.path.join(root, m.filename)).startswith(root):
            sys.exit("unsafe path in archive")
    z.extractall(root)
for dp, dn, fn in os.walk(root):
    if os.path.basename(dp) == "newton" and "installer.py" in fn:
        print(os.path.dirname(dp)); break
else:
    sys.exit("not a Newton download")
PYEOF
  ) || die "could not download Newton from $NEWTON_URL"
fi

"$PY" "$DIR/newton/installer.py" install "$@"
