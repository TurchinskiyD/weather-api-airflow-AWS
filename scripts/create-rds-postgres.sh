#!/bin/bash

# Назви змінних, щоб не було пекла хардкоду
DB_IDENTIFIER="rds-db-for-open-weather"
DB_USERNAME="postgres"
DB_PASSWORD="YOUR_SUPER_SECRET_PASSWORD"
DB_INSTANCE_CLASS="db.t3.micro"
DB_ENGINE="postgres"
DB_ALLOCATED_STORAGE=20
DB_SECURITY_GROUP="rds-db-ow-vpc-security"
DB_REGION="es-west-2"

echo "Створюємо RDS PostgreSQL інстанс: $DB_IDENTIFIER ..."

aws rds create-db-instance \
  --db-instance-identifier "$DB_IDENTIFIER" \
  --db-instance-class "$DB_INSTANCE_CLASS" \
  --engine "$DB_ENGINE" \
  --allocated-storage "$DB_ALLOCATED_STORAGE" \
  --master-username "$DB_USERNAME" \
  --master-user-password "$DB_PASSWORD" \
  --vpc-security-group-ids "$DB_SECURITY_GROUP" \
  --backup-retention-period 7 \
  --availability-zone "${DB_REGION}a" \
  --no-publicly-accessible \
  --db-name weather \
  --region "$DB_REGION"

echo "Готово. Чекаємо 5-10 хвилин"
