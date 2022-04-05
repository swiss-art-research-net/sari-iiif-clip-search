FROM python:3.8

RUN mkdir /workdir
COPY ./requirements.txt /workdir/
WORKDIR /workdir
RUN pip install -r requirements.txt

RUN pip install flask waitress

ENV FLASK_ENV=development
ENV FLASK_APP=/workdir/src/api.py

# Run idling
ENTRYPOINT flask run --host=0.0.0.0