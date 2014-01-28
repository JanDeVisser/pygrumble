# To change this license header, choose License Headers in Project Properties.
# To change this template file, choose Tools | Templates
# and open the template in the editor.

from PySide.QtGui import QApplication
from PySide.QtGui import QMainWindow
from PySide.QtGui import QTableView
import grumble.geopt
import gripe.sessionbridge

class Settings(grumble.Model):
    key = grumble.TextProperty(is_key = True)
    value = grumble.TextProperty()


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

app = SweatTrails(sys.argv)

w = STMainWindow()
w.show()
app.exec_()
sys.exit()

