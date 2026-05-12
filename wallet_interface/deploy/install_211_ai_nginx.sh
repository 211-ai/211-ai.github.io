#!/bin/sh
set -eu

SOURCE_CONFIG="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)/nginx.211-ai.com.conf"
TARGET_AVAILABLE="/etc/nginx/sites-available/211-ai.com.conf"
TARGET_ENABLED="/etc/nginx/sites-enabled/211-ai.com.conf"

if [ "$(id -u)" -ne 0 ]; then
    echo "Run as root so the nginx site can be installed under /etc/nginx." >&2
    exit 1
fi

install -D -m 0644 "$SOURCE_CONFIG" "$TARGET_AVAILABLE"

ln -sfn "$TARGET_AVAILABLE" "$TARGET_ENABLED"

nginx -t

if command -v systemctl >/dev/null 2>&1; then
    systemctl reload nginx
else
    nginx -s reload
fi

echo "Installed nginx site for 211-ai.com and reloaded nginx."