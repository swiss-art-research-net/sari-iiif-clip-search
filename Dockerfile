FROM python:3.10

RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

RUN mkdir /workdir
COPY ./requirements.txt /workdir/
WORKDIR /workdir
RUN pip install -r requirements.txt

# Install task runner (http://taskfile.dev) into /usr/local/bin
RUN sh -c "curl -sSL https://taskfile.dev/install.sh | sh -s -- -b /usr/local/bin"

RUN pip install flask requests waitress sari-sparql-parser==0.0.6

ADD ./precomputedFeatures /precomputedFeatures
ADD ./src /workdir/src

# Run once to download model to image
RUN python src/test.py

ENV FLASK_APP=/workdir/src/api.py

VOLUME ["/workdir/data"]

CMD ["python", "src/api.py"]