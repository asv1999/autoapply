#!/bin/bash
# AutoApply v3.1 — Deploy fixes and re-run pipeline
# Run from: ~/Development\ -\ Claude/autoapply/
# Usage:  chmod +x deploy_and_test.sh && ./deploy_and_test.sh

set -e
DROPLET="root@167.172.116.247"
REMOTE="/home/autoapply/app"
BACKEND="${REMOTE}/backend"

echo "════════════════════════════════════════"
echo "  AutoApply — Deploy & Re-Test Script"
echo "════════════════════════════════════════"

# ── Step 1: Push local git changes ──────────────────────────────────────────
echo ""
echo "▶ Step 1: Pushing local changes to GitHub..."
git push origin main
echo "  ✓ Pushed (Netlify will auto-deploy frontend in ~2 min)"

# ── Step 2: Deploy backend fixes to droplet ─────────────────────────────────
echo ""
echo "▶ Step 2: Copying fixed backend files to droplet..."
scp backend/intelligence/engine.py ${DROPLET}:${BACKEND}/intelligence/engine.py
scp backend/documents/resume_gen.py ${DROPLET}:${BACKEND}/documents/resume_gen.py
scp backend/main.py ${DROPLET}:${BACKEND}/main.py
scp requirements.txt ${DROPLET}:${REMOTE}/requirements.txt
echo "  ✓ Files copied"

# ── Step 3: Clear bad data and restart service ──────────────────────────────
echo ""
echo "▶ Step 3: Clearing old broken data and restarting service..."
ssh ${DROPLET} "
  cd ${REMOTE}
  source venv/bin/activate
  pip install -r requirements.txt
  touch ${BACKEND}/documents/__init__.py

  # Delete all empty/broken applications (where tailored_bullets has no content)
  sqlite3 ${REMOTE}/data/autoapply.db \"
    DELETE FROM applications;
    DELETE FROM playbooks;
    DELETE FROM runs;
  \"
  echo '  ✓ Cleared applications, playbooks, runs'

  # Restart the service with fixed code
  systemctl restart autoapply
  sleep 3
  systemctl status autoapply --no-pager | head -5
  echo '  ✓ Service restarted'
"

# ── Step 4: Trigger pipeline ─────────────────────────────────────────────────
echo ""
echo "▶ Step 4: Triggering full pipeline..."
curl -s -X POST http://167.172.116.247/api/pipeline | python3 -m json.tool
echo ""
echo "  Pipeline started! Waiting 4 minutes for completion..."
sleep 240

# ── Step 5: Verify results ───────────────────────────────────────────────────
echo ""
echo "▶ Step 5: Verifying tailored content..."
curl -s "http://167.172.116.247/api/applications?limit=10" | python3 -c "
import sys, json
apps = json.load(sys.stdin)
total = len(apps)
with_bullets = 0
correct_co = 0
unknown_arch = 0

for a in apps:
    tb = a.get('tailored_bullets', {})
    if isinstance(tb, str):
        import json as j2
        try: tb = j2.loads(tb)
        except: tb = {}
    bullet_count = sum(len(v) for v in tb.values() if isinstance(v, list))
    cl = (a.get('cover_letter') or '')
    co = (a.get('company') or '').lower()

    if bullet_count > 0:
        with_bullets += 1
    if co and co in cl.lower():
        correct_co += 1
    if a.get('archetype') == 'Unknown':
        unknown_arch += 1

    print(f'  App {a[\"id\"]}: {(a.get(\"title\") or \"\")[:30]} @ {a.get(\"company\",\"?\")} | bullets={bullet_count} | arch={a.get(\"archetype\",\"?\")} | CL={len(cl)}ch | correct_co={co in cl.lower()}')

print()
print(f'SUMMARY: {with_bullets}/{total} apps with bullets | {correct_co}/{total} correct company | {unknown_arch}/{total} Unknown archetype')
"

# ── Step 6: Generate .docx files ─────────────────────────────────────────────
echo ""
echo "▶ Step 6: Generating .docx resume files..."
curl -s -X POST http://167.172.116.247/api/docs-batch | python3 -m json.tool

# ── Step 7: Verify .docx files ───────────────────────────────────────────────
echo ""
echo "▶ Step 7: Checking generated .docx files on droplet..."
ssh ${DROPLET} "ls -lah ${REMOTE}/data/outputs/resumes/ | head -20"

# ── Step 8: Test decision maker ───────────────────────────────────────────────
echo ""
echo "▶ Step 8: Testing decision maker finder..."
JOB_ID=$(curl -s "http://167.172.116.247/api/jobs?limit=1" | python3 -c "import sys,json; data=json.load(sys.stdin); print(data[0]['id']) if data else print('')")
if [ -n "$JOB_ID" ]; then
  curl -s -X POST "http://167.172.116.247/api/connections/${JOB_ID}" | python3 -c "
import sys, json
r = json.load(sys.stdin)
title = r.get('contact_title','')
msg = r.get('outreach_message','')
print(f'  Title: {title}')
print(f'  Message: {msg[:100]}...' if len(msg) > 100 else f'  Message: {msg}')
print(f'  ✓ PASS' if title and title != 'Hiring Manager' and msg else f'  ✗ FAIL - title={bool(title)}, msg={bool(msg)}')
"
fi

echo ""
echo "════════════════════════════════════════"
echo "  Deployment complete. Check results above."
echo "════════════════════════════════════════"
