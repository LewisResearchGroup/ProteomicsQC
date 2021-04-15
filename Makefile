migrate: 
	sudo docker-compose run web python app/manage.py migrate

migrations: 
	sudo docker-compose run web python app/manage.py makemigrations $(ARGS)

run:
	sudo docker-compose up

build:
	sudo docker-compose build

createsuperuser:
	sudo docker-compose run web python app/manage.py createsuperuser

collectstatic:
	sudo docker-compose run web python app/manage.py collectstatic

showenv:
	sudo docker-compose run web pip list

manage:
	sudo docker-compose run web python app/manage.py $(CMD)
