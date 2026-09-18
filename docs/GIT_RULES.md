# Правила Git для Qwen Code

## Ты всегда работаешь в feature-ветке!

### Перед началом работы проверь:
1. git branch — должна быть feature/* ветка
2. Если main или develop — СТОП, переключись

### Команды:
- git add .
- git commit -m "тип: описание" (Conventional Commits)
- git push

### Запрещено:
- Коммитить в main
- Коммитить в develop
- Делать git merge без моего разрешения