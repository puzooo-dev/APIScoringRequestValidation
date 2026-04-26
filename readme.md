# 🐍 Python Test Automation Framework

> Автоматизированное тестирование API/UI с использованием Python, Pytest и GitHub Actions.

## 📋 Содержание

- [Описание](#описание)
- [Стек технологий](#стек-технологий)
- [Быстрый старт](#быстрый-старт)
    - [Установка](#установка)
    - [Запуск тестов](#запуск-тестов)
---

## 📖 Описание

Этот репозиторий содержит фреймворк для автоматизации тестирования, разработанный на **Python** с использованием библиотеки **pytest**.

Основные цели проекта:
*   Обеспечение стабильности функционала через автоматические регрессионные тесты.
*   Интеграция проверок качества кода (линтинг) в процесс разработки.
*   Автоматический запуск тестов при каждом изменении кода (CI/CD).

---

## 🛠 Стек технологий

*   **Язык:** Python 3.10+
*   **Фреймворк тестирования:** [Pytest](https://docs.pytest.org/)
*   **HTTP клиент:** [Requests](https://docs.python-requests.org/) (для API тестов)
*   **Линтер:** [Flake8](https://flake8.pycqa.org/) / [Black](https://black.readthedocs.io/)
*   **Покрытие кода:** [Coverage.py](https://coverage.readthedocs.io/)
*   **CI/CD:** GitHub Actions

---

## 🚀 Быстрый старт

### Установка

1.  Клонируйте репозиторий:
    ```bash
    git clone https://github.com/<your-username>/<your-repo-name>.git
    cd <your-repo-name>
    ```

2.  Создайте и активируйте виртуальное окружение (рекомендуется):

    **Linux / macOS:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

    **Windows:**
    ```bash
    python -m venv venv
    venv\Scripts\activate
    ```

3.  Установите зависимости:
    ```bash
    pip install --upgrade pip
    pip install -r requirements.txt
    ```

### Запуск тестов

Запустить все тесты из папки `tests`:
```bash
pytest tests/