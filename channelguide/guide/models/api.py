from django.conf import settings
from channelguide.guide import tables
from sqlhelper.orm import record
import sha

class ApiKey(record.Record):
    table = tables.api_key

    def __init__(self, owner_id, description):
        data = file('/dev/urandom').read(20)
        self.api_key = sha.new(data).hexdigest()
        self.owner_id = owner_id
        self.description = description
        self.active = True
