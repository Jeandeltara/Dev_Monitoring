name: Cleanup Old Reports

on:
  schedule:
    - cron: '1 21 * * *'  # Каждый день в 21:01 UTC (00:01 по Киеву в летнее время)
  workflow_dispatch:      # Кнопка ручного запуска для тестов

permissions:
  contents: write         # Разрешение на удаление и коммит файлов в репозиторий

jobs:
  cleanup-job:
    runs-on: ubuntu-latest

    steps:
    - name: Проверяем код репозитория
      uses: actions/checkout@v4
      with:
        persist-credentials: true

    - name: Настраиваем Python
      uses: actions/setup-python@v5
      with:
        python-version: '3.10'

    - name: Запуск скрипта удаления старых отчетов
      run: python clean_reports.py

    - name: Синхронизация изменений с GitHub
      run: |
        git config --local user.email "github-actions[bot]@users.noreply.github.com"
        git config --local user.name "github-actions[bot]"
        
        # Фиксируем удаление файлов в git tracking
        # Если файлы были удалены скриптом, git status это заметит
        git add -A
        
        # Коммитим только если действительно были удалены файлы
        git diff --cached --quiet || (git commit -m "Автоматическое удаление отчетов 3-дневной давности [skip ci]" && git push origin main)
