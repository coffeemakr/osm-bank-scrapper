import phonenumbers
import scrapy
import json
import fields
import re

NEUE_AARGAUER_BANK = 'Neue Aargauer Bank'
NEUE_AARGAUER_BANK_AG = NEUE_AARGAUER_BANK + " AG"
HOUSE_NUMBER_REGEX = re.compile(r'\s+(\d+)$')


def yes_or_no(value):
    if value:
        return 'yes'
    else:
        return 'no'


def get_coordinates_from_location(location):
    return {'lat': location['latitude'], 'lon': location['longitude']}


def parse_location(response, location):
    tags = {
        'amenity': 'bank',
        'operator': NEUE_AARGAUER_BANK_AG,
        'name': NEUE_AARGAUER_BANK,
    }
    city = location['city']
    if ',' in city:
        city = city.split(',')[0].strip()
    tags[fields.ADDR_POSTCODE] = location['zipcode']
    tags[fields.OPENING_HOURS_URL] = response.urljoin(location['link'])

    street = location['address']
    housenumber_match = HOUSE_NUMBER_REGEX.search(street)
    if housenumber_match:
        tags[fields.ADDR_HOUSENUMBER] = housenumber_match.group(1)
        street = HOUSE_NUMBER_REGEX.sub('', street)

    # expand street abbreviation
    street = re.sub('([Ss])tr\.$', r'\1trasse', street)

    phone_selector = scrapy.Selector(text=location['phone'])
    phone_number = phone_selector.xpath('//a/@href').extract_first().split(':')[1]
    phone_number = phonenumbers.parse(phone_number, None)
    phone_number = phonenumbers.format_number(phone_number, phonenumbers.PhoneNumberFormat.INTERNATIONAL)
    tags['phone'] = phone_number

    fax = phonenumbers.parse(location['fax'], "CH")
    tags['fax'] = phonenumbers.format_number(fax, phonenumbers.PhoneNumberFormat.INTERNATIONAL)
    tags[fields.ADDR_STREET] = street
    tags['bic'] = location['swift_bic']
    return {'tags': tags, 'coordinates': get_coordinates_from_location(location)}


def parse_atm(response, location):
    print("ATM")
    tags = {'amenity': 'atm',
            'operator': NEUE_AARGAUER_BANK_AG}
    request = scrapy.Request(response.urljoin(location['link']), callback=parse_atm_page)
    request.meta['tags'] = tags
    request.meta['coordinates'] = get_coordinates_from_location(location)

    return request


def parse_atm_page(response):
    tags = response.meta['tags']

    tags['wheelchair'] = yes_or_no(response.xpath('//*[contains(text(), "Rollstuhlgängig")]').extract())
    tags['cash_in'] = yes_or_no(response.xpath('//*[contains(text(), "einzahlungen")]').extract())

    currencies = response.css('.bodytext').re_first(r'[(]CHF(?:/EUR)?[)]')
    if not currencies:
        raise ValueError("currencies not found")
    tags["currency:EUR"] = yes_or_no("EUR" in currencies)
    tags["currency:CHF"] = yes_or_no("CHF" in currencies)

    yield {'tags': tags, 'coordinates': response.meta['coordinates'],
           'title': response.css('h1.csc-firstHeader::text').extract_first()}


class NabSpider(scrapy.Spider):
    name = NEUE_AARGAUER_BANK + ' Spider'

    start_urls = ['https://www.nab.ch/kontakt-services/kontakt-standorte.html']

    def parse(self, response):
        locationArray = response \
            .xpath('//script[contains(text(),"locationArray")]/text()') \
            .re(r'locationArray\s*=\s*(.+);\s*$')[0]
        locations = json.loads(locationArray)
        for location in locations:
            if location['is_bankomat'] == '0':
                result = parse_location(response, location)
            else:
                result = parse_atm(response, location)
            yield result
