#!/usr/bin/env bash
# Envía cada fichero *.csv de un directorio al endpoint POST /imports/csv (JWT requerido).
set -euo pipefail

API_URL="${API_URL:-http://127.0.0.1:8000}"
TOKEN="${JWT_TOKEN:?Definir JWT_TOKEN con el bearer de acceso tras login}"

dir="${1:-}"
if [[ -z "$dir" || ! -d "$dir" ]]; then
  echo "Uso: JWT_TOKEN='<token>' [API_URL=http://localhost:8000] $0 /ruta/carpeta_con_csv"
  exit 1
fi

shopt -s nullglob
files=("$dir"/*.csv)
if [[ ${#files[@]} -eq 0 ]]; then
  echo "No hay ficheros .csv en $dir"
  exit 1
fi

for f in "${files[@]}"; do
  printf 'Importando: %s\n' "$f"
  curl -sS -f -H "Authorization: Bearer ${TOKEN}" \
    -F "file=@${f};type=text/csv" \
    "${API_URL%/}/imports/csv"
  printf '\n'
done
