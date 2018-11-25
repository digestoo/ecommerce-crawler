# #!/usr/bin/python3

from klein import run, route, Klein
app = Klein()

import uuid
import langid
# import objgraph
import json
from scrapy import signals
from scrapy.crawler import CrawlerRunner
from spiders.ecommerce_crawler import EcommerceCrawler

from scrapy.utils.log import configure_logging

# from pympler.tracker import SummaryTracker
# tracker = SummaryTracker()


class MyCrawlerRunner(CrawlerRunner):
    """
    Crawler object that collects items and returns output after finishing crawl.
    """
    def crawl(self, crawler_or_spidercls, *args, **kwargs):
        self.items = []
        crawler = self.create_crawler(crawler_or_spidercls)

        crawler.signals.connect(self.item_scraped, signals.item_scraped)

        dfd = self._crawl(crawler, *args, **kwargs)

        dfd.addCallback(self.return_items)
        
        return dfd

    def item_scraped(self, item, response, spider):
        self.items.append(item)

    def return_items(self, result):
        p = list(self.items)
        self.items.clear()
        del self.items
        return p

class EmptyOutput(Exception):
    pass

def return_spider_output(output):
    if len(output) == 0:
        raise EmptyOutput()
    print('output',output)
    wynik = {}
    from collections import Counter
    for x in ['phones','emails','couriers','psp_providers','langs','company_number','used_lang']:
        lista = []
        for item in [dict(p) for p in output]:
            if len(item[x])>0:
                lista.extend(item[x])
        if x in ['phones','emails']:
            wynik[x] = [p[0] for p in Counter(lista).most_common(3)]
        else:
            wynik[x]=list(set(lista))
        lista.clear()
            
    return json.dumps(wynik)



@app.route("/ecommerce/<domain>")
def getdata(request,domain):
    all_phones = request.args.get(b'phones',[b'all'])[0].decode('utf-8')
    runner = MyCrawlerRunner( )#{'JOBDIR':'/tmp/alask_%s'%uuid.uuid4().hex})
    spider = EcommerceCrawler()
    spider.all_phones = all_phones
    deferred = runner.crawl(spider,all_phones=all_phones,start_urls=['http://%s'%domain], main_page=True)
    deferred.addCallback(return_spider_output)
    return deferred

@app.handle_errors(EmptyOutput)
def badresponse(request, failure):
    request.setResponseCode(500)
    return 'Domain is not responding.'


resource = app.resource
configure_logging()
app.run("0.0.0.0", 5005)
    