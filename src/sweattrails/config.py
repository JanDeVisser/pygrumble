# To change this license header, choose License Headers in Project Properties.
# To change this template file, choose Tools | Templates
# and open the template in the editor.

__author__="jan"
__date__ ="$3-Oct-2013 8:40:17 AM$"

import gripe
import grumble
import grumble.image

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

class SessionType(grumble.Model):
    name = grumble.StringProperty()
    description = grumble.StringProperty()
    trackDistance = grumble.BooleanProperty()
    speedPace = grumble.StringProperty(choices=set(['Speed', 'Pace', 'Swim Pace']))
    icon = grumble.image.ImageProperty()

class GearType(grumble.Model):
    name = grumble.StringProperty()
    description = grumble.StringProperty()
    icon = grumble.image.ImageProperty()

class CriticalPowerInterval(grumble.Model):
    name = grumble.StringProperty()
    duration = grumble.IntegerProperty()	# seconds


# ----------------------------------------------------------------------------
#  NODE MACHINERY
# ----------------------------------------------------------------------------

class NodeBase(object):
    id_prop = "name"

    def get_profile(self):
        return self.parent()

    def get_type(self):
        return getattr(self, self.pointer_name)

    def get_links(self):
        return ()

    def set_links(self, links):
        pass

    def remove(self):
        self.prune_tree()
        hasattr(self, "on_delete") and callable(self.on_delete) and self.on_delete()
        self.delete()

    def prune_tree(self):
        pass

    def get_or_create_node(self, descriptor, pointer_name):
        node_class, pointer_class = ActivityProfile.node_defs[pointer_name]
        node = None
        pointer = pointer_class.get(descriptor["key"]) \
            if "key" in descriptor \
            else pointer_class.by(self.id_prop, descriptor[self.id_prop], ancestor = self.get_profile().parent())
        if not pointer:
            pointer = pointer_class.create(descriptor, self.get_profile().parent())
        if pointer:
            node = node_class(parent = self.parent())
            setattr(node, pointer_name, pointer)
            node.put()
        return node

class TreeNodeBase(NodeBase):

    def get_subtypes(self, all = False):
        ret = []
        subs = []
        subs.append(self)
        while subs:
            node = subs.pop(0)
            for sub in node.subtypes:
                ret.append(sub.get_type())
            if all:
                subs.extend(node.subtypes)
        return ret

    def get_all_subtypes(self):
        return self.get_subtypes(True)

    def has_subtype(self, type, deep = True):
        subs = []
        subs.append(self)
        while subs:
            node = subs.pop(0)
            for sub in node.subtypes:
                if sub.get_type() == type:
                    return True
            if deep:
                subs.extend(node.subtypes)
        return False

    def prune_tree(self):
        for sub in self.subtypes:
            sub.isA = None
            sub.put()


# ----------------------------------------------------------------------------
#  PROFILE NODES
# ----------------------------------------------------------------------------

class SessionTypeNode(grumble.Model, TreeNodeBase):
    sessionType = grumble.ReferenceProperty(SessionType)
    pointer_class = SessionType
    pointer_name = "sessionType"


class GearTypeNode(grumble.Model, TreeNodeBase):
    gearType = grumble.ReferenceProperty(GearType)
    partOf = grumble.SelfReferenceProperty(collection_name = "parts")
    usedFor = grumble.ReferenceProperty(SessionType)
    pointer_class = GearType
    pointer_name = "gearType"

    def get_links(self):
        return (self.partOf.gearType if self.partOf else None, self.usedFor)

    def set_links(self, links):
        (partOf, usedFor) = links
        self.partOf = self.get_profile().get_node_for_type(partOf, "gearType")
        self.usedFor = usedFor
        return self

    def update(self, descriptor):
        if "usedFor" in descriptor and (type(descriptor["usedFor"]) == dict):
            self.usedFor = self.get_or_create_node(descriptor["usedFor"], "sessionType")
        if "partOf" in descriptor and (type(descriptor["partOf"]) == dict):
            self.partOf = self.get_or_create_node(descriptor["partOf"], "gearType")
        return self

    def on_delete(self):
        for part in self.parts:
            part.partOf = None
            part.put()

    def prune_tree(self):
        super(GearTypeNode, self).prune_tree()
        for part in self.parts:
            part.partOf = None
            part.put()

class CriticalPowerIntervalNode(grumble.Model, NodeBase):
    criticalPowerInterval = grumble.ReferenceProperty(CriticalPowerInterval)
    pointer_class = CriticalPowerInterval
    pointer_name = "criticalPowerInterval"



class ActivityProfile(grumble.Model):
    name = grumble.StringProperty(is_key = True)
    description = grumble.StringProperty()
    icon = grumble.image.ImageProperty()
    node_defs = {}
    for (part, partdef) in gripe.Config.app.grizzle.activityprofileparts.items():
        node_defs[part] = ( gripe.resolve(partdef.nodeClass), gripe.resolve(partdef.pointerClass) )

    def sub_to_dict(self, descriptor):
        # TODO: Build tree...
        return descriptor

    def sub_update(self, d):
        for pointer_name, defs in self.node_defs.items():
            self.update_or_create_nodes(d, pointer_name, defs)
        return self

    def update_or_create_nodes(self, d, pointer_name, (node_class, pointer_class)):
        sub = d[pointer_name] if pointer_name in d else None
        if not sub:
            return
        sub = sub if type(sub) == list else [sub]
        for subdict in sub:
            node = None
            isA = subdict["isA"] if "isA" in subdict else None
            parent = node_class.get(isA) if isA else None
            if isA and not parent:
                return None
            if "key" in subdict:
                node = node_class.get(subdict["key"])
                if hasattr(self, "isA") and ((parent and parent != node.isA) or (not parent and node.isA)):
                    # Change of parent requested:
                    if (parent and node.has_subtype(parent.get_type())):
                        # Cyclical reference
                        return None
                    node.isA = parent
            else:
                pointer = pointer_class.by(node_class.id_prop, subdict[node_class.id_prop], parent = self.parent()) \
                    if node_class.id_prop in subdict else None
                if not pointer:
                    return None
                if self.has_type(pointer_name, pointer):
                    return None
                node = node_class(parent = self, isA = parent) if isA else node_class(parent = self)
                setattr(node, pointer_name, pointer)
                node.put()
            if node:
                hasattr(node, "update") and callable(node.update) and node.update(subdict)
                node.put()

    def on_delete(self):
        for (node_class, _) in self.node_defs.values():
            db.delete(node_class.query(ancestor = self))

    def remove(self, q):
        removed_node = False
        for pointer_name, defs in self.node_defs.items():
            r = self.delete_node(q, pointer_name, defs)
            removed_node = removed_node or r
        if not removed_node:
            self.on_delete()
            self.delete()

    # This deletes the node no questions asked. This means that all relations
    # get removed. Subtypes become root types, and parts become top-level
    # assemblies.
    def delete_node(self, q, pointer_name, (node_class, pointer_class)):
        key = q[pointer_name] if pointer_name in q else None
        if key:
            node = node_class.get(key)
            if node:
                node.remove()
            return True
        else:
            return False
        
    def import_profile(self, profile):
        if type(profile) == str:
            profile = ActivityProfile.by("name", profile, parent = self.parent())
        if not(profile):
            return self
        if (profile.parent() == self.parent()) or profile.parent().is_root():
            for pointer_name, (node_class, _) in self.node_defs.values():
                p = profile
                new_p = self
                parents = [(profile, self)]
                links = []
                while parents:
                    subs = []
                    for (p, new_p) in parents:
                        for node in node_class.query(parent = p):
                            new_node = node_class(parent = new_p)
                            setattr(new_node, pointer_name, getattr(node, pointer_name))
                            new_node.put()
                            links.append((new_node, node.get_links()))
                            subs.append((node, new_node))
                    parents = subs
                for node_tuple in links:
                    (new_node, node_links) = node_tuple
                    new_node.set_links(node_links)                
        return self

    def get_node_for_type(self, type, pointer_name):
        node_class, _ = self.node_defs[pointer_name]
        q = node_class.query(ancestor = self)
        q.add_filter('"' + pointer_name + '" = ', type)
        return q.get()

    def get_all_types(self, pointer_name, only_root):
        node_class, _ = self.node_defs[pointer_name]
        ret = []
        q = node_class.query(ancestor = self)
        if only_root and hasattr(node_class, "isA"):
            q.add_filter('"isA" = ', None)
        for node in q:
            ret.append(getattr(node, pointer_name))
        return ret

    def has_type(self, pointer_name, type):
        node_class, _ = self.node_defs[pointer_name]
        q = node_class.query(ancestor = self)
        q.add_filter('"' + pointer_name + '" = ', type)
        return q.count() > 0


#
# ============================================================================
#  B R A N D S  A N D  P R O D U C T S
# ============================================================================
#

class Brand(grumble.Model):
    name = grumble.StringProperty()
    description = grumble.StringProperty()
    logo = grumble.image.ImageProperty()
    website = grumble.StringProperty()   # FIXME LinkProperty
    about = grumble.TextProperty()
    country = grumble.ReferenceProperty(Country)
    gearTypes = grumble.ListProperty() # (grumble.Key) FIXME Make list items typesafe

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


