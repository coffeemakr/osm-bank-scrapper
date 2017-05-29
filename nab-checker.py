import getpass

import osmapi

from changer import Changer
from check3 import Checker
import json
import overpass
from helper import open_browser
import helper


NAME = 'osm-bank-scraper'
VERSION = '0.3.0'
NAB_ATM_SOURCE=("https://www.nab.ch/fileadmin/user_upload/Public/Inhalte/"
                "Kontakt-Services/Standorte/740700_Geldausgabeautomaten_der_NAB.pdf")

def is_same_ignore_case(first, second):
    return first.strip().lower() == second.strip().lower()


class ATMChecker(Checker):
    required_fields = {
        'amenity': 'atm'
    }

    def __init__(self, *args, allowed_names, **kwargs):
        super(ATMChecker, self).__init__(*args, **kwargs)
        self.allowed_names = allowed_names

    def get_required_fields(self):
        return self.required_fields

    def are_tags_the_same(self, expected_tags, received_tags):
        if 'operator' not in received_tags and 'name' not in received_tags:
            # Has no name and no operator so we can assume its our :)
            return True
        if is_same_ignore_case(expected_tags['operator'], received_tags.get('operator', '')) or \
                is_same_ignore_case(expected_tags['operator'], received_tags.get('name', '')):
            return True

        if received_tags.get('operator', '') in self.allowed_names:
            return True

        if received_tags.get('name', '') in self.allowed_names:
            return True
        print("Skipping because of different operator/name: %s" % received_tags)


def main():
    with open('nab.json', 'r') as fp:
        nab_locations = json.load(fp)

    atms = []
    banks = []
    for location in nab_locations:
        if location['tags']['amenity'] == 'atm':
            atms.append(location)
        else:
            banks.append(location)

    allowed_names = ['Neue Aargauer Bank', 'Neue Aargauer Bank AG', 'NAB']

    atm_checker = ATMChecker(atms, allowed_names=allowed_names, overpass_api=overpass.API())

    username = input("username: ")
    password = getpass.getpass("password: ")
    osm_api = osmapi.OsmApi(username=username, password=password, appid=NAME + " " + VERSION)

    changer = Changer(osm_api, dry_run=True, source=NAB_ATM_SOURCE)
    changer.begin("Add information to the ATM of Neue Aargauer Bank")

    for obj, match in atm_checker.find_all_objects():
        if match:
            changer.set_some_tags(match, obj['tags'], allowed_tags=['operator'])
            print("=" * 80)
            print(obj)
            print("=" * 80)
            print(match)
            print("=" * 80)
        else:
            open_browser(**obj['coordinates'])
    for action in changer.get_planned_actions():
        tags = action.previous_tags
        next_tags = action.obj['tag']
        helper.print_different_tags(tags, next_tags)
        input("Enter... :)")
    changer.commit()

if __name__ == '__main__':
    main()
