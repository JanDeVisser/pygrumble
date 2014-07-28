import sys

from PySide.QtCore import QAbstractListModel
from PySide.QtCore import QAbstractTableModel
from PySide.QtCore import QModelIndex
from PySide.QtCore import Qt

from PySide.QtGui import QTableView

import gripe
import gripe.db
import grumble

logger = gripe.get_logger(__name__)

class GrumbleTableColumn(object):
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

class GrumbleTableModel(QAbstractTableModel):
    def __init__(self, query, *args):
        QAbstractTableModel.__init__(self)
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
                if isinstance(arg, GrumbleTableColumn):
                    col = arg
                else:
                    col = GrumbleTableColumn(str(arg))
                col.prop = getattr(self._kind, col.name)
                col.kind = self._kind
                ret.append(col)
        return ret
                
    def add_columns(self, *args):
        self._columns.extend(self._get_column_defs(args))
        
    def rowCount(self, parent = QModelIndex()):
        ret = len(self._data) if self._data is not None else self._query.count()
        #logger.debug("GrumbleTableModel.rowCount() = %s (%squeried)", ret,
        #             "not " if self._data is not None else "")
        return ret

    def columnCount(self, parent = QModelIndex()):
        #logger.debug("GrumbleTableModel.columnCount()")
        return len(self._columns)

    def headerData(self, col, orientation, role):
        #logger.debug("GrumbleTableModel.headerData(%s,%s,%s)", col, orientation, role)
        return self._columns[col].get_header() \
            if orientation == Qt.Horizontal and role == Qt.DisplayRole \
            else None

    def _get_data(self, ix):
        if self._data is None:
            #logger.debug("GrumbleTableModel._get_data(%s) -> query", ix)
            with gripe.db.Tx.begin():
                self._data = [o for o in self._query]
        return self._data[ix]

    def data(self, index, role = Qt.DisplayRole):
        if role == Qt.DisplayRole:
            instance = self._get_data(index.row())
            col = self._columns[index.column()]
            ret = col.get_value(instance)
            #logger.debug("GrumbleTableModel.data(%s,%s) = %s", index.row(), index.column(), ret)
            return ret
        elif role == Qt.UserRole:
            r = self._get_data(index.row())
            return r.key()
        else:
            return None
        
    def flush(self):
        logger.debug("GrumbleTableModel.flush()")
        self.beginResetModel()
        self.layoutAboutToBeChanged.emit()
        self._data = None
        self.layoutChanged.emit()
        self.endResetModel()

    def sort(self, colnum, order):
        """
            Sort table by given column number.
        """
        logger.debug("GrumbleTableModel.sort(%s)", colnum)
        self.layoutAboutToBeChanged.emit()
        self._data = None
        self._query.clear_sort()
        self._query.add_sort(self._columns[colnum].name, order == Qt.AscendingOrder)
        self.layoutChanged.emit()


class GrumbleTableView(QTableView):
    def __init__(self, query = None, columns = None, parent = None):
        super(GrumbleTableView, self).__init__(parent)
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
            tm = grumble.qt.GrumbleTableModel(self._query, self._columns)
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


class GrumbleListModel(QAbstractListModel):
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
    from PySide.QtGui import QApplication
    from PySide.QtGui import QComboBox
    from PySide.QtGui import QHBoxLayout
    from PySide.QtGui import QLabel
    from PySide.QtGui import QMainWindow
    from PySide.QtGui import QPushButton
    from PySide.QtGui import QTableView
    from PySide.QtGui import QVBoxLayout
    from PySide.QtGui import QWidget
    import grumble.geopt
    import gripe.sessionbridge

    class Country(grumble.Model):
        countryname = grumble.TextProperty(verbose_name = "Country name", is_label = True)
        countrycode = grumble.TextProperty(is_key = True, verbose_name = "ISO Code")

        def get_flag(self):
            return "http://flagspot.net/images/{0}/{1}.gif".format(self.code[0:1].lower(), self.code.lower())


    class User(grumble.Model):
        email = grumble.TextProperty(is_key = True)
        display_name = grumble.TextProperty(required = True, is_label = True)


    class Profile(grumble.Model):
        country = grumble.TextProperty(default = "CA")
        dob = grumble.DateProperty()
        gender = grumble.TextProperty(choices = set(['female', 'male', 'other']), default = 'other')
        height = grumble.IntegerProperty(default = 170)  # in cm
        units = grumble.TextProperty(choices = set(['metric', 'imperial']))
        location = grumble.geopt.GeoPtProperty()
        whoami = grumble.TextProperty(multiline = True)
        regkey = grumble.TextProperty()
        uploads = grumble.IntegerProperty(default = 0)
        last_upload = grumble.DateTimeProperty()


    class STMainWindow(QMainWindow):
        def __init__(self):
            QMainWindow.__init__(self)
            fileMenu = self.menuBar().addMenu(self.tr("&File"))
            # fileMenu.addAction(Act)
            # fileMenu.addAction(openAct)
            # fileMenu.addAction(saveAct)
            window = QWidget()
            layout = QVBoxLayout(self)
            l = QHBoxLayout()
            l.addWidget(self.createCombo())
            self.button = QPushButton("Pick Me")
            self.button.clicked.connect(self.set_user_id)
            l.addWidget(self.button)
            layout.addLayout(l)
            self.user_id = QLabel()
            layout.addWidget(self.user_id)
            layout.addWidget(self.createTable())
            window.setLayout(layout)
            self.setCentralWidget(window)

        def set_user_id(self):
            self.user_id.setText(self.combo.itemData(self.combo.currentIndex()).name)

        def createCombo(self):
            self.combo = QComboBox()
            view = GrumbleListModel(grumble.Query(User, False), "display_name")
            self.combo.setModel(view)
            return self.combo

        def createTable(self):
            # create the view
            tv = QTableView()

            # set the table model
            tm = GrumbleTableModel(grumble.Query(Country, False), ["countryname", "countrycode"])
            tv.setModel(tm)

            # set the minimum size
            tv.setMinimumSize(400, 300)

            # hide grid
            tv.setShowGrid(False)

            # set the font
            # font = QFont("Courier New", 8)
            # tv.setFont(font)

            # hide vertical header
            vh = tv.verticalHeader()
            vh.setVisible(False)

            # set horizontal header properties
            hh = tv.horizontalHeader()
            hh.setStretchLastSection(True)

            # set column width to fit contents
            tv.resizeColumnsToContents()

            # set row height
            # nrows = len(self.tabledata)
            # for row in xrange(nrows):
            #    tv.setRowHeight(row, 18)

            # enable sorting
            tv.setSortingEnabled(True)

            return tv

    class SweatTrails(QApplication):
        def __init__(self, argv):
            super(SweatTrails, self).__init__(argv)

    app = SweatTrails(sys.argv)

    w = STMainWindow()
    w.show()
    app.exec_()
    sys.exit()

