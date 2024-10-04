from typing import Literal, Union
from krita import DockWidget, Krita
import krita
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import (QPushButton, QHBoxLayout, QFontComboBox,
                             QWidget, QVBoxLayout, QListWidget, QListWidgetItem, QSpinBox,
                             QComboBox, QTextEdit)
from PyQt5.QtGui import QFont
from .svgtext import guide_rect, textgen
from secrets import token_urlsafe
import xml.etree.ElementTree as ET
import inspect
import html
import json


MASK_GRP_NAME = "ft_masks"
TEXT_GRP_NAME = "ft_texts"
METADATA_LAYER_NAME = "ft_metadata"
ORIG_LAYER_NAME = "Background"
UI_FONT_SIZE = 16

DOCKER_TITLE = "Fan Translation Docker"

def findOrCreateLayer(doc: krita.Document, layerName: str, layerType: str) -> krita.Node:
    nodesList = doc.topLevelNodes()
    layer = None
    for node in nodesList:
        if node.type() == layerType and node.name() == layerName:
            layer = node
            break
    if layer is None:
        if layerType == "grouplayer":
            layer = doc.createGroupLayer(layerName)
        elif layerType == "vectorlayer":
            layer = doc.createVectorLayer(layerName)
        doc.rootNode().addChildNode(layer, None) # type: ignore
    return layer

def getRootGroup(doc: krita.Document, groupof: Union[Literal["text"], Literal["mask"]]) -> krita.GroupLayer:
    GRP_NAME = {"text": TEXT_GRP_NAME, "mask": MASK_GRP_NAME}[groupof]
    return findOrCreateLayer(doc, GRP_NAME, "grouplayer")

def getMetadataLayer(doc: krita.Document) -> krita.VectorLayer:
    return findOrCreateLayer(doc, METADATA_LAYER_NAME, "vectorlayer")

def getTextGroupShapeById(doc:krita.Document,uid:str):
    grp=getRootGroup(doc,"text")
    for layer in grp.childNodes():
        if layer.type() != "vectorlayer":
            continue
        rect,text=None,None
        for shp in layer.shapes():
            elem=ET.fromstring(shp.toSvg())
            if elem.get("id")==f'ft_guide/{uid}':
                rect=shp
            if elem.find(f".//tspan[.='ft_text/{uid}']") is not None:
                text=shp
            if rect is not None and text is not None:
                return layer,rect,text
    return None, None, None

shape_cache={}
def update_text_shape(doc: krita.Document, uid: str, new_text: str, font: str = "Arial", size: int = UI_FONT_SIZE):
    text_layer, rect_shape, text_shape = getTextGroupShapeById(doc, uid)
    if text_layer is None or rect_shape is None:
        return

    guide_rect = ET.fromstring(rect_shape.toSvg())
    x, y, w, h = extract_rect_properties(guide_rect)
    
    # Check if the shape exists in the cache
    if uid in shape_cache:
        cached_data = shape_cache[uid]
        # Compare current values with cached values
        if (x, y, w, h) == cached_data['rect'] and \
           (new_text, font, size) == cached_data['text']:
            return  # No changes, skip update

    # Create new text element
    new_text_elem = create_new_text_element(new_text, w, font, uid, x, y, size)
    svg_string = create_svg_string(doc, new_text_elem)
    
    if text_shape is not None:
        text_shape.remove()
    text_layer.addShapesFromSvg(svg_string)

    # Update cache
    shape_cache[uid] = {
        'rect': (x, y, w, h),
        'text': (new_text, font, size)
    }
def extract_rect_properties(guide_rect):
    x, y = extract_translate_values(guide_rect.get('transform', ''))
    w = float(guide_rect.get('width', 100))
    h = float(guide_rect.get('height', 50))
    return x, y, w, h

def extract_translate_values(transform):
    x, y = 0, 0
    if transform.startswith('translate('):
        translate_values = transform.split('(')[1].split(')')[0].split(',')
        if len(translate_values) >= 2:
            x = float(translate_values[0].strip())
            y = float(translate_values[1].strip())
    return x, y

def create_new_text_element(new_text, w, font, uid, x, y,size):
    new_text_elem = textgen(new_text, w, font,size)
    new_text_elem.set('id', f'ft_text/{uid}')
    sub = ET.SubElement(new_text_elem, "tspan", {"style": "fill:#00deadcd"})
    sub.text = f'ft_text/{uid}'
    sub.set("x", "0")
    new_text_elem.set('transform', f'translate({x}, {y})')
    return new_text_elem

def create_svg_string(doc, new_text_elem):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{doc.width()}" height="{doc.height()}">'
            f'{ET.tostring(new_text_elem, encoding="unicode")}'
            '</svg>')

def new_text_shape(uid,w,h):
    R=guide_rect(100,100,100,50)
    R.set('id', f'ft_guide/{uid}')
    
    T=textgen("Text",100,"Ariel")
    T.set('id', f'ft_text/{uid}')
    # Hacky way to set hidden attr on krita svg system
    ET.SubElement(T,"tspan",{"style":"fill:#00deadcd"}).text=f'ft_text/{uid}'
    
    # Create an SVG string
    svg_string = f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}">'
    svg_string += ET.tostring(R, encoding='unicode')
    svg_string += ET.tostring(T, encoding='unicode')
    svg_string += '</svg>'
    return svg_string

def save_page_json(doc:krita.Krita,content:dict):
    layer=getMetadataLayer(doc)
    text_shape=layer.shapes()[0]
    text_shape.remove()
    jsonstr=json.dumps(content)
    svg=f'<svg xmlns="http://www.w3.org/2000/svg"><text fill="#00feadff"><tspan x="0">{html.escape(jsonstr)}</tspan></text></svg>'
    layer.addShapesFromSvg(svg)

def load_page_json(doc:krita.Krita,content:dict):
    layer=getMetadataLayer(doc)
    text_shape=layer.shapes()[0]
    nd = ET.fromstring(text_shape.toSvg()).find("../text/tspan[0]")
    if nd:
        return json.loads(html.unescape(nd.text)) # type: ignore
    return {}

class TranslationPair(QWidget):
    def __init__(self, uid, source="", translation=""):
        super().__init__()
        layout = QVBoxLayout()
        self.uid=uid
        self.font="Ariel"
        self.text_size=24
        self.source_text = QTextEdit(source)
        self.source_text.setMaximumHeight(self.source_text.fontMetrics().lineSpacing() * 2 + 10)
        self.source_text.setStyleSheet("background-color: #333;")
        self.translated_text = QTextEdit(translation)
        self.translated_text.setMaximumHeight(self.translated_text.fontMetrics().lineSpacing() * 2 + 10)
        self.translated_text.setStyleSheet("background-color: #404040;")
        layout.addWidget(self.source_text)
        layout.addWidget(self.translated_text)
        self.setLayout(layout)
    def toJSON(self):
        return {
            "orig":self.source_text.toPlainText(),
            "tran":self.translated_text.toPlainText(),
            "font":self.font,
            "size":self.text_size
        }

def ensure_active_document(func):
    def wrapper(self, *args, **kwargs):
        doc = Krita.instance().activeDocument()
        if doc is None:
            return
        arl=len(inspect.signature(func).parameters)-2
        return func(self, doc, *args[:arl], **kwargs)
    return wrapper  # type: ignore

class TranslateDocker(DockWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(DOCKER_TITLE)
        self.setup_ui()
        self.setup_connections()
        self.translation_pairs: list[TranslationPair] = []

    def setup_ui(self):
        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)

        self.setup_buttons(main_layout)
        self.setup_text_selector(main_layout)
        self.setup_text_styler(main_layout)
        self.setup_pair_list(main_layout)

        self.setWidget(main_widget)

    def setup_buttons(self, layout):
        button_layout = QHBoxLayout()
        self.add_mask_btn = QPushButton("Add Mask")
        self.add_text_btn = QPushButton("Add Text")
        button_layout.addWidget(self.add_mask_btn)
        button_layout.addWidget(self.add_text_btn)
        layout.addLayout(button_layout)

    def setup_text_styler(self, layout):
        styler_layout = QHBoxLayout()

        self.font_selector = QFontComboBox()
        self.font_selector.setCurrentFont(QFont("Arial"))
        styler_layout.addWidget(self.font_selector)

        self.font_size_selector = QSpinBox()
        self.font_size_selector.setRange(4, 512)
        self.font_size_selector.setValue(24)
        styler_layout.addWidget(self.font_size_selector)
        layout.addLayout(styler_layout)

    def setup_text_selector(self, layout):
        self.text_selector = QComboBox()
        self.text_selector.addItems(["Both", "Source Only", "Translated Only"])
        layout.addWidget(self.text_selector)

    def setup_pair_list(self, layout):
        self.pair_list = QListWidget()
        layout.addWidget(self.pair_list)

    def setup_connections(self):
        self.add_mask_btn.clicked.connect(self.addNewMask)
        self.add_text_btn.clicked.connect(self.addNewText)
        self.text_selector.currentIndexChanged.connect(self.updateTextList)
        self.pair_list.itemClicked.connect(self.translationItemClicked)
        self.font_selector.currentFontChanged.connect(self.updatePairStyles)
        self.font_size_selector.valueChanged.connect(self.updatePairStyles)

        self.watcher = QTimer(self)
        self.watcher.setInterval(1000)
        self.watcher.timeout.connect(self.updateShapes)
        self.watcher.start(1000)

    @ensure_active_document
    def updateShapes(self, doc):
        for pair in self.translation_pairs:
            update_text_shape(doc, pair.uid, pair.translated_text.toPlainText(), pair.font, pair.text_size)

    @ensure_active_document
    def translationItemClicked(self, doc, item):
        row = self.pair_list.row(item)
        uid = self.translation_pairs[row].uid
        layer, shape, _ = getTextGroupShapeById(doc, uid)
        if shape:
            doc.setActiveNode(layer)
            shape.select()

    @ensure_active_document
    def addNewMask(self, doc):
        mask_group = getRootGroup(doc, "mask")
        new_mask_number = self.get_next_number(mask_group)
        new_mask = doc.createNode(f"Mask {new_mask_number}", "paintlayer")
        mask_group.addChildNode(new_mask, None) # type: ignore

    @ensure_active_document
    def addNewText(self, doc):
        pair = TranslationPair(uid=token_urlsafe(8))
        self.translation_pairs.append(pair)
        self.add_pair_to_list(pair)
        
        text_group = getRootGroup(doc, "text")
        new_text_number = self.get_next_number(text_group)
        layername = f"Text {new_text_number}"
        new_text_layer = doc.createNode(layername, "vectorlayer")
        text_group.addChildNode(new_text_layer, None) # type: ignore
        
        doc.refreshProjection()
        new_text_layer = text_group.findChildNodes(layername)[0]
        new_text_layer.addShapesFromSvg(new_text_shape(pair.uid, doc.width(), doc.height()))
        
        # Set pair's font to the current selected font
        pair.font = self.font_selector.currentFont().family()
        pair.text_size = self.font_size_selector.value()
        self.updatePairStyles()

    def add_pair_to_list(self, pair):
        item = QListWidgetItem(self.pair_list)
        self.pair_list.setItemWidget(item, pair)
        item.setSizeHint(pair.sizeHint())
        self.updateTextList()

    def updateTextList(self):
        mode = self.text_selector.currentText()
        for pair in self.translation_pairs:
            pair.source_text.setVisible(mode in ["Both", "Source Only"])
            pair.translated_text.setVisible(mode in ["Both", "Translated Only"])
            pair.translated_text.setFont(QFont(pair.font))

    def get_next_number(self, group):
        numbers = [int_tryparse(node.name().rsplit(" ", 1)[-1]) for node in group.childNodes()]
        numbers = [num for num in numbers if num is not None]
        return max(numbers + [0]) + 1

    def updatePairStyles(self):
        font = self.font_selector.currentFont().family()
        size = self.font_size_selector.value()
        selected_items = self.pair_list.selectedItems()
        for item in selected_items:
            pair = self.translation_pairs[self.pair_list.row(item)]
            pair.font = font
            pair.text_size = size
            pair.source_text.setFont(QFont(font, UI_FONT_SIZE))

    def canvasChanged(self, canvas):
        pass
    
def int_tryparse(x: str) -> Union[int, None]:
    try:
        return int(x)
    except ValueError:
        return None