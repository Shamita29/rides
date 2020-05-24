FROM python:3-alpine
ADD . /todo
WORKDIR /todo
RUN pip3 install flask requests
RUN pip3 install flask_marshmallow
RUN pip3 install Flask-SQLAlchemy
EXPOSE 80
