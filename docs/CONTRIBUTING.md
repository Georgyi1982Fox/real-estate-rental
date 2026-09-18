# Правила работы с репозиторием

git clone https://github.com/Georgyi1982Fox/real-estate-rental.git

## Ветки
- main — продакшн
- develop — разработка
- feature/* — фичи

## Кто за что отвечает
- Бэкенд: src/bina/, tests/, alembic/
- Фронтенд: frontend/

## Перед началом работы
git pull origin develop

## Перед пушем
git pull origin develop
# Разрешить конфликты если есть
git push


# Полный цикл GIT WORKFLOW:
main          ← только стабильные релизы (как магазин на полке)
  │
  └── develop ← кухня, где готовят все фичи (интеграция)
        │
        ├── feature/backend-translate    ← вы готовите блюдо
        ├── feature/frontend-search      ← друг готовит блюдо
        └── feature/fix-bug              ← кто-то чинит


Правило в одну строку:
feature/* → develop → main

Шаг 1: Вы начинаете задачу

# 1. Переключитесь на develop
git checkout develop

# 2. Обновите локальную версию (на случай если кто то что-то слил)
git pull origin develop

# 3. Создайте свою feature-ветку
git checkout -b feature/любое название

---------------


Шаг 2: Вы работаете и коммитите

# Пишете код...
git add .
git commit -m "feat: add translate use-case"

# Ещё код...
git add .
git commit -m "feat: add tests for translate"

Можно делать сколько угодно коммитов в своей ветке.

-----------------


Шаг 3: Отправляете ветку на GitHub
git push -u origin feature/backend-translate

Что произошло: ваша ветка появилась на GitHub. Теперь её видно.


--------------------


Шаг 4: Создаёте Pull Request (на GitHub)

1.Зайдите на GitHub в ваш репозиторий

2.Вверху увидите жёлтую плашку: "feature/твоя ветка had recent pushes" с кнопкой Compare & pull request

3.Нажмите её

4.Убедитесь что стрелка идёт feature/твоя → develop (НЕ в main!)

Напишите описание что сделали

Нажмите Create pull request

-----------------------

Шаг 5: Ревью и слияние

Друг ревьюит (когда начнёте строго соблюдать процесс)

Друг смотрит ваш PR

Оставляет комментарии или approves

Вы мерджите


После того как фича слита в develop, ветка становится мусором.

На GitHub (после мерджа PR):
GitHub сам предложит кнопку "Delete branch" — нажмите её
Или в настройках репо включите автоудаление: Settings → General → ✅ Automatically delete head branches

Локально (в PowerShell):
# Удалить одну ветку
git branch -d feature/backend-translate

# Удалить все слитые ветки разом
git branch --merged develop | Where-Object { $_ -notmatch 'develop|main' } | ForEach-Object { git branch -d $_.Trim() }

На GitHub (удалить удалённую ветку):
git push origin --delete feature/backend-translate


--------------------------

Шаг 6: Возврат к develop для новой задачи

git checkout develop
git pull origin develop
git checkout -b feature/новая-задача

-----------------------------



Когда сливать develop в main?
Только когда готовы к релизу! Например:
Раз в неделю
Когда собрали MVP
Когда протестировали всё вместе

# Находясь на main
git checkout main
git pull origin main
git merge develop
git push origin main


Или через PR на GitHub: develop → main (рекомендую так).



Визуальная схема полного цикла

День 1:
main ─────────────────────────────────────────────
         \
          develop ─────────────────────────────────
                   \                    \
                    \                    \
                     feature/             feature/
                     backend              frontend
                     (вы)                 (друг)

День 3 (вы закончили):
main ─────────────────────────────────────────────
         \
          develop ─────────────────────────────────
                   \                    \
                    [MERGE]              feature/
                                         frontend

День 5 (друг закончил):
main ─────────────────────────────────────────────
         \
          develop ─────────────────────────────────
                   \                    \
                    [MERGE]             [MERGE]

День 7 (релиз):
main ─────────────────────────────────────────────
         \                    \
          develop ───────────[MERGE]→ main v1.0


