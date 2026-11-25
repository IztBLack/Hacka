#!/usr/bin/env bash
# Respaldo y restauración de PostgreSQL (contenedor cedis-postgres).
#   ./respaldo_pg.sh respaldar              -> genera respaldos/cedis_AAAAmmdd_HHMMSS.dump
#   ./respaldo_pg.sh verificar ARCHIVO      -> restaura en BD temporal y compara conteos
#   CONFIRMAR=si ./respaldo_pg.sh restaurar ARCHIVO [BD_DESTINO]
set -euo pipefail

CONTENEDOR="${CONTENEDOR:-cedis-postgres}"
BD="${BD:-cedis}"
USUARIO="${USUARIO:-cedis}"
DIR_RESPALDOS="${DIR_RESPALDOS:-$(cd "$(dirname "$0")/.." && pwd)/respaldos}"

psql_admin() { docker exec -i "$CONTENEDOR" psql -U "$USUARIO" -d postgres -v ON_ERROR_STOP=1 "$@"; }

conteos() {  # conteo de filas por tabla pública, ordenado, para comparar BDs
  docker exec -i "$CONTENEDOR" psql -U "$USUARIO" -d "$1" -At -v ON_ERROR_STOP=1 -c "
    SELECT table_name || ' ' ||
      (xpath('/row/c/text()', query_to_xml(
        format('SELECT count(*) AS c FROM %I.%I', table_schema, table_name), false, true, ''
      )))[1]::text
    FROM information_schema.tables
    WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
    ORDER BY table_name;"
}

respaldar() {
  mkdir -p "$DIR_RESPALDOS"
  local archivo="$DIR_RESPALDOS/${BD}_$(date +%Y%m%d_%H%M%S).dump"
  docker exec "$CONTENEDOR" pg_dump -U "$USUARIO" -d "$BD" -Fc -Z 9 > "$archivo"
  # Integridad básica: el archivo debe ser legible por pg_restore.
  docker exec -i "$CONTENEDOR" pg_restore --list < "$archivo" > /dev/null
  sha256sum "$archivo" > "$archivo.sha256"
  echo "Respaldo OK: $archivo"
}

verificar() {
  local archivo="${1:?Indica el archivo .dump}"
  local temporal="${BD}_verif_$$"
  trap 'psql_admin -c "DROP DATABASE IF EXISTS \"'"$temporal"'\" WITH (FORCE)" >/dev/null' EXIT
  [[ -f "$archivo.sha256" ]] && sha256sum -c "$archivo.sha256"
  psql_admin -c "CREATE DATABASE \"$temporal\""
  docker exec -i "$CONTENEDOR" pg_restore -U "$USUARIO" -d "$temporal" \
    --no-owner --exit-on-error < "$archivo"
  if diff <(conteos "$BD") <(conteos "$temporal"); then
    echo "Restauración verificada: conteos idénticos a $BD."
  else
    echo "ERROR: los conteos difieren entre $BD y la restauración." >&2
    exit 1
  fi
}

restaurar() {
  local archivo="${1:?Indica el archivo .dump}"
  local destino="${2:-$BD}"
  if [[ "${CONFIRMAR:-no}" != "si" ]]; then
    echo "Esto sobrescribe '$destino'. Repite con CONFIRMAR=si para continuar." >&2
    exit 1
  fi
  docker exec -i "$CONTENEDOR" pg_restore -U "$USUARIO" -d "$destino" \
    --clean --if-exists --no-owner --exit-on-error < "$archivo"
  echo "Restauración completada en '$destino'."
}

case "${1:-}" in
  respaldar) respaldar ;;
  verificar) shift; verificar "$@" ;;
  restaurar) shift; restaurar "$@" ;;
  *) echo "Uso: $0 {respaldar|verificar ARCHIVO|restaurar ARCHIVO [BD]}" >&2; exit 2 ;;
esac
