# To change this template, choose Tools | Templates
# and open the template in the editor.

__author__ = "jan"
__date__ = "$11-Feb-2013 2:47:51 PM$"

import hashlib
import os
import psycopg2
import gripe
import gripe.db
import grumble.converter
import grumble.property

class BinaryConverter(grumble.converter.PropertyConverter):
    datatype = psycopg2.Binary

    def convert(self, value):
        # psycopg2.Binary is a function, not a class. Therefore our isinstance
        # test in the base convert method doesn't work.
        return self.datatype(value)

class BinaryProperty(grumble.property.ModelProperty):
    datatype = psycopg2.Binary
    sqltype = "BYTEA"

    def _to_json_value(self, instance, value):
        raise gripe.NotSerializableError(self.name)

    def _from_json_value(self, value):
        raise gripe.NotSerializableError(self.name)

class ImageProperty(grumble.property.CompoundProperty):
    def __init__(self, **kwargs):
        bin_kwargs = { "suffix": "_blob"}
        ct_kwargs = { "suffix": "_ct"}
        hash_kwargs = { "suffix": "_hash"}
        if "verbose_name" in kwargs:
            bin_kwargs["verbose_name"] = kwargs["verbose_name"]
        super(ImageProperty, self).__init__(
            BinaryProperty(**bin_kwargs),
            grumble.property.StringProperty(**ct_kwargs),
            grumble.property.StringProperty(**hash_kwargs)
        )

    def __set__(self, instance, value):
        v = None
        if isinstance(value, tuple) or isinstance(value, list):
            l = len(value)
            assert l in [2, 3], "Cannot assign sequence of length %s to ImageProperty" % len
            if l == 3:
                v = value
            else:
                hash = hashlib.md5(value[0]).hexdigest()
                v = (value[0], value[1], hash)
        else:
            assert isinstance(value, basestring), "Can't assign %s (%s) to ImageProperty" % (value, type(value))
            content = None
            with open(value, "rb") as fh:
                content = fh.read()
            hash = hashlib.md5(content).hexdigest()
            v = (content, gripe.get_content_type(value), hash)
        super(ImageProperty, self).__set__(instance, v)

if __name__ == "__main__":
    import grumble.model

    class Test(grumble.model.Model):
        label = grumble.property.TextProperty(required = True)
        image = ImageProperty()

    with gripe.db.Tx.begin():
        with open("C:/Users/Public/Pictures/Sample Pictures/Desert.jpg", "rb") as fh:
            img = fh.read()
            desert = Test(label = "Desert")
            desert.image = (img, "image/jpeg")
            desert.put()
            k = desert.key()

    try:
        os.remove("C:/Users/Public/Pictures/Sample Pictures/Desert_1.jpg")
    except:
        pass

    with gripe.db.Tx.begin():
        desert = Test.get(k)
        with open("C:/Users/Public/Pictures/Sample Pictures/Desert_1.jpg", "wb") as fh:
            fh.write(desert.image_blob)


