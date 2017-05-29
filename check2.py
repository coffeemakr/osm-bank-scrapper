import overpass
import osmapi
import json
import math
import texttable as tt
import webbrowser
import os.path
import getpass

NAME = 'osm-bank-spider'
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

    for element in scraped:
        element['tags']['amenity'] = 'bank'
        element['tags']['atm'] = 'yes'

    checker = Checker(overpass_api, osm_api, load_banks(overpass_api), scraped)
    checker.run()


def add_fields_to_table(tab, keys, existing, new, name):
    for same_key in keys:
        existing_value = ""
        if same_key in existing:
            existing_value = existing[same_key]
        new_value = ""
        if same_key in new:
            new_value = new[same_key]
        tab.add_row([same_key, existing_value, new_value, name])


def print_different_tags(existing, new):
    existing_keys = set(existing.keys())
    new_keys = set(new.keys())
    intersect_keys = existing_keys.intersection(new_keys)
    removed = existing_keys - new_keys
    added = new_keys - existing_keys
    modified = {o: (existing[o], new[o]) for o in intersect_keys if existing[o] != new[o]}
    same = set(o for o in intersect_keys if existing[o] == new[o])
    tab = tt.Texttable()
    tab.add_row(["Key", "Existing", "New", "State"])
    add_fields_to_table(tab, same, existing, new, "same")
    add_fields_to_table(tab, modified, existing, new, "modified")
    add_fields_to_table(tab, added, existing, new, "added")
    add_fields_to_table(tab, removed, existing, new, "existing")
    print(tab.draw())


def open_browser(lat, lon):
    webbrowser.open(
        'https://www.openstreetmap.org/note/new?lat={lat}&lon={lon}#map=19/{lat}/{lon}&layers=N'.format(lat=lat,
                                                                                                        lon=lon))


class Changer(object):

    class SetTags(object):
        def __init__(self, tags):
            self.tags = tags

        def __call__(self, node):
            for name, value in self.tags.items():
                node['tag'][name] = value
            return node

    class AddTags(object):
        def __init__(self, tags):
            self.tags = tags

        def __call__(self, node):
            for name, value in self.tags.items():
                if name not in node['tag']:
                    node['tag'][name] = value
            return node

    def __init__(self, osm_api):
        self.osm_api = osm_api

    def begin(self):
        self.osm_api.ChangesetCreate({u"comment": u"Import AKB information", "source": "https://www.akb.ch/die-akb/kontakt/geschaeftsstellen.aspx"})

    def commit(self):
        self.osm_api.ChangesetClose()

    def _modify_node(self, existing_object, modifier_fnc):
        obj_type = existing_object['type']
        identifier = existing_object['id']
        if obj_type == 'node':
            obj = self.osm_api.NodeGet(identifier)
            update_fnc = self.osm_api.NodeUpdate
        else:
            raise NotImplementedError("Type %s not implemented" % obj_type)
        print("NodeData", obj)
        tags_before = dict(obj['tag'])
        obj = modifier_fnc(obj)
        print_different_tags(tags_before, obj['tag'])
        input("Cancel if not ok")
        # update_fnc(obj)

    def set_tags(self, existing_object, tags):
        self._modify_node(existing_object, Changer.SetTags(tags))

    def add_tags(self, existing_object, tags):
        self._modify_node(existing_object, Changer.AddTags(tags))

    def create_node(self, wanted):
        raise NotImplementedError()


class Checker(object):
    def __init__(self, overpass_api, osm_api, existing, wanted):
        self.overpass_api = overpass_api
        self.changer = Changer(osm_api)
        self.existing_points = existing
        self.wanted_points = wanted

    def run(self):
        for point in self.wanted_points:
            self.changer.begin()
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


def distance(origin, destination):
    lat1, lon1 = origin
    lat2, lon2 = destination
    radius = 6371  # km

    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) * math.sin(dlat / 2) + math.cos(math.radians(lat1)) \
                                                  * math.cos(math.radians(lat2)) * math.sin(dlon / 2) * math.sin(
        dlon / 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    d = radius * c

    return d


if __name__ == '__main__':
    main()
