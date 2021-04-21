migrate: 
	sudo docker-compose run web python manage.py migrate

migrations: 
	sudo docker-compose run web python manage.py makemigrations $(ARGS)

run:
	sudo docker-compose down && sudo docker-compose up

devel:
	sudo docker-compose -f docker-compose-develop.yml down && sudo docker-compose -f docker-compose-develop.yml up

build:
	sudo docker-compose build

createsuperuser:
	sudo docker-compose run web python manage.py createsuperuser

collectstatic:
	sudo docker-compose run web python manage.py collectstatic

showenv:
	sudo docker-compose run web pip list

manage:
	sudo docker-compose run web python manage.py $(CMD)

reset_migrations:
	sudo find . -path "*/migrations/*.pyc"  -delete
	sudo find . -path "*/migrations/*.py" -not -name "__init__.py" -delete
	make init-db

initiate:
    make migrations ARGS=user
	make migrations ARGS=maxquant
	make migrations ARGS=api
	make migrations ARGS=rawtools
	make migrations ARGS=project
	make migrate
	make createsuperuser
