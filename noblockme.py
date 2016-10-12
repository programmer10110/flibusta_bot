import requests


def noblock(url):
    try_n = 0
    while try_n < 3:
        try:
            request = requests.get('http://noblockme.ru/api/anonymize?url='+url)
        except requests.exceptions.ConnectionError as exp:
            print(exp)
            try_n += 1
        except requests.exceptions.ConnectTimeout as exp:
            print(exp)
            try_n += 1
        except requests.exceptions.ReadTimeout as exp:
            print(exp)
            try_n += 1
        else:
            result = request.json()
            if result['status'] == 0:
                return result['result']
            else:
                return None
