FROM python:3.8-buster

# Install node prereqs, nodejs and yarn
# Ref: https://deb.nodesource.com/setup_12.x
# Ref: https://yarnpkg.com/en/docs/install
RUN \
  echo "deb https://deb.nodesource.com/node_12.x buster main" > /etc/apt/sources.list.d/nodesource.list \
  && wget -qO- https://deb.nodesource.com/gpgkey/nodesource.gpg.key | apt-key add - \
  && echo "deb https://dl.yarnpkg.com/debian/ stable main" > /etc/apt/sources.list.d/yarn.list \
  && wget -qO- https://dl.yarnpkg.com/debian/pubkey.gpg | apt-key add - \
  && apt-get update \
  && apt-get install -yqq \
    nodejs \
    yarn \
    libgirepository1.0-dev \
    libgexiv2-dev \
  && pip install -U pip && pip install pipenv \
  && npm i -g npm@^6 \
  && rm -rf /var/lib/apt/lists/*

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
