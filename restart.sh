# Stop any running containers
docker-compose down

# Rebuild and re-initialize correctly
AIRFLOW_UID=$(id -u) docker-compose up airflow-init

# Start all services
AIRFLOW_UID=$(id -u) docker-compose up -d