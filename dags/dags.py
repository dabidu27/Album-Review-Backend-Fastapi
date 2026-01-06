from user_manager import UserManager, other_albums_by_artist, collaborative_filtering
from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta

user_manager = UserManager()


async def recommendation_engine():

    await user_manager.other_albums_by_artist()
    await user_manager.collaborative_filtering()


default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "start_date": datetime(2025, 9, 14),
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}
with DAG(
    "weekly_recommendations",
    default_args=default_args,
    description="Run recommendation engine weekly",
    schedule_interval="@weekly",
    catchup=False,
) as dag:

    generate_recommendations = PythonOperator(
        task_id="generate_recommendations", python_callable=recommendation_engine
    )
