from krita import DockWidget,Krita
from PyQt5.QtCore import Qt, QMimeData, pyqtSignal, QTimer,QObject
from pathlib import Path
from .datatypes import Project,Page

class ProjectWatcher(QObject):
    project_changed = pyqtSignal(Project)
    page_changed = pyqtSignal(Page,int)
    __instance = None
    @classmethod
    def instance(cls):
        if cls.__instance is None:
            cls.__instance=cls()
        return cls.__instance

    def __init__(self):
        super(ProjectWatcher,self).__init__()
        self.watcher = QTimer(self)
        self.watcher.timeout.connect(self.watchActiveDocChange)
        self.watcher.setInterval(1000)
        self.watcher.start(500)

        self._prev_project = None
        self._prev_page = None
    
    def checkProject(self,filename):
        project_json = Path(filename).parent.parent / "project.json"
        if self._prev_project == project_json:
            return
        if project_json.exists(): 
            self.project=Project.load(project_json)
        else:
            self.project = None
            self._prev_page=None
        self.project_changed.emit(self.project)
        self._prev_project = project_json
    
    # def checkPage(self,filename):
    #     if self.project is None or self._prev_page == filename: 
    #         return
    #     current_page=None
    #     for idx,pg in enumerate(self.project.pages):

    #     self.page_changed.emit()
    #     self._prev_page = filename


    def watchActiveDocChange(self):
        krita_inst = Krita.instance()
        doc = krita_inst.activeDocument()
        if doc is None:
            return
        self.checkProject(doc.fileName())