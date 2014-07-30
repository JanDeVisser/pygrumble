import sys

from PySide.QtCore import QAbstractListModel
from PySide.QtCore import QAbstractTableModel
from PySide.QtCore import QModelIndex
from PySide.QtCore import Qt


import gripe
import gripe.db

logger = gripe.get_logger(__name__)

class TableColumn(object):
    def __init__(self, name, **kwargs):
        self.name = name
        for (n,v) in kwargs.items():
            setattr(self, n, v)
            
    def get_header(self):
        return self.header if hasattr(self, "header") else self.prop.verbose_name
    
    def get_format(self):
        return self.format if hasattr(self, "format") else "s"
    
    def get_value(self, instance):
        if callable(self):
            val = self(instance)
        else:
            val = self.value(instance) \
                if hasattr(self, "value") \
                else getattr(instance, self.name)
        fmt = "{:" + self.get_format() + "}" 
        return fmt.format(val) if val is not None else ''

class TableModel(QAbstractTableModel):
    def __init__(self, query, *args):
        super(TableModel, self).__init__()
        self._query = query
        self._kind = query.get_kind()
        self._columns = self._get_column_defs(args)
        self._data = None
        
    def _get_column_defs(self, *args):
        ret = []
        for arg in args:
            if isinstance(arg, (list, tuple)):
                ret.extend(self._get_column_defs(*arg))
            else:
                if isinstance(arg, TableColumn):
                    col = arg
                else:
                    col = TableColumn(str(arg))
                col.prop = getattr(self._kind, col.name)
                col.kind = self._kind
                ret.append(col)
        return ret
                
    def add_columns(self, *args):
        self._columns.extend(self._get_column_defs(args))
        
    def rowCount(self, parent = QModelIndex()):
        ret = len(self._data) if self._data is not None else self._query.count()
        #logger.debug("TableModel.rowCount() = %s (%squeried)", ret,
        #             "not " if self._data is not None else "")
        return ret

    def columnCount(self, parent = QModelIndex()):
        #logger.debug("TableModel.columnCount()")
        return len(self._columns)

    def headerData(self, col, orientation, role):
        #logger.debug("TableModel.headerData(%s,%s,%s)", col, orientation, role)
        return self._columns[col].get_header() \
            if orientation == Qt.Horizontal and role == Qt.DisplayRole \
            else None

    def _get_data(self, ix):
        if self._data is None:
            #logger.debug("TableModel._get_data(%s) -> query", ix)
            with gripe.db.Tx.begin():
                self._data = [o for o in self._query]
        return self._data[ix]

    def data(self, index, role = Qt.DisplayRole):
        if role == Qt.DisplayRole:
            instance = self._get_data(index.row())
            col = self._columns[index.column()]
            ret = col.get_value(instance)
            #logger.debug("TableModel.data(%s,%s) = %s", index.row(), index.column(), ret)
            return ret
        elif role == Qt.UserRole:
            r = self._get_data(index.row())
            return r.key()
        else:
            return None
        
    def flush(self):
        #logger.debug("TableModel.flush()")
        self.beginResetModel()
        self.layoutAboutToBeChanged.emit()
        self._data = None
        self.layoutChanged.emit()
        self.endResetModel()

    def sort(self, colnum, order):
        """
            Sort table by given column number.
        """
        #logger.debug("TableModel.sort(%s)", colnum)
        self.layoutAboutToBeChanged.emit()
        self._data = None
        self._query.clear_sort()
        self._query.add_sort(self._columns[colnum].name, order == Qt.AscendingOrder)
        self.layoutChanged.emit()


class ListModel(QAbstractListModel):
    def __init__(self, query, display_column):
        QAbstractListModel.__init__(self)
        self._query = query
        self._query.add_sort(display_column, True)
        self._column_name = display_column
        self._data = None

    def rowCount(self, parent = QModelIndex()):
        if self._data:
            return len(self._data)
        else:
            return self._query.count()

    def headerData(self, section, orientation, role):
        return self._display_column.verbose_name \
            if orientation == Qt.Horizontal and role == Qt.DisplayRole \
            else None

    def _get_data(self, ix):
        if not self._data:
            self._data = []
            with gripe.db.Tx.begin():
                self._data = [ o for o in self._query ]
        return self._data[ix]

    def data(self, index, role = Qt.DisplayRole):
        if (role == Qt.DisplayRole) and (index.column() == 0):
            r = self._get_data(index.row())
            return getattr(r, self._column_name)
        elif (role == Qt.UserRole):
            r = self._get_data(index.row())
            return r.key()
        else:
            return None


if __name__ == '__main__':
