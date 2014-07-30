'''
Created on Jul 29, 2014

@author: jan
'''

from PySide.QtCore import Qt
from PySide.QtGui import QTableView

import grumble.qt.model

class TableView(QTableView):
    def __init__(self, query = None, columns = None, parent = None):
        super(TableView, self).__init__(parent)
        self._query = None
        self._columns = None
        if query is not None or columns is not None:
            self.setQueryAndColumns(query, *columns)
        self.setSelectionBehavior(self.SelectRows)
        self.setShowGrid(False)
        vh = self.verticalHeader()
        vh.setVisible(False)
        hh = self.horizontalHeader()
        hh.setStretchLastSection(True)
        self.resizeColumnsToContents()
        self.setSortingEnabled(True)

    def refresh(self):
        self.model().beginResetModel()
        self.resetQuery()
        self.model().flush()
        self.model().endResetModel()
        self.resizeColumnsToContents()

    def setQueryAndColumns(self, query, *columns):
        self._query = query
        self._columns = columns
        if self._query is not None:
            tm = grumble.qt.model.TableModel(self._query, self._columns)
            self.setModel(tm)

    def query(self):
        return self._query

    def columns(self):
        return self._columns

    def resetQuery(self):
        pass

    def getSelectedObject(self):
        ix = self.selectedIndexes()[0]
        ret = self.model().data(ix, Qt.UserRole)
        return None if ret is None else ret()


