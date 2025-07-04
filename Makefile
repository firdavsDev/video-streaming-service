ifneq (,$(wildcard ./.env))
	include .env
	export ENV_FILE_PARAM = --env-file .envs
endif

up:
	docker-compose up --build --remove-orphans

down:
	docker-compose down --remove-orphans

makemigrations:
	docker-compose exec -T app python manage.py makemigrations

migrate:
	docker-compose exec -T app python manage.py migrate
