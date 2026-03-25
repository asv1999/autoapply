#!/bin/bash
# Run this from your Mac terminal inside ~/Development\ -\ Claude/autoapply/
# This pushes the fixes and deploys to the droplet in one shot.

set -e

echo "Step 1: Pushing to GitHub..."
git push origin main

echo "Step 2: Copying fixed files to droplet..."
scp backend/intelligence/engine.py root@167.172.116.247:/home/autoapply/backend/intelligence/engine.py
scp backend/main.py root@167.172.116.247:/home/autoapply/backend/main.py

echo "Step 3: Clearing broken DB data and restarting..."
ssh root@167.172.116.247 '
  sqlite3 /home/autoapply/data/autoapply.db "DELETE FROM applications; DELETE FROM playbooks; DELETE FROM runs;"
  systemctl restart autoapply
  sleep 2
  echo "Service status:"
  systemctl is-active autoapply
'

echo "Step 4: Triggering full pipeline..."
sleep 3
curl -s -X POST http://167.172.116.247/api/pipeline | python3 -m json.tool

echo ""
echo "Pipeline is running! Wait 4-5 minutes, then check:"
echo "  http://167.172.116.247/api/dashboard"
echo "  http://167.172.116.247/api/applications?limit=5"
echo ""
echo "Done. Come back to Claude Desktop when the pipeline finishes."
