from typing import Literal, Union, cast, SupportsFloat, Optional
from krita import DockWidget, Document, Node, GroupLayer, VectorLayer
import krita
from PyQt5.QtCore import QTimer, pyqtSignal
from PyQt5.QtWidgets import (QAbstractItemView, QBoxLayout, QPushButton, QHBoxLayout, QFontComboBox,
                             QWidget, QVBoxLayout, QListWidget, QListWidgetItem, QSpinBox,
                             QComboBox, QTextEdit)
from PyQt5.QtGui import QFocusEvent, QFont
from .svgtext import guide_rect, textgen
from .commons.document import KritaDocument
from secrets import token_urlsafe
import xml.etree.ElementTree as ET
import inspect
import html
import json
from dataclasses import dataclass, asdict

MASK_GRP_NAME = "ft_masks"
TEXT_GRP_NAME = "ft_texts"
METADATA_LAYER_NAME = "ft_metadata"
ORIG_LAYER_NAME = "Background"
UI_FONT_SIZE = 12
DOCKER_TITLE = "Fan Translation Docker"

@dataclass
class ShapeCache:
    rect: tuple[float, float, float, float]
    text: tuple[str, str, int]

def find_or_create_layer(doc: KritaDocument, layer_name: str, layer_type: str) -> Node:
    _doc = doc._doc
    for node in _doc.topLevelNodes():
        if node.type() == layer_type and node.name() == layer_name:
            return node
    layer = _doc.createGroupLayer(layer_name) if layer_type == "grouplayer" else _doc.createVectorLayer(layer_name)
    _doc.rootNode().addChildNode(layer, None)
    return _doc.rootNode().findChildNodes(layer_name)[-1]

def get_root_group(doc: KritaDocument, group_of: Literal["text", "mask"]) -> GroupLayer:
    grp_name = TEXT_GRP_NAME if group_of == "text" else MASK_GRP_NAME
    return cast(GroupLayer, find_or_create_layer(doc, grp_name, "grouplayer"))

def get_metadata_layer(doc: KritaDocument) -> VectorLayer:
    return cast(VectorLayer, find_or_create_layer(doc, METADATA_LAYER_NAME, "vectorlayer"))

def get_text_group_shape_by_id(doc: KritaDocument, uid: str) -> tuple[Optional[VectorLayer], Optional[Node], Optional[Node]]:
    grp = get_root_group(doc, "text")
    for layer in grp.childNodes():
        if layer.type() != "vectorlayer":
            continue
        layer = cast(VectorLayer, layer)
        rect, text = None, None
        for shp in layer.shapes():
            elem = ET.fromstring(shp.toSvg())
            if elem.get("id") == f'ft_guide/{uid}':
                rect = shp
            if elem.find(f".//tspan[.='ft_text/{uid}']") is not None:
                text = shp
            if rect is not None and text is not None:
                return layer, rect, text
    return None, None, None

shape_cache: dict[str, ShapeCache] = {}

def update_text_shape(doc: KritaDocument, uid: str, new_text: str, font: str = "Arial", size: int = UI_FONT_SIZE):
    text_layer, rect_shape, text_shape = get_text_group_shape_by_id(doc, uid)
    if text_layer is None or rect_shape is None:
        return

    guide_rect = ET.fromstring(rect_shape.toSvg())
    x, y, w, h = extract_rect_properties(guide_rect)
    rect = (x, y, w, h)

    if uid in shape_cache and shape_cache[uid].rect == rect and shape_cache[uid].text == (new_text, font, size):
        return

    new_text_elem = create_new_text_element(new_text, rect, font, uid, size)
    svg_string = create_svg_string(doc._doc, new_text_elem)
    
    if text_shape is not None:
        text_shape.remove()
    text_layer.addShapesFromSvg(svg_string)

    shape_cache[uid] = ShapeCache(rect=rect, text=(new_text, font, size))

def extract_rect_properties(guide_rect: ET.Element) -> tuple[float, float, float, float]:
    x, y = extract_translate_values(guide_rect.get('transform', ''))
    w = float(guide_rect.get('width', 100))
    h = float(guide_rect.get('height', 50))
    return x, y, w, h

def extract_translate_values(transform: str) -> tuple[float, float]:
    if transform.startswith('translate('):
        translate_values = transform.split('(')[1].split(')')[0].split(',')
        if len(translate_values) >= 2:
            return float(translate_values[0].strip()), float(translate_values[1].strip())
    return 0., 0.

def create_new_text_element(new_text: str, rect: tuple[float, float, float, float], font: str, uid: str, size: int) -> ET.Element:
    x, y, w, h = rect
    new_text_elem, toty = textgen(new_text, w, font, size)
    new_text_elem.set('id', f'ft_text/{uid}')
    sub = ET.SubElement(new_text_elem, "tspan", {"style": "fill:#00deadcd"})
    sub.text = f'ft_text/{uid}'
    sub.set("x", "0")
    new_text_elem.set('transform', f'translate({x}, {y+h/2-toty/2})')
    return new_text_elem

def create_svg_string(doc: Document, new_text_elem: ET.Element) -> str:
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{doc.width()}" height="{doc.height()}">'
            f'{ET.tostring(new_text_elem, encoding="unicode")}'
            '</svg>')

def new_text_shape(uid: str, x: SupportsFloat, y: SupportsFloat, w: SupportsFloat, h: SupportsFloat, doc: Document) -> str:
    R = guide_rect(x, y, w, h)
    R.set('id', f'ft_guide/{uid}')
    
    T, _ = textgen("Text", w, "Arial")
    T.set('id', f'ft_text/{uid}')
    ET.SubElement(T, "tspan", {"style": "fill:#00deadcd"}).text = f'ft_text/{uid}'
    
    # Create an SVG string
    svg_string = f'<svg xmlns="http://www.w3.org/2000/svg" width="{doc.width()}" height="{doc.height()}">'
    svg_string += ET.tostring(R, encoding='unicode')
    svg_string += ET.tostring(T, encoding='unicode')
    svg_string += '</svg>'
    return svg_string

def save_page_json(doc: KritaDocument, content: Union[dict, list]):
    layer = get_metadata_layer(doc)
    for shape in layer.shapes():
        shape.remove()
    jsonstr = json.dumps(content)
    svg = f'<svg xmlns="http://www.w3.org/2000/svg"><text fill="#00feadff"><tspan x="0">{html.escape(jsonstr)}</tspan></text></svg>'
    layer.addShapesFromSvg(svg)

def load_page_json(doc: KritaDocument) -> list:
    layer = get_metadata_layer(doc)
    try:
        text_shape = layer.shapes()[0]
        nd = ET.fromstring(text_shape.toSvg()).find("../text/tspan[0]")
        if nd is not None and nd.text is not None:
            return json.loads(html.unescape(nd.text))
    except Exception:
        pass
    return []

class FocusSignalingTextEdit(QTextEdit):
    focus_in = pyqtSignal()
    
    def focusInEvent(self, event: QFocusEvent):
        self.focus_in.emit()
        super().focusInEvent(event)

@dataclass
class TranslationPair(QWidget):
    uid: str
    source: str = ""
    translation: str = ""
    font: str = "Arial"
    size: int = 24

    def __post_init__(self):
        super().__init__()
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()
        self.source_text = self.create_text_edit(self.source, "#333")
        self.translated_text = self.create_text_edit(self.translation, "#404040")
        layout.addWidget(self.source_text)
        layout.addWidget(self.translated_text)
        self.setLayout(layout)

    def create_text_edit(self, text: str, bg_color: str) -> FocusSignalingTextEdit:
        text_edit = FocusSignalingTextEdit(text)
        text_edit.setMaximumHeight(text_edit.fontMetrics().lineSpacing() * 2 + 10)
        text_edit.setStyleSheet(f"background-color: {bg_color};")
        return text_edit

    @classmethod
    def from_json(cls, data: dict):
        return cls(data["uid"], data["orig"], data["tran"], data["font"], data["size"])

    def to_json(self):
        return {
            "orig": self.source_text.toPlainText(),
            "tran": self.translated_text.toPlainText(),
            "font": self.font,
            "size": self.size
        }

def ensure_active_document(func):
    def wrapper(self, *args, **kwargs):
        doc = KritaDocument.active()
        if doc is None:
            return
        arg_len = len(inspect.signature(func).parameters) - 2
        return func(self, doc, *args[:arg_len], **kwargs)
    return wrapper

class TranslateDocker(DockWidget):
    def __init__(self):
        super().__init__()
        self.current_page_fn = None
        self.cached_pair_json = None
        self.translation_pairs: list[TranslationPair] = []
        self.setWindowTitle(DOCKER_TITLE)
        self.setup_ui()
        self.setup_connections()

    def setup_ui(self):
        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)
        self.setup_buttons(main_layout)
        self.setup_text_selector(main_layout)
        self.setup_text_styler(main_layout)
        self.setup_pair_list(main_layout)
        self.setWidget(main_widget)

    @ensure_active_document
    def load_page(self, doc: KritaDocument):
        self.current_page_fn = doc._doc.fileName()
        self.translation_pairs = [TranslationPair.from_json(pair) for pair in load_page_json(doc)]
        self.pair_list.clear()
        for pair in self.translation_pairs:
            self.add_pair_to_list(pair)

    def setup_buttons(self, layout: QBoxLayout):
        button_layout = QHBoxLayout()
        self.add_mask_btn = QPushButton("Add Mask")
        self.add_text_btn = QPushButton("Add Text")
        button_layout.addWidget(self.add_mask_btn)
        button_layout.addWidget(self.add_text_btn)
        layout.addLayout(button_layout)

    def setup_text_styler(self, layout: QBoxLayout):
        styler_layout = QHBoxLayout()
        self.font_selector = QFontComboBox()
        self.font_selector.setCurrentFont(QFont("Arial"))
        self.font_size_selector = QSpinBox()
        self.font_size_selector.setRange(4, 512)
        self.font_size_selector.setValue(24)
        styler_layout.addWidget(self.font_selector)
        styler_layout.addWidget(self.font_size_selector)
        layout.addLayout(styler_layout)

    def setup_text_selector(self, layout: QBoxLayout):
        self.text_selector = QComboBox()
        self.text_selector.addItems(["Both", "Source Only", "Translated Only"])
        layout.addWidget(self.text_selector)

    def setup_pair_list(self, layout: QBoxLayout):
        self.pair_list = QListWidget()
        self.pair_list.setSelectionMode(QAbstractItemView.SingleSelection)
        layout.addWidget(self.pair_list)

    def setup_connections(self):
        self.add_mask_btn.clicked.connect(self.add_new_mask)
        self.add_text_btn.clicked.connect(self.add_new_text)
        self.text_selector.currentIndexChanged.connect(self.update_text_list)
        self.pair_list.itemSelectionChanged.connect(self.translation_item_clicked)
        self.font_selector.currentFontChanged.connect(self.update_pair_styles)
        self.font_size_selector.valueChanged.connect(self.update_pair_styles)
        self.watcher = QTimer(self)
        self.watcher.setInterval(1000)
        self.watcher.timeout.connect(self.update_shapes)
        self.watcher.start(1000)

    @ensure_active_document
    def update_shapes(self, doc: KritaDocument):
        if doc._doc.fileName() != self.current_page_fn:
            self.load_page(doc)
        for pair in self.translation_pairs:
            update_text_shape(doc, pair.uid, pair.translated_text.toPlainText(), pair.font, pair.size)
        
        pair_json = [pair.to_json() for pair in self.translation_pairs]
        if self.cached_pair_json != pair_json:
            self.cached_pair_json = pair_json
            save_page_json(doc, pair_json)

    @ensure_active_document
    def translation_item_clicked(self, doc: KritaDocument):
        row = self.pair_list.selectedIndexes()[0].row()
        pair = self.translation_pairs[row]
        layer, shape, _ = get_text_group_shape_by_id(doc, pair.uid)
        if layer and shape:
            doc._doc.setActiveNode(layer)
            shape.select()
        self.font_selector.setCurrentFont(QFont(pair.font))
        self.font_size_selector.setValue(pair.size)

    @ensure_active_document
    def add_new_mask(self, doc: KritaDocument):
        mask_group = get_root_group(doc, "mask")
        new_mask_number = self.get_next_number(mask_group)
        new_mask = doc._doc.createNode(f"Mask {new_mask_number}", "paintlayer")
        mask_group.addChildNode(new_mask, None)

    @ensure_active_document
    def add_new_text(self, doc: KritaDocument):
        pair = TranslationPair(uid=token_urlsafe(8))
        self.translation_pairs.append(pair)
        self.add_pair_to_list(pair)
        
        text_group = get_root_group(doc, "text")
        new_text_number = self.get_next_number(text_group)
        layername = f"Text {new_text_number}"
        new_text_layer = doc._doc.createNode(layername, "vectorlayer")
        text_group.addChildNode(new_text_layer, None)
        
        x, y, w, h = self.get_text_bounds(doc)
        doc._doc.refreshProjection()
        new_text_layer = cast(VectorLayer, text_group.findChildNodes(layername)[0])
        new_text_layer.addShapesFromSvg(new_text_shape(pair.uid, x, y, w, h, doc._doc))
        
        pair.font = self.font_selector.currentFont().family()
        pair.size = self.font_size_selector.value()
        self.update_pair_styles()

    def get_text_bounds(self, doc: KritaDocument) -> tuple[float, float, float, float]:
        if doc.layers.active.parent_layer and doc.layers.active.parent_layer.name == MASK_GRP_NAME:
            bounds = doc.layers.active.bounds
            return bounds.offset[0], bounds.offset[1], bounds.extent[0], bounds.extent[1]
        return 100, 100, 200, 100

    def add_pair_to_list(self, pair: TranslationPair):
        item = QListWidgetItem(self.pair_list)
        self.pair_list.setItemWidget(item, pair)
        item.setSizeHint(pair.sizeHint())
        pair.source_text.focus_in.connect(lambda: item.setSelected(True))
        pair.translated_text.focus_in.connect(lambda: item.setSelected(True))
        self.update_text_list()

    def update_text_list(self):
        mode = self.text_selector.currentText()
        for pair in self.translation_pairs:
            pair.source_text.setVisible(mode in ["Both", "Source Only"])
            pair.translated_text.setVisible(mode in ["Both", "Translated Only"])
            pair.translated_text.setFont(QFont(pair.font, UI_FONT_SIZE))

    def get_next_number(self, group: GroupLayer) -> int:
        numbers = [int_tryparse(node.name().rsplit(" ", 1)[-1]) for node in group.childNodes()]
        numbers = [num for num in numbers if num is not None]
        return max(numbers + [0]) + 1

    def update_pair_styles(self):
        font = self.font_selector.currentFont().family()
        size = self.font_size_selector.value()
        for item in self.pair_list.selectedItems():
            pair = self.translation_pairs[self.pair_list.row(item)]
            pair.font = font
            pair.size = size
        self.update_text_list()

    def canvasChanged(self, canvas):
        pass

def int_tryparse(x: str) -> Optional[int]:
    try:
        return int(x)
    except ValueError:
        return None