import texttable as tt
import webbrowser
import math


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
