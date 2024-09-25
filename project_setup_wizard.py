from pathlib import Path
from PyQt5.QtWidgets import (QWizard, QWizardPage, QLineEdit, QVBoxLayout, QLabel, QProgressDialog,
                             QFileDialog, QPushButton, QListWidget, QAbstractItemView, QHBoxLayout)
from krita import Krita, Extension
from .datatypes import Page, Project


class ProjectSetupWizard(QWizard):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWizardStyle(QWizard.ModernStyle)  # Apply Modern style
        self.addPage(ProjectInfoPage())
        self.addPage(ImageImportPage())
        self.addPage(ImageOrderPage())

        self.setWindowTitle("Project Setup Wizard")

    def accept(self):
        project_title = self.field("projectTitle")
        project_folder = Path(self.field("projectFolder"))
        selected_files = self.field("selectedFiles")
        
        # Get the reordered file list
        image_order_page = self.page(2)
        reordered_files = [selected_files[i] for i in image_order_page.get_file_order()]

        project = Project(project_folder)
        project.title = project_title

        # Import and convert images
        krita_inst=Krita.instance()

        progress_dialog = QProgressDialog("Importing images...", "Cancel", 0, len(reordered_files), self)
        progress_dialog.setWindowTitle("Progress")
        progress_dialog.show()

        for i, file_path in enumerate(reordered_files):
            project.add_page(krita_inst, file_path)
            progress_dialog.setValue(i + 1)
            if progress_dialog.wasCanceled():
                break

        progress_dialog.close()
        
        project.save()
        newdoc=krita_inst.openDocument(str(project.pages[0].kra_fn))
        krita_inst.activeWindow().addView(newdoc)
        super().accept()

class ProjectInfoPage(QWizardPage):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setTitle("Project Information")
        self.setSubTitle("Enter project details and select project folder")

        layout = QVBoxLayout()

        # Project Title
        title_layout = QHBoxLayout()
        self.title_edit = QLineEdit()
        title_layout.addWidget(QLabel("Project Title:"))
        title_layout.addWidget(self.title_edit)
        layout.addLayout(title_layout)

        # Project Folder
        folder_layout = QHBoxLayout()
        self.folder_edit = QLineEdit()
        self.folder_button = QPushButton("Browse")
        self.folder_button.clicked.connect(self.select_folder)
        folder_layout.addWidget(QLabel("Project Folder:"))
        folder_layout.addWidget(self.folder_edit)
        folder_layout.addWidget(self.folder_button)
        layout.addLayout(folder_layout)

        self.setLayout(layout)

        self.registerField("projectTitle*", self.title_edit)
        self.registerField("projectFolder*", self.folder_edit)

    def select_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Project Folder")
        if folder:
            self.folder_edit.setText(folder)

class ImageImportPage(QWizardPage):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setTitle("Import Images")
        self.setSubTitle("Select images to import into your project")

        layout = QVBoxLayout()
        self.file_label = QLabel("No files selected")
        layout.addWidget(self.file_label)
        layout.addWidget(QPushButton("Select Files", clicked=self.select_files))
        self.setLayout(layout)

        self.registerField("selectedFiles", self, "selectedFiles")
        self.setProperty("selectedFiles", [])

    def select_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Select Images", "", "Image Files (*.png *.jpg *.bmp *.tiff)")
        if files:
            self.setProperty("selectedFiles", files)
            self.file_label.setText(f"{len(files)} file(s) selected")

class DraggableListWidget(QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragDropMode(QAbstractItemView.InternalMove)
        self.setSelectionMode(QAbstractItemView.SingleSelection)

    def dropEvent(self, event):
        super().dropEvent(event)
        self.parent().update_preview()

class ImageOrderPage(QWizardPage):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setTitle("Image Order")
        self.setSubTitle("Drag and drop to reorder images")

        layout = QVBoxLayout()
        self.list_widget = DraggableListWidget(self)
        layout.addWidget(self.list_widget)
        self.preview_label = QLabel()
        layout.addWidget(self.preview_label)
        self.setLayout(layout)

    def initializePage(self):
        selected_files = self.field("selectedFiles")
        self.list_widget.clear()
        for file_path in selected_files:
            self.list_widget.addItem(Path(file_path).stem)

    def get_file_order(self):
        return [self.list_widget.row(self.list_widget.item(i)) for i in range(self.list_widget.count())]


class ProjectSetupExtension(Extension):
    def __init__(self, parent):
        super().__init__(parent)

    def setup(self):
        pass

    def createActions(self, window):
        action = window.createAction("projectSetupAction", "Project Setup Wizard")
        action.triggered.connect(self.show_project_setup_wizard)

    def show_project_setup_wizard(self):
        wizard = ProjectSetupWizard(Krita.instance().activeWindow().qwindow())
        wizard.exec_()
