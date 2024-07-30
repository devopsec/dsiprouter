# make sure the generated source files are imported instead of the template ones
import sys

if sys.path[0] != '/etc/dsiprouter/gui':
    sys.path.insert(0, '/etc/dsiprouter/gui')

import inspect, os
from sqlalchemy import create_engine, exc as sql_exceptions
import settings
from shared import IO, debugException
from util.security import AES_CTR
from .constants import DB_ENGINE_NAME


# TODO: switch to sqlalchemy.engine.URL API
def createDBURI(db_driver=None, db_type=None, db_user=None, db_pass=None, db_host=None, db_port=None, db_name=None, db_charset='utf8mb4'):
    """
    Get any and all DB Connection URI's
    Facilitates HA DB Server connections through multiple host's defined in settings
    :return:    list of DB URI connection strings
    """
    uri_list = []

    # URI is built from the following by order of precedence:
    # 1: function arguments
    # 2: environment variables (debug mode only)
    # 3: settings file
    if db_driver is None:
        db_driver = os.getenv('KAM_DB_DRIVER', settings.KAM_DB_DRIVER) if settings.DEBUG else settings.KAM_DB_DRIVER
    if db_type is None:
        db_type = os.getenv('KAM_DB_TYPE', settings.KAM_DB_TYPE) if settings.DEBUG else settings.KAM_DB_TYPE
    if db_user is None:
        db_user = os.getenv('KAM_DB_USER', settings.KAM_DB_USER) if settings.DEBUG else settings.KAM_DB_USER
    if db_pass is None:
        db_pass = os.getenv('KAM_DB_PASS', settings.KAM_DB_PASS) if settings.DEBUG else settings.KAM_DB_PASS
    if db_host is None:
        db_host = os.getenv('KAM_DB_HOST', settings.KAM_DB_HOST) if settings.DEBUG else settings.KAM_DB_HOST
    if db_port is None:
        db_port = os.getenv('KAM_DB_PORT', settings.KAM_DB_PORT) if settings.DEBUG else settings.KAM_DB_PORT
    if db_name is None:
        db_name = os.getenv('KAM_DB_NAME', settings.KAM_DB_NAME) if settings.DEBUG else settings.KAM_DB_NAME

    # need to decrypt password
    if isinstance(db_pass, bytes):
        db_pass = AES_CTR.decrypt(db_pass)
    # formatting for driver
    if len(db_driver) > 0:
        db_driver = '+{}'.format(db_driver)
    # string template
    db_uri_str = db_type + db_driver + "://" + db_user + ":" + db_pass + "@" + "{host}" + ":" + db_port + "/" + db_name + "?charset=" + db_charset
    # for cluster of DB add all hosts
    if isinstance(db_host, list):
        for host in db_host:
            uri_list.append(db_uri_str.format(host=host))
    else:
        uri_list.append(db_uri_str.format(host=db_host))

    if settings.DEBUG:
        IO.printdbg('createDBURI() returned: [{}]'.format(','.join('"{0}"'.format(uri) for uri in uri_list)))

    return uri_list


def createValidEngine(uri_list):
    """
    Create DB engine if connection is valid
    Attempts each uri in the list until a valid connection is made
    This method uses a singleton pattern and returns db_engine if created

    :param uri_list:    list of connection uri's
    :return:            DB engine object
    :raise:             SQLAlchemyError if all connections fail
    """

    # globals from the top-level module
    caller_globals = dict(inspect.getmembers(inspect.stack()[-1][0]))["f_globals"]

    if DB_ENGINE_NAME in caller_globals:
        return caller_globals[DB_ENGINE_NAME]

    errors = []

    for conn_uri in uri_list:
        try:
            db_engine = create_engine(conn_uri,
                echo=settings.DEBUG,
                echo_pool=settings.DEBUG,
                pool_recycle=300,
                pool_size=10,
                isolation_level="READ UNCOMMITTED",
                connect_args={"connect_timeout": 5})
            # test connection
            _ = db_engine.connect()
            # conn good return it
            return db_engine
        except Exception as ex:
            errors.append(ex)

    # we failed to return good connection raise exceptions
    if settings.DEBUG:
        for ex in errors:
            debugException(ex)

    try:
        raise sql_exceptions.SQLAlchemyError(errors)
    except:
        raise Exception(errors)
