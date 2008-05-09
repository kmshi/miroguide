from django.conf import settings
from channelguide.guide import tables
from sqlhelper.orm import record
import sha

class ApiKey(record.Record):
    table = tables.api_key

    @classmethod
    def new(klass, owner_id, description):
        obj = klass()
        data = file('/dev/urandom').read(20)
        obj.api_key = sha.new(data).hexdigest()
        obj.owner_id = owner_id
        obj.description = description
        obj.active = True
        return obj
