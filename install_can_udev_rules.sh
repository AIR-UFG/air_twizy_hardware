#!/usr/bin/env bash

set -euo pipefail

RULE_SOURCE="$(dirname "$(readlink -f "$0")")/90-twizy-can-names.rules"
RULE_TARGET="/etc/udev/rules.d/90-twizy-can-names.rules"

if [ ! -f "$RULE_SOURCE" ]; then
    echo "Rule file not found: $RULE_SOURCE" >&2
    exit 1
fi

sudo install -m 0644 "$RULE_SOURCE" "$RULE_TARGET"
sudo udevadm control --reload-rules

echo "Installed $RULE_TARGET"
echo "Now reboot, or disconnect/reconnect the PEAK USB adapter and reload the PEAK PCIe driver."
