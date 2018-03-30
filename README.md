# EcommerceCrawler

Simple scraper to get ecommerce information from eshop site.

Currently supported:
* PSP providers detection
* Couriers detection
* Phone, Emails 
* Languages (as a list of domains)

Currently supported markets:
- UK, PL, DE, NL, ES, IT, FR

## Requirement

Python3 or docker machine

## Run API
You need to provide 3 files 
* psp_providers.json
* couriers.json
* keywords.json

to resources folder.

### Manual 

```bash
git clone git@github.com:digestoo/ecommerce-crawler.git
cd ecommerce-crawler
pip install -r requirements.txt
cd ecommerce_crawler
python api.py
```

### Docker

```bash
docker pull mdruzkowski/ecommerce-crawler
docker run -it -v $PWD:/usr/src/app/resources -p 5005:5005 mdruzkowski/ecommerce-crawler
```

## Making requests

```bash
curl -XGET -H "Content-Type: application/json" http://localhost:5005/ecommerce/<domain>
```

GET params:

- `domain`
