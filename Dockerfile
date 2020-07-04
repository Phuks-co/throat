FROM python:3.8-slim-buster

RUN apt-get update && apt-get install -y \
	git \
	redis-server \
	build-essential \
	libmagic-dev \
	libexiv2-dev \
	zlib1g-dev \
	libbz2-dev \
	libreadline-dev \
	libsqlite3-dev \
	wget \
	libffi-dev \
	curl \
	libssl-dev \
	npm \
	libboost-python-dev \
	libcairo2-dev \
	ibgirepository1.0-dev \
	libgexiv2-dev \
	libpq-dev \
	postgresql-client

COPY requirements.txt /requirements.txt
RUN pip install -r requirements.txt && rm requirements.txt

COPY package.json /package.json
COPY package-lock.json /package-lock.json
RUN npm ci

COPY . /throat
WORKDIR /throat
RUN mv ../node_modules node_modules && npm run build

EXPOSE 5000

CMD ["./throat.py"]
