# C3D3 FastAPI
No dependencies.

---

C3D3 FastAPI backend helps to automate C3D3 Data Vault management.

# Configuration

First of all to configure FastAPI backend correctly need to do next steps:

- Clone current repository:
```
git clone https://github.com/e183b796621afbf902067460/c3d3-fastapi.git
```

- Get into the project folder:
```
cd c3d3-fastapi/src/microservices
```

- Set environment variables in [.env](https://github.com/e183b796621afbf902067460/c3d3-fastapi/blob/master/src/microservices/.env).

# Docker

- Run docker compose (`sudo`):
```
docker-compose up -d --build
```

- Check C3 and D3 container's ID and copy them:
```
docker ps
```

- Create AuthDB, C3Vault and D3Vault instances:
```
docker exec -it <CONTAINER ID> python3 app/orm/scripts/create.py
```

- And setup alembic for each instance:
```
sudo docker exec -it <CONTAINER ID> bash -c 'cd app/orm; alembic upgrade head'
```

- Create default admin user in `auth` container:
```
docker exec -it <CONTAINER ID> python3 app/__init__.py
```

# Exit
- To stop all running containers:
```
docker stop $(docker ps -a -q)
```
- And remove it all:
```
docker rm $(docker ps -a -q)
```

# Alembic
- After any changes in DBs this command should be done in `/app/orm` path:
```
alembic revision --autogenerate
```
- And make migrations:
```
alembic upgrade head
```

# Endpoints

### auth/
- `/api/v1/auth/login`
```python
import requests as r


url = 'http://0.0.0.0:8000/api/v1/auth/login?self=self'
data = {
  "username": "string",
  "password": "string"
}
header = {'accept': 'application/json', 'Content-Type': 'application/json'}

response = r.post(url=url, json=data, headers=header)
```

### c3/
- `/api/v1/c3/new_account`
```python
import requests as r


access_token = ''
url = 'http://0.0.0.0:8000/api/v1/c3/new_account?self=self'
data = {
  "label_name": "string",
  "label_api_key": "string",
  "label_api_secret": "string"
}
header = {'accept': 'application/json', 'Content-Type': 'application/json', 'authorization': access_token}

response = r.post(url=url, json=data, headers=header)
```

- `/api/v1/c3/new_account_balances`
```python
import requests as r


access_token = ''
url = 'http://0.0.0.0:8000/api/v1/c3/new_account_balances?self=self'
data = {
  "exchange_name": "string",
  "instrument_name": "string",
  "label_name": "string"
}
header = {'accept': 'application/json', 'Content-Type': 'application/json', 'authorization': access_token}

response = r.post(url=url, json=data, headers=header)
```

- `/api/v1/c3/new_account_limit_orders`
```python
import requests as r


access_token = ''
url = 'http://0.0.0.0:8000/api/v1/c3/new_account_limit_orders?self=self'
data = {
  "exchange_name": "string",
  "instrument_name": "string",
  "label_name": "string"
}
header = {'accept': 'application/json', 'Content-Type': 'application/json', 'authorization': access_token}

response = r.post(url=url, json=data, headers=header)
```

- `/api/v1/c3/new_account_liquidations`
```python
import requests as r


access_token = ''
url = 'http://0.0.0.0:8000/api/v1/c3/new_account_liquidations?self=self'
data = {
  "exchange_name": "string",
  "instrument_name": "string",
  "label_name": "string"
}
header = {'accept': 'application/json', 'Content-Type': 'application/json', 'authorization': access_token}

response = r.post(url=url, json=data, headers=header)
```

### d3/

- `/api/v1/d3/new_chain`
```python
import requests as r


access_token = ''
url = 'http://0.0.0.0:8000/api/v1/d3/new_chain?self=self'
data = {
  "network_name": "string",
  "native_chain_token": "string",
  "rpc_node": "string",
  "block_limit": 0,
  "network_uri": "string",
  "network_api_key": "string"
}
header = {'accept': 'application/json', 'Content-Type': 'application/json', 'authorization': access_token}

response = r.post(url=url, json=data, headers=header)
```

- `/api/v1/d3/new_hedge_to_borrows`
```python
import requests as r


access_token = ''
url = 'http://0.0.0.0:8000/api/v1/d3/new_hedge_to_borrows?self=self'
data = {
  "wallet_address": "string",
  "token_address": "string",
  "network_name": "string",
  "label_name": "string",
  "protocol_name": "string",
  "specification_name": "string"
}
header = {'accept': 'application/json', 'Content-Type': 'application/json', 'authorization': access_token}

response = r.post(url=url, json=data, headers=header)
```

- `/api/v1/d3/new_hedge_to_supplies`
```python
import requests as r


access_token = ''
url = 'http://0.0.0.0:8000/api/v1/d3/new_hedge_to_supplies?self=self'
data = {
  "wallet_address": "string",
  "token_address": "string",
  "network_name": "string",
  "label_name": "string",
  "protocol_name": "string",
  "specification_name": "string"
}
header = {'accept': 'application/json', 'Content-Type': 'application/json', 'authorization': access_token}

response = r.post(url=url, json=data, headers=header)
```

- `/api/v1/d3/new_wallet_balances`
```python
import requests as r


access_token = ''
url = 'http://0.0.0.0:8000/api/v1/d3/new_wallet_balances?self=self'
data = {
  "wallet_address": "string",
  "token_address": "string",
  "network_name": "string",
  "label_name": "string"
}
header = {'accept': 'application/json', 'Content-Type': 'application/json', 'authorization': access_token}

response = r.post(url=url, json=data, headers=header)
```
