# Compile the translations.
# This is done in its own step as the translations are used by both
# webpack and Flask.
FROM python:3.7-slim-buster AS translations
RUN pip install Babel
COPY app/translations /translations
RUN pybabel compile --directory=translations


FROM node:14-buster-slim as webpack
# Install our npm requirements
COPY package.json package-lock.json /
RUN npm ci
# Build our static assets with webpack.
COPY webpack.config.js .
RUN mkdir /app
COPY app/static /app/static
COPY --from=translations /translations /app/translations
RUN npm run build


FROM python:3.7-slim-buster

# Install system packages.
RUN \
  apt-get update && apt-get install -yqq \
     build-essential \
     libpq-dev \
     postgresql-client \
  && rm -rf /var/lib/apt/lists/*

# Install our python requirements
COPY requirements.txt /requirements.txt
RUN pip3 install -r requirements.txt && rm requirements.txt

# Create the app user and the application directory.
RUN useradd -ms /bin/bash app
COPY --chown=app:app . /throat
WORKDIR /throat

# Pull in the compiled translations and static files.
COPY --from=translations --chown=app:app /translations /throat/app/translations
COPY --from=webpack --chown=app:app /app/manifest.json /throat/app/manifest.json
COPY --from=webpack --chown=app:app /app/static/gen /throat/app/static/gen

USER app
EXPOSE 5000

CMD ["./start_all.sh"]
