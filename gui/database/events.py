# make sure the generated source files are imported instead of the template ones
import sys

if sys.path[0] != '/etc/dsiprouter/gui':
    sys.path.insert(0, '/etc/dsiprouter/gui')

import contextlib, functools
from typing import Union, Dict, Type
from sqlalchemy import bindparam, select, Update as UpdateDML, Insert as InsertDML, Delete as DeleteDML
from sqlalchemy.orm import ORMExecuteState, Session
from shared import rowToDict
from .orm import MappedTable, HookBeforeInsert, HookBeforeUpdate, HookBeforeDelete

class PausableEvent(object):
    """
    Context wrapper for a pausable sqlalchemy event

    Basic test case:

    .. code-block:: python

        @PausableEvent
        def event1(*arg, **kwargs):
            print('event1 executed')
        @PausableEvent(namespace='event')
        def event2(*args, **kwargs):
            print('event2 executed')
        def event3(*args, **kwargs):
            print('event3 executed')

        def y():
            print('should run')
        def n():
            print('should not run')

        y()
        event1(1)
        y()
        event2(2)
        y()
        event3(3)

        with PausableEvent.pause():
            n()
            event1()
            y()
            event2()
            y()
            event3()

        with PausableEvent.pause(namespace='event'):
            y()
            event1()
            n()
            event2()
            y()
            event3()
    """

    pause_state: Dict[str, int] = {}

    def __new__(cls, event_fn=None, *, namespace='all'):
        if event_fn is None:
            return lambda fn: (
                obj := cls.__new__(cls, event_fn=fn, namespace=namespace),
                cls.__init__(obj, event_fn=fn, namespace=namespace),
                obj
            )[-1]
        return super(PausableEvent, cls).__new__(cls)

    def __init__(self, event_fn, *, namespace='all'):
        self.event_fn = event_fn
        self.namespace = namespace
        self.__class__.pause_state[namespace] = False
        functools.update_wrapper(self, event_fn)

    def __call__(self, *args, **kwargs):
        if self.__class__.pause_state[self.namespace]:
            return None
        return self.event_fn(*args, **kwargs)

    @classmethod
    @contextlib.contextmanager
    def pause(cls, namespace='all'):
        cls.pause_state[namespace] = True
        yield None
        cls.pause_state[namespace] = False

@PausableEvent
def ormExecuteEventHandler(orm_execute_state: ORMExecuteState):
    # we only handle hooking into ORM statements
    if not orm_execute_state.is_orm_statement:
        return None
    # we only handle INSERT, UPDATE, and DELETE statements
    if not any((orm_execute_state.is_insert, orm_execute_state.is_update, orm_execute_state.is_delete)):
        return None

    # noinspection PyTypeChecker
    stmnt: Union[InsertDML, UpdateDML, DeleteDML] = orm_execute_state.statement
    sesh: Session = orm_execute_state.session
    mapped_class: Type[MappedTable] = stmnt.entity_description['type']

    if orm_execute_state.is_insert and issubclass(mapped_class, HookBeforeInsert):
        if stmnt._values is not None:
            kwargs = {
                column.name: bind.value for column, bind in stmnt._values.items()
            }

            mapped_table = mapped_class(**kwargs)
            mapped_table._beforeInsert()

            stmnt._values = None
            orm_execute_state.statement = stmnt.values(rowToDict(mapped_table))

        if len(stmnt._multi_values) > 0:
            kwargs_list = [
                {column.name: value} \
                for statement_values in stmnt._multi_values \
                for statement_dict in statement_values \
                for column, value in statement_dict.items()
            ]

            statement_values_list = []
            for kwargs in kwargs_list:
                mapped_table = mapped_class(**kwargs)
                mapped_table._beforeInsert()
                statement_values_list.append(rowToDict(mapped_table))

            stmnt._multi_parameters = tuple()
            orm_execute_state.statement = stmnt.values(statement_values_list)

        if stmnt._select_names is not None:
            with PausableEvent.pause():
                kwargs_list = []
                for sqla_row in sesh.execute(stmnt.select).all():
                    kwargs = {}
                    i = 0
                    for sqla_col in sqla_row:
                        if hasattr(sqla_col, '_sa_instance_state'):
                            kwargs.update(rowToDict(sqla_col))
                        else:
                            kwargs[stmnt._select_names[i]] = sqla_col
                        i += 1
                    kwargs_list.append(kwargs)

            statement_values_list = []
            for kwargs in kwargs_list:
                mapped_table = mapped_class(**kwargs)
                mapped_table._beforeInsert()
                statement_values_list.append(rowToDict(mapped_table))

            stmnt._select_names = None
            stmnt.select = None
            orm_execute_state.statement = stmnt.values(statement_values_list)

    elif orm_execute_state.is_update and issubclass(mapped_class, HookBeforeUpdate):
        if stmnt._ordered_values is not None:
            kwargs = {
                column.name: bind.value for column, bind in stmnt._ordered_values
            }

            with PausableEvent.pause():
                kwargs_list = []
                for mapped_table in sesh.scalars(
                    select(
                        mapped_class
                    ).where(
                        stmnt.whereclause
                    )
                ).all():
                    for column, value in kwargs.items():
                        setattr(mapped_table, column, value)
                    mapped_table._beforeUpdate()
                    kwargs_list.append(rowToDict(mapped_table))

            stmnt._where_criteria = tuple()
            stmnt._ordered_values = None
            for pkey_col in mapped_class.__mapper__.primary_key:
                stmnt = stmnt.where(getattr(mapped_class, pkey_col.name) == bindparam(pkey_col.name))
            stmnt = stmnt.values({
                data_col.name: bindparam(data_col.name) for data_col in
                (set(mapped_class.__mapper__.columns) - set(mapped_class.__mapper__.primary_key))
            })
            orm_execute_state.statement = stmnt
            orm_execute_state.parameters = kwargs_list

        if stmnt._values is not None:
            kwargs = {
                column.name: bind.value for column, bind in stmnt._values.items()
            }

            with PausableEvent.pause():
                kwargs_list = []
                for mapped_table in sesh.scalars(
                    select(
                        mapped_class
                    ).where(
                        stmnt.whereclause
                    )
                ).all():
                    for column, value in kwargs.items():
                        setattr(mapped_table, column, value)
                    mapped_table._beforeUpdate()
                    kwargs_list.append(rowToDict(mapped_table))

            stmnt._where_criteria = tuple()
            stmnt._values = None
            for pkey_col in mapped_class.__mapper__.primary_key:
                stmnt = stmnt.where(getattr(mapped_class, pkey_col.name) == bindparam(pkey_col.name))
            stmnt = stmnt.values({
                data_col.name: bindparam(data_col.name) for data_col in
                (set(mapped_class.__mapper__.columns) - set(mapped_class.__mapper__.primary_key))
            })
            orm_execute_state.statement = stmnt
            orm_execute_state.parameters = kwargs_list

        if len(stmnt._multi_values) > 0:
            kwargs_list = [
                {column.name: value} \
                for statement_values in stmnt._multi_values \
                for statement_dict in statement_values \
                for column, value in statement_dict.items()
            ]

            with PausableEvent.pause():
                statement_parameters_list = []
                for mapped_table, kwargs in zip(
                    sesh.scalars(select(mapped_class).where(stmnt.whereclause)).all(),
                    kwargs_list
                ):
                    for column, value in kwargs.items():
                        setattr(mapped_table, column, value)
                    mapped_table._beforeUpdate()
                    kwargs_list.append(rowToDict(mapped_table))
                    statement_parameters_list.append(rowToDict(mapped_table))

            stmnt._where_criteria = tuple()
            stmnt._multi_values = tuple()
            for pkey_col in mapped_class.__mapper__.primary_key:
                stmnt = stmnt.where(getattr(mapped_class, pkey_col.name) == bindparam(pkey_col.name))
            stmnt = stmnt.values({
                data_col.name: bindparam(data_col.name) for data_col in
                (set(mapped_class.__mapper__.columns) - set(mapped_class.__mapper__.primary_key))
            })
            orm_execute_state.statement = stmnt
            orm_execute_state.parameters = statement_parameters_list

    elif orm_execute_state.is_delete and issubclass(mapped_class, HookBeforeDelete):
        with PausableEvent.pause():
            for mapped_table in sesh.scalars(
                select(
                    mapped_class
                ).where(
                    stmnt.whereclause
                )
            ).all():
                mapped_table._beforeDelete()

@PausableEvent
def ormFlushEventHandler(session: Session, flush_context, instances):
    for mapped_table in session.new:
        if isinstance(mapped_table, HookBeforeInsert):
            mapped_table._beforeInsert()

    for mapped_table in session.dirty:
        if isinstance(mapped_table, HookBeforeUpdate):
            mapped_table._beforeUpdate()

    for mapped_table in session.deleted:
        if isinstance(mapped_table, HookBeforeDelete):
            mapped_table._beforeDelete()
