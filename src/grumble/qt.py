import sys

from PySide.QtCore import QAbstractTableModel
from PySide.QtCore import QModelIndex
from PySide.QtCore import Qt

import gripe.pgsql
import grumble

class GrumbleTableModel(QAbstractTableModel):
    def __init__(self, query, column_names):
        QAbstractTableModel.__init__(self)
        self._query = query
        self._kind = query.get_kind()
        self._columns = [getattr(self._kind, n) for n in column_names]
        self._data = None

    def rowCount(self, parent=QModelIndex()):
        if self._data:
            return len(self._data)
        else:
            return self._query.count()

    def columnCount(self, parent=QModelIndex()):
        return len(self._columns)

    def headerData(self, col, orientation, role):
        return self._columns[col].verbose_name \
            if orientation == Qt.Horizontal and role == Qt.DisplayRole \
            else None

    def _get_data(self, ix):
        if not self._data:
            self._data = []
            with gripe.pgsql.Tx.begin():
                for o in self._query:
                    self._data.append(o)
        return self._data[ix]

    def data(self, index, role=Qt.DisplayRole):
        if role == Qt.DisplayRole:
            r = self._get_data(index.row())
            return self._columns[index.column()].__get__(r)
        else:
            return None
        
    def sort(self, colnum, order):
        """
            Sort table by given column number.
        """
        self.layoutAboutToBeChanged.emit()
        self._data = None
        self._query.clear_sort()
        self._query.add_sort(self._columns[colnum].name, order == Qt.AscendingOrder)
        self.layoutChanged.emit()

if __name__ == '__main__':
    from PySide.QtGui import QApplication
    from PySide.QtGui import QMainWindow
    from PySide.QtGui import QTableView
    import grumble.geopt
    import gripe.sessionbridge

    class Country(grumble.Model):
        name = grumble.TextProperty(verbose_name = "Country name", is_label = True)
        code = grumble.TextProperty(is_key = True, verbose_name = "ISO Code")

        def get_flag(self):
            return "http://flagspot.net/images/{0}/{1}.gif".format(self.code[0:1].lower(), self.code.lower())


    class User(grumble.Model):
        email = grumble.TextProperty(is_key = True)
        display_name = grumble.TextProperty(required = True, is_label = True)


    class Profile(grumble.Model):
        country =     grumble.TextProperty(default = "CA")
        dob =         grumble.DateProperty()
        gender =      grumble.TextProperty(choices=set(['female', 'male', 'other']), default = 'other')
        height =      grumble.IntegerProperty(default = 170)	# in cm
        units =       grumble.TextProperty(choices=set(['metric', 'imperial']))
        location =    grumble.geopt.GeoPtProperty()
        whoami =      grumble.TextProperty(multiline=True)
        regkey =      grumble.TextProperty()
        uploads =     grumble.IntegerProperty(default = 0)
        last_upload = grumble.DateTimeProperty()


    class STMainWindow(QMainWindow):
        def __init__(self):
            QMainWindow.__init__(self)
            fileMenu = self.menuBar().addMenu(self.tr("&File"))
            #fileMenu.addAction(Act)
            #fileMenu.addAction(openAct)
            #fileMenu.addAction(saveAct)
            self.setCentralWidget(self.createTable())

        def createTable(self):
            # create the view
            tv = QTableView()

            # set the table model
            tm = GrumbleTableModel(grumble.Query(User, False), ["display_name", "email"])
            tv.setModel(tm)

            # set the minimum size
            tv.setMinimumSize(400, 300)

            # hide grid
            tv.setShowGrid(False)

            # set the font
            #font = QFont("Courier New", 8)
            #tv.setFont(font)

            # hide vertical header
            vh = tv.verticalHeader()
            vh.setVisible(False)

            # set horizontal header properties
            hh = tv.horizontalHeader()
            hh.setStretchLastSection(True)

            # set column width to fit contents
            tv.resizeColumnsToContents()

            # set row height
            #nrows = len(self.tabledata)
            #for row in xrange(nrows):
            #    tv.setRowHeight(row, 18)

            # enable sorting
            tv.setSortingEnabled(True)

            return tv

    class SweatTrails(QApplication):
        def __init__(self, argv):
            super(SweatTrails, self).__init__(argv)
            gripe.sessionbridge.login('jan@de-visser.net', ['admin', 'user'])

    app = SweatTrails(sys.argv)

    w = STMainWindow()
    w.show()
    app.exec_()
    sys.exit()
        