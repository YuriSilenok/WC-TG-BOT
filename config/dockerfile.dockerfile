FROM python:3.11-slim

WORKDIR /app

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

# Клонирование репозитория
RUN git clone https://github.com/YuriSilenok/WC-TG-BOT.git .

# Установка Python зависимостей
RUN pip install --no-cache-dir -r requirements.txt

# Создание директории для данных
RUN mkdir -p /app/data

# Запуск приложения
CMD ["python", "main.py"]