import json
from datetime import datetime
import requests

from config import ELASTICPATH_ID
from database import get_database_connection


def read_token_from_db(redis_db):
    data = {
        'client_id': ELASTICPATH_ID,
        'grant_type': 'implicit'
    }
    response = requests.post('https://api.moltin.com/oauth/access_token', data=data)
    response.raise_for_status()
    redis_db.set('auth_credentials', response.text)
    access_token = response.json()['access_token']
    return access_token


def get_access_token():
    redis_db = get_database_connection()
    try:
        auth_credentials = json.loads(redis_db.get('auth_credentials'))
        timestamp_now = datetime.now().timestamp()
        if auth_credentials:
            if auth_credentials['expires'] > timestamp_now + 100:
                return auth_credentials['access_token']
            return read_token_from_db(redis_db)
    except (ValueError, TypeError):
        return read_token_from_db(redis_db)
    return read_token_from_db(redis_db)


def get_products():
    access_token = get_access_token()
    headers = {
        'Authorization': f'Bearer {access_token}'
    }
    response = requests.get('https://api.moltin.com/v2/products', headers=headers)
    response.raise_for_status()
    return response.json()['data']


def get_product_by_id(product_id):
    access_token = get_access_token()
    headers = {
        'Authorization': f'Bearer {access_token}'
    }
    response = requests.get(f'https://api.moltin.com/v2/products/{product_id}', headers=headers)
    response.raise_for_status()
    return response.json()['data']


def get_photo_by_id(product_id):
    product = get_product_by_id(product_id)
    image_id = product['relationships']['main_image']['data']['id']
    access_token = get_access_token()
    headers = {
        'Authorization': f'Bearer {access_token}'
    }
    response = requests.get(f'https://api.moltin.com/v2/files/{image_id}', headers=headers)
    response.raise_for_status()
    image_url = response.json()['data']['link']['href']
    return image_url


def add_to_cart(product_id, amount, user_id):
    access_token = get_access_token()
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
    }
    data = {'data': {'id': product_id, 'type': 'cart_item', 'quantity': int(amount)}}
    response = requests.post(
        f'https://api.moltin.com/v2/carts/{user_id}/items',
        headers=headers,
        json=data
    )
    response.raise_for_status()


def get_cart_by_user_id(user_id):
    access_token = get_access_token()
    headers = {
        'Authorization': f'Bearer {access_token}'
    }
    response = requests.get(f'https://api.moltin.com/v2/carts/{user_id}/items', headers=headers)
    response.raise_for_status()
    return response.json()


def register_customer(name, email):
    access_token = get_access_token()
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
    }
    data = {'data': {'type': 'customer', 'name': name, 'email': email}}
    response = requests.post('https://api.moltin.com/v2/customers', headers=headers, json=data)
    response.raise_for_status()


def delete_item(user_id, item_id):
    access_token = get_access_token()
    headers = {
        'Authorization': f'Bearer {access_token}'
    }
    response = requests.delete(f'https://api.moltin.com/v2/carts/{user_id}/items/{item_id}', headers=headers)
    response.raise_for_status()
