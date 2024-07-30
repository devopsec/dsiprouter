# make sure the generated source files are imported instead of the template ones
import sys

if sys.path[0] != '/etc/dsiprouter/gui':
    sys.path.insert(0, '/etc/dsiprouter/gui')

from enum import Enum
from datetime import datetime, timedelta
from sqlalchemy import Column, String, event, DATETIME, VARCHAR
from sqlalchemy.orm import Mapped, mapped_column
import settings
from shared import dictToStrFields
from util.networking import safeUriToHost, safeFormatSipUri, encodeSipUser
from .dialects import UnsignedInt
from .orm import MappedTable, HookBeforeInsert, HookBeforeUpdate, HookBeforeDelete


class Gateways(object):
    """
    Schema for dr_gateways table\n
    Documentation: `dr_gateways table <https://kamailio.org/docs/db-tables/kamailio-db-5.5.x.html#gen-db-dr-gateways>`_\n
    Allowed address types: SIP URI, IP address or DNS domain name\n
    The address field can be a full SIP URI, partial URI, or only host; where host portion is an IP or FQDN
    """

    gwid = Column(UnsignedInt, primary_key=True, autoincrement=True, nullable=False)

    def __init__(self, name, address, strip, prefix, type=0, gwgroup=None, addr_id=None,
                 msteams_domain='', signalling='proxy', media='proxy'):
        description = {"name": name}
        if gwgroup is not None:
            description["gwgroup"] = str(gwgroup)
        if addr_id is not None:
            description['addr_id'] = str(addr_id)

        self.type = type
        self.address = address
        self.strip = strip
        self.pri_prefix = prefix
        self.attrs = Gateways.buildAttrs(0, type, msteams_domain, signalling, media)
        self.description = dictToStrFields(description)

    @staticmethod
    def buildAttrs(gwid=0, type=0, msteams_domain='', signalling='proxy', media='proxy'):
        # gwid in dr_attrs is updated via trigger before insert/update
        return ','.join([str(gwid), str(type), msteams_domain, signalling, media])

    def attrsToDict(self):
        attrs_dict = {}
        attrs_list = self.attrs.split(',')
        try:
            attrs_dict['gwid'] = int(attrs_list[0])
        except IndexError:
            attrs_dict['gwid'] = 0
        try:
            attrs_dict['type'] = int(attrs_list[1])
        except IndexError:
            attrs_dict['type'] = 0
        try:
            attrs_dict['msteams_domain'] = attrs_list[2]
        except IndexError:
            attrs_dict['msteams_domain'] = ''
        try:
            attrs_dict['signalling'] = attrs_list[3]
        except IndexError:
            attrs_dict['signalling'] = 'proxy'
        try:
            attrs_dict['media'] = attrs_list[4]
        except IndexError:
            attrs_dict['media'] = 'proxy'
        return attrs_dict


class GatewayGroups(object):
    """
    Schema for dr_gw_lists table\n
    Documentation: `dr_gw_lists table <https://kamailio.org/docs/db-tables/kamailio-db-5.5.x.html#gen-db-dr-gw-lists>`_
    """

    id = Column(UnsignedInt, primary_key=True, autoincrement=True, nullable=False)

    class FILTER(Enum):
        ENDPOINT = f'type:{settings.FLT_PBX}(,|$)'
        CARRIER = f'type:{settings.FLT_CARRIER}(,|$)'
        MSTEAMS = f'type:{settings.FLT_MSTEAMS}(,|$)'
        ENDPOINT_OR_CARRIER = f'type:({settings.FLT_PBX}|{settings.FLT_CARRIER})(,|$)'

    def __init__(self, name, gwlist=[], type=settings.FLT_CARRIER, dlg_timeout=None):
        description = {'name': name, 'type': type}
        if dlg_timeout is not None:
            description['dlg_timeout'] = dlg_timeout

        self.description = dictToStrFields(description)
        self.gwlist = ",".join(str(gw) for gw in gwlist)


class Address(object):
    """
    Schema for address table\n
    Documentation: `address table <https://kamailio.org/docs/db-tables/kamailio-db-5.5.x.html#gen-db-address>`_\n
    Allowed address types: exact IP address, subnet IP address or DNS domain name\n
    The ip_addr field is either an IP address or DNS domain name; mask field is for subnet
    """

    def __init__(self, name, ip_addr, mask, type, gwgroup=None, port=0):
        tag = {"name": name}
        if gwgroup is not None:
            tag["gwgroup"] = str(gwgroup)

        self.grp = type
        self.ip_addr = ip_addr
        self.mask = mask
        self.port = port
        self.tag = dictToStrFields(tag)

    pass


class InboundMapping(object):
    """
    Partial Schema for modified version of dr_rules table\n
    Documentation: `dr_rules table <https://kamailio.org/docs/db-tables/kamailio-db-5.5.x.html#gen-db-dr-rules>`_
    """

    gwname = Column(String)

    def __init__(self, groupid, prefix, gwlist, description=''):
        self.groupid = groupid
        self.prefix = prefix
        self.gwlist = gwlist
        self.description = description
        self.timerec = ''
        self.routeid = ''

    pass


class OutboundRoutes(object):
    """
    Schema for dr_rules table\n
    Documentation: `dr_rules table <https://kamailio.org/docs/db-tables/kamailio-db-5.5.x.html#gen-db-dr-rules>`_
    """

    def __init__(self, groupid, prefix, timerec, priority, routeid, gwlist, description):
        self.groupid = groupid
        self.prefix = prefix
        self.timerec = timerec
        self.priority = priority
        self.routeid = routeid
        self.gwlist = gwlist
        self.description = description

    pass


class CustomRouting(object):
    """
    Schema for dr_custom_rules table\n
    """

    def __init__(self, locality, ppm, description):
        self.locality = locality
        self.ppm = ppm
        self.description = description

    pass


class dSIPLCR(object):
    """
    Schema for LCR lookup\n
    Mapped to db table: dsip_lcr
    The pattern field contains a complex key that includes FROM XNPA and TO NPA\n
    There the pattern field looks like this XNPA-NPA\n
    The dr_groupid field contains a dynamic routing group that maps to a gateway
    """

    def __init__(self, pattern, from_prefix, dr_groupid, cost=0.00):
        self.pattern = pattern
        self.from_prefix = from_prefix
        self.dr_groupid = dr_groupid
        self.cost = cost

    pass


class dSIPMultiDomainMapping(object):
    """
    Schema for Multi-Tenant PBX\n
    Mapped to db table: dsip_multidomain_mapping
    """

    class FLAGS(Enum):
        DOMAIN_DISABLED = 0
        DOMAIN_ENABLED = 1
        TYPE_UNKNOWN = 0
        TYPE_FUSIONPBX = 1
        TYPE_FUSIONPBX_CLUSTER = 2
        TYPE_FREEPBX = 3

    def __init__(self, pbx_id, db_host, db_username, db_password, domain_list=None, attr_list=None, type=0, enabled=1):
        self.pbx_id = pbx_id
        self.db_host = db_host
        self.db_username = db_username
        self.db_password = db_password
        self.domain_list = ",".join(str(domain_id) for domain_id in domain_list) if domain_list else ''
        self.attr_list = ",".join(str(attr_id) for attr_id in attr_list) if attr_list else ''
        self.type = type
        self.enabled = enabled

    pass


class dSIPDomainMapping(object):
    """
    Schema for Single-Tenant PBX domain mapping\n
    Mapped to db table: dsip_domain_mapping
    """

    class FLAGS(Enum):
        DOMAIN_DISABLED = 0
        DOMAIN_ENABLED = 1
        TYPE_UNKNOWN = 0
        TYPE_ASTERISK = 1
        TYPE_SIPFOUNDRY = 2
        TYPE_ELASTIX = 3
        TYPE_FREESWITCH = 4
        TYPE_OPENPBX = 5
        TYPE_FREEPBX = 6
        TYPE_PBXINAFLASH = 7
        TYPE_3CX = 8

    def __init__(self, pbx_id, domain_id, attr_list, type=0, enabled=1):
        self.pbx_id = pbx_id
        self.domain_id = domain_id
        self.attr_list = ",".join(str(attr_id) for attr_id in attr_list)
        self.type = type
        self.enabled = enabled

    pass


class Subscribers(object):
    """
    Schema for subscriber table\n
    Documentation: `subscriber table <https://kamailio.org/docs/db-tables/kamailio-db-5.5.x.html#gen-db-subscriber>`_
    """

    def __init__(self, username, password, domain, gwid, email_address=None):
        self.username = username
        self.password = password
        self.domain = domain
        self.ha1 = ''
        self.ha1b = ''
        self.rpid = gwid
        self.email_address = email_address

    pass


class dSIPLeases(object):
    """
    Schema for dsip_endpoint_leases table\n
    maintains a list of active leases based on seconds
    """

    def __init__(self, gwid, sid, ttl):
        self.gwid = gwid
        self.sid = sid
        t = datetime.now() + timedelta(seconds=ttl)
        self.expiration = t.strftime('%Y-%m-%d %H:%M:%S')

    pass


class dSIPMaintModes(object):
    """
    Schema for dsip_maintmode table\n
    maintains a list of endpoints and carriers that are in maintenance mode
    """

    def __init__(self, ipaddr, gwid, status=1):
        self.ipaddr = ipaddr
        self.gwid = gwid
        self.status = status
        self.createdate = datetime.now()

    pass


class dSIPCallSettings(object):
    """
    Schema for dsip_call_settings table\n
    """

    def __init__(self, gwgroupid, limit=None, timeout=None):
        self.gwgroupid = gwgroupid
        self.limit = limit
        self.timeout = timeout

    pass


class dSIPNotification(object):
    """
    Schema for dsip_notification table\n
    maintains the list of notifications
    """

    class FLAGS(Enum):
        METHOD_EMAIL = 0
        METHOD_SLACK = 1
        TYPE_OVERLIMIT = 0
        TYPE_GWFAILURE = 1

    def __init__(self, gwgroupid, type, method, value):
        self.gwgroupid = gwgroupid
        self.type = type
        self.method = method
        self.value = value
        self.createdate = datetime.now()

    pass


class dSIPHardFwd(object):
    """
    Schema for dsip_hardfwd table\n
    """

    def __init__(self, dr_ruleid, did, dr_groupid):
        self.dr_ruleid = dr_ruleid
        self.did = did
        self.dr_groupid = dr_groupid

    pass


class dSIPCDRInfo(object):
    """
    Schema for dsip_cdrinfo table\n
    """

    def __init__(self, gwgroupid, email, send_interval):
        self.gwgroupid = gwgroupid
        self.email = email
        self.send_interval = send_interval
        self.last_sent = datetime.now()

    pass


class dSIPFailFwd(object):
    """
    Schema for dsip_failfwd table\n
    """

    def __init__(self, dr_ruleid, did, dr_groupid):
        self.dr_ruleid = dr_ruleid
        self.did = did
        self.dr_groupid = dr_groupid

    pass


class dSIPCertificates(object):
    """
    Schema for dsip_certificates table\n
    """

    def __init__(self, domain, type, email, cert, key):
        self.domain = domain
        self.type = type
        self.email = email
        self.cert = cert
        self.key = key

    pass


class dSIPDNIDEnrichment(object):
    """
    Schema for dsip_dnid_enrich_lnp table\n
    """

    def __init__(self, dnid, country_code='', routing_number='', rule_name=''):
        description = {'name': rule_name}

        self.dnid = dnid
        self.country_code = country_code
        self.routing_number = routing_number
        self.description = dictToStrFields(description)

    pass


class UAC(object):
    """
    Schema for uacreg table\n
    Documentation: `uacreg table <https://kamailio.org/docs/db-tables/kamailio-db-5.5.x.html#gen-db-uacreg>`_
    """

    class FLAGS(Enum):
        REG_ENABLED = 0
        REG_DISABLED = 1
        REG_IN_PROGRESS = 2
        REG_SUCCEEDED = 4
        REG_IN_PROGRESS_AUTH = 8
        REG_INITIALIZED = 16

    def __init__(self, uuid, username="", password="", realm="", auth_username="", auth_proxy="", local_domain="", remote_domain="", flags=0):
        self.l_uuid = uuid
        self.l_username = username
        self.l_domain = local_domain
        self.r_username = encodeSipUser(username)
        self.auth_username = auth_username
        self.r_domain = remote_domain
        self.realm = realm
        self.auth_password = password
        self.auth_ha1 = ""
        self.auth_proxy = auth_proxy
        self.expires = 60
        self.flags = flags
        self.reg_delay = 0
        self.socket = ''

def uacMapperEventHandler(mapper, connection, target):
    target.r_username = encodeSipUser(target.r_username)

event.listen(UAC, 'before_insert', uacMapperEventHandler)
event.listen(UAC, 'before_update', uacMapperEventHandler)



class Domain(MappedTable, HookBeforeInsert, HookBeforeUpdate, HookBeforeDelete):
    """
    Schema for domain table\n
    Documentation: `domain table <https://kamailio.org/docs/db-tables/kamailio-db-devel.html>`_
    """

    id: Mapped[int] = mapped_column(UnsignedInt, primary_key=True)
    domain: Mapped[str] = mapped_column(VARCHAR(64), nullable=False)
    last_modified: Mapped[datetime] = mapped_column(DATETIME, nullable=False)
    did: Mapped[str] = mapped_column(VARCHAR(64))

    def _initialize(self) -> None:
        if self.domain is None:
            raise ValueError('domain can not be null')
        if self.did is None:
            self.did = self.domain
        if self.last_modified is None:
            self.last_modified = datetime.utcnow()

    def _beforeInsert(self) -> None:
        if self.domain == '':
            raise ValueError('empty string is an invalid domain')

    def _beforeUpdate(self) -> None:
        if self.domain == '':
            raise ValueError('empty string is an invalid domain')

    def _beforeDelete(self) -> None:
        pass


class DomainAttrs(object):
    """
    Schema for domain_attrs table\n
    Documentation: `domain_attrs table <https://kamailio.org/docs/db-tables/kamailio-db-5.5.x.html#gen-db-domain-attrs>`_
    """

    class FLAGS(Enum):
        TYPE_INTEGER = 0
        TYPE_STRING = 2

    def __init__(self, did, name="pbx_ip", type=2, value=None, last_modified=datetime.utcnow()):
        self.did = did
        self.name = name
        self.type = type
        self.last_modified = last_modified
        temp_value = value if value is not None else safeUriToHost(did)
        self.value = temp_value if temp_value is not None else did

    pass


class Dispatcher(object):
    """
    Schema for dispatcher table\n
    Documentation: `dispatcher table <https://kamailio.org/docs/db-tables/kamailio-db-5.5.x.html#gen-db-dispatcher>`_
    """

    DST_ALG = {
        'ROUND_ROBIN': 4,
        'PRIORITY_BASED': 8,
        'WEIGHT_BASED': 9,
        'LOAD_DISTRIBUTION': 10,
        'RELATIVE_WEIGHT': 11,
        'PARALLEL_FORKING': 12
    }
    FLAGS = {
        'INACTIVE_DST': 1,
        'TRYING_DST': 2,
        'DISABLED_DST': 4,
        'KEEP_ALIVE': 8,
        'SKIP_DNS': 16
    }

    # TODO: setting attrs directly will be removed in the future and each possible attribute identified
    def __init__(self, setid, destination, flags=None, priority=None, attrs=None, rweight=0, signalling='proxy', media='proxy',
                 name=None, gwid=None):
        self.setid = setid
        self.destination = safeFormatSipUri(destination)
        self.flags = flags
        self.priority = priority
        if attrs is not None:
            self.attrs = attrs
        else:
            self.attrs = Dispatcher.buildAttrs(rweight, signalling, media)
        self.description = Dispatcher.buildDescription(name, gwid)

    @staticmethod
    def buildAttrs(rweight=0, signalling='proxy', media='proxy'):
        attrs = {'signalling': signalling, 'media': media, 'rweight': str(rweight)}
        return dictToStrFields(attrs, delims=(';', '='))

    @staticmethod
    def buildDescription(name=None, gwid=None):
        description = {}
        if name is not None:
            description['name'] = name
        if gwid is not None:
            description['gwid'] = str(gwid)
        return dictToStrFields(description, delims=(';', '='))

    def attrsToDict(self):
        attrs = {}
        for attr in self.attrs.split(';'):
            attr = attr.split('=', maxsplit=1)
            if len(attr) != 2 or attr[1] == '':
                continue
            if attr[1].isnumeric():
                attrs[attr[0]] = int(attr[1])
            else:
                attrs[attr[0]] = attr[1]
        return attrs


# TODO: create class for dsip_settings table

class dSIPUser(object):
    """
    Schema for the dSIPROuter User table
    """

    def __init__(self, firstname, lastname, username, password, roles, domains, token, token_expiration):
        self.firstname = firstname
        self.lastname = lastname
        self.username = username
        self.password = password
        self.roles = roles
        self.domains = domains
        self.token = token
        self.token_expiration = token_expiration

    pass


# TODO: this is temporary and will be refactored
class DsipGwgroup2LB(object):
    pass
