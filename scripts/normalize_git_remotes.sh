#!/usr/bin/env bash
set -euo pipefail

# origin / upstream が混在しているリポジトリを標準形にそろえる補助スクリプト。
# - origin は残す
# - upstream は --keep-upstream 指定時のみ保持
# - main があれば origin/main を upstream に設定

keep_upstream=false
if [[ "${1:-}" == "--keep-upstream" ]]; then
  keep_upstream=true
fi

if ! git rev-parse --git-dir >/dev/null 2>&1; then
  echo "[ERROR] git リポジトリ外です" >&2
  exit 1
fi

if ! git remote get-url origin >/dev/null 2>&1; then
  echo "[WARN] origin remote が未設定のため、自動整理をスキップしました"
  exit 0
fi

if git remote get-url upstream >/dev/null 2>&1; then
  if [[ "$keep_upstream" == true ]]; then
    echo "[INFO] --keep-upstream が指定されたため upstream を保持します"
  else
    git remote remove upstream
    echo "[OK] upstream を削除しました"
  fi
else
  echo "[INFO] upstream は存在しません"
fi

if git show-ref --verify --quiet refs/heads/main; then
  if git show-ref --verify --quiet refs/remotes/origin/main; then
    git branch --set-upstream-to=origin/main main >/dev/null
    echo "[OK] main -> origin/main の upstream を設定しました"
  else
    echo "[INFO] origin/main が未取得のため upstream 設定をスキップしました"
  fi
fi

echo "[DONE] remote 整理が完了しました"
