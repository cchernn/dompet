# dompet  

A serverless transaction tracking API built with Python and designed for deployment on AWS Lambda. This API powers a web dashboard, [dompet-web](https://github.com/cchernn/dompet-web) that tracks personal transactions, allowing users to attach files, tag locations and organize transactions into groups.  

## Features  

- add and manage transactions via REST API  
- link attachments  
- tag locations  
- organize transactions into groups  
- serverless architecture using AWS Lambda + AWS API Gateway  

## Installation  

#### 1. Clone the repository  

``` bash
git clone https://github.com/cchernn/dompet.git  
cd dompet  
```

#### 2. Create a virtual environment (Optional, but Recommended)  

Basic `venv` method
``` bash
python -m venv venv  
source  venv/bin/activate  
```

or use [pipenv](https://pypi.org/project/pipenv/). There is Pipfile and Pipfile.lock files for easier pipenv setups.  
```
pipenv shell
```

#### 3. Install dependencies  

``` bash
pip install -r requirements.txt  
```

``` bash  
pipenv install  
```

#### 4. Install AWS CLI and setup AWS Credentials  

Follow the steps in [here](https://docs.aws.amazon.com/braket/latest/developerguide/braket-using-boto3-profiles.html)  

### *** [WIP] To be Added ***  
#### 5. Setup AWS Lambda, API Gateway and IAM  

### ******

## Setup  

#### 1. Environment Configuration  

Create a `.env` with the following variables  

- `DB_POSTGRESQL_HOST`  
- `DB_POSTGRESQL_NAME`  
- `DB_POSTGRESQL_PASSWORD`  
- `DB_POSTGRESQL_PORT`  
- `DB_POSTGRESQL_USER`  
- `GIT_REPO_URL`  
- `GIT_REPO_BRANCH`  

#### 2. Run migration to set up databases  

Recommeded PostgreSQL database is [Supabase](https://supabase.com/)
``` python
python Setup.py migrate
```

#### 3. Push code to AWS Lambda  

``` python
python Setup.py upload  
```

## Usage  

Access the following endpoints by the following endpoints  

| Method | Endpoint | Description |
|--------|-------------------------|----------------------------------------|
| GET | `/transactions` | List all transactions for the user |
| POST | `/transactions` | Create a new transaction |
| GET | `/transactions/{id}` | Get a specific transaction by ID |
| PUT | `/transactions/{id}` | Update a transaction |
| DELETE | `/transactions/{id}` | Delete a transaction |
| GET | `/transactions/groups` | List groups the user has access to |
| POST | `/transactions/groups` | Create a new transaction group |
| GET | `/transactions/groups/{id}` | Get a specific transaction group by ID |
| PUT | `/transactions/groups/{id}` | Update a transaction group |
| DELETE | `/transactions/groups/{id}` | Delete a transaction group |
| GET | `/attachments` | List all attachments for the user |
| POST | `/attachments` | Create a new attachment |
| GET | `/attachments/{id}` | Get a specific attachment by ID |
| PUT | `/attachments/{id}` | Update a attachment |
| DELETE | `/attachments/{id}` | Delete a attachment |
| GET | `/locations` | List all locations |
| POST | `/locations` | Create a new location |
| GET | `/locations/{id}` | Get a specific location by ID |
| PUT | `/locations/{id}` | Update a location |
| DELETE | `/locations/{id}` | Delete a location |

## Roadmap  

- Pagination for `list` methods  
- Module/Row level Authorization methods and tables  
- Scripts for AWS Lambda and API Gateway setup  

## Contact  

cchernn@gmail.com  