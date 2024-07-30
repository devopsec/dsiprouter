# make sure the generated source files are imported instead of the template ones
import sys

if sys.path[0] != '/etc/dsiprouter/gui':
    sys.path.insert(0, '/etc/dsiprouter/gui')

from sqlalchemy import Integer
import settings
from shared import debugException

# DB specific settings
if settings.KAM_DB_TYPE == "mysql":
    try:
        import MySQLdb as db_driver
    except ImportError:
        try:
            import _mysql as db_driver
        except ImportError:
            try:
                import pymysql as db_driver
            except ImportError:
                raise
            except Exception as ex:
                if settings.DEBUG:
                    debugException(ex)
                raise

    from sqlalchemy.dialects.mysql import INTEGER
    UnsignedInt = Integer().with_variant(INTEGER(unsigned=True), 'mysql', 'mariadb')
else:
    UnsignedInt = Integer()
