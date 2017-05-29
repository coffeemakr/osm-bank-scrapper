import sys

class Checker(object):

    def __init__(self, objects, overpass_api):
        self.objects = objects
        self.overpass_api = overpass_api
        self.radius = 50

    def __get_find_objects_query(self, coordinates):
        selector = ''
        for name, value in self.get_required_fields().items():
            if value is not None:
                selector += '["{name}"="{value}"]'.format(name=name, value=value)

        selector += '(around: {rad},{lat},{lon})'.format(rad=self.radius, **coordinates)
        query = '[out:json][timeout:10]; \n ('
        for obj_type in ['node', 'way', 'relation']:
            query += ' ' + obj_type + selector + ';\n'
        query += ');\n (._;>;);\n out body;'
        return query

    def are_tags_the_same(self, expected_tags, received_tags):
        raise NotImplementedError()

    def get_required_fields(self):
        raise NotImplementedError()

    def find_all_objects(self):
        for obj in self.objects:
            sys.stdout.write('.')
            sys.stdout.flush()
            result = self.find_object(obj)
            yield obj, result

    def find_object(self, obj):
        query = self.__get_find_objects_query(obj['coordinates'])
        nodes = self.overpass_api.Get(query, responseformat='json', build=False)['elements']
        for node in nodes:
            if self.are_tags_the_same(obj['tags'], node['tags']):
                return node