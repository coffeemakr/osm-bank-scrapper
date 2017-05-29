from collections import namedtuple


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


class SetAllowedTags(object):
    def __init__(self, tags, allowed_tags):
        self.tags = tags
        self.allowed_tags = allowed_tags

    def __call__(self, node):
        for name, value in self.tags.items():
            if name not in node['tag'] or name in self.allowed_tags:
                node['tag'][name] = value
        return node

ChangerAction = namedtuple("ChangerAction", ["previous_tags", "obj", "update_function"])


class Changer(object):
    def __init__(self, osm_api, source=None, dry_run=False):
        self.osm_api = osm_api
        if source is not None:
            source = str(source)
        self.source = source
        self.dry_run = dry_run
        self.tasks = []

    def begin(self, comment):
        tags = {u"comment": comment}
        if self.source is not None:
            tags['source'] = self.source
        if not self.dry_run:
            self.osm_api.ChangesetCreate(tags)

    def _commit_action(self, action):
        if not self.dry_run:
            action.update_function(action.obj)
        else:
            print("Dry running %s " % str(action))

    def commit(self):
        while self.tasks:
            action = self.tasks.pop(0)
            self._commit_action(action)
        if not self.dry_run:
            self.osm_api.ChangesetClose()

    def modify_node(self, existing_object, modifier_fnc):
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
        self.tasks.append(ChangerAction(tags_before, obj, update_fnc))

    def get_planned_actions(self):
        return list(self.tasks)

    def set_tags(self, existing_object, tags):
        self.modify_node(existing_object, SetTags(tags))

    def add_tags(self, existing_object, tags):
        self.modify_node(existing_object, AddTags(tags))

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

    def set_some_tags(self, existing_object, tags, allowed_tags):
        self.modify_node(existing_object, SetAllowedTags(tags, allowed_tags))
