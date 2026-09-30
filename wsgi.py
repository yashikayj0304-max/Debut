from app import create_app

app = create_app(init=False)  # schema is created by `python manage.py init-db` (run once per deploy, see start.sh)
