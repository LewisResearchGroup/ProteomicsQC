migrate: 
	sudo docker-compose run web python manage.py migrate

migrations: 
	sudo docker-compose run web python manage.py makemigrations $(ARGS)

run:
	sudo docker-compose down && sudo docker-compose up

serve:
	sudo docker-compose down && sudo docker-compose up -d

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

init:
	make build
	make migrations
	make migrations ARGS=user
	make migrations ARGS=maxquant
	make migrations ARGS=api
	make migrations ARGS=project
	make migrations ARGS=dashboards
	make migrate
	make createsuperuser
	make collectstatic

update:
	git pull --recurse-submodules
	make build
	make migrations
	make migrate

down:
	sudo docker-compose down
	sudo docker-compose -f docker-compose-develop.yml down

test: 
	sudo docker-compose -f docker-compose-develop.yml run web python manage.py test --noinput

get-test-data:
	gdown --folder https://drive.google.com/drive/folders/1kdQUXbr6DTBNLFBXLYrR_RLoXDFwCh_N?usp=sharing --output app/tests/data/D01

doc:
	mkdocs gh-deploy

schema:
	sudo docker-compose -f docker-compose-develop.yml run web python manage.py graph_models --arrow-shape normal -o schema.png -a 

versions:
	sudo docker-compose run web conda env export -n base


