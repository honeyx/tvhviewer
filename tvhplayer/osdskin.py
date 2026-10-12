"""OSD skin support for TVHviewer.

Reads skins in the XML "OSDSkin 1.1" layout (one folder per skin containing
index.xml, font.xml, one XML file per OSD window and an Images/ folder) from
the user's OSDskins directory and paints them with QPainter.

No skin is shipped with TVHviewer - users copy skins they are entitled to use
into the OSDskins folder themselves.
"""
import os
import re
import xml.etree.ElementTree as ET
from datetime import datetime

from PyQt5.QtCore import Qt, QRectF, QPointF
from PyQt5.QtGui import QColor, QPainter, QPixmap, QFont
from PyQt5.QtWidgets import QWidget

# Which skin file draws which OSD (by file name, as found in the skin folder)
WINDOW_FILES = {
    'volume': 'myVolume.xml',
    'clock': 'myClock.xml',
    'miniepg': 'myMiniEPG.xml',
}

_TOKEN = re.compile(r'#[A-Za-z][A-Za-z0-9_]*(?:\.[A-Za-z0-9_:]+)*')
_TIME_PARTS = re.compile(r'yyyy|mmmm|dddd|hh|nn|ss|dd|mm')
_TIME_MAP = {'yyyy': '%Y', 'mmmm': '%B', 'dddd': '%A', 'hh': '%H',
             'nn': '%M', 'ss': '%S', 'dd': '%d', 'mm': '%m'}


def parse_color(text, default='FFFFFFFF'):
    """'AARRGGBB' (hex) -> QColor"""
    text = (text or default).strip()
    try:
        value = int(text, 16)
    except ValueError:
        value = int(default, 16)
    return QColor((value >> 16) & 255, (value >> 8) & 255, value & 255, (value >> 24) & 255)


def _fields(element):
    """Child elements as a lower-cased {tag: text} dict (skins mix X/x, Y/y)"""
    return {child.tag.lower(): (child.text or '').strip() for child in element
            if child.tag.lower() != 'subcontrols'}


def _num(fields, key, default=0.0):
    try:
        return float(fields.get(key, default))
    except ValueError:
        return float(default)


class OSDWindow:
    """One parsed skin window: a flat list of controls (dicts)"""

    def __init__(self, path):
        root = ET.parse(path).getroot()
        self.controls = []
        items = root.find('items')
        for item in (items if items is not None else []):
            ctl = _fields(item)
            subs = item.find('subcontrols')
            ctl['subs'] = [_fields(sub) for sub in subs] if subs is not None else []
            self.controls.append(ctl)


class OSDSkin:
    def __init__(self, folder):
        self.folder = folder
        self.name = os.path.basename(folder)
        self.size_x, self.size_y = 1280.0, 720.0
        self.author = ''
        self.fonts = {}
        self.label_defaults = {}
        self._windows = {}
        self._pixmaps = {}
        self._image_index = None
        self._load_info()
        self._load_fonts()
        self._load_references()

    # -- loading ---------------------------------------------------------
    def _load_info(self):
        path = os.path.join(self.folder, 'index.xml')
        if not os.path.isfile(path):
            return
        try:
            info = _fields(ET.parse(path).getroot())
        except ET.ParseError:
            return
        self.name = info.get('skinname') or self.name
        self.author = info.get('author', '')
        self.size_x = _num(info, 'sizex', 1280) or 1280.0
        self.size_y = _num(info, 'sizey', 720) or 720.0

    def _load_fonts(self):
        path = os.path.join(self.folder, 'font.xml')
        if not os.path.isfile(path):
            return
        try:
            root = ET.parse(path).getroot()
        except ET.ParseError:
            return
        for font in root.iter('font'):
            f = _fields(font)
            if f.get('name'):
                self.fonts[f['name'].lower()] = (f.get('filename', ''), int(_num(f, 'height', 20)),
                                                 int(_num(f, 'style', 0)))

    def _load_references(self):
        """references.xml holds per-type defaults; labels without their own
        font/colour/alignment inherit them (typically dark text)."""
        path = os.path.join(self.folder, 'references.xml')
        if not os.path.isfile(path):
            return
        try:
            root = ET.parse(path).getroot()
        except ET.ParseError:
            return
        for control in root.findall('control'):
            fields = _fields(control)
            if fields.get('type', '').lower() == 'label':
                self.label_defaults = {k: v for k, v in fields.items()
                                       if k in ('font', 'textcolor', 'verticalalign', 'align')}
                break

    @staticmethod
    def is_skin_folder(folder):
        return os.path.isfile(os.path.join(folder, 'index.xml')) and \
            any(os.path.isfile(os.path.join(folder, f)) for f in WINDOW_FILES.values())

    # -- lookups ---------------------------------------------------------
    def window(self, key):
        if key not in self._windows:
            path = os.path.join(self.folder, WINDOW_FILES[key])
            window = OSDWindow(path) if os.path.isfile(path) else None
            if window is not None:
                for ctl in window.controls:
                    if ctl.get('type', '').lower() == 'label':
                        for k, v in self.label_defaults.items():
                            ctl.setdefault(k, v)
            self._windows[key] = window
        return self._windows[key]

    def pixmap(self, name):
        """Image from the skin's Images folder (case-insensitive), or None"""
        if not name or name == '-':
            return None
        if self._image_index is None:
            images = os.path.join(self.folder, 'Images')
            self._image_index = {f.lower(): os.path.join(images, f)
                                 for f in os.listdir(images)} if os.path.isdir(images) else {}
        key = name.replace('\\', '/').split('/')[-1].lower()
        if key not in self._pixmaps:
            path = self._image_index.get(key)
            if not path and os.path.isfile(name):  # absolute path (e.g. channel logo)
                path = name
            pix = QPixmap(path) if path else None
            self._pixmaps[key] = pix if pix is not None and not pix.isNull() else None
        return self._pixmaps[key]

    def qfont(self, name):
        family, height, style = self.fonts.get((name or 'defaultfont').lower(),
                                               self.fonts.get('defaultfont', ('', 24, 0)))
        font = QFont(family) if family else QFont()
        font.setPixelSize(max(1, height))
        font.setBold(bool(style & 1))
        return font


def expand(text, values):
    """Replace #placeholders in a skin string using values (lower-case keys)"""
    def sub(match):
        token = match.group(0)
        low = token.lower()
        if low.startswith('#time.'):
            fmt = _TIME_PARTS.sub(lambda m: _TIME_MAP[m.group(0)], token[6:].replace('_', ' '))
            return values.get('_now', datetime.now()).strftime(fmt)
        return str(values.get(low[1:], ''))
    return _TOKEN.sub(sub, text or '').strip() if text and '#' in text else (text or '')


def _rect(ctl, parent=None):
    """Control rectangle; sub-controls without x/y/size inherit the parent's"""
    def get(key):
        return _num(ctl, key, _num(parent, key) if parent else 0)
    return QRectF(get('x'), get('y'), get('width'), get('height'))


# The host program shows/hides some controls by their id; this skin family
# uses 203=recording, 204=timeshift, 205=encrypted, 206=teletext.
_ID_FLAGS = {'203': 'recording', '204': 'timeshift', '205': 'encrypted', '206': 'teletext'}


def _hidden(ctl, values):
    """True if the control belongs to a feature that isn't active right now"""
    flag = None
    if 'timeshift' in (ctl.get('label', '') + ' ' + ctl.get('description', '')).lower():
        flag = 'timeshift'
    elif ctl.get('id') in _ID_FLAGS and '#' not in ctl.get('texture', ''):
        flag = _ID_FLAGS[ctl['id']]
    return flag is not None and not values.get(flag)


def _percent(value):
    try:
        return max(0.0, min(100.0, float(str(value).replace('%', '').strip())))
    except ValueError:
        return 0.0


def _draw_image(painter, skin, ctl, values, rect):
    texture = expand(ctl.get('texture', ''), values)
    pix = skin.pixmap(texture)
    if pix is not None:
        target = QRectF(rect)
        if target.width() <= 0 or target.height() <= 0:
            target = QRectF(rect.x(), rect.y(), pix.width(), pix.height())
        painter.drawPixmap(target, pix, QRectF(pix.rect()))
    elif ctl.get('graphicstyp', '').lower() == 'rectangle' and ctl.get('color'):
        color = parse_color(ctl['color'])
        if color.alpha() and rect.width() > 0 and rect.height() > 0:
            painter.fillRect(rect, color)


def _draw_label(painter, skin, ctl, values, rect):
    text = expand(ctl.get('label', ''), values)
    if not text or text == '-':
        return
    font = skin.qfont(ctl.get('font'))
    painter.setFont(font)
    align = {'right': Qt.AlignRight, 'center': Qt.AlignHCenter}.get(ctl.get('align', '').lower(), Qt.AlignLeft)
    valign = {'top': Qt.AlignTop, 'bottom': Qt.AlignBottom}.get(ctl.get('verticalalign', '').lower(), Qt.AlignVCenter)
    flags = int(align | valign)
    if rect.height() >= font.pixelSize() * 1.8:
        flags |= Qt.TextWordWrap
    if ctl.get('shadow', '').lower() == 'true':
        painter.setPen(QColor(0, 0, 0, 200))
        painter.drawText(rect.translated(_num(ctl, 'shadowx', 1), _num(ctl, 'shadowy', 1)), flags, text)
    painter.setPen(parse_color(ctl.get('textcolor'), 'FFFFFFFF'))
    painter.drawText(rect, flags, text)


def _draw_progress(painter, skin, ctl, values, rect):
    """progress / tickprogress: draw the background part, then the 'mid' part
    clipped to the current value (horizontal, or vertical when direction=1)."""
    percent = _percent(expand(ctl.get('label', ''), values))
    for sub in ctl['subs']:
        name = sub.get('description', '').lower()
        if name in ('left', 'right', 'label'):
            continue
        sub_rect = _rect(sub, ctl)
        sub_rect.moveTo(rect.x(), rect.y())
        painter.save()
        if name == 'mid':
            if sub.get('direction', '0') == '1':
                filled = sub_rect.height() * percent / 100.0
                painter.setClipRect(QRectF(sub_rect.x(), sub_rect.bottom() - filled,
                                           sub_rect.width(), filled))
            else:
                painter.setClipRect(QRectF(sub_rect.x(), sub_rect.y(),
                                           sub_rect.width() * percent / 100.0, sub_rect.height()))
        _draw_image(painter, skin, sub, values, sub_rect)
        painter.restore()


def render(painter, skin, key, values, width, height):
    """Paint OSD window `key` (volume/clock/miniepg) into a width x height area"""
    window = skin.window(key)
    if window is None:
        return
    painter.save()
    painter.setRenderHints(QPainter.Antialiasing | QPainter.TextAntialiasing |
                           QPainter.SmoothPixmapTransform)
    painter.scale(width / skin.size_x, height / skin.size_y)
    for ctl in window.controls:
        if _hidden(ctl, values):
            continue
        ctype = ctl.get('type', '').lower()
        rect = _rect(ctl)
        if ctype == 'image':
            _draw_image(painter, skin, ctl, values, rect)
        elif ctype == 'label':
            _draw_label(painter, skin, ctl, values, rect)
        elif ctype in ('progress', 'tickprogress'):
            _draw_progress(painter, skin, ctl, values, rect)
        # buttons / spincontrols / videowindow are interactive or HTPC-only: skipped
    painter.restore()


def find_skins(root_folder):
    """{display name: folder} for every valid skin below root_folder"""
    skins = {}
    if not os.path.isdir(root_folder):
        return skins
    for entry in sorted(os.listdir(root_folder)):
        folder = os.path.join(root_folder, entry)
        if os.path.isdir(folder) and OSDSkin.is_skin_folder(folder):
            skins[entry] = folder
    return skins


class OSDOverlay(QWidget):
    """Frameless, click-through, translucent window painted from a skin.
    It sits over the video area and can show several OSD layers at once
    (e.g. volume bar + mini EPG); each layer hides itself after its timeout
    and the window hides when no layer is left."""

    def __init__(self, parent=None):
        super().__init__(parent, Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint |
                         Qt.WindowDoesNotAcceptFocus)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.skin = None
        self.values = {}
        self.layers = {}  # key -> deadline (time.monotonic()), None = stay
        from PyQt5.QtCore import QTimer
        self._timer = QTimer(self)
        self._timer.setInterval(200)
        self._timer.timeout.connect(self._expire)

    def show_layer(self, skin, key, values, area_rect, timeout_ms=4000):
        """area_rect: QRect in global screen coordinates (the video area)"""
        import time
        self.skin, self.values = skin, values
        self.layers[key] = time.monotonic() + timeout_ms / 1000.0 if timeout_ms else None
        self.setGeometry(area_rect)
        self.show()
        self.raise_()
        self.update()
        self._timer.start()

    def hide_layer(self, key):
        self.layers.pop(key, None)
        if not self.layers:
            self._timer.stop()
            self.hide()
        else:
            self.update()

    def _expire(self):
        import time
        now = time.monotonic()
        for key in [k for k, deadline in self.layers.items() if deadline is not None and deadline <= now]:
            self.layers.pop(key, None)
        if not self.layers:
            self._timer.stop()
            self.hide()
        else:
            self.update()

    def paintEvent(self, event):
        if self.skin is None:
            return
        painter = QPainter(self)
        for key in list(self.layers):
            render(painter, self.skin, key, self.values, self.width(), self.height())
        painter.end()
