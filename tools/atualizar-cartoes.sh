#!/usr/bin/env bash
# Daily (cron): regenerates the profile stats cards and pushes them only when the numbers changed.
set -euo pipefail
cd /opt/github-profile
git pull -q --ff-only
python3 tools/cartoes.py cartoes > /dev/null
# The cards carry today's date; only commit when something other than that date changed.
if git diff --quiet -I 'atualizado em' -- cartoes && [ -z "$(git ls-files --others --exclude-standard cartoes)" ]; then
  git checkout -q -- cartoes
  echo "$(date -Is) sem mudanças"
  exit 0
fi
git add cartoes
git -c user.name="Eduardo Lopes Diaz" -c user.email="lopesdiazeduardo@gmail.com" commit -q -m "Cartões: estatísticas de $(date +%d/%m/%Y)"
git push -q
echo "$(date -Is) cartões atualizados"
