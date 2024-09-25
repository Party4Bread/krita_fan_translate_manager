from typing import Union
from krita import DockWidget,Krita
import krita
from PyQt5.QtCore import Qt, QMimeData, pyqtSignal, QTimer,QObject
from pathlib import Path
from .datatypes import Project,Page
from PyQt5.QtWidgets import QDialog, QStackedWidget, QPushButton, QHBoxLayout,  QSplitter
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QGridLayout, QLabel, QListWidget, QListWidgetItem
from PyQt5.QtGui import QPixmap, QDrag
from PyQt5.QtCore import Qt, QMimeData, pyqtSignal, QTimer
from pathlib import Path
from .datatypes import Project,Page
from .project_watcher import ProjectWatcher

MASK_GRP_NAME="ft_masks"
ORIG_LAYER_NAME="Background"

DOCKER_TITLE = "Fan Translation Docker"
class TranslateDocker(DockWidget):

    def __init__(self):
        super().__init__()
        self.project=None
        self.setWindowTitle(DOCKER_TITLE)
        
        base = QVBoxLayout()
        widget = QWidget()
        widget.setLayout(base)

        baseLayout = QSplitter()
        base.addWidget(baseLayout)
        add_text_mask_btn = QPushButton("Add Mask")
        add_text_mask_btn.clicked.connect(lambda x:self.addNewMask())
        add_text_mask_btn = QPushButton("OCR From Mask")
        add_text_mask_btn.clicked.connect(lambda x:self.ocrMaskedText())
        base.addWidget(add_text_mask_btn)
        self.setWidget(widget)

        # self.watcher = QTimer(self)
        # self.watcher.setInterval(1000)
        # self.watcher.timeout.connect()
        # self.watcher.start(500)

    def addNewMask(self):
        doc = Krita.instance().activeDocument()

        nodesList = doc.topLevelNodes()
        mask_group = None
        for layer in nodesList:
            if layer.type()=="grouplayer" and layer.name()==MASK_GRP_NAME:
                mask_group=layer
                break
        if mask_group is None:
            mask_group=doc.createGroupLayer(MASK_GRP_NAME)
            doc.rootNode().addChildNode(mask_group,None)
        ms:list[int] = [*filter(lambda x: x is not None, [int_tryparse(x.name().rsplit(" ",1)[-1]) for x in mask_group.childNodes()])]
        maxmsk=max(ms+[0])
        mask_group.addChildNode(doc.createNode("Mask "+str(maxmsk+1),"paintlayer"),None)

    def ocrMaskedText(self):
        asdf



    def canvasChanged(self, canvas):
        pass

def int_tryparse(x:str)->Union[int,None]:
    try:
        return int(x)
    except:
        return None