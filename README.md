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
- `ATTACHMENTS_S3_BUCKET` — S3 bucket for attachment file storage (bucket + AWS credentials must be provisioned separately; the app only reads the bucket name)  

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
| POST | `/attachments` | Create a new attachment. `name` is an optional display label, separate from `filename` (the stored file name) -- defaults to `filename` if omitted |
| GET | `/attachments/{id}` | Get a specific attachment by ID |
| PUT | `/attachments/{id}` | Update a attachment |
| DELETE | `/attachments/{id}` | Delete a attachment |
| GET | `/locations` | List all locations |
| POST | `/locations` | Create a new location. Physical locations require `country` (ISO 3166-1 alpha-2, e.g. `MY`); online locations require `url` |
| GET | `/locations/{id}` | Get a specific location by ID |
| PUT | `/locations/{id}` | Update a location |
| DELETE | `/locations/{id}` | Delete a location |
| POST | `/users` | Create your user profile (username, display_name, configuration) |
| GET | `/users/me` | Get your own user profile |
| PUT | `/users/me` | Edit your own user profile |
| GET | `/transactions/suggestions` | Your recurring transaction patterns, ranked by recency-weighted frequency, for one-click creation. Each carries `origin_transaction_id` (its most recent use) to open the add page prefilled with `?from=<id>`. Filters: `q`, `type`, `min_uses` (default 2); pass `tz_offset` (minutes east of UTC, e.g. `480`) to boost patterns you usually record around this time of day |
| GET | `/transactions/summary` | Aggregate totals and breakdowns for transactions (by category, source account, budget) |
| GET | `/transactions/trend` | Bucketed income/expense time series for transactions |
| GET | `/budgets/search` | Search budgets by name (`q`, substring match) or exactly by `budget_id` |
| GET | `/budgets/summary` | Aggregate totals and breakdown by budget. `q` is a substring match on name; `budget_id` selects exactly one budget |
| GET | `/budgets/trend` | Bucketed income/expense time series for budget activity. `q` is a substring match on name; `budget_id` selects exactly one budget |
| POST | `/assistant/query` | Ask a natural-language question about your own transactions, budgets, and bills. Rate-limited per user |
| GET | `/bills` | List bill occurrences (recurring and one-off) |
| POST | `/bills` | Create a one-off bill. Requires `bill_date` (when it was issued); `due_date` defaults to `bill_date` if omitted |
| GET | `/bills/search` | Search bills by name/category/account/status, with computed paid status, linked transactions (for navigating to the transaction page), and attachments merged from the bill itself and any linked transaction (tagged with `linked_via` so the frontend knows which unlink endpoint applies) |
| GET | `/bills/groups` | The bills landing list: one row per recurring series and per one-off bill, each tagged `kind` (`series` or `one_off`) with `next_due_date`, `unpaid_count`, `overdue_count` and the latest occurrence's amount/status. Filters: `q`, `kind`, `category`, `account`, `is_overdue`; fully paid one-offs are hidden unless `include_paid=true`. Open a series with `GET /bills/search?series_id=<id>`, a one-off with `GET /bills/{id}` |
| GET | `/bills/{id}` | Get a specific bill occurrence |
| PUT | `/bills/{id}` | Update a bill occurrence |
| DELETE | `/bills/{id}` | Deactivate a bill occurrence |
| GET | `/bills/series` | List recurring bill definitions |
| POST | `/bills/series` | Create a recurring bill definition. `anchor_date` is the first occurrence's `bill_date` (issue date); each occurrence's `due_date` defaults to the day before the next occurrence's `bill_date` |
| GET | `/bills/series/{id}` | Get a specific recurring bill definition |
| PUT | `/bills/series/{id}` | Update a recurring bill definition |
| DELETE | `/bills/series/{id}` | Deactivate a recurring bill definition |
| GET | `/bills/{id}/payments` | List payments recorded against a bill |
| POST | `/bills/{id}/payments` | Record a payment toward a bill, optionally linked to a transaction |
| PUT | `/bills/{id}/payments/{payment_id}` | Edit a recorded payment, e.g. unlink its transaction by setting `transaction_id` to null while keeping the amount/date |
| DELETE | `/bills/{id}/payments/{payment_id}` | Remove a recorded payment |
| GET | `/bills/{id}/attachments` | List attachments linked to a bill |
| POST | `/bills/{id}/attachments` | Link an attachment to a bill |
| DELETE | `/bills/{id}/attachments/{attachment_id}` | Unlink an attachment from a bill |
| GET | `/bills/{id}/budgets` | List budgets a bill is tied to |
| POST | `/bills/{id}/budgets` | Tie a bill to a shared budget (other members can then see it); for a recurring bill, ties every occurrence in the series, including ones generated later |
| DELETE | `/bills/{id}/budgets/{budget_id}` | Untie a bill from a budget; for a recurring bill, unties every occurrence in the series |
| GET | `/budgets/{id}/bills` | List every bill tied to a budget, across all its members |
| GET | `/statements` | List statement occurrences (expected and received), newest first |
| POST | `/statements` | Record a standalone statement. Requires `account_id`, `statement_date`, `period_start`, `period_end`; `currency_code` is required if a balance is given |
| GET | `/statements/search` | Search statements by account/status (`pending`, `received`, `overdue`)/date range, with attachments. `status` is derived: `received` once `received_date` is set, `overdue` once `statement_date` has passed without one |
| GET | `/statements/{id}` | Get a specific statement |
| PUT | `/statements/{id}` | Update a statement, e.g. set `received_date` and balances when it arrives |
| DELETE | `/statements/{id}` | Deactivate a statement |
| GET | `/statements/series` | List recurring statement schedules |
| POST | `/statements/series` | Create a recurring statement schedule for an account (one active schedule per account). `anchor_date` is the first occurrence's `statement_date`; each occurrence's period ends on its `statement_date` and starts the day after the previous one |
| GET | `/statements/series/{id}` | Get a specific statement schedule |
| PUT | `/statements/series/{id}` | Update a schedule's recurrence or currency (affects only occurrences generated afterwards) |
| DELETE | `/statements/series/{id}` | Deactivate a schedule, freeing the account for a new one |
| GET | `/statements/{id}/attachments` | List attachments linked to a statement |
| POST | `/statements/{id}/attachments` | Link an attachment to a statement |
| DELETE | `/statements/{id}/attachments/{attachment_id}` | Unlink an attachment from a statement |
| GET | `/staged-transactions` | List draft transactions awaiting approval (`status` = `draft` by default, `approved`, `discarded` or `all`) |
| POST | `/staged-transactions` | Stage a draft. Every field is optional; `tag_ids`, `budget_ids` and `attachment_ids` may be sent as lists. Set `origin_transaction_id` to record the transaction it was copied from (marks the origin as `suggestion`) |
| GET | `/staged-transactions/search` | Search drafts by name/notes, status, type, origin, account, and `is_complete`; each result lists the `missing_fields` still blocking approval |
| GET | `/staged-transactions/{id}` | Get a draft, including its tag, budget and attachment ids |
| PUT | `/staged-transactions/{id}` | Edit a draft. A tag/budget/attachment list that is sent replaces that set; one left out is untouched |
| DELETE | `/staged-transactions/{id}` | Discard a draft (kept as `discarded`, not erased) |
| POST | `/staged-transactions/{id}/approve` | Turn a draft into a real transaction through the same validation as `POST /transactions`, copying its tags, budgets and attachments, and return the new transaction. Send `datetime` (or `date`) to override or supply the draft's own |

## Roadmap  

- Scripts for AWS Lambda and API Gateway setup  

## Contact  

cchernn@gmail.com  