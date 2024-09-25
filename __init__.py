from krita import DockWidgetFactory, DockWidgetFactoryBase, Krita
from .project_manager_docker import ProjectManagerDocker
from .project_setup_wizard import ProjectSetupExtension
from .translate_docker import TranslateDocker


instance = Krita.instance()

dock_widget_factory = DockWidgetFactory('project_manager_docker',
                                        DockWidgetFactoryBase.DockRight,
                                        ProjectManagerDocker)
instance.addDockWidgetFactory(dock_widget_factory)


dock_widget_factory = DockWidgetFactory('translate_docker',
                                        DockWidgetFactoryBase.DockRight,
                                        TranslateDocker)
instance.addDockWidgetFactory(dock_widget_factory)


instance.addExtension(ProjectSetupExtension(Krita.instance()))