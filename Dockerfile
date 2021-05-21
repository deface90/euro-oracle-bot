FROM python:3.9-slim as dependencies

RUN apt-get update && \
    apt-get install -y gcc libpq-dev

RUN python -m pip install --upgrade pip
COPY requirements.txt ./
RUN python -m pip install --user -r requirements.txt

FROM python:3.9-slim as final

RUN apt-get update && \
    apt-get install -y gcc libpq-dev

COPY --from=dependencies /root/.local /root/.local

COPY ./euro_oracle_bot /app/src
WORKDIR /app/src
ENTRYPOINT exec python -u main.py
