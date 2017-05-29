from helper import print_different_tags


class OSMObject(object):
    def __init__(self, id_, type_, osmapi_result):
        self.id = id_
        self.type = type_
        self.osmapi_result = osmapi_result

    def to_osmapi(self):
        return self.osmapi_result

    @property
    def tags(self):
        return self.osmapi_result['tag']


class OSMWay(OSMObject):
    def __init__(self, id_, osmapi_result):
        super(OSMWay, self).__init__(id_, 'way', osmapi_result)

    def get_nodes(self):
        return self.osmapi_result['nd']


class OSMNode(OSMObject):
    def __init__(self, id_, osmapi_result):
        super(OSMNode, self).__init__(id_, 'node', osmapi_result)


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

    def __init__(self, osm_api, source=None):
        self.osm_api = osm_api
        if source is not None:
            source = str(source)
        self.source = source

    def begin(self, comment):
        tags = {u"comment": comment}
        if self.source is not None:
            tags['source'] = self.source
        self.osm_api.ChangesetCreate()

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
        update_fnc(obj)

    def set_tags(self, existing_object, tags):
        self._modify_node(existing_object, Changer.SetTags(tags))

    def add_tags(self, existing_object, tags):
        self._modify_node(existing_object, Changer.AddTags(tags))

    def create_node(self, wanted):
        raise NotImplementedError()

    '''
    Loads an object.
    
    The object must have the fields 'type' and 'id'
    '''
    def load_object(self, obj):
        id = obj['id']
        obj_type = obj['type']
        if obj_type == 'node':
            return OSMNode(id, self.osm_api.NodeGet(id))
        elif obj_type == 'way':
            return OSMWay(id, self.osm_api.WayGet(id))
        elif obj_type == 'relation':
            raise NotImplementedError("Relations are not implemented yet")
        else:
            raise ValueError("Invalid type: " + obj_type)

    def update_object(self, obj):
        if obj.type == 'node':
            return self.osm_api.NodeUpdate(obj.to_osmapi())
        elif obj.type == 'way':
            return self.osm_api.WayUpdate(obj.to_osmapi())
        else:
            raise ValueError("Invalid type: " + obj.type)