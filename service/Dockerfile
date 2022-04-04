FROM python:3.8

RUN mkdir /workdir
COPY ./requirements.txt /workdir/
WORKDIR /workdir
RUN pip install -r requirements.txt

RUN pip install SPARQLWrapper pathlib
# Run idling
ENTRYPOINT tail -f /dev/null