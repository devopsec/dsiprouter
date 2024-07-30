import abc
from typing import Dict, Tuple
from sqlalchemy import Table, Column
from sqlalchemy.orm import ClassManager as SAClassManager, InstanceState as SAInstanceState, Mapper


class MappedTable(object, metaclass=abc.ABCMeta):
    _sa_class_manager: SAClassManager
    _sa_instance_state: SAInstanceState
    __mapper__: Mapper
    __table__: Table

    def __init__(self, *args: Tuple, **kwargs: Dict) -> None:
        for col, val in zip(self.__class__.__mapper__.columns, args):
            if isinstance(col, Column):
                kwargs[col.name] = val
            else:
                kwargs[col] = val
        for col, val in kwargs.items():
            setattr(self, col, val)
        self._initialize()

    @abc.abstractmethod
    def _initialize(self) -> None:
        pass

class HookBeforeInsert(object, metaclass=abc.ABCMeta):
    __mapper__: Mapper

    @abc.abstractmethod
    def _beforeInsert(self) -> None:
        pass

class HookBeforeUpdate(object, metaclass=abc.ABCMeta):
    __mapper__: Mapper

    @abc.abstractmethod
    def _beforeUpdate(self) -> None:
        pass

class HookBeforeDelete(object, metaclass=abc.ABCMeta):
    __mapper__: Mapper

    @abc.abstractmethod
    def _beforeDelete(self) -> None:
        pass
