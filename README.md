# Dompet

This is a API project for personal expenditure tracking, built with [django](https://www.djangoproject.com/) and [django-rest-framework](https://www.django-rest-framework.org/)  

## Requisites  

1. Python 3.10  
2. Django 4.2.4  
3. Django-Rest-Framework 3.14  
4. PostgreSQL 14.10  

## Setup  

Clone the git project into your local project directory  
Use `.env.sample` to generate in the project root directory:  
- `.env` for testing environment  
- `.env.prod` for production environment  

Use `.env.db.sample` to generate in the project root directory:  
- `.env.db` in any environment  

### Using Docker  
Docker approach is geared for production environment, uses `.env.prod`  
1. Have [Docker](https://docs.docker.com/engine/install/) installed in your environment  
2. In the local directory, build the image and container  
```  
docker-compose build  
```  

### Using Local Environment  
1. Create a virtualenv using the virtualenv tool of your choice  
2. Install the required packages in the environment, using `requirements.txt` or `pipenv`  
3. Run the necessary migrations  
```  
python3 manage.py makemigrations  
python3 manage.py migrate  
```  

## Usage  
### Using Docker  
Run the container  
```  
docker-compose up  
```  
Access the application on your local browser  
```  
http://[host]:[port]
```  

### Using Local Environment  
Run the local django server  
```  
python3 manage.py runserver
```  

Access the application on your local browser  
```  
http://127.0.0.1:8000
```  