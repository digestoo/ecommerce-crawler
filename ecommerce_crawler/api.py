# #!/usr/bin/python3

from klein import run, route, Klein
app = Klein()


import json
from scrapy import signals
from scrapy.crawler import CrawlerRunner
from spiders.ecommerce_crawler import EcommerceCrawler


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
        return self.items


def return_spider_output(output):
    wynik = {}

    for x in ['phones','emails','couriers','psp_providers','langs']:
        lista = []
        for item in [dict(p) for p in output]:
            if len(item[x])>0:
                lista.extend(item[x])
        wynik[x]=list(set(lista))
    return json.dumps(wynik)


@app.route("/ecommerce/<domain>")
def getdata(request,domain):
    runner = MyCrawlerRunner()
    spider = EcommerceCrawler()
    deferred = runner.crawl(spider,start_urls=['http://%s'%domain])
    deferred.addCallback(return_spider_output)
    
    return deferred


resource = app.resource

app.run("0.0.0.0", 5005)
