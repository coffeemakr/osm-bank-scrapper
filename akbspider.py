
import scrapy
import fields


class AKBSpider(scrapy.Spider):

    name = 'AKB Spider'
    start_urls = ['https://www.akb.ch/die-akb/kontakt/geschaeftsstellen.aspx']

    @staticmethod
    def get_osm_address(address):
        tags = {}
        street, number = address.pop(0).rsplit(' ', 1)
        postcode, city = address.pop(0).split(' ', 1)
        tags[fields.ADDR_STREET] = street.strip()
        tags[fields.ADDR_HOUSENUMBER] = number.strip()
        tags[fields.ADDR_POSTCODE] = postcode.strip()
        tags[fields.ADDR_CITY] = city.strip()
        return tags

    def parse(self, response):
        links = response.css('.countrymap')[0].css('a.poi')
        finance_infos = response\
            .css('.modFooter .info p:first-child')\
            .xpath('//text()[preceding-sibling::br][contains(., "BIC")]').extract_first()
        finance_tags = {}
        for finance_info in finance_infos.split(','):
            name, value = map(str.strip, finance_info.split(':'))
            if "BIC" in name:
                finance_tags['bic'] = value

        for link in links:
            rel = link.xpath('@rel').extract_first()
            rel = list(map(str.strip, rel.split('|')))
            next_page = link.xpath('@href').extract_first()
            request = scrapy.Request(response.urljoin(next_page), callback=self.parse_filiale)
            rel.pop()  # pop the link
            filiale_type = rel.pop(0)
            tags = self.get_osm_address(rel)
            tags.update(finance_tags)
            request.meta['item'] = {'type': filiale_type, 'tags': tags}
            yield request

    def parse_filiale(self, response):
        fixed_selector = scrapy.Selector(text=response.body.replace(b'</br>', b'<br/>'))
        item = response.meta['item']
        address = fixed_selector.css('.table-contact p').xpath('text()[preceding-sibling::br]').extract()
        tel = None
        if address:
            tel = address.pop().lstrip('Tel. ')

        coordinates = response.selector.re(r'GLatLng[(]([^,]*,[^\)]*)[)]')[0].split(',')
        item['coordinates'] = list(map(float, map(str.strip, coordinates)))
        item['tags']['name'] = "Aargauische Kantonalbank " + response.css('h1 ::text').extract_first()
        item['tags']['operator'] = "Aargauische Kantonalbank"
        item['tags']['phone'] = tel
        item['tags'][fields.OPENING_HOURS_URL] = response.url
        item['tags']['amenity'] = 'bank'

        yield item
