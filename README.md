# Cymbal Coffee - Oracle VertexAI Demo

## Developer Setup Instructions

### Setup database and environment

```shell
make install # install dev components
cp .env.example .env # edit accordingly
make start-infra # starts containers and configures user
```

#### Manual Infrastructure Setup

**Note** If would like to do this manually, here are the steps the above `make start-infra` process is running:

```shell
docker-compose up -d # starts dev infra
cp .env.example .env # edit accordingly
docker exec -it  oracledb-vertexai-demo-db-1 bash
sqlplus / as sysdba
```

`app` needs to be able to select on `v_$transaction` to execute the initial migrations.

```sql
ALTER SESSION SET CONTAINER = freepdb1;
grant connect, resource to app;
grant select on v_$transaction to app;
```

### deploy database models

```shell
pdm run app database upgrade
```

- you can activate the virtual env manually (. .venv/bin/activate) or prefix every command with `pdm run`

### deploy default data

```shell
pdm run app database load-fixtures
```

### generate vectors from product descriptions

```shell
pdm run app database load-vectors
```

### run the CLI version of the app

```shell
pdm run app recommend
```

### run the web server

```shell
pdm run app run -p 5005 # set port accordingly
```
