from typing import Union, cast
from krita import DockWidget,Krita
from PyQt5.QtWidgets import QSplitter, QWidget, QVBoxLayout, QLabel, QListWidget, QListWidgetItem
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt, pyqtSignal
from pathlib import Path
from .datatypes import Project,Page
from .project_watcher import ProjectWatcher
from .commons.util import ensure

DOCKER_TITLE = 'Fan Translate Page Managing Docker'
THM_RECT = 64


class DraggableContainer(QWidget):
    def __init__(self, page:Page, thumb, index):
        super().__init__()
        self.page = page
        self.index = index
        
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        self.thumbnail = QLabel()
        self.thumbnail.setAlignment(Qt.AlignCenter)
        
        pixmap = QPixmap(str(thumb))
        w, h = pixmap.width(), pixmap.height()
        r = THM_RECT / max(w, h)
        rw, rh = int(w * r), int(h * r)
        self.thumbnail.setPixmap(pixmap.scaled(rw, rh))
        
        self.page_number = QLabel(f"Page {index + 1}")
        self.page_number.setAlignment(Qt.AlignCenter)
        
        layout.addWidget(self.thumbnail)
        layout.addWidget(self.page_number)
        
        # self.setStyleSheet("border: none;")
            
    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            krita_inst = Krita.instance()
            kra_fn = self.page.kra_fn
            win = krita_inst.activeWindow()
            for vw in win.views():
                if Path(vw.document().fileName()) == kra_fn:
                    win.activate()
                    win.showView(vw)
                    vw.setVisible()
                    return
            # If not open, open the document and set it as active
            doc = krita_inst.openDocument(str(kra_fn))
            win.addView(doc)

class ThumbnailGrid(QListWidget):
    reordered = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setViewMode(QListWidget.IconMode)
        self.setResizeMode(QListWidget.Adjust)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDragDropMode(QListWidget.InternalMove)
        # self.itemClicked.connect(self.on_item_clicked)
        self.current_selected = None
        
    def update_project(self, project):
        self.project = project
        
    def clear_grid(self):
        self.clear()
        
    def update_thumbnails(self):
        self.clear_grid()
        thumbs = self.project.thms
        for i, (page, thumb) in enumerate(zip(self.project.pages, thumbs)):
            container = DraggableContainer(page, thumb, i)
            item = QListWidgetItem(self)
            item.setSizeHint(container.sizeHint())
            self.setItemWidget(item, container)
            
    def dropEvent(self, event):
        super().dropEvent(event)
        new_order = []
        for i in range(self.count()):
            item = self.item(i)
            container = cast(DraggableContainer,self.itemWidget(item))
            new_order.append(container.page)
        self.project.pages = new_order
        self.update_thumbnails()
        self.reordered.emit()
        
    # def on_item_clicked(self, item):
    #     if self.current_selected:
    #         self.itemWidget(self.current_selected).setStyleSheet("border: none;")
        
    #     container = self.itemWidget(item)
    #     container.setStyleSheet("border: 2px solid lightblue;")
    #     self.current_selected = item


class ProjectManagerDocker(DockWidget):

    def __init__(self):
        super().__init__()
        self.project=None
        self.setWindowTitle(DOCKER_TITLE)
        
        base = QVBoxLayout()
        widget = QWidget()
        widget.setLayout(base)
        self.thumbnail_grid = ThumbnailGrid(widget)
        self.thumbnail_grid.reordered.connect(self.thumbnailReordered)

        baseLayout = QSplitter()
        base.addWidget(baseLayout)
        base.addWidget(self.thumbnail_grid)
        self.label1 = QLabel("Path here")
        base.addWidget(self.label1)
        self.setWidget(widget)

        ProjectWatcher.instance().project_changed.connect(self.watchActiveDocumentChange)
    
    def thumbnailReordered(self):
        self.project=self.thumbnail_grid.project
        self.project.save()

    def watchActiveDocumentChange(self,project:Union[Project,None]):
        self.project=project
        if project is None:
            self.thumbnail_grid.clear_grid()
            return
        project = ensure(project)
        self.thumbnail_grid.update_project(self.project)
        self.thumbnail_grid.update_thumbnails()
        self.label1.setText("Project "+project.title)


    def canvasChanged(self, canvas):
        pass
    
