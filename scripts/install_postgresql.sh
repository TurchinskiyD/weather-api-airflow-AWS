#!/bin/bash

set -e  # Зупинити скрипт при помилці

echo "Додаємо офіційний ключ PostgreSQL..."
curl -fsSL https://www.postgresql.org/media/keys/ACCC4CF8.asc | gpg --dearmor | sudo tee /etc/apt/trusted.gpg.d/postgresql.gpg > /dev/null

echo "Додаємо репозиторій PostgreSQL до APT..."
echo "deb http://apt.postgresql.org/pub/repos/apt/ $(lsb_release -cs)-pgdg main" | sudo tee /etc/apt/sources.list.d/pgdg.list

echo "Оновлюємо кеш пакетів..."
sudo apt update

echo "Встановлюємо PostgreSQL..."
sudo apt install -y postgresql-16

echo "Перевірка статусу служби PostgreSQL..."
sudo systemctl status postgresql --no-pager

echo "PostgreSQL успішно встановлено!"
psql --version
