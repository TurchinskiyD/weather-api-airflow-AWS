from airflow import DAG
from airflow.operators.dummy_operator import DummyOperator
from airflow.providers.postgres.operators.postgres import PostgresOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
from datetime import timedelta, datetime, timezone
from airflow.providers.http.sensors.http import HttpSensor
from airflow.providers.http.operators.http import SimpleHttpOperator
from airflow.operators.python import PythonOperator
from airflow.utils.task_group import TaskGroup
import pandas as pd
import json
from airflow.models import Variable
import logging

api_key = Variable.get("openweathermap_api_key")


def kelvin_to_celsius(temp_in_kelvin):
    temp_in_celsius = temp_in_kelvin - 273.15
    return round(temp_in_celsius, 2)


def transform_load_data(task_instance):
    data = task_instance.xcom_pull(task_ids='group_a.tsk_extract_weather_data')

         # Перевірка, чи дані були отримані успішно
    logging.info(f"XCom: {data}")

    if not data or not isinstance(data, dict):
        raise ValueError("Дані від API не отримані або є порожніми.")

    city = data['name']
    weather_description = data['weather'][0]['description']
    temp_celsius = kelvin_to_celsius(data['main']['temp'])
    feels_like_celsius = kelvin_to_celsius(data['main']['feels_like'])
    min_temp_celsius = kelvin_to_celsius(data['main']['temp_min'])
    max_temp_celsius = kelvin_to_celsius(data['main']['temp_max'])
    pressure = data['main']['pressure']
    humidity = data['main']['humidity']
    wind_speed = data['wind']['speed']
    time_of_record = (datetime.fromtimestamp(data['dt'] + data['timezone'], tz=timezone.utc).
                                strftime('%Y-%m-%d %H:%M:%S'))
    sunrise_time = (datetime.fromtimestamp(data['sys']['sunrise'] + data['timezone'], tz=timezone.utc).
                            strftime('%Y-%m-%d %H:%M:%S'))
    sunset_time=(datetime.fromtimestamp(data['sys']['sunset'] + data['timezone'], tz=timezone.utc).
                            strftime('%Y-%m-%d %H:%M:%S'))

    transformed_data = {"City": city,
                        "Description": weather_description,
                        "Temperature (°C)": temp_celsius,
                        "Feels Like (°C)": feels_like_celsius,
                        "Min Temp (°C)": min_temp_celsius,
                        "Max Temp (°C)": max_temp_celsius,
                        "Pressure": pressure,
                        "Humidity": humidity,
                        "Wind Speed (m/s)": wind_speed,
                        "Time of Record": time_of_record,
                        "Sunrise (Local Time)": sunrise_time,
                        "Sunset (Local Time)": sunset_time
                        }

    transform_data_list = [transformed_data]
    df_data = pd.DataFrame(transform_data_list)
    df_data.to_csv('current_weather_data.csv', index=False, header=False)
      
      
def join_data_and_push(**kwargs):
    hook = PostgresHook(postgres_conn_id='postgres_conn')
    sql = """
        SELECT
            wd.city, 
            wd.description, 
            wd.temperature_celsius,
            wd.feels_like_celsius,
            wd.min_temp_celsius,
            wd.max_temp_celsius,
            wd.pressure,
            wd.humidity,
            wd.wind_speed, 
            wd.time_of_record,
            wd.sunrise_local_time,
            wd.sunset_local_time,
            cl.state,
            cl.population_2020,
            cl.land_area_sq_km, 
            cl.population_density
        FROM weather_data AS wd
        INNER JOIN city_look_up AS cl USING(city);
    """
    connection = hook.get_conn()
    cursor = connection.cursor()
    cursor.execute(sql)
    result = cursor.fetchall()
    return result

    
def load_joined_data_to_s3(task_instance):
    data = task_instance.xcom_pull(task_ids="tsk_join_data", key='return_value')
    
    print("рџ”Ќ Pulled from XCom:", data)

    if not data:
        raise ValueError("вќЊ РќРµРјР°С” РґР°РЅРёС… Сѓ XCom РІС–Рґ tsk_join_data")
    df = pd.DataFrame(data, columns = ['city', 'description', 'temperature_celsius', 
                                       'feels_like_celsius', 'min_temp_celsius', 
                                       'max_temp_celsius', 'pressure','humidity', 
                                       'wind_speed', 'time_of_record', 
                                       'sunrise_local_time', 'sunset_local_time', 
                                       'state', 'population_2020', 'land_area_sq_km', 
                                       'population_density'])

    now = datetime.now()
    city = data[0][0]
    dt_string = now.strftime("%d%m%Y%H%M")
    dt_string = 'joined_weather_data_' + city + dt_string
    df.to_csv(f"s3://weather-api-airflow/{dt_string}.csv", index=False)


def load_weather():
    hook = PostgresHook(postgres_conn_id = 'postgres_conn')
    hook.copy_expert(
         sql="COPY weather_data FROM stdin WITH DELIMITER as ',' ",
         filename='current_weather_data.csv')


default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2024, 11, 5),
    'email': ['myemail@domain.com'],
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=1)
}
with DAG('weather_dag',
        default_args=default_args,
        schedule_interval = '@daily',
        catchup=False) as dag:
        start_pipeline = DummyOperator(
            task_id ='task_start_pipeline',
        )

        test_postgres_conn = PostgresOperator(
             task_id='tsk_test_postgres_conn',
             postgres_conn_id='postgres_conn',
             sql="SELECT 1;"
        )
             
        join_data = PythonOperator(
            task_id='tsk_join_data',
            python_callable=join_data_and_push,
            provide_context=True
        )

        load_joined_data = PythonOperator(
             task_id = 'tsk_load_joined_data',
             python_callable=load_joined_data_to_s3
        )

        end_pipeline = DummyOperator(
            task_id = 'task_end_pipeline'
        )

        with TaskGroup(group_id = 'group_a', 
                        tooltip= "Extract_from_S3_and_weatherapi") as group_A:
            create_table_1 = PostgresOperator(
                task_id='tsk_create_table_1',
                postgres_conn_id = "postgres_conn",
                sql= '''CREATE TABLE IF NOT EXISTS city_look_up (
                    city TEXT NOT NULL,
                    state TEXT NOT NULL,
                    population_2020 numeric NOT NULL,
                    land_area_sq_km numeric NOT NULL,
                    population_density numeric NOT NULL);
                    '''
            )

            truncate_table = PostgresOperator(
                task_id='tsk_truncate_table',
                postgres_conn_id = "postgres_conn",
                sql= '''TRUNCATE TABLE city_look_up;'''
            )

            uploadS3_to_postgres = PostgresOperator(
            task_id="tsk_uploadS3_to_postgres",
            postgres_conn_id="postgres_conn",
            sql='''SELECT aws_s3.table_import_from_s3(
                        'city_look_up',                           -- назва таблиці в PostgreSQL
                        '',                                       -- список колонок ('' = всі колонки)
                        '(format csv, DELIMITER '','', HEADER true)',  -- формат CSV: роздільник — кома, з заголовками
                        'for-open-weather-bucket',                -- ім’я бакету в S3
                        'ua_city.csv',                            -- ім’я CSV-файлу в бакеті
                        'us-west-2'                               -- регіон AWS, де знаходиться бакет
                        );'''
        )

            create_table_2 = PostgresOperator(
                task_id='tsk_create_table_2',
                postgres_conn_id = "postgres_conn",
                sql= ''' 
                    CREATE TABLE IF NOT EXISTS weather_data (
                    city TEXT,
                    description TEXT,
                    temperature_celsius NUMERIC,
                    feels_like_celsius NUMERIC,
                    min_temp_celsius NUMERIC,
                    max_temp_celsius NUMERIC,
                    pressure NUMERIC,
                    humidity NUMERIC,
                    wind_speed NUMERIC,
                    time_of_record TIMESTAMP,
                    sunrise_local_time TIMESTAMP,
                    sunset_local_time TIMESTAMP);
                    '''
            )

            is_weather_api_ready = HttpSensor(
                task_id ='tsk_weather_api_ready',
                http_conn_id='weathermap_api',
                endpoint=f'/data/2.5/weather?q=Kharkiv&appid={api_key}',
            )

            extract_weather_data = SimpleHttpOperator(
                task_id ='tsk_extract_weather_data',
                http_conn_id='weathermap_api',
                endpoint='/data/2.5/weather?q=Kharkiv&appid={{ var.value.openweathermap_api_key }}',
                method = 'GET',
                response_filter = lambda r: json.loads(r.text),
                log_response = True,
                do_xcom_push=True
            )

            transform_load_weather_data = PythonOperator(
                task_id ='tsk_transform_load_weather_data',
                python_callable=transform_load_data
            )

            load_weather_data = PythonOperator(
                task_id = 'tsk_load_weather_data',
                python_callable= load_weather
            )

            create_table_1 >> truncate_table >> uploadS3_to_postgres
            create_table_2 >> is_weather_api_ready >> extract_weather_data >> transform_load_weather_data >> load_weather_data
         
    start_pipeline >> test_postgres_conn >> group_A >> join_data >> load_joined_data >> end_pipeline