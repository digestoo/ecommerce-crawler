import requests
import json
from ecommerce_crawler.spiders.ecommerce_crawler import read_json_file


def get_company_num(domain):
    v = requests.get('http://localhost:5005/ecommerce/%s'%domain)
    vjson = v.json()
    if 'company_number' in vjson:
        return vjson['company_number']
    else:
        return []

def test_companies_numbers():
    domains = read_json_file('../resources/tests.json')
    for domain,correct_number in domains:
        assert correct_number in get_company_num(domain)
        print(domain,'OK')