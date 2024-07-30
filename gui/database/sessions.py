import inspect
from typing import Tuple
from sqlalchemy import MetaData, Table, event, Engine
from sqlalchemy.orm import registry, sessionmaker, scoped_session, Session
from .constants import SESSION_LOADER_NAME, DB_ENGINE_NAME
from .events import ormExecuteEventHandler, ormFlushEventHandler
from .engine import createValidEngine, createDBURI
from .models import Address, Dispatcher, Domain, DomainAttrs, DsipGwgroup2LB, GatewayGroups, Gateways, InboundMapping, OutboundRoutes, Subscribers, \
    UAC, dSIPCDRInfo, dSIPCallSettings, dSIPCertificates, dSIPDNIDEnrichment, dSIPDomainMapping, dSIPFailFwd, dSIPHardFwd, dSIPLCR, dSIPLeases, \
    dSIPMaintModes, dSIPMultiDomainMapping, dSIPNotification, dSIPUser


def startSession() -> Session:
    """
    This method uses a singleton pattern to grab the global session loader and start a session
    """

    # globals from the top-level module
    caller_globals = dict(inspect.getmembers(inspect.stack()[-1][0]))["f_globals"]

    if SESSION_LOADER_NAME in caller_globals:
        return caller_globals[SESSION_LOADER_NAME]()

    db_engine, session_loader = createSessionObjects()
    return session_loader()


def createSessionObjects() -> Tuple[Engine, scoped_session[Session]]:
    """
    Create the DB engine and session factory

    :return:    Session factory and DB Engine
    :rtype:     (:class:`sqlalchemy.orm.Session`,:class:`sqlalchemy.engine.Engine`)
    """

    db_engine = createValidEngine(createDBURI())

    mapper = registry(metadata=MetaData(schema=db_engine.url.database))

    dr_gateways = Table('dr_gateways', mapper.metadata, autoload_replace=True, autoload_with=db_engine)
    address = Table('address', mapper.metadata, autoload_replace=True, autoload_with=db_engine)
    outboundroutes = Table('dr_rules', mapper.metadata, autoload_replace=True, autoload_with=db_engine)
    inboundmapping = Table('dr_rules', mapper.metadata, autoload_replace=True, autoload_with=db_engine)
    subscriber = Table('subscriber', mapper.metadata, autoload_replace=True, autoload_with=db_engine)
    dsip_domain_mapping = Table('dsip_domain_mapping', mapper.metadata, autoload_replace=True, autoload_with=db_engine)
    dsip_multidomain_mapping = Table('dsip_multidomain_mapping', mapper.metadata, autoload_replace=True, autoload_with=db_engine)
    # fusionpbx_mappings = Table('dsip_fusionpbx_mappings', mapper.metadata, autoload_replace=True, autoload_with=db_engine)
    dsip_lcr = Table('dsip_lcr', mapper.metadata, autoload_replace=True, autoload_with=db_engine)
    uacreg = Table('uacreg', mapper.metadata, autoload_replace=True, autoload_with=db_engine)
    dr_gw_lists = Table('dr_gw_lists', mapper.metadata, autoload_replace=True, autoload_with=db_engine)
    # dr_groups = Table('dr_groups', mapper.metadata, autoload_replace=True, autoload_with=db_engine)
    domain = Table('domain', mapper.metadata, autoload_replace=True, autoload_with=db_engine)
    domain_attrs = Table('domain_attrs', mapper.metadata, autoload_replace=True, autoload_with=db_engine)
    dispatcher = Table('dispatcher', mapper.metadata, autoload_replace=True, autoload_with=db_engine)
    dsip_endpoint_lease = Table('dsip_endpoint_lease', mapper.metadata, autoload_replace=True, autoload_with=db_engine)
    dsip_maintmode = Table('dsip_maintmode', mapper.metadata, autoload_replace=True, autoload_with=db_engine)
    dsip_call_settings = Table('dsip_call_settings', mapper.metadata, autoload_replace=True, autoload_with=db_engine)
    dsip_notification = Table('dsip_notification', mapper.metadata, autoload_replace=True, autoload_with=db_engine)
    dsip_hardfwd = Table('dsip_hardfwd', mapper.metadata, autoload_replace=True, autoload_with=db_engine)
    dsip_failfwd = Table('dsip_failfwd', mapper.metadata, autoload_replace=True, autoload_with=db_engine)
    dsip_cdrinfo = Table('dsip_cdrinfo', mapper.metadata, autoload_replace=True, autoload_with=db_engine)
    dsip_certificates = Table('dsip_certificates', mapper.metadata, autoload_replace=True, autoload_with=db_engine)
    dsip_dnid_enrichment = Table('dsip_dnid_enrich_lnp', mapper.metadata, autoload_replace=True, autoload_with=db_engine)
    dsip_user = Table('dsip_user', mapper.metadata, autoload_replace=True, autoload_with=db_engine)
    # TODO: this is temporary and will be refactored
    dsip_gwgroup2lb = Table('dsip_gwgroup2lb', mapper.metadata, autoload_replace=True, autoload_with=db_engine)

    # dr_gw_lists_alias = select([
    #     dr_gw_lists.c.id.label("drlist_id"),
    #     dr_gw_lists.c.gwlist,
    #     dr_gw_lists.c.description.label("drlist_description"),
    # ]).correlate(None).alias()
    # gw_join = join(dr_gw_lists_alias, dr_groups,
    #                dr_gw_lists_alias.c.drlist_id == dr_groups.c.id,
    #                dr_gw_lists_alias.c.drlist_description == dr_groups.c.description)

    mapper.map_imperatively(Gateways, dr_gateways)
    mapper.map_imperatively(Address, address)
    mapper.map_imperatively(InboundMapping, inboundmapping)
    mapper.map_imperatively(OutboundRoutes, outboundroutes)
    mapper.map_imperatively(dSIPDomainMapping, dsip_domain_mapping)
    mapper.map_imperatively(dSIPMultiDomainMapping, dsip_multidomain_mapping)
    mapper.map_imperatively(Subscribers, subscriber)
    # mapper.map_imperatively(CustomRouting, customrouting)
    mapper.map_imperatively(dSIPLCR, dsip_lcr)
    mapper.map_imperatively(UAC, uacreg)
    mapper.map_imperatively(GatewayGroups, dr_gw_lists)
    mapper.map_imperatively(Domain, domain)
    mapper.map_imperatively(DomainAttrs, domain_attrs)
    mapper.map_imperatively(Dispatcher, dispatcher)
    mapper.map_imperatively(dSIPLeases, dsip_endpoint_lease)
    mapper.map_imperatively(dSIPMaintModes, dsip_maintmode)
    mapper.map_imperatively(dSIPCallSettings, dsip_call_settings)
    mapper.map_imperatively(dSIPNotification, dsip_notification)
    mapper.map_imperatively(dSIPHardFwd, dsip_hardfwd)
    mapper.map_imperatively(dSIPFailFwd, dsip_failfwd)
    mapper.map_imperatively(dSIPCDRInfo, dsip_cdrinfo)
    mapper.map_imperatively(dSIPCertificates, dsip_certificates)
    mapper.map_imperatively(dSIPDNIDEnrichment, dsip_dnid_enrichment)
    mapper.map_imperatively(dSIPUser, dsip_user)
    # TODO: this is temporary and will be refactored
    mapper.map_imperatively(DsipGwgroup2LB, dsip_gwgroup2lb)

    # mapper.map_imperatively(GatewayGroups, gw_join, properties={
    #     'id': [dr_groups.c.id, dr_gw_lists_alias.c.drlist_id],
    #     'description': [dr_groups.c.description, dr_gw_lists_alias.c.drlist_description],
    # })

    session_loader = scoped_session(sessionmaker(bind=db_engine))

    # map the table level event handlers to the session event handlers
    event.listen(session_loader, 'before_flush', ormFlushEventHandler)
    event.listen(session_loader, 'do_orm_execute', ormExecuteEventHandler)

    # load them into the top level module global namespace
    caller_globals = dict(inspect.getmembers(inspect.stack()[-1][0]))["f_globals"]
    caller_globals[DB_ENGINE_NAME] = db_engine
    caller_globals[SESSION_LOADER_NAME] = session_loader

    # return references for the calling function
    return caller_globals[DB_ENGINE_NAME], caller_globals[SESSION_LOADER_NAME]


# TODO: change to the global define pattern instead of instantiating dummy objects
class DummySession():
    """
    Sole purpose is to avoid exceptions when startSession fails
    This allows us to handle exceptions later in the try blocks
    We also avoid exceptions in the except blocks by using dummy sesh
    """

    @staticmethod
    def __contains__(self, *args, **kwargs):
        pass

    def __iter__(self, *args, **kwargs):
        pass

    def add(self, *args, **kwargs):
        pass

    def add_all(self, *args, **kwargs):
        pass

    def begin(self, *args, **kwargs):
        pass

    def begin_nested(self, *args, **kwargs):
        pass

    def close(self, *args, **kwargs):
        pass

    def commit(self, *args, **kwargs):
        pass

    def connection(self, *args, **kwargs):
        pass

    def delete(self, *args, **kwargs):
        pass

    def execute(self, *args, **kwargs):
        pass

    def expire(self, *args, **kwargs):
        pass

    def expire_all(self, *args, **kwargs):
        pass

    def expunge(self, *args, **kwargs):
        pass

    def expunge_all(self, *args, **kwargs):
        pass

    def flush(self, *args, **kwargs):
        pass

    def get_bind(self, *args, **kwargs):
        pass

    def is_modified(self, *args, **kwargs):
        pass

    def bulk_save_objects(self, *args, **kwargs):
        pass

    def bulk_insert_mappings(self, *args, **kwargs):
        pass

    def bulk_update_mappings(self, *args, **kwargs):
        pass

    def merge(self, *args, **kwargs):
        pass

    def query(self, *args, **kwargs):
        pass

    def refresh(self, *args, **kwargs):
        pass

    def rollback(self, *args, **kwargs):
        pass

    def scalar(self, *args, **kwargs):
        pass

    def remove(self, *args, **kwargs):
        pass

    def configure(self, *args, **kwargs):
        pass

    def query_property(self, *args, **kwargs):
        pass
