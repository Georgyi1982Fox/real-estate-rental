# Git Workflow проекта Bina.ai

## Ветки
- main — продакшн, только релизы
- develop — интеграционная ветка, сюда сливаются все фичи
- feature/* — ветки для задач

## Правила
1. Никогда не коммитить напрямую в main или develop
2. Каждая задача = отдельная feature-ветка от develop
3. Перед началом работы: git pull origin develop
4. После завершения: PR feature/* → develop
5. Релиз: PR develop → main (раз в неделю или по готовности)

## Команды для новой задачи
git checkout develop
git pull origin develop
git checkout -b feature/название-задачи

## Команды для завершения задачи
git add .
git commit -m "feat: описание"
git push -u origin feature/название-задачи
# Создать PR на GitHub