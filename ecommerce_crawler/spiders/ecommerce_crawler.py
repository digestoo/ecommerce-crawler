#!/usr/bin/python3
# -*- coding: utf-8 -*-
import scrapy

# -*- coding: utf-8 -*-
import scrapy
import os
from scrapy.spiders import CrawlSpider, Rule, SitemapSpider
from scrapy.linkextractors import LinkExtractor
from scrapy.http import Request, XmlResponse
from scrapy.selector import Selector

import phonenumbers

import re
import sys, traceback
import slugify
from bs4 import BeautifulSoup

def get_phones(text,country):
    list_of_phones = list(phonenumbers.PhoneNumberMatcher(text,country))
    return list(set([phonenumbers.format_number(x.number, phonenumbers.PhoneNumberFormat.E164) for x in list_of_phones]))
    
def get_emails(body):
    lista = [x.strip().lower() for x in re.findall(r"[a-z0-9\.\-+_]+@[a-z0-9\.\-+_]+\.[a-z]+", body, re.I)] 
    return list(set([x for x in lista if not x.endswith('png') and not x.endswith('gif') \
        and x not in ['jankowalski@domena.pl','johndoe@domain.com'] ]))


def clean_all_numbers(text):
    if len(text) == 0:
        return text
    new_text = text[0]
    for x in range(1,len(text)-1):
        if text[x-1].isdigit() and text[x+1].isdigit()  and text[x] in (',',' ','.','-'):
            pass
        else:
            new_text+=text[x]
    return new_text


def clean_html(html):
    soup = BeautifulSoup(html)
    for s in soup(['script', 'style']):
        s.decompose()
    return (' '.join(soup.stripped_strings)).lower()


import tldextract
import lxml.html

def url_to_domain(url):
    p = tldextract.extract(url)
    if p.subdomain:
        return '.'.join(p)
    else:
        return '%s.%s'%(p.domain,p.suffix)


def get_rid_off_www(url):
    if url.startswith('http://'):
        return get_rid_off_www(url[7:])
    if url.startswith('https://'):
        return get_rid_off_www(url[8:])
    
    if url.startswith('www.'):
        return url[4:]
    else:
        return url


langs_supported = ['fr','en','pl','de','es','it','nl','ua','se','no','fi','sk','cz','ro','hu']


def subdomain_lang(x,main):
    if (x.domain == main.domain and x.suffix != main.suffix):
        return x.domain + '.' + x.suffix
    if (x.domain==main.domain and x.suffix==main.suffix) and \
    x.subdomain in langs_supported:
        return '.'.join(x)
    return None


tld = tldextract.TLDExtract(extra_suffixes=['com.ru'])

def get_languages_from_links(response, main_domain):
    all_links = Selector(response=response).xpath('//@href').extract()

    main = tld(main_domain)   
    potential_domains = [ tld(x) for x in all_links if x.startswith('http')]
    langs = [subdomain_lang(x,main) for x in potential_domains  ] 

    return [url_to_domain(get_rid_off_www(x)) for x in langs if x]   


def get_languages_from_hreflang(response):
    return [ url_to_domain(get_rid_off_www(x)) for x in  \
                Selector(response=response).xpath('//link[@hreflang]//@href').extract()]


from scrapy.linkextractors import LinkExtractor


# rexy = {}

# def prepare_rexes(service_list):
#     result = {}
#     for k in service_list:
#         rex = re.compile(r'\b%s\b'%k['name'].lower(),re.I)
#         result[k['name']] = [rex]
#         if (k['other'] is not None) and (len(k['other'])>0):
#             bex = re.compile(r'\b(%s)\b'%k['other'].lower(),re.I)
#             result[k['name']].append(bex)
#     return result



# def service_checker_rex(text,service_list,rexy):
#     result = []
#     for k in service_list:
#         for p in rexy[k['name']]:
#             if p.search(text):
#                 result.append(k['name'])
#                 break
#     return result


def service_checker(text,service_list):
    result = []
    for k in service_list:
        ok = 0
        if k['name'].lower() in text:
            ok = 1
        if (k['other'] is not None) and (len(k['other'])>0):
            for other in k['other'].split('|'):
               if other.lower() in text:
                   ok=1
        if ok>0:
            result.append(k['name'].strip())
    return result


def read_json_file(name):
    import json
    f = open(name,'r')
    return json.load(f)


def email_at_domain(email,domain):
    return email.endswith(domain)


keywords_dict = read_json_file('../resources/keywords.json')
couriers_list = read_json_file('../resources/couriers.json')
psp_list = read_json_file('../resources/psp_providers.json')

#psp_rex = prepare_rexes(psp_list)
#couriers_rex = prepare_rexes(couriers_list)

def get_phone_country(lang):
    if lang == 'en':
        return None
    if lang in langs_supported:
        return lang.upper()
    return None

def detect_lang(url):
    suffix_full = tld(url).suffix
    suffix = suffix_full.split('.')[-1]
    if suffix in langs_supported:
        return suffix
    else:
        return 'en'


class EcommerceCrawler(scrapy.Spider):
    name = "ecommerce_crawler"
    custom_settings = {
        'DEPTH_LIMIT':os.getenv('DEPTH',2),
        'DNS_TIMEOUT':5,
        'CLOSESPIDER_TIMEOUT':os.getenv('TIMEOUT', 7),
        'LOG_ENABLED':True,
        'DOWNLOAD_TIMEOUT':5,
        'RETRY_TIMES':1,
        'USER_AGENT':"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_6_8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/32.0.1700.102 Safari/537.36",
        
        'DEFAULT_REQUEST_HEADERS': {
           'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        },

        'LOG_LEVEL':'DEBUG'
    }
    start_urls = ['https://adamot.pl']
    #allowed_domains = ['http://happysocks.com']

    def parse(self, response):
            try:
                psp = []
                couriers = []
                other = []
                keywords = []
                phone_country = None
                main_domain = get_rid_off_www(url_to_domain(response.url))

                lang = detect_lang(response.url)

                if getattr(self,'all_phones','all') == 'all':    
                    phone_country = get_phone_country(lang)

                if lang in keywords_dict:
                    keywords = keywords_dict[lang]

                keywords.extend(keywords_dict['en'])
                keywords = list(set(keywords))
                
                if tldextract.extract(response.request.url)[1] == tldextract.extract(self.start_urls[0])[1]:
                    links = LinkExtractor().extract_links(response)
                    
                    for link in links:
                            link_slug = slugify.slugify(link.text)
                            if tldextract.extract(link.url)[1] == tldextract.extract(main_domain)[1]:
                                for keyword in keywords:  
                                    if keyword in link_slug or keyword in link.url:
                                        yield Request(url=link.url)
                

                body_no_html = clean_html(response.body)
                body_no_num = clean_all_numbers(body_no_html)
                text = body_no_num.replace('\n',' ')
#                text = text.replace('\t',' ')
#               text = ' %s '%text

                psp = service_checker(text,psp_list)
                couriers = service_checker(text,couriers_list)

                yield {
                    'domain': get_rid_off_www(url_to_domain(response.url)),
                    'phones': get_phones(body_no_html, phone_country),
                    'emails': [email for email in get_emails(text) if email_at_domain(email,main_domain)],
                    'couriers': list(set(couriers)),
                    'psp_providers': list(set(psp)),
                    'langs': list(set(get_languages_from_hreflang(response) 
                        + get_languages_from_links(response, main_domain))),
                }
            except Exception as e:
                print(e)
                exc_type, exc_value, exc_traceback = sys.exc_info()
                traceback.print_exception(exc_type, exc_value, exc_traceback, limit=10, file=sys.stdout)

