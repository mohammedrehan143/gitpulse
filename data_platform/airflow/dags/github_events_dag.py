"""Airflow DAG: Hourly GitHub Event Stream Ingestion."""

from datetime import datetime, timedelta
# In real production Airflow deployment, import DAG, PythonOperator from airflow
# We structure this DAG in idiomatic Airflow format

DAG_DEFAULT_ARGS = {
    "owner": "airflow-engineer",
    "depends_on_past": False,
    "email_on_failure": True,
    "email": ["alerts@gitpulse.internal"],
    "retries": 3,
    "retry_delay": timedelta(minutes=5),
}


def extract_github_events(**context):
    """Fetches incremental events for tracked repositories."""
    print("Extracting incremental GitHub events...")
    return {"extracted_count": 142}


def publish_to_kafka(**context):
    """Streams extracted events to Apache Kafka topic."""
    print("Publishing extracted events to Kafka topic: gitpulse.github.raw_events")
    return {"published_count": 142}


dag_config = {
    "dag_id": "gitpulse_github_events_ingestion",
    "default_args": DAG_DEFAULT_ARGS,
    "description": "Hourly batch extraction and streaming of GitHub activity streams",
    "schedule_interval": "0 * * * *",
    "start_date": datetime(2026, 1, 1),
    "catchup": False,
    "tags": ["gitpulse", "ingestion", "kafka"],
}
