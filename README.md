# UEFA EURO 2020 Oracle Telegram bot

Telegram bot for game of predictions on matches of UEFA EURO 2020 (which plays in 2021).

An actual version on russian available here: [@Euro2020OracleBot](https://t.me/Euro2020OracleBot)

## Deployment for production ##
Use `docker-compose.yml` file to deploy required containers. Specify ENV var `POSTGRES_PASSWORD`
with default Postgres password. Postgres container will bind to localhost and non-standart
`5433` port. Change it if needed. 

Next, you need to apply migrations. Enter `bot` container:

`docker exec -ti bot /bin/bash`

Edit file `/app/src/alembic.ini` and set correct DSN for connection to DB (line 42):

`sqlalchemy.url = postgresql://postgres:postgres@postgres/bot`

Now execute follow command to apply migrations (at `/app/src`):

`/root/.local/bin/alembic upgrade head`

You will not see any Python exceptions if migrations were applied successfull.

Now create (or copy `.env.dist`) file `.env` and fill token and DSN env vars, or configure environment globaly (not recommended).

Possible ENV vars:

| Name | Description | Required |
| ---- | ----------- | -------- |
| DATA_API_TOKEN | API token of [elenasports.io](https://elenasport.io/) to fetch matches and results (available free plan) | Yes |
| BOT_TOKEN | Telegram Bot token | Yes |
| POSTGRES_DSN | Postgres DSN | Yes |
| TZ | Timezone for user output | No, `Europe/Moscow` is default |
