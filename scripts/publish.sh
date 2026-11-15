#!/bin/sh
# Publishes the folder site/ to splicefs.org by rsync over ssh.
#
# The upload key can read and write the folder of this one website and do nothing else.
# Variables: UPLOAD_KEY_FILE (required, private key, mode 600), UPLOAD_KNOWN_HOSTS_FILE
# (required), UPLOAD_HOST (splicefs.org), UPLOAD_PORT (7022), UPLOAD_USER (site-splicefs).
# Test hook: UPLOAD_TARGET is a complete rsync destination, for example a local folder; it
# replaces user@host:/ and no ssh is used.
set -eu

root="$(cd "$(dirname "$0")/.." && pwd)"
host=${UPLOAD_HOST:-splicefs.org}
port=${UPLOAD_PORT:-7022}
user=${UPLOAD_USER:-site-splicefs}

[ -f "$root/site/index.html" ] || { echo "site/index.html is missing" >&2; exit 1; }

# Old files are removed only after the new ones are in place, so a visitor never gets a
# half-published site. The modes make every file readable by the web server.
if [ -n "${UPLOAD_TARGET:-}" ]; then
    rsync -a --delete-after --chmod=D755,F644 "$root/site/" "$UPLOAD_TARGET"
    exit 0
fi

: "${UPLOAD_KEY_FILE:?UPLOAD_KEY_FILE is not set}"
: "${UPLOAD_KNOWN_HOSTS_FILE:?UPLOAD_KNOWN_HOSTS_FILE is not set}"
[ -f "$UPLOAD_KEY_FILE" ] || { echo "UPLOAD_KEY_FILE is not a file" >&2; exit 1; }
[ -f "$UPLOAD_KNOWN_HOSTS_FILE" ] || { echo "UPLOAD_KNOWN_HOSTS_FILE is not a file" >&2; exit 1; }

# Only this key and only the stored host key: no agent, no personal ssh configuration, and
# no trust in a server that shows a different key.
ssh_cmd="ssh -p $port -i $UPLOAD_KEY_FILE -o IdentitiesOnly=yes -o IdentityAgent=none"
ssh_cmd="$ssh_cmd -o StrictHostKeyChecking=yes -o UserKnownHostsFile=$UPLOAD_KNOWN_HOSTS_FILE"
ssh_cmd="$ssh_cmd -o BatchMode=yes -F /dev/null"

rsync -a --delete-after --chmod=D755,F644 -e "$ssh_cmd" "$root/site/" "$user@$host:/"
echo "published site/ to $host"
