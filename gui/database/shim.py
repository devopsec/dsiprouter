# make sure the generated source files are imported instead of the template ones
import sys

if sys.path[0] != '/etc/dsiprouter/gui':
    sys.path.insert(0, '/etc/dsiprouter/gui')

import base64, bson
from collections import OrderedDict
from sqlalchemy import exc as sql_exceptions, text
import settings
from shared import rowToDict, objToDict
from .sessions import startSession, DummySession


# TODO: needs refactoring into the same model formats we use for the rest of the tables
class DsipSettings(OrderedDict):
    """
    Identifies the contained data as already formatted for the table
    """
    pass

def settingsToTableFormat(settings, updates=None):
    data = objToDict(settings)
    if updates is not None:
        data.update(updates)

    # translate db specific fields
    if isinstance(data['KAM_DB_HOST'], (list, tuple)):
        data['KAM_DB_HOST'] = ','.join(data['KAM_DB_HOST'])
    data['DSIP_LICENSE_STORE'] = base64.b64encode(bson.dumps(data['DSIP_LICENSE_STORE']))

    # order matters here, as this is used to update table settings as well
    return DsipSettings([
        ('DSIP_ID', data['DSIP_ID']),
        ('DSIP_CLUSTER_ID', data['DSIP_CLUSTER_ID']),
        ('DSIP_CLUSTER_SYNC', data['DSIP_CLUSTER_SYNC']),
        ('DSIP_PROTO', data['DSIP_PROTO']),
        ('DSIP_PORT', data['DSIP_PORT']),
        ('DSIP_USERNAME', data['DSIP_USERNAME']),
        ('DSIP_PASSWORD', data['DSIP_PASSWORD']),
        ('DSIP_IPC_PASS', data['DSIP_IPC_PASS']),
        ('DSIP_API_PROTO', data['DSIP_API_PROTO']),
        ('DSIP_API_PORT', data['DSIP_API_PORT']),
        ('DSIP_PRIV_KEY', data['DSIP_PRIV_KEY']),
        ('DSIP_PID_FILE', data['DSIP_PID_FILE']),
        ('DSIP_UNIX_SOCK', data['DSIP_UNIX_SOCK']),
        ('DSIP_IPC_SOCK', data['DSIP_IPC_SOCK']),
        ('DSIP_API_TOKEN', data['DSIP_API_TOKEN']),
        ('DSIP_LOG_LEVEL', data['DSIP_LOG_LEVEL']),
        ('DSIP_LOG_FACILITY', data['DSIP_LOG_FACILITY']),
        ('DSIP_SSL_KEY', data['DSIP_SSL_KEY']),
        ('DSIP_SSL_CERT', data['DSIP_SSL_CERT']),
        ('DSIP_SSL_CA', data['DSIP_SSL_CA']),
        ('DSIP_SSL_EMAIL', data['DSIP_SSL_EMAIL']),
        ('DSIP_CERTS_DIR', data['DSIP_CERTS_DIR']),
        ('VERSION', data['VERSION']),
        ('DEBUG', data['DEBUG']),
        ('ROLE', data['ROLE']),
        ('GUI_INACTIVE_TIMEOUT', data['GUI_INACTIVE_TIMEOUT']),
        ('KAM_DB_HOST', data['KAM_DB_HOST']),
        ('KAM_DB_DRIVER', data['KAM_DB_DRIVER']),
        ('KAM_DB_TYPE', data['KAM_DB_TYPE']),
        ('KAM_DB_PORT', data['KAM_DB_PORT']),
        ('KAM_DB_NAME', data['KAM_DB_NAME']),
        ('KAM_DB_USER', data['KAM_DB_USER']),
        ('KAM_DB_PASS', data['KAM_DB_PASS']),
        ('KAM_KAMCMD_PATH', data['KAM_KAMCMD_PATH']),
        ('KAM_CFG_PATH', data['KAM_CFG_PATH']),
        ('KAM_TLSCFG_PATH', data['KAM_TLSCFG_PATH']),
        ('RTP_CFG_PATH', data['RTP_CFG_PATH']),
        ('FLT_CARRIER', data['FLT_CARRIER']),
        ('FLT_PBX', data['FLT_PBX']),
        ('FLT_MSTEAMS', data['FLT_MSTEAMS']),
        ('FLT_OUTBOUND', data['FLT_OUTBOUND']),
        ('FLT_INBOUND', data['FLT_INBOUND']),
        ('FLT_LCR_MIN', data['FLT_LCR_MIN']),
        ('FLT_FWD_MIN', data['FLT_FWD_MIN']),
        ('DEFAULT_AUTH_DOMAIN', data['DEFAULT_AUTH_DOMAIN']),
        ('TELEBLOCK_GW_ENABLED', data['TELEBLOCK_GW_ENABLED']),
        ('TELEBLOCK_GW_IP', data['TELEBLOCK_GW_IP']),
        ('TELEBLOCK_GW_PORT', data['TELEBLOCK_GW_PORT']),
        ('TELEBLOCK_MEDIA_IP', data['TELEBLOCK_MEDIA_IP']),
        ('TELEBLOCK_MEDIA_PORT', data['TELEBLOCK_MEDIA_PORT']),
        ('FLOWROUTE_ACCESS_KEY', data['FLOWROUTE_ACCESS_KEY']),
        ('FLOWROUTE_SECRET_KEY', data['FLOWROUTE_SECRET_KEY']),
        ('FLOWROUTE_API_ROOT_URL', data['FLOWROUTE_API_ROOT_URL']),
        ('HOMER_ID', data['HOMER_ID']),
        ('HOMER_HEP_HOST', data['HOMER_HEP_HOST']),
        ('HOMER_HEP_PORT', data['HOMER_HEP_PORT']),
        ('NETWORK_MODE', data['NETWORK_MODE']),
        ('IPV6_ENABLED', data['IPV6_ENABLED']),
        ('INTERNAL_IP_ADDR', data['INTERNAL_IP_ADDR']),
        ('INTERNAL_IP_NET', data['INTERNAL_IP_NET']),
        ('INTERNAL_IP6_ADDR', data['INTERNAL_IP6_ADDR']),
        ('INTERNAL_IP6_NET', data['INTERNAL_IP6_NET']),
        ('INTERNAL_FQDN', data['INTERNAL_FQDN']),
        ('EXTERNAL_IP_ADDR', data['EXTERNAL_IP_ADDR']),
        ('EXTERNAL_IP6_ADDR', data['EXTERNAL_IP6_ADDR']),
        ('EXTERNAL_FQDN', data['EXTERNAL_FQDN']),
        ('PUBLIC_IFACE', data['PUBLIC_IFACE']),
        ('PRIVATE_IFACE', data['PRIVATE_IFACE']),
        ('UPLOAD_FOLDER', data['UPLOAD_FOLDER']),
        ('MAIL_SERVER', data['MAIL_SERVER']),
        ('MAIL_PORT', data['MAIL_PORT']),
        ('MAIL_USE_TLS', data['MAIL_USE_TLS']),
        ('MAIL_USERNAME', data['MAIL_USERNAME']),
        ('MAIL_PASSWORD', data['MAIL_PASSWORD']),
        ('MAIL_ASCII_ATTACHMENTS', data['MAIL_ASCII_ATTACHMENTS']),
        ('MAIL_DEFAULT_SENDER', data['MAIL_DEFAULT_SENDER']),
        ('MAIL_DEFAULT_SUBJECT', data['MAIL_DEFAULT_SUBJECT']),
        ('DSIP_LICENSE_STORE', data['DSIP_LICENSE_STORE']),
    ])


def settingsTableToDict(table_values, updates=None):
    if updates is not None:
        table_values.update(updates)

    if ',' in table_values['KAM_DB_HOST']:
        table_values['KAM_DB_HOST'] = table_values['KAM_DB_HOST'].split(',')
    table_values['DSIP_LICENSE_STORE'] = bson.loads(base64.b64decode(table_values['DSIP_LICENSE_STORE']))
    return table_values


def updateDsipSettingsTable(fields):
    """
    Update the dsip_settings table using our stored procedure

    :param fields:  columns/values to update
    :type fields:   dict
    :return:        None
    :rtype:         None
    :raises:        sql_exceptions.SQLAlchemyError
    """

    db = DummySession()
    try:
        if isinstance(fields, DsipSettings):
            db_fields = fields
        else:
            db_fields = settingsToTableFormat(settings, updates=fields)
        field_mapping = ', '.join([':{}'.format(x, x) for x in db_fields.keys()])

        db = startSession()
        db.execute(
            text('CALL update_dsip_settings({})'.format(field_mapping)),
            params=db_fields
        )
        db.commit()
    except sql_exceptions.SQLAlchemyError:
        db.rollback()
        db.flush()
        raise
    finally:
        db.close()


def getDsipSettingsTableAsDict(dsip_id, updates=None):
    db = DummySession()
    try:
        db = startSession()
        data = rowToDict(
            db.execute(
                text('SELECT * FROM dsip_settings WHERE DSIP_ID=:dsip_id'),
                params={'dsip_id': dsip_id}
            ).first()
        )
        # translate db specific fields
        return settingsTableToDict(data, updates=updates)
    except sql_exceptions.SQLAlchemyError:
        raise
    finally:
        db.close()
