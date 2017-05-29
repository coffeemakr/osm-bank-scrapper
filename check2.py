import overpass
import osmapi
import json
import os.path
import getpass
from changer import Changer
from helper import *

NAME = 'osm-bank-scraper'
VERSION = '0.1.0'


def load_banks(overpass_api):
    name = "query.txt"
    cache_file = name + ".cache"
    if os.path.isfile(cache_file):
        with open(cache_file) as fp:
            data = json.load(fp)
    else:
        with open(name, 'r') as fp:
            query = fp.read()
        data = overpass_api.Get(query, build=False, responseformat="json")
        with open(cache_file, 'w') as fp:
            json.dump(data, fp)
    return data


def main():
    overpass_api = overpass.API()
    overpass_api.Debug = True

    username = input("Username: ")
    password = getpass.getpass("Password: ")
    osm_api = osmapi.OsmApi(username=username, password=password, appid=NAME + " " + VERSION, debug=True)

    with open('locs.json', 'r') as fp:
        scraped = json.load(fp)

    checker = Checker(overpass_api, osm_api, load_banks(overpass_api), scraped)
    checker.run()


class Checker(object):
    def __init__(self, overpass_api, osm_api, existing, wanted):
        self.overpass_api = overpass_api
        self.changer = Changer(osm_api, source="https://www.akb.ch/die-akb/kontakt/geschaeftsstellen.aspx")
        self.existing_points = existing
        self.wanted_points = wanted

    def run(self):
        self.changer.begin("Import AKB information.")
        for point in self.wanted_points:
            distances_and_element = self.get_nearest_elements(point)
            self.pick_element(distances_and_element, point)
        self.changer.commit()

    def pick_element(self, distances_and_element, wanted):
        accepted = False
        existing = None
        distance = -1.0
        print("Choosing an element for %s" % wanted)
        while not accepted and distances_and_element:
            if existing is None:
                distance, existing = distances_and_element.pop(0)
            if distance > 0.5:
                break
            print("=" * 80)
            print("Distance: %.3f km" % distance)
            print_different_tags(existing['tags'], wanted['tags'])

            try:
                value = input("Is this your element? (n/y)").lower()
            except KeyboardInterrupt:
                value = "abort!"
            if value == 'n':
                existing = None
            elif value == 'y':
                accepted = True
            elif value == 's':
                open_browser(*wanted['coordinates'])
            elif value == 'abort!':
                break

        if not accepted:
            print("Create object?")
        else:
            command = ''
            while not command == 'q':
                print("How should we change the fields?")
                print("a: add new fields")
                print("w: write different fields")
                print("q: cancel")
                command = input("command: ").lower()
                if command == 'a':
                    print("Adding tags")
                    self.changer.add_tags(existing, wanted['tags'])
                    command = 'q'
                elif command == 'w':
                    print("Writing different tags")
                    self.changer.set_tags(existing, wanted['tags'])
                    command = 'q'
                elif command == 'q':
                    print("Aborting!")

    def get_elements(self):
        return self.existing_points['elements']

    def get_nearest_elements(self, point):
        element_distances = []
        for existing_point in self.get_elements():
            dist = distance(point['coordinates'], self.get_coordinates(existing_point))
            element_distances.append((dist, existing_point))
        element_distances = sorted(element_distances, key=lambda tpl: tpl[0])
        return list(element_distances)

    def get_coordinates(self, point):
        if point['type'] == 'node':
            return point['lat'], point['lon']
        elif 'center' in point:
            return point['center']['lat'], point['center']['lon']
        elif point['type'] == 'relation':
            for member in point['members']:
                if member['type'] == 'way' and member['role'] == 'outer':
                    way = self.get_element_by_id(member['ref'])
                    return self.get_coordinates(way)
        else:
            raise Exception()

    def get_element_by_id(self, identifier):
        for element in self.get_elements():
            if element["id"] == identifier:
                return element

    def load_element_by_address(self, tags, lat, lon, radius):
        location = '(around:{radius},{lat},{lon})'.format(lat=lat, lon=lon, radius=radius)

        selector = ''
        for name, value in tags.items():
            selector += '["{name}"="{value}"]'.format(name=name, value=value)
        query = '''
        [out:json][timeout:25];
        (
          node{selector}({location});
          way{selector}({location});
          relation{selector}({location});
        );
        out body;
        >;
        out skel qt;
        '''.format(selector=selector, location=location)
        return self.overpass_api.Get(query, responseformat='json', build=False)


if __name__ == '__main__':
    main()
