import requests
import conf.config

REQUEST_URL = 'http://localhost:8080/retrieve_premises'

def get_param():
    params = {
        'query': conf.config.TEST_QUERY,
        'num': 20
    }
    return params

def get_from_http():
    data = get_param()
    response = requests.post(REQUEST_URL, json=data)
    if response.status_code == 200:
        print('Response JSON:', response.json())
        result = response.json()['data']
        print(f"size = {len(result[0])}")
    else:
        print('Error:', response.json())


if __name__ == '__main__':
    get_from_http()







