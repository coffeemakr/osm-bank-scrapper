import scrapy


class NabSpider(scrapy.Spider):

    name = 'Neue Aargauer Bank Spider'

    start_urls = ['https://www.nab.ch/kontakt-services/kontakt-standorte.html']

    def parse(self, response):
        locationArray = response.xpath('//script[contains(text(),"locationArray")]/text()').extract_first()