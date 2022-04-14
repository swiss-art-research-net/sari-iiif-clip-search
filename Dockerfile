FROM python:3.8

RUN mkdir /workdir
COPY ./requirements.txt /workdir/
WORKDIR /workdir
RUN pip install -r requirements.txt

RUN pip install flask requests waitress sari-sparql-parser==0.0.6

ADD ./precomputedFeatures /precomputedFeatures
ADD ./src /workdir/src

# Run once to download model to image
RUN python src/test.py

ENV FLASK_ENV=development
ENV FLASK_APP=/workdir/src/api.py

VOLUME ["/workdir/data"]

# Run idling
ENTRYPOINT flask run --host=0.0.0.0