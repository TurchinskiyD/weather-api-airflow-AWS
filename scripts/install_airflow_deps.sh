#!/bin/bash

set -e

echo "��������� ������ �� ������������ Python-���������..."

sudo apt update -y
sudo apt install -y python3-pip python3-venv

echo "��������� ��������� ���������� airflow_venv..."

python3 -m venv airflow_venv
source airflow_venv/bin/activate

echo "������������ Python-��������..."

pip install --upgrade pip  # ������������� ����� ����������

pip install pandas
pip install s3fs
pip install fsspec

echo "�������� AWS ������� (����� ����������, ���� ��� �����������)..."
aws sts get-session-token || echo "?? �� ������� �������� �����. �������������, �� aws configure ��������!"

echo "������������ Apache Airflow (���� ������� ����� ������)..."

export AIRFLOW_VERSION=2.9.1
export PYTHON_VERSION="$(python3 --version | cut -d ' ' -f 2 | cut -d '.' -f 1,2)"
export CONSTRAINT_URL="https://raw.githubusercontent.com/apache/airflow/constraints-${AIRFLOW_VERSION}/constraints-${PYTHON_VERSION}.txt"

pip install "apache-airflow==${AIRFLOW_VERSION}" --constraint "$CONSTRAINT_URL"
pip install apache-airflow-providers-postgres --constraint "$CONSTRAINT_URL"

echo "��������� Airflow � standalone �����..."
airflow standalone