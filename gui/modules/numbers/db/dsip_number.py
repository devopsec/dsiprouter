"""dSIP Number DB model (MetaData approach)

Defines `dSIPNumber` class mapping to the `numbers` table.
"""
from sqlalchemy import Column, Integer, String


class dSIPNumber(object):
    """Model for `numbers` table.

    Fields:
      - id: primary key
      - did: the number (string)
      - status: status of the number
      - carrier: carrier identifier
      - pool: pool identifier
      - assigned_length: integer length assigned
      - assigned_reference_id: integer reference id
    """

    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    did = Column(String(64), nullable=False)
    status = Column(String(64), nullable=True)
    carrier = Column(String(128), nullable=True)
    pool = Column(String(128), nullable=True)
    assigned_length = Column(Integer, nullable=True)
    assigned_reference_id = Column(Integer, nullable=True)

    def __init__(self, did, status=None, carrier=None, pool=None, assigned_length=None, assigned_reference_id=None):
        self.did = did
        self.status = status
        self.carrier = carrier
        self.pool = pool
        self.assigned_length = assigned_length
        self.assigned_reference_id = assigned_reference_id

    def to_dict(self):
        return {
            'id': getattr(self, 'id', None),
            'did': self.did,
            'status': self.status,
            'carrier': self.carrier,
            'pool': self.pool,
            'assigned_length': self.assigned_length,
            'assigned_reference_id': self.assigned_reference_id,
        }
