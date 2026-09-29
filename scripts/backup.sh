#!/bin/sh
# Бэкапы базы Bina.ai (TASK-044/045). Работает в контейнере backup (docker-compose.yml).
#
#   sh /backup.sh loop            — следить и делать копию, если последней больше BACKUP_EVERY_HOURS
#   sh /backup.sh once            — копия сейчас
#   sh /backup.sh list            — список копий
#   sh /backup.sh restore latest  — восстановить последнюю копию (или имя файла)
#
# Подключение к базе — переменные PGHOST, PGUSER, PGPASSWORD, PGDATABASE.
# Копии: /backups/bina-ГГГГ-ММ-ДД_ЧЧ-ММ.dump (pg_dump -Fc), старше BACKUP_KEEP_DAYS удаляются.
set -eu

DIR="${BACKUP_DIR:-/backups}"
KEEP_DAYS="${BACKUP_KEEP_DAYS:-14}"
EVERY_HOURS="${BACKUP_EVERY_HOURS:-24}"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }

latest() {
    ls -1 "$DIR"/bina-*.dump 2>/dev/null | sort | tail -n 1
}

backup_once() {
    prefix="${1:-bina}"
    mkdir -p "$DIR"
    file="$DIR/$prefix-$(date '+%Y-%m-%d_%H-%M').dump"
    tmp="$file.tmp"
    log "Копия базы $PGDATABASE -> $file"
    pg_dump -Fc -f "$tmp"
    # Файл читается целиком — копия не битая
    pg_restore --list "$tmp" >/dev/null
    mv "$tmp" "$file"
    log "Готово: $(du -h "$file" | cut -f1)"
    find "$DIR" -name 'bina-*.dump' -mtime +"$KEEP_DAYS" -print -delete | sed 's/^/Удалена старая копия: /'
}

# Нужна ли копия: последней нет или она старше EVERY_HOURS
due() {
    last="$(latest)"
    [ -z "$last" ] && return 0
    [ -n "$(find "$last" -mmin +$((EVERY_HOURS * 60)))" ]
}

case "${1:-loop}" in
    loop)
        log "Бэкапы: каждые $EVERY_HOURS ч, хранить $KEEP_DAYS дн., папка $DIR"
        until pg_isready -q; do sleep 5; done
        while true; do
            if due; then
                backup_once || log "ОШИБКА: копия не создана"
            fi
            sleep 3600
        done
        ;;
    once)
        backup_once
        ;;
    list)
        ls -lh "$DIR"/*.dump 2>/dev/null || echo "Копий пока нет"
        ;;
    restore)
        target="${2:-latest}"
        if [ "$target" = "latest" ]; then
            target="$(latest)"
        elif [ -f "$DIR/$target" ]; then
            target="$DIR/$target"
        fi
        if [ -z "$target" ] || [ ! -f "$target" ]; then
            echo "Копия не найдена: ${2:-latest}" >&2
            exit 1
        fi
        pg_restore --list "$target" >/dev/null
        # Страховка: текущая база сохраняется перед заменой
        backup_once "before-restore"
        log "Восстановление из $target"
        # Начисто и одной транзакцией: при ошибке база остаётся как была
        {
            echo "SET client_min_messages = warning; DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
            pg_restore --no-owner -f - "$target"
        } | psql -v ON_ERROR_STOP=1 --single-transaction -q -o /dev/null -d "$PGDATABASE"
        log "База восстановлена"
        ;;
    *)
        echo "Команды: loop | once | list | restore [latest|файл]" >&2
        exit 2
        ;;
esac
