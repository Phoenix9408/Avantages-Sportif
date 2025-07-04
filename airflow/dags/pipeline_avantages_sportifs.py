from datetime import datetime
import pendulum
import os
from dotenv import load_dotenv
from airflow import DAG
from airflow.operators.bash import BashOperator

# ------------------------------------------------------------------ #
# 1) Paramètres généraux                                           #
# ------------------------------------------------------------------ #
load_dotenv('/opt/airflow/project/.env')

def env_var(key, default=None):
    return os.getenv(key, default)

BASE_DIR = '/opt/airflow/project'
PARIS = pendulum.timezone('Europe/Paris')

def make_bash_task(task_id, script_path, extra_env=None):
    env = {
        'POSTGRES_HOST': env_var('POSTGRES_HOST', 'postgres'),
        'POSTGRES_DB': env_var('POSTGRES_DB', 'sport_avantages'),
        'POSTGRES_USER': env_var('POSTGRES_USER', 'postgres'),
        'POSTGRES_PASSWORD': env_var('POSTGRES_PASSWORD', 'postgres'),
        'GOOGLE_MAPS_API_KEY': env_var('GOOGLE_MAPS_API_KEY'),
        'ENTREPRISE_ADRESSE': env_var('ENTREPRISE_ADRESSE'),
        'PRIME_RATE': env_var('PRIME_RATE', '0.05'),
        'WB_THRESHOLD': env_var('WB_THRESHOLD', '15'),
        'DEP_LIMIT_MARCHE': env_var('DEP_LIMIT_MARCHE', '15'),
        'DEP_LIMIT_VELO': env_var('DEP_LIMIT_VELO', '25'),
        'DEP_LIMIT_TROTT': env_var('DEP_LIMIT_TROTT', '25'),
        'JOURS_BIEN_ETRE': env_var('JOURS_BIEN_ETRE', '5'),
    }
    if extra_env:
        env.update(extra_env)
    return BashOperator(
        task_id=task_id,
        bash_command=f'python {BASE_DIR}/{script_path}',
        env=env
    )

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'retries': 1,
}

# ------------------------------------------------------------------ #
# 2) Définition du DAG                                             #
# ------------------------------------------------------------------ #
with DAG(
    dag_id='pipeline_avantages_sportifs',
    default_args=default_args,
    start_date=datetime(2024,12,1,0,0,tzinfo=PARIS),
    schedule_interval='0 3 1 12 *',  # 3h 1er décembre
    catchup=False,
    tags=['p12','avantages'],
) as dag:

    # ------------------------------------------------------------------ #
    # 3) Tâches                                                        #
    # ------------------------------------------------------------------ #
    process_data = make_bash_task(
        task_id='process_data',
        script_path='activity_sport_script/Sport_Data_Solution_Activity_.py'
    )

    run_ge_tests = make_bash_task(
        task_id='run_ge_tests',
        script_path='activity_sport_script/Sport_data_solution_Great_Expectation.py'
    )

    # ------------------------------------------------------------------ #
    # 4) Dépendances                                                   #
    # ------------------------------------------------------------------ #
    process_data >> run_ge_tests
