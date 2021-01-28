import sys
import os
import json
import compas

from functools import partial

os.environ['QT_MAC_WANTS_LAYER'] = '1'

from PySide2 import QtCore, QtGui, QtWidgets

from ..views import View120
from ..views import View330
from ..objects import Object

from .controller import Controller
from .selector import Selector

HERE = os.path.dirname(__file__)
ICONS = os.path.join(HERE, '../icons')
CONFIG = os.path.join(HERE, 'config.json')

VERSIONS = {'120': (2, 1), '330': (3, 3)}


class App:
    """Viewer app.

    The app has a (main) window with a central OpenGL widget (i.e. the "view"),
    and a menubar, toolbar, and statusbar.
    The menubar provides access to all supported "actions".
    The toolbar is meant to be a "quicknav" to a selected set of actions.
    The app supports rotate/pan/zoom, and object selection via picking or box selections.

    Currently the app uses OpenGL 2.2 and GLSL 120 with a "compatibility" profile.
    Support for OpenGL 3.3 and GLSL 330 with a "core" profile is under development.

    Parameters
    ----------
    version: {'120', '330'}, optional
        The version of the GLSL used by the shaders.
        Default is ``'120'`` with a compatibility profile.
        The option ``'330'`` is not yet available.
    width: int, optional
        The width of the app window at startup.
        Default is ``800``.
    height: int, optional
        The height of the app window at startup.
        Default is ``500``.
    viewmode: {'shaded', 'ghosted'}, optional
        The display mode of the OpenGL view.
        Default is ``'shaded'``.
        In ``'ghosted'`` mode, all objects have a default opacity of ``0.7``.

    Attributes
    ----------
    window: :class:`PySide2.QtWidgets.QMainWindow`
        The main window of the application.
        This window contains the view and any other UI components
        such as the menu, toolbar, statusbar, ...
    view: :class:`compas_view2.View`
        Instance of OpenGL view.
        This view is the central widget of the main window.
    controller: :class:`compas_view2.app.Controller`
        The action controller of the app.

    Notes
    -----
    The app can currently only be used "as-is".
    This means that there is no formal mechanism for adding actions to the controller
    or to add functionality to the shader, other than by extending the core classes.
    In the future, such mechanism will be provided by allowing the user to overwrite
    the configuration file and add actions to the controller, without having
    to modify the package source code.

    Currently the app has no scene graph.
    All added COMPAS objects are wrapped in a viewer object and stored in a dictionary,
    mapping the object's ID (``id(object)``) to the instance.

    Examples
    --------
    To use the app in 'interactive' mode.

    >>> from compas_view2 import app
    >>> viewer = app.App()
    >>> viewer.show()

    To use the app in 'scripted' mode.

    >>> import random
    >>> import math
    >>> import compas
    >>> from compas.datastructures import Network
    >>> from compas.datastructures import Mesh
    >>> from compas.geometry import Box
    >>> from compas.geometry import Torus
    >>> from compas.geometry import Pointcloud
    >>> from compas.geometry import Rotation
    >>> from compas.utilities import i_to_rgb
    >>> from compas_view2 import app

    Create an instance of the viewer.

    >>> viewer = app.App(viewmode='ghosted')

    Add a mesh and a network.

    >>> mesh = Mesh.from_off(compas.get('tubemesh.off'))
    >>> network = Network.from_obj(compas.get('grid_irregular.obj'))
    >>> viewer.add(mesh, show_vertices=False)
    >>> viewer.add(network)

    Add a cloud of boxes.

    >>> cloud = Pointcloud.from_bounds(10, 5, 3, 100)
    >>> R1 = Rotation.from_axis_and_angle([0, 0, 1], math.radians(180))
    >>> R2 = Rotation.from_axis_and_angle([0, 0, 1], math.radians(90))
    >>> for point in cloud.transformed(R1):
    ...     box = Box((point, [1, 0, 0], [0, 1, 0]), 0.1, 0.1, 0.1)
    ...     color = i_to_rgb(random.random(), normalize=True)
    ...     viewer.add(box, show_vertices=False, color=color, is_selected=random.choice([0, 1]))
    ...

    Add a cloud of rings.

    >>> for point in cloud.transformed(R2):
    ...     r1 = 0.1 * random.random()
    ...     r2 = random.random() * r1
    ...     torus = Torus((point, [0, 0, 1]), r1, r2)
    ...     viewer.add(torus, show_vertices=False)

    Display the viewer with all added objects.

    >>> viewer.show()

    """

    def __init__(self, version='120', width=800, height=500, viewmode='shaded'):
        if version not in VERSIONS:
            raise Exception("Only these versions are currently supported: {}".format(VERSIONS))

        glFormat = QtGui.QSurfaceFormat()
        glFormat.setVersion(* VERSIONS[version])

        if version == '330':
            View = View330
            glFormat.setProfile(QtGui.QSurfaceFormat.CoreProfile)
        elif version == '120':
            View = View120
            glFormat.setProfile(QtGui.QSurfaceFormat.CompatibilityProfile)
        else:
            raise NotImplementedError

        glFormat.setDefaultFormat(glFormat)
        QtGui.QSurfaceFormat.setDefaultFormat(glFormat)

        app = QtCore.QCoreApplication.instance()
        if app is None:
            app = QtWidgets.QApplication(sys.argv)
        app.references = set()

        self.width = width
        self.height = height
        self.window = QtWidgets.QMainWindow()
        self.view = View(self, mode=viewmode)
        self.window.setCentralWidget(self.view)
        self.window.setContentsMargins(0, 0, 0, 0)
        self.controller = Controller(self)

        self._app = app
        self._app.references.add(self.window)
        self.selector = Selector(self)

        self.init_statusbar()

        with open(CONFIG) as f:
            config = json.load(f)
            self.init_menubar(config.get("menubar"))
            self.init_toolbar(config.get("toolbar"))

        self.resize(width, height)

    def resize(self, width, height):
        self.window.resize(width, height)
        desktop = self._app.desktop()
        rect = desktop.availableGeometry()
        x = 0.5 * (rect.width() - width)
        y = 0.5 * (rect.height() - height)
        self.window.setGeometry(x, y, width, height)

    def add(self, data, **kwargs):
        obj = Object.build(data, **kwargs)
        self.view.objects[obj] = obj
        self.selector.add(obj)
        if self.view.isValid():
            obj.init()

    def show(self):
        self.window.show()
        self._app.exec_()

    # ==============================================================================
    # UI
    # ==============================================================================

    def init_statusbar(self):
        self.statusbar = self.window.statusBar()
        self.statusbar.setContentsMargins(0, 0, 0, 0)
        self.statusbar.showMessage('Ready')

    def init_menubar(self, items):
        if not items:
            return
        self.menubar = self.window.menuBar()
        self.menubar.setNativeMenuBar(False)
        self.menubar.setContentsMargins(0, 0, 0, 0)
        self.add_menubar_items(items, self.menubar)

    def init_toolbar(self, items):
        if not items:
            return
        toolbar = self.window.addToolBar('Tools')
        toolbar.setMovable(False)
        toolbar.setObjectName('Tools')
        toolbar.setIconSize(QtCore.QSize(24, 24))
        undotool = toolbar.addAction(QtGui.QIcon(os.path.join(ICONS, 'undo-solid.svg')), 'Undo', self.undo)
        redotool = toolbar.addAction(QtGui.QIcon(os.path.join(ICONS, 'redo-solid.svg')), 'Redo', self.redo)

    def add_menubar_items(self, items, parent):
        if not items:
            return
        for item in items:
            if item['type'] == 'separator':
                parent.addSeparator()
            elif item['type'] == 'menu':
                menu = parent.addMenu(item['text'])
                if 'items' in item:
                    self.add_menubar_items(item['items'], menu)
            elif item['type'] == 'radio':
                radio = QtWidgets.QActionGroup(self.window, exclusive=True)
                for item in item['items']:
                    action = self.add_action(item, parent)
                    action.setCheckable(True)
                    action.setChecked(item['checked'])
                    radio.addAction(action)
            elif item['type'] == 'action':
                self.add_action(item, parent)
            else:
                raise NotImplementedError

    def add_toolbar_items(self, items, parent):
        if not items:
            return
        for item in items:
            if item['type'] == 'separator':
                parent.addSeparator()
            elif item['type'] == 'action':
                self.add_action(item, parent)
            else:
                raise NotImplementedError

    def add_action(self, item, parent):
        text = item['text']
        action = getattr(self.controller, item['action'])
        args = item.get('args', None) or []
        kwargs = item.get('kwargs', None) or {}
        if 'icon' in item:
            icon = QtGui.QIcon(item['icon'])
            return parent.addAction(icon, text, partial(action, *args, **kwargs))
        return parent.addAction(text, partial(action, *args, **kwargs))
