import sys 
import xml.etree.ElementTree as ET

from PyQt5.QtSvg import QSvgWidget
from PyQt5.QtWidgets import QLineEdit, QSlider,QApplication,QWidget,QVBoxLayout,QFontComboBox
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QFontMetrics

def guide_rect(x,y,w,h):
    ele=ET.Element('rect')
    ele.set('transform', 'translate({0}, {1})'.format(x,y))
    ele.set('fill', 'none')
    ele.set('stroke', '#00000000')
    ele.set('stroke-width', '10')
    ele.set('stroke-linecap', 'square')
    ele.set('stroke-linejoin', 'bevel')
    ele.set('width', str(w))
    ele.set('height', str(h))
    return ele

def textgen(txt, w, font, fontsize=24, line_multiplier=1.0):
    # Create QFont and QFontMetrics objects
    qfont = QFont(font, fontsize)
    font_metrics = QFontMetrics(qfont)

    ele = ET.Element('text')
    ele.set('id', 'ft_text/i')
    ele.set("krita:textVersion","3")
    ele.set("krita:userichtext","false")
    ele.set('text-rendering', 'auto')
    eleattr = {
        'text-anchor': 'middle',
        'fill': '#000000',
        'stroke-opacity': '0',
        'stroke': '#000000',
        'stroke-width': '0',
        'stroke-linecap': 'square',
        'stroke-linejoin': 'bevel',
        'kerning': 'none',
        'letter-spacing': '0',
        'word-spacing': '0'
    }
    for key, value in eleattr.items():
        ele.set(key, value)
    css={
        "text-align": "start",
        "text-align-last": "auto",
        "font-family": font,
        "font-size": fontsize
    }
    ele.set('style', ';'.join([f'{x}:{y}' for x,y in css.items()]))

    # Word wrap logic using QFontMetrics
    words_chunks = txt.split('\n')
    lines = []
    current_line = []
    current_width = 0
    max_width = int(w)

    for chunk in words_chunks:
        words = chunk.split()

        for word in words:
            
            word_width = font_metrics.horizontalAdvance(word)
            if current_width + word_width <= max_width:
                current_line.append(word)
                current_width += word_width + font_metrics.horizontalAdvance(' ')
            else:
                lines.append(' '.join(current_line))
                current_line = [word]
                current_width = word_width

        lines.append(' '.join(current_line))
        current_line = []
        current_width = 0

    # Create tspan elements for each line
    # y_offset = 0
    line_height = font_metrics.height()
    totaly=0
    for line in lines:
        tspan = ET.SubElement(ele, 'tspan')
        tspan.set('x', str(max_width/2))  # Set x to 0 for all lines
        tspan.set('dy', str(line_height*line_multiplier))
        totaly+=line_height*line_multiplier
        tspan.text = line

    ele.set('transform', f'translate({w/2}, {font_metrics.capHeight()})')
    return ele,totaly

def main():
    app = QApplication(sys.argv)

    # Create main window
    main_window = QWidget()
    main_window.setGeometry(50, 50, 759, 850)  # Adjusted height to accommodate new layout

    # Create layout
    layout = QVBoxLayout()

    # Create and add SVG widget
    svgWidget = QSvgWidget()
    layout.addWidget(svgWidget)

    # Create and add QLineEdit for text input
    text_input = QLineEdit()
    text_input.setPlaceholderText("Enter text here")
    layout.addWidget(text_input)

    # Create and add QSlider for width adjustment
    width_slider = QSlider(Qt.Horizontal)
    width_slider.setRange(100, 500)  # Set min and max width values
    width_slider.setValue(300)  # Set default width
    layout.addWidget(width_slider)

    # Create and add QFontComboBox for font selection
    font_selector = QFontComboBox()
    font_selector.setCurrentFont(QFont("Arial"))  # Set default font
    layout.addWidget(font_selector)

    # Create and add QLineEdit for displaying raw SVG code (readonly)
    svg_code_display = QLineEdit()
    svg_code_display.setReadOnly(True)
    svg_code_display.setPlaceholderText("Raw SVG code will be displayed here")
    layout.addWidget(svg_code_display)

    # Set the layout for the main window
    main_window.setLayout(layout)

    # Function to update SVG
    def update_svg():
        text = text_input.text()
        width = width_slider.value()
        font = font_selector.currentFont().family()
        svg_content = textgen(text, width, font)
        svgWidget.load(svg_content.encode('utf-8'))
        svg_code_display.setText(svg_content)  # Display raw SVG code

    # Connect signals to update_svg function
    text_input.textChanged.connect(update_svg)
    width_slider.valueChanged.connect(update_svg)
    font_selector.currentFontChanged.connect(update_svg)

    # Initial SVG update
    update_svg()

    main_window.show()
    sys.exit(app.exec_())

if __name__=="__main__":
    main()
