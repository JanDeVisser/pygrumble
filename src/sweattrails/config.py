# To change this license header, choose License Headers in Project Properties.
# To change this template file, choose Tools | Templates
# and open the template in the editor.

__author__ = "jan"
__date__ = "$3-Oct-2013 8:40:17 AM$"

import gripe
import grizzle
import grumble
import grumble.image

logger = gripe.get_logger(__name__)

def get_flag(country):
    return "http://flagspot.net/images/{0}/{1}.gif".format(country.countrycode[0:1].lower(), country.countrycode.lower()) \
        if country.countrycode \
        else None

class Country(grumble.Model):
    countryname = grumble.StringProperty(verbose_name = "Country name", is_label = True)
    countrycode = grumble.StringProperty(verbose_name = "ISO 3166-1 code", is_key = True)
    flag_url = grumble.StringProperty(transient = True, getter = get_flag)

#
# ============================================================================
#  A C T I V I T Y  P R O F I L E  A N D  P A R T S
# ============================================================================
#

# ----------------------------------------------------------------------------
#  PROFILE COMPONENTS
# ----------------------------------------------------------------------------

class ProfileReference(object):
    @classmethod
    def get_node_definition(cls):
        return NodeTypeRegistry.get_by_ref_class(cls)

class SessionType(grumble.Model, ProfileReference):
    name = grumble.StringProperty(is_key = True, scoped = True)
    description = grumble.StringProperty()
    trackDistance = grumble.BooleanProperty()
    speedPace = grumble.StringProperty(choices = set(['Speed', 'Pace', 'Swim Pace']))
    icon = grumble.image.ImageProperty()

class GearType(grumble.Model, ProfileReference):
    name = grumble.StringProperty(is_key = True, scoped = True)
    description = grumble.StringProperty()
    icon = grumble.image.ImageProperty()

class CriticalPowerInterval(grumble.Model, ProfileReference):
    name = grumble.StringProperty(is_key = True, scoped = True)
    duration = grumble.IntegerProperty()  # seconds


# ----------------------------------------------------------------------------
#  NODE MACHINERY
# ----------------------------------------------------------------------------

class NodeTypeRegistry():
    _by_ref_name = {}
    _by_ref_class = {}
    _by_node_class = {}
        
    @classmethod
    def register(cls, definition):
        cls._by_ref_name[definition._ref_name] = definition
        cls._by_ref_class[definition._ref_class] = definition
        cls._by_node_class[definition._node_class] = definition
        
    @classmethod
    def get_by_name(cls, ref_name):
        return cls._by_ref_name[ref_name]

    @classmethod
    def get_by_ref_class(cls, ref_class):
        return cls._by_ref_class[ref_class]

    @classmethod
    def get_by_node_class(cls, node_class):
        return cls._by_node_class[node_class]
    
    @classmethod
    def names(cls):
        return cls._by_ref_name.keys()
    
    @classmethod
    def types(cls):
        return cls._by_ref_name.values()

class NodeTypeDefinition(object):
    def __init__(self, ref_name, ref_class, node_class):
        self._ref_name = ref_name
        self._ref_class = ref_class
        self._node_class = node_class
        NodeTypeRegistry.register(self)
        
    def name(self):
        return self._ref_name
    
    def ref_class(self):
        return self._ref_class
    
    def node_class(self):
        return self._node_class
    
    def name_property(self):
        return self.ref_class().keyproperty()

    def link_properties(self):
        if not hasattr(self, "_link_props"):
            self._link_props = {}
            for p in self.node_class().properties():
                if isinstance(p, grumble.ReferenceProperty) and issubclass(p.reference_class, NodeBase):
                   self._link_props[p.name] = NodeTypeRegistry.get_by_node_class(p.reference_class)
        return self._link_props
    
    def get_reference_by_name(self, profile, key_name):
        p = profile.parent()
        ref = self.ref_class().get_by_key_and_parent(key_name, p)
        if ref is None and p is not None:
            ref = self.ref_class().get_by_key_and_parent(key_name, None)
        assert ref, "Cannot find reference to %s:%s" % (self.ref_class(), key_name)
        return ref

    def get_or_create_node(self, profile, descriptor, parent = None):
        ref = self.ref_class().get(descriptor[self.name()]) \
            if self.name() in descriptor \
            else self.get_reference_by_name(profile, descriptor[self.name_property()])
        if not ref:
            ref = self.ref_class()(parent = profile.parent())
        assert ref, "No reference found for %s in %s" % (self, name(), descriptor)
        node = self.get_or_create_node_for_reference(profile, ref, parent)
        self.update_node(node, descriptor)
        return node
    
    def update_node(self, node, descriptor):
        ref = getattr(node, self.name())
        assert ref, "%s.update_node: no reference" % self.name()
        if ref.parent() == node.get_profile().parent():
            ref.update(descriptor)
        dirty = False
        for (prop, t) in self.link_properties():
            if prop in descriptor:
                n = t.get_or_create_node(self, descriptor[prop])
                setattr(node, prop, n)
                dirty = True
        if dirty:
            node.put()
        return node
    
    def get_or_create_node_for_reference(self, profile, ref, parent = None):
        node = self.get_node_for_reference(profile, ref)
        if not node:
            node = self.node_class()(parent = parent if parent else profile)
            setattr(node, self.name(), ref)
            node.put()
        assert node, "%s.get_or_create_node_for_reference(): No node" % self.name()
        return node

    def get_node_for_reference(self, profile, ref):
        q = self.node_class().query(ancestor = profile)
        q.add_filter(self.name(), "=", ref)
        return q.get()
    
    def get_node_by_reference_name(self, profile, key_name):
        ref = self.get_reference_by_name(profile, key_name)
        return self.get_node_for_reference(profile, ref)

    def get_or_duplicate_reference(self, original, profile):
        ref_key = getattr(original, self.name_property())
        # Check if the reference already exists:
        ref = self.get_reference_by_name(profile, ref_key)
        if ref:
            return ref
        # Only copy if reference is owned by another profile. If the reference
        # is not owned by another profile, it's a global entity.
        ref = original
        if ref.parent():
            ref = self.ref_class().create(original.to_dict(), profile.parent())
        return ref
    
    def duplicate_node(self, original, profile):
        orig_ref = getattr(original, self.name())
        ref = self.get_or_duplicate_reference(orig_ref, profile)
        if isinstance(original.parent(), original.__class__):
            orig_parent_ref = getattr(original.parent(), self.name())
            orig_parent = self.get_node_for_reference(profile, orig_parent_ref)
            parent = self.duplicate_node(orig_parent, profile)
        else:
            parent = profile
        node = self.get_or_create_node_for_reference(profile, ref, parent)
        dirty = False
        for (prop, t) in self.link_properties():
            n = t.duplicate_node(getattr(original, prop), profile)
            node.setattr(node, prop, n)
            dirty = True
        if dirty:
            node.put()
        
        
@grumble.abstract
class NodeBase(grumble.Model):
    
    @classmethod
    def get_node_definition(cls):
        return NodeTypeRegistry.get_by_node_class(cls)
    
    @classmethod
    def is_tree(cls):
        return False
    
    def scope(self):
        if not hasattr(self, "_scope"):
            r = self.root()
            self._scope = None if r.kind() == ActivityProfile.kind() else r
        return self._scope

    def get_profile(self):
        if not hasattr(self, "_profile"):
            path = self.pathlist()
            self._profile = path[0] if path[0].kind() == 'sweattrails.config.activityprofile' else path[1]
        return self._profile
    
    def sub_to_dict(self, d, **flags):
        ref = getattr(self, self.get_node_definition().name())
        d.update(ref.to_dict())
        return d


@grumble.abstract
class TreeNodeBase(NodeBase):
    @classmethod
    def is_tree(cls):
        return True
    
    def get_subtypes(self, all = False):
        q = self.children() if not all else self.descendents()
        return q.fetch_all()

    def get_all_subtypes(self):
        return self.get_subtypes(True)

    def has_subtype(self, type, deep = True):
        q = self.children() if not deep else self.descendents()
        q.add_filter(self.name(), '=', type)
        return q.fetch() is not None

    def on_delete(self):
        # FIXME: Go over link_properties and set reverse links to None
        p = self.get_profile()
        for sub in self.get_all_subtypes():
            sub.set_parent(p)
            sub.put()


# ----------------------------------------------------------------------------
#  PROFILE NODES
# ----------------------------------------------------------------------------

class SessionTypeNode(TreeNodeBase):
    sessionType = grumble.ReferenceProperty(SessionType, serialize = False)


class GearTypeNode(TreeNodeBase):
    gearType = grumble.ReferenceProperty(GearType, serialize = False)
    partOf = grumble.SelfReferenceProperty(collection_name = "parts")
    usedFor = grumble.ReferenceProperty(SessionTypeNode)

class CriticalPowerIntervalNode(NodeBase):
    criticalPowerInterval = grumble.ReferenceProperty(CriticalPowerInterval, serialize = False)


logger.debug("sweattrails config: %s", gripe.Config.app.sweattrails)
for (part, partdef) in gripe.Config.app.sweattrails.activityprofileparts.items():
    definition = NodeTypeDefinition(part, gripe.resolve(partdef.refClass), gripe.resolve(partdef.nodeClass))


class ActivityProfile(grizzle.UserComponent):
    name = grumble.StringProperty(is_key = True)
    description = grumble.StringProperty()
    isdefault = grumble.BooleanProperty()
    icon = grumble.image.ImageProperty()

    def sub_to_dict(self, descriptor):
        logger.debug("ActivityProfile.sub_to_dict(%s)", self.name)
        for part in grumble.Query(NodeBase, False, True).set_ancestor(self):
            logger.debug("ActivityProfile.sub_to_dict(%s) got part %s", self.name, part)
            node_type = NodeTypeRegistry.get_by_node_class(part.__class__)
            if node_type.name() not in descriptor:
                descriptor[node_type.name()] = []
            descriptor[node_type.name()].append(part.to_dict())
        return descriptor

    def sub_update(self, d):
        for ref_name in NodeTypeRegistry.names():
            if ref_name in d:
                self.update_or_create_nodes(d[ref_name], ref_name)
        return self

    def initialize(self):
        # Only do this for profiles that are user components:
        if not self.parent():
            return

        # Set the profile's name. Every user has only one profile object which
        # is manipulated whenever the user selects another template profile.
        self.name = "Activity Profile for " + self.parent()().display_name

        # Find the default profile:
        profile = self.__class__.by("isdefault", True, parent = None)
        logger.debug("initialize(%s): default profile = %s", self.name, profile)

        # If there is a default profile, import it into this profile:
        if profile:
            self.import_profile(profile)

    @classmethod
    def import_template_data(cls, data):
        """
            Import template activity profile data.
        """
        with gripe.pgsql.Tx.begin():
            if cls.all(keys_only = True).count() > 0:
                return
        logger.debug("Loading ActivityProfile template data")
        for profile in data:
            with gripe.pgsql.Tx.begin():
                p = cls(name = profile.name,
                    description = profile.description,
                    isdefault = profile.isdefault)
                p.put()
                logger.debug("import_template_data: Created profile %s", p.name)
                for ref_name in NodeTypeRegistry.names():
                    logger.debug("import_template_data: checking %s", ref_name)
                    if ref_name in profile:
                        logger.debug("import_template_data: processing %s", ref_name)
                        p.update_or_create_nodes(profile[ref_name], ref_name)

    def update_or_create_nodes(self, d, ref_name):
        node_type = NodeTypeRegistry.get_by_name(ref_name)
        d = d if isinstance(d, list) else [d]
        for subdict in d:
            node = None
            isA = subdict["isA"] if "isA" in subdict else None
            parent = node_type.get_or_create_node(self, isA) if isA else None
            if "key" in subdict:
                # Code path for JSON updates
                node = node_type.node_class().get(subdict["key"])
                if node:
                    if node.is_tree() and ((parent and parent != node.parent()) or (not parent and node.parent())):
                        node.set_parent(parent)
                        node.put()
                    node_type.update_node(node, subdict)
            else:
                # Path for import or JSON creates:
                # Find or create node, and update it.
                node = node_type.get_or_create_node(self, subdict, parent)

    def on_delete(self):
        pass

    # This deletes the node no questions asked. This means that all relations
    # get removed. Subtypes become root types, and parts become top-level
    # assemblies.
    #def delete_node(self, q, pointer_name, (node_class, pointer_class)):
    #    key = q[pointer_name] if pointer_name in q else None
    #    if key:
    #        node = node_class.get(key)
    #        if node:
    #            node.remove()
    #        return True
    #    else:
    #        return False

    def import_profile(self, profile):
        if type(profile) == str:
            profile = ActivityProfile.by("name", profile, parent = None)
        if not(profile):
            return self
        logger.debug("Profile %s: Importing profile %s", self.name, profile.name)
        if (profile.parent() == self.parent()) or not profile.parent():
            logger.debug("Profile %s: Importing profile %s REALLY", self.name, profile.name)
            for node_type in NodeTypeRegistry.types():
                logger.debug(" -> node_type %s", node_type.name())
                for node in node_type.node_class().query(ancestor = profile):
                    logger.debug(" --> node %s", node)
                    new_node = node_type.duplicate_node(node, self)
        return self

    def scope(self):
        if not hasattr(self, "_scope"):
            self._scope = self.parent()
        return self._scope
    
    def get_reference_from_descriptor(self, ref_class, d):
        p = self.parent()
        key = None
        name = None
        if type(d) == dict:
            key = d["key"] if "key" in d else None
            name = d["name"] if "name" in d else None
        else:
            key = str(d)
        assert key or name, "ActivityProfile.get_reference_from_descriptor: descriptor must specify name or key"
        if key:
            ref = ref_class.get(key)
            assert ref, "ActivityProfile.get_reference_from_descriptor(%s): descriptor specified key = '%s' but no reference found" % (ref_class, key)
        else:
            return self.get_reference_by_name(ref_class, name)
        return ref
        

#
# ============================================================================
#  B R A N D S  A N D  P R O D U C T S
# ============================================================================
#

class Brand(grumble.Model):
    name = grumble.StringProperty()
    description = grumble.StringProperty()
    logo = grumble.image.ImageProperty()
    website = grumble.StringProperty()  # FIXME LinkProperty
    about = grumble.TextProperty()
    country = grumble.ReferenceProperty(Country)
    gearTypes = grumble.ListProperty()  # (grumble.Key) FIXME Make list items typesafe

    def sub_to_dict(self, descriptor):
        gts = []
        for gt in self.gearTypes:
            gts.append(GearType.get(gt).to_dict())
        descriptor["gearTypes"] = gts
        return descriptor

class Product(grumble.Model):
    name = grumble.StringProperty()
    icon = grumble.image.ImageProperty()
    isA = grumble.SelfReferenceProperty(collection_name = "subtypes_set")
    usedFor = grumble.ReferenceProperty(SessionType)
    partOf = grumble.SelfReferenceProperty(collection_name = "parts_set")
    baseType = grumble.SelfReferenceProperty(collection_name = "descendenttypes")


