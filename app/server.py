from waitress import serve

from main.wsgi import application

if __name__ == "__main__":
    serve(
        application,
        port="8080",
        url_scheme="https",
        threads=4,
        max_request_body_size=20 * 1073741824,
    )
