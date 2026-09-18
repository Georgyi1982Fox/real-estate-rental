
# Кто за что отвечает

## Бэкенд (Я)
- src/bina/
- tests/
- alembic/
- pyproject.toml
- requirements.txt
- alembic.ini

## Фронтенд (Друг)
- frontend/templates/
- frontend/static/
- frontend/mock_data.json

## Общее (только через согласование)
- docs/
- README.md
- docker-compose.yml


2. Файлы которые могут пересекаться
requirements.txt — если другу нужны Python-зависимости для тестов фронтенда:
Он пишет вам в чат: "добавь pytest-html"
Вы добавляете и коммитите
docs/ — оба могут редактировать:
Правило: один человек = один файл
Или разные файлы: docs/API.md (вы), docs/UI.md (друг)
docker-compose.yml (когда появится):
Только Я(Букенд разработчик) редактируете


## Git workflow без конфликтов
Каждый день перед началом работы:

# Бесик делает:
git checkout develop
git pull origin develop
git checkout -b feature/frontend-search-page

# Я делаю:
git checkout develop
git pull origin develop
git checkout -b feature/backend-translate

Перед пушем:
# Сначала pull, потом push
git pull origin develop
# Если конфликты — разрешить, потом commit
git push origin feature/...



_______


Если конфликт всё же возник
Сценарий: оба изменили docs/SPEC.md

# 1. Pull с конфликтом
git pull origin develop

# Git покажет:
# CONFLICT (content): Merge conflict in docs/SPEC.md

# 2. Откройте файл в редакторе
# Увидите маркеры конфликтов:
# <<<<<<< HEAD
# Ваша версия
# =======
# Версия друга
# >>>>>>> feature/...

# 3. Выберите нужную версию (или объедините)
# 4. Сохраните файл

# 5. Закоммитьте
git add docs/SPEC.md
git commit -m "merge: resolve conflict in SPEC.md"
git push


Инструменты для разрешения конфликтов:

VS Code (лучший вариант):
Открывает файл с кнопками "Accept Current Change" / "Accept Incoming Change"
Визуально показывает различия
GitKraken или SourceTree:
Графические клиенты с удобным merge tool


