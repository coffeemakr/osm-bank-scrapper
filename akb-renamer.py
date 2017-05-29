"""
Search for 'Aargauer Kantonalbank' and replace it with 'Aargauische Kantonalbank' which is the correct name.

It is important to notice that there is also a 'Neue Aargauer Bank'.
"""

import overpass
import osmapi
import getpass

from changer import Changer

NAME = "akb-renamer"
VERSION = "1.0"


def main():
    username = input("Username: ")
    password = getpass.getpass("Password: ")
    osm_api = osmapi.OsmApi(username=username, password=password, appid=NAME + " " + VERSION, debug=True)
    changer = Changer(osm_api)
    wrong_name = "Aargauer Kantonalbank"
    correct_name = "Aargauische Kantonalbank"
    changer.begin("Rename Aargauer Kantonalbank to Aargauische Kantonalbank")
    for node in get_wrong_nodes():
        obj = changer.load_object(node)
        print("Got node with id %s" % obj.id)
        for name, value in obj.tags.items():
            if value.strip() == wrong_name:
                print("Replacing field '%s' from %s -> %s" % (name, value, correct_name))
                obj.tags[name] = correct_name
        changer.update_object(obj)
    changer.commit()


def get_wrong_nodes():
    overpass_api = overpass.API()
    query = '''
    [out:json][timeout:25];
    ( area[name="Aargau"]; )->.ch;
    
    (
        relation["name"="Aargauer Kantonalbank"](area.ch);
        way["name"="Aargauer Kantonalbank"](area.ch);
        node["name"="Aargauer Kantonalbank"](area.ch);
        relation["operator"="Aargauer Kantonalbank"](area.ch);
        way["operator"="Aargauer Kantonalbank"](area.ch);
        node["operator"="Aargauer Kantonalbank"](area.ch);
    );
    (._;>;);
    out ids;
    '''
    return overpass_api.Get(query, responseformat='json', build=False)['elements']


if __name__ == '__main__':
    main()
