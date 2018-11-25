#!/usr/bin/python3
# -*- coding: utf-8 -*-
import scrapy

# -*- coding: utf-8 -*-
import scrapy
import os
from scrapy.spiders import CrawlSpider, Rule, SitemapSpider
from scrapy.linkextractors import FilteringLinkExtractor as LinkExtractor
from scrapy.http import Request, XmlResponse
from scrapy.selector import Selector
import logging
import phonenumbers
import langid
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

    return new_text.replace('.','').replace('-','')


def clean_html(html):
    soup = BeautifulSoup(html,'lxml')
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


def get_kvk_nl(text):
  p =  [x[1] for x in re.findall(r'(kvk)[^0-9]{0,10}(\d{8})[^0-9]', text)]
  return list(set(p))


def get_nip(text):
  p =  [x[1] for x in re.findall(r'(nip)[^0-9a-z]*(\d{10})[^0-9]', text)]
  return list([t for t in p if valid_nip(t)])[:1]

def get_rcs(text):
  p =  [x[1] for x in re.findall(r'(rcs|siret|siren|métropole|immatriculée)[^0-9]*(\d{9})[^0-9a-z]', text)]
  q = [x[0] for x in re.findall(r'[^0-9a-z](\d{9})[^0-9]{0,4}(rcs)', text)]
  notvalid = set(['546380197','542097902'])
  potentials = set( p + q) - notvalid
  return potentials

    
def valid_nip(x):
    y = x[:-1]
    control = [6,5,7,2,3,4,5,6,7]
    return (sum(list(map(lambda x: x[0]*x[1], (zip(map(int,y),control))))) % 11) == int(x[-1])
    
def get_uk_number(text):
  p =  [x[1].rjust(8,'0') for x in re.findall(r'(company|registration|companies house|registered)[^0-9]{1,20}((\d){6,8})[^0-9]', text)]
  return list(p)


def get_spain_nif_cif(text):
  p =  [x[1] for x in re.findall(r'(nif|cif)[^0-9]{1,10}((a|b)(\d){8})[^0-9]', text)]
  return list(p)



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
couriers_list = read_json_file('../resources/meta.json')
psp_list = read_json_file('../resources/psp_providers.json')


def get_phone_country(lang,url):
    suffix_full = tld(url).suffix
    if suffix_full == 'co.uk':
        return 'GB'

    if lang == 'en':
        return None
    if lang in langs_supported:
        return lang.upper()
    return None

def detect_lang(url, response):
    suffix_full = tld(url).suffix
    suffix = suffix_full.split('.')[-1]
    if suffix in langs_supported:
        return suffix
    else:
        title = Selector(response=response).xpath('//title').extract()
        description = Selector(response=response).xpath('//meta[@name="description"]//@content').extract()
        langi = langid.classify( ','.join(title+description) )
        if langi[0] not in langs_supported:
            return 'en'
        else:
            return langi[0]


def get_number_not_supported_lang(text):
    return []

def get_company_number_function(lang):
    if lang == 'fr':
        return get_rcs
    elif lang == 'nl':
        return get_kvk_nl
    elif lang == 'pl':
        return get_nip
    elif lang == 'en':
        return get_uk_number
    elif lang == 'es':
        return get_spain_nif_cif
    else:
        return get_number_not_supported_lang
 


class EcommerceCrawler(scrapy.Spider):
    name = "ecommerce_crawler"
    #handle_httpstatus_list = [404, 500, 503]

    custom_settings = {
        'DEPTH_LIMIT':os.getenv('DEPTH',2),
        # 'LOG_FILE': '/tmp/mdexample2.log',
        'DNS_TIMEOUT':10,
        'REACTOR_THREADPOOL_MAXSIZE': 20,
        'CONCURRENT_REQUESTS': 2,
        'CLOSESPIDER_TIMEOUT':os.getenv('TIMEOUT', 20),
        'LOG_ENABLED':False,
        'DOWNLOAD_TIMEOUT':10,
        'COOKIES_ENABLED': False,
        #'RETRY_ENABLED':False,
        'MEMUSAGE_ENABLE':True,
        # 'MEMUSAGE_ENABLED': 1,
        #'MEMUSAGE_LIMIT_MB': 256,
        #'LOG_STDOUT': True,
        'RETRY_TIMES':2,
        'USER_AGENT':"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_6_8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/32.0.1700.102 Safari/537.36",
        
        'DEFAULT_REQUEST_HEADERS': {
           'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        },

        'LOG_LEVEL':'INFO'
    }
    start_urls = ['http://centrobud.pl']
    #allowed_domains = ['http://happysocks.com']

    def parse(self,response):
        main_domain = url_to_domain(get_rid_off_www(response.url))
        self.lang = detect_lang(response.url,response)
        return self.parse_ecommerce(response)


    def parse_ecommerce(self,response):
#        print (self.response)
        main_domain = url_to_domain(get_rid_off_www(response.url))
        phone_country = None
        
        lang = self.lang

        if getattr(self,'phones','all') == 'all':    
            phone_country = get_phone_country(lang,response.url)

        keywords = []

        if lang in keywords_dict:
            keywords = keywords_dict[lang] + keywords_dict['en']
        else:
            keywords = keywords_dict['en']
        
        keywords = list(set(keywords))
        potential_urls = []

        if self.main_page:
            links = LinkExtractor().extract_links(response)
            self.main_page=False
            for link in links:
                link_text_slug = slugify.slugify(link.text)

                if tldextract.extract(url_to_domain(get_rid_off_www(link.url)))[1] == \
                    tldextract.extract(main_domain)[1]:
                    for keyword in keywords:
                        if keyword in link_text_slug or keyword in link.url:
                            if not link.url.endswith('pdf'):
                                potential_urls.append(link.url)

            for x in list(set(potential_urls)):
                yield Request(url=x, callback=self.parse_ecommerce)

            potential_urls.clear()
            del potential_urls

        body_no_html = clean_html(response.body)
        body_numbers = clean_all_numbers(body_no_html)
        body_no_html = body_no_html.replace('\n',' ')

        couriers = service_checker(body_no_html,couriers_list[lang]['couriers'])
        psp = service_checker(body_no_html,psp_list)

        yield {
                    'domain': get_rid_off_www(url_to_domain(response.url)),
                    'phones': get_phones(body_no_html, phone_country),
                    'emails': [email for email in get_emails(body_no_html) if email_at_domain(email,main_domain)],
                    'couriers': list(set(couriers)),
                    'psp_providers': list(set(psp)),
                    'langs': list(set(get_languages_from_hreflang(response) 
                        + get_languages_from_links(response, main_domain))),
                    'company_number': get_company_number_function(lang)(body_numbers),
                    'used_lang': [lang]
                }

