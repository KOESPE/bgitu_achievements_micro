# Первоначальная настройка
После настройки venv нужно установить chromium для playwright
1. Активируйте виртуальное окружение:

    На Windows:

    ```bash
    venv\Scripts\activate
    ```
    На Linux:
    
    ```bash
    source venv/bin/activate
    ```
2. Установите chromium
    ``` bash
    playwright install chromium
    ```
3. Для работы на Linux без GUI:
    ``` bash
    playwright install-deps chromium
    ```

# Текущие проблемы
- Спортивные достижения не имеют баллов, вообще никаких вариантов, которые будут иметь вес.(КАЛУГА ФСП по документам — спорт). Решение: либо менять в еос (если возможно), либо искусственно добавлять им баллы
- /auth выдает ошибку