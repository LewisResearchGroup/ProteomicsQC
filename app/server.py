from waitress import serve

from main.wsgi import application

if __name__ == '__main__':
    serve(application, port='8000', 
          url_scheme='https', threads=12,
          max_request_body_size=20*1073741824)