#!/bin/bash

set -e

echo "Оновлюємо пакети та встановлюємо Python-залежності..."

sudo apt update -y
sudo apt install -y python3-pip python3-venv

echo "Створюємо віртуальне середовище airflow_venv..."

python3 -m venv airflow_venv
source airflow_venv/bin/activate

echo "Встановлюємо Python-бібліотеки..."

pip install --upgrade pip  # Рекомендується перед установкою

pip install pandas
pip install s3fs
pip install fsspec

echo "Перевірка AWS доступу (можна пропустити, якщо вже налаштовано)..."
aws sts get-session-token || echo "?? Не вдалося отримати токен. Переконайтесь, що aws configure виконано!"

echo "Встановлюємо Apache Airflow (може зайняти кілька хвилин)..."

export AIRFLOW_VERSION=2.9.1
export PYTHON_VERSION="$(python3 --version | cut -d ' ' -f 2 | cut -d '.' -f 1,2)"
export CONSTRAINT_URL="https://raw.githubusercontent.com/apache/airflow/constraints-${AIRFLOW_VERSION}/constraints-${PYTHON_VERSION}.txt"

pip install "apache-airflow==${AIRFLOW_VERSION}" --constraint "$CONSTRAINT_URL"
pip install apache-airflow-providers-postgres --constraint "$CONSTRAINT_URL"

echo "Запускаємо Airflow у standalone режимі..."
airflow standalone