"""OSD skin support for TVHviewer.

Reads skins in the XML "OSDSkin 1.1" layout (one folder per skin containing
index.xml, font.xml, one XML file per OSD window and an Images/ folder) from
the user's OSDskins directory and paints them with QPainter.

No skin is shipped with TVHviewer - users copy skins they are entitled to use
into the OSDskins folder themselves.
"""
import os
import re
import time
import xml.etree.ElementTree as ET
from datetime import datetime

from PyQt5.QtCore import Qt, QRectF, QPointF, QLocale
from PyQt5.QtGui import (QColor, QPainter, QPixmap, QFont, QFontMetrics, QLinearGradient,
                         QPolygonF, QPen)
from PyQt5.QtWidgets import QWidget

# Which skin file draws which OSD (by file name, as found in the skin folder)
WINDOW_FILES = {   # every entry: candidate file names, first existing one wins (case-insensitive)
    'volume': ('myVolume.xml',),
    'clock': ('myClock.xml',),
    'miniepg': ('myMiniEPG.xml',),
    'channels': ('mychannels.xml',),
    'home': ('home.xml', 'myhome.xml'),          # sub menus (Media Center, System, ...)
    'homemain': ('myhome.xml', 'home.xml'),      # the main menu
    'recordings': ('myrecordings.xml',),
    'videos': ('mymovies.xml', 'myvideo.xml'),
    'pictures': ('mypics.xml',),
    'music': ('mymusicfiles.xml',),
    'epgchannel': ('myepgchannel.xml',),
    'timeline': ('mytvguide.xml',), 'timer': ('myTimer.xml',),
}

_TOKEN = re.compile(r'#[A-Za-z][A-Za-z0-9_]*(?:\.[A-Za-z0-9_:]+)*(?:[+-]\d)?')
_TIME_TOKEN = re.compile(r'#Time\.[^\s#]+', re.I)
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


def _parse_control(element):
    """A control as a dict of its fields plus 'subs' (parsed recursively)"""
    ctl = _fields(element)
    subs = element.find('subcontrols')
    ctl['subs'] = [_parse_control(sub) for sub in subs] if subs is not None else []
    return ctl


class OSDWindow:
    """One parsed skin window: a flat list of controls (dicts)"""

    def __init__(self, path):
        root = ET.parse(path).getroot()
        self.default_focus = (root.get('default') or '').strip()
        self.controls = []
        self.has_bg = (root.get('hasbg') or '').strip().lower() == 'true'
        # <Backdrop DefaultFile=.. DefaultDifuseColor=..>: full-screen picture behind the window
        # ('-' or empty = none); None = the window has no such element
        backdrop = root.find('Backdrop')
        self.backdrop = None if backdrop is None else (backdrop.get('DefaultFile') or '').strip()
        self.backdrop_color = (backdrop.get('DefaultDifuseColor') or 'FFFFFFFF') if backdrop is not None else 'FFFFFFFF'
        items = root.find('items')
        self.controls = [_parse_control(item) for item in (items if items is not None else [])]


class OSDSkin:
    def __init__(self, folder):
        self.folder = folder
        self.name = os.path.basename(folder)
        self.size_x, self.size_y = 1280.0, 720.0
        self.author = ''
        self.fonts = {}
        self.label_defaults = {}
        self.list_defaults = {}
        self._windows = {}
        self._pixmaps = {}
        self._image_index = None
        self.missing_icons = set()
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

    def _register_font_files(self):
        """font.xml names font *families*; load the skin's own .ttf/.otf files so they exist"""
        from PyQt5.QtGui import QFontDatabase
        try:
            folders = [os.path.join(self.folder, d) for d in os.listdir(self.folder)
                       if d.lower() in ('font', 'fonts') and os.path.isdir(os.path.join(self.folder, d))]
        except OSError:
            return
        for base in folders:
            for dirpath, _dirs, files in os.walk(base):
                for f in files:
                    if f.lower().endswith(('.ttf', '.otf')):
                        QFontDatabase.addApplicationFont(os.path.join(dirpath, f))

    def _load_fonts(self):
        self._register_font_files()
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
            kind = fields.get('type', '').lower()
            if kind == 'label' and not self.label_defaults:
                self.label_defaults = {k: v for k, v in fields.items()
                                       if k in ('font', 'textcolor', 'verticalalign', 'align')}
            elif kind == 'listcontrol' and not self.list_defaults:
                self.list_defaults = {k: v for k, v in fields.items() if k not in (
                    'x', 'y', 'width', 'height', 'id', 'description', 'type')}

    @staticmethod
    def is_skin_folder(folder):
        return os.path.isfile(os.path.join(folder, 'index.xml')) and \
            any(OSDSkin._find_file(folder, names) for names in WINDOW_FILES.values())

    @staticmethod
    def _find_file(folder, names):
        try:
            present = {f.lower(): f for f in os.listdir(folder)}
        except OSError:
            return ''
        for name in names:
            if name.lower() in present:
                return os.path.join(folder, present[name.lower()])
        return ''

    # -- lookups ---------------------------------------------------------
    def window(self, key):
        if key not in self._windows:
            path = self._find_file(self.folder, WINDOW_FILES[key])
            window = OSDWindow(path) if path else None
            if window is not None:
                for ctl in window.controls:
                    if ctl.get('type', '').lower() == 'label':
                        for k, v in self.label_defaults.items():
                            ctl.setdefault(k, v)
                    elif ctl.get('type', '').lower() == 'listcontrol':
                        for k, v in self.list_defaults.items():
                            ctl.setdefault(k, v)
            self._windows[key] = window
        return self._windows[key]

    def _index_images(self):
        """lower-case name -> path for every file below the skin's images folder
        (any spelling of the folder name, sub folders included)"""
        index = {}
        try:
            folders = [os.path.join(self.folder, d) for d in os.listdir(self.folder)
                       if d.lower() in ('images', 'image', 'media') and os.path.isdir(os.path.join(self.folder, d))]
        except OSError:
            folders = []
        for base in folders:
            for dirpath, _dirs, files in os.walk(base):
                for f in files:
                    path = os.path.join(dirpath, f)
                    rel = os.path.relpath(path, base).replace('\\', '/').lower()
                    index.setdefault(rel, path)
                    index.setdefault(f.lower(), path)
        return index

    def pixmap(self, name):
        """Image from the skin's images folder (case-insensitive), or None"""
        if not name or name == '-':
            return None
        if self._image_index is None:
            self._image_index = self._index_images()
        norm = name.replace('\\', '/').lower()
        key = norm
        if key not in self._pixmaps:
            path = self._image_index.get(norm) or self._image_index.get(norm.split('/')[-1])
            if not path and os.path.isfile(name):  # absolute path (e.g. channel logo)
                path = name
            pix = QPixmap(path) if path else None
            self._pixmaps[key] = pix if pix is not None and not pix.isNull() else None
        return self._pixmaps[key]

    def menu_icon(self, name):
        """Icon name for a menu entry. Like DVBViewer, an icon the skin lacks stays
        empty (noted in missing_icons, which the app writes to tvhviewer.log)."""
        if name and self.pixmap(name) is None:
            self.missing_icons.add(name)
        return name or ''

    def qfont(self, name):
        family, height, style = self.fonts.get((name or 'defaultfont').lower(),
                                               self.fonts.get('defaultfont', ('', 24, 0)))
        font = QFont(family) if family else QFont()
        font.setPixelSize(max(1, height))
        font.setBold(bool(style & 1))
        return font


def expand(text, values):
    """Replace #placeholders in a skin string using values (lower-case keys)"""
    def time_sub(match):
        fmt = _TIME_PARTS.sub(lambda m: _TIME_MAP[m.group(0)], match.group(0)[6:].replace('_', ' '))
        return values.get('_now', datetime.now()).strftime(fmt)

    def sub(match):
        return str(values.get(match.group(0).lower()[1:], ''))
    if not text or '#' not in text:
        return text or ''
    text = _TIME_TOKEN.sub(time_sub, text)
    return _TOKEN.sub(sub, text).strip()


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


# Skins label some controls with numbers: ids into the host program's language
# table. These are the ones used by the colour-button legend of the list windows.
UI_STRINGS = {
    'de': {'901': 'TV / Radio / Fav', '902': 'EPG anzeigen', '903': 'Favoriten-Editor', '904': 'Kontext', '3': 'Videos',
           '136': 'Wiedergabeliste', '341': 'DVD', '654': 'Auswerfen',
           },
    'en': {'901': 'TV / Radio / Fav', '902': 'Show EPG', '903': 'Favourites editor', '904': 'Context', '3': 'Videos',
           '136': 'Playlist', '341': 'DVD', '654': 'Eject',
           },
}
# host-supplied captions of file-window buttons (#Lang.xxx placeholders and the view/sort buttons)
LANG_STRINGS = {'#lang.addtoplaylist': 'Add Playlist', '#lang.directoryup': 'Dir. back', '#lang.context': 'Context Menu',
                'view-as button': 'Listenansicht', 'sort button': 'Name'}


def default_pills(skin, ctl):
    """(focus, nofocus) image controls of a list/menu. A sub-image without any texture means the
    host's default pill (lstbtn_*.png, when the skin has them); a texture of '-' means none."""
    focus, nofocus = _sub(ctl, 'imgfocus'), _sub(ctl, 'imgnofocus')
    if focus is None and nofocus is None and skin.pixmap('lstbtn_focus.png'):
        focus = {'texture': ''}                    # no image sub-controls at all: host default pills
    if focus is not None and not focus.get('texture') and skin.pixmap('lstbtn_focus.png'):
        focus = dict(focus, texture='lstbtn_focus.png')
        if nofocus is None and skin.pixmap('lstbtn_nofocus.png'):
            nofocus = {'texture': 'lstbtn_nofocus.png'}
    if nofocus is not None and not nofocus.get('texture') and skin.pixmap('lstbtn_nofocus.png'):
        nofocus = dict(nofocus, texture='lstbtn_nofocus.png')
    return focus, nofocus
_language = 'en'


def set_language(code):
    global _language
    _language = code if code in UI_STRINGS else 'en'


def ui_string(label):
    """A button label: numbers are looked up in the string table, text is kept"""
    label = (label or '').strip()
    if label.isdigit():
        return UI_STRINGS[_language].get(label, '')
    return label


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
    elif ctl.get('graphicstyp', '').lower() in ('rectangle', 'gradient_rectangle') and ctl.get('color'):
        color = parse_color(ctl['color'])
        if color.alpha() and rect.width() > 0 and rect.height() > 0:
            if ctl.get('color2') and 'gradient' in ctl.get('graphicstyp', '').lower():
                from PyQt5.QtGui import QLinearGradient
                grad = QLinearGradient(rect.topLeft(), rect.bottomLeft())
                grad.setColorAt(0, color)
                grad.setColorAt(1, parse_color(ctl['color2']))
                painter.fillRect(rect, grad)
            else:
                painter.fillRect(rect, color)


def _draw_label(painter, skin, ctl, values, rect):
    text = expand(ctl.get('label', ''), values)
    if text.isdigit():   # window title given as a string-table number
        text = UI_STRINGS[_language].get(text, '')
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
    family = skin.fonts.get((ctl.get('font') or 'defaultfont').lower(), ('',))[0].lower()
    if 'mirror' in family:  # reflection under a text: same text, flipped
        painter.save()
        painter.translate(0, rect.center().y())
        painter.scale(1, -1)
        painter.translate(0, -rect.center().y())
        painter.drawText(rect, flags, text)
        painter.restore()
    else:
        painter.drawText(rect, flags, text)


def _draw_button(painter, skin, ctl, values, rect):
    """A skin Button in its unfocused look: its image, plus its label"""
    image = _sub(ctl, 'imgnofocus')
    host_pill = False
    if image is None and _sub(ctl, 'imgfocus') is None and ctl.get('visible', 'true').lower() != 'false' \
            and skin.pixmap('lstbtn_nofocus.png') and _sub(ctl, 'buttonlabel') is not None:
        image, host_pill = {'texture': 'lstbtn_nofocus.png'}, True
    elif image is not None and not image.get('texture') and skin.pixmap('lstbtn_nofocus.png'):
        image, host_pill = dict(image, texture='lstbtn_nofocus.png'), True      # host default pill
    elif image is None and _sub(ctl, 'imgfocus') is not None and not _sub(ctl, 'imgfocus').get('texture') \
            and skin.pixmap('lstbtn_nofocus.png'):
        image, host_pill = {'texture': 'lstbtn_nofocus.png'}, True
    if image:
        _draw_image(painter, skin, dict(image), values, QRectF(rect))
    label = _sub(ctl, 'buttonlabel')
    if not label:
        return
    caption = (label.get('label') or '').strip()
    text = ''
    if caption.isdigit():
        text = ui_string(caption)
    elif caption.lower() in LANG_STRINGS:
        text = LANG_STRINGS[caption.lower()]
    elif not caption or caption == '-':
        text = LANG_STRINGS.get((ctl.get('description') or '').lower(), '')
    elif host_pill:
        text = caption      # plain captions are real texts only on buttons showing the host pill
    if text:
        lab = dict(label)
        lab['label'] = text
        lab['textcolor'] = lab.get('textcolor') or lab.get('disabledcolor') or ('FFFFFFFF' if host_pill else 'FF000000')
        if host_pill and not lab.get('font'):
            lab['font'] = 'font14'
        ox = _num(ctl, 'textoffsetx', 0) or (30 if host_pill else 0)
        lab_rect = QRectF(rect.x() + ox, rect.y(), max(10.0, rect.width() - ox - 2), rect.height())
        _draw_label(painter, skin, lab, values, lab_rect)


def _draw_group_banner(painter, skin, ctl, screen, values, window):
    """Bottom-right group logo (TV / Radio / Favourites); the image carries the title text"""
    wanted = {'tv': '3', 'radio': '4', 'fav': '5'}.get(getattr(screen, 'group', 'tv'), '3')
    if ctl.get('id') != wanted:
        return
    rect = _rect(ctl)
    if rect.width() < 400:   # small toggles are tab buttons (older skins), not a group logo
        return
    image = _sub(ctl, 'imgfocus')
    if image:
        _draw_image(painter, skin, dict(image), values, QRectF(rect))


def _draw_menu_label(painter, skin, ctl, values, rect):
    """Name of the focused menu entry, centred, in the skin's 'selected' colour"""
    text = values.get('menufocustext', '')
    if not text:
        return
    painter.setFont(skin.qfont(ctl.get('font') or ctl.get('font2')))
    painter.setPen(parse_color(ctl.get('selectedcolor') or ctl.get('textcolor'), 'FF45BDFC'))
    painter.drawText(rect, int(Qt.AlignHCenter | Qt.AlignVCenter), text)


def _menu_step(skin, ctl, button):
    """Row pitch of a list menu: the button height, else focus image height plus the Menu's Space"""
    height = _num(button, 'height', 0)
    if height:
        return height
    focus = _sub(ctl, 'imgfocus')
    pix = skin.pixmap(focus.get('texture')) if focus else None
    return (pix.height() if pix and not pix.isNull() else 40) + _num(ctl, 'space', 0)


def menu_is_list(skin, ctl):
    """True when a Menu control is a vertical list rather than a ring/single label"""
    button = _sub(ctl, 'button')
    return bool(button) and _rect(ctl).height() >= _menu_step(skin, ctl, button) * 1.5


def _draw_menu_list(painter, skin, ctl, button, screen, rect):
    """A Menu control that is a vertical list of buttons (e.g. the Default skin's main
    menu): the focused entry sits in the middle row and the list wraps around"""
    step = _menu_step(skin, ctl, button)
    backdrop = _sub(ctl, 'image')
    if backdrop is not None and not backdrop.get('texture'):
        painter.fillRect(_rect(backdrop), QColor(26, 42, 100, 238))   # host-drawn panel behind the list
    focus_img = _sub(ctl, 'imgfocus')
    nofocus_img = _sub(ctl, 'imgnofocus')
    # a missing texture means the host default pill; '-' means none
    if focus_img is not None and not focus_img.get('texture'):
        focus_img = dict(focus_img, texture='lstbtn_focus.png')
    if nofocus_img is None and focus_img is not None and skin.pixmap('lstbtn_nofocus.png'):
        nofocus_img = {'texture': 'lstbtn_nofocus.png'}
    label = _sub(ctl, 'buttonlabel') or {}
    rows = max(1, int(rect.height() // step))
    items, n = screen.items, len(screen.items)
    if n <= rows:
        layout = [(r, r) for r in range(n)]
    else:
        layout = [(r, (screen.index + r - rows // 2) % n) for r in range(rows)]
    painter.save()
    painter.setClipRect(rect)
    painter.setFont(skin.qfont(label.get('font')))
    for row, index in layout:
        row_rect = QRectF(rect.x(), rect.y() + row * step, rect.width(), step)
        selected = index == screen.index
        if selected and focus_img:
            _draw_image(painter, skin, dict(focus_img), {}, QRectF(row_rect))
        elif not selected and nofocus_img and nofocus_img.get('texture'):
            _draw_image(painter, skin, dict(nofocus_img), {}, QRectF(row_rect.adjusted(0, 2, 0, -2)))
        color = (ctl.get('selectedcolor') or label.get('textselectedcolor')) if selected else \
            (label.get('disabledcolor') or label.get('textcolor'))
        painter.setPen(parse_color(color, 'FFFFFFFF'))
        item = items[index]
        text_rect = row_rect.adjusted(_num(button, 'textoffsetx', 0) + 8, 0, -6, 0)
        painter.drawText(text_rect, int(Qt.AlignLeft | Qt.AlignVCenter), item.get('display', item.get('text', '')))
    painter.restore()


def _draw_textbox(painter, skin, ctl, values, rect):
    """Multi-line text (descriptions): wrapped, from the top"""
    text = expand(ctl.get('label', ''), values)
    if not text:
        return
    painter.setFont(skin.qfont(ctl.get('font')))
    painter.setPen(parse_color(ctl.get('textcolor'), 'FFFFFFFF'))
    painter.save()
    painter.setClipRect(rect)
    painter.drawText(rect, int(Qt.AlignLeft | Qt.AlignTop | Qt.TextWordWrap), text)
    painter.restore()


def _draw_progress(painter, skin, ctl, values, rect):
    """progress / tickprogress: draw the background part, then the 'mid' part
    clipped to the current value (horizontal, or vertical when direction=1)."""
    label = expand(ctl.get('label', ''), values)
    if ctl.get('label', '').strip().startswith('#') and not label.strip():
        return                       # no value behind the placeholder (e.g. no programme): no bar at all
    percent = _percent(label)
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


def render(painter, skin, key, values, width, height, screen=None):
    """Paint OSD window `key` (volume/clock/miniepg) into a width x height area"""
    window = skin.window(key)
    if window is None:
        return
    painter.save()
    painter.setRenderHints(QPainter.Antialiasing | QPainter.TextAntialiasing |
                           QPainter.SmoothPixmapTransform)
    painter.scale(width / skin.size_x, height / skin.size_y)
    if screen is not None:
        # the window's own <Backdrop>; windows without one use background.png when hasbg="true"
        name = window.backdrop if window.backdrop else ('background.png' if window.has_bg and window.backdrop != '-' else '')
        backdrop = skin.pixmap(name) if name and name != '-' else None
        if backdrop is not None:
            painter.save()
            painter.setOpacity(painter.opacity() * parse_color(window.backdrop_color, 'FFFFFFFF').alphaF())
            painter.drawPixmap(QRectF(0, 0, skin.size_x, skin.size_y), backdrop, QRectF(backdrop.rect()))
            painter.restore()
    for ctl in window.controls:
        if _hidden(ctl, values):
            continue
        ctype = ctl.get('type', '').lower()
        rect = _rect(ctl)
        if screen is not None and getattr(screen, 'key', '') == 'timeline':
            if ctl.get('id') == '2' and ctype == 'image':
                _draw_timeline_grid(painter, skin, screen, rect)
                continue
            if ctype == 'image' and ctl.get('id') in ('4', '7', '25'):   # templates the grid code uses
                continue
        if ctype == 'textbox':
            _draw_textbox(painter, skin, ctl, values, rect)
        elif ctype == 'image':
            _draw_image(painter, skin, ctl, values, rect)
        elif ctype == 'label':
            _draw_label(painter, skin, ctl, values, rect)
        elif ctype in ('progress', 'tickprogress'):
            _draw_progress(painter, skin, ctl, values, rect)
        elif ctype == 'button' and screen is not None and getattr(screen, 'key', '') != 'home':
            _draw_button(painter, skin, ctl, values, rect)
        elif ctype == 'togglebutton' and screen is not None and getattr(screen, 'key', '') == 'channels':
            _draw_group_banner(painter, skin, ctl, screen, values, window)
        elif ctype == 'menu' and screen is not None and getattr(screen, 'key', '') == 'home':
            button = _sub(ctl, 'button') or {}
            if menu_is_list(skin, ctl):
                _draw_menu_list(painter, skin, ctl, button, screen, rect)   # vertical list menu
            else:
                _draw_menu_label(painter, skin, ctl, screen.values, rect)   # ring: name of the focused entry
        elif ctype == 'listcontrol' and screen is not None and ctl.get('id') in screen.lists:
            _draw_list(painter, skin, ctl, screen.lists[ctl['id']], screen.focus == ctl['id'])
        # buttons / spincontrols / videowindow are interactive or HTPC-only: skipped
    painter.restore()


def _sub(ctl, name):
    """Find a sub-control by description, searching nested sub-controls too"""
    for sub in ctl.get('subs', []):
        if sub.get('description', '').lower() == name:
            return sub
        found = _sub(sub, name)
        if found:
            return found
    return None


def _draw_list(painter, skin, ctl, lst, focused):
    """Rows of a skin ListControl: row background, icon and up to three labels"""
    rect = _rect(ctl)
    item_h = _num(ctl, 'itemheight', 40) or 40
    space = _num(ctl, 'space', 0)
    step = item_h + space
    focus_img, nofocus_img = default_pills(skin, ctl)
    painter.save()
    painter.setClipRect(rect)
    rows = lst.visible_rows(step)
    for row in range(rows):
        index = lst.top + row
        if index >= len(lst.items):
            break
        item = lst.items[index]
        row_rect = QRectF(rect.x(), rect.y() + row * step, rect.width(), item_h)
        selected = index == lst.selected
        highlighted = selected and focused
        if nofocus_img:
            _draw_image(painter, skin, dict(nofocus_img), {}, QRectF(row_rect))
        if selected and focused and focus_img:
            _draw_image(painter, skin, dict(focus_img), {}, QRectF(row_rect))
        elif selected and not focused:
            painter.fillRect(row_rect, QColor(255, 255, 255, 40))
        # icon (e.g. channel logo)
        pix = skin.pixmap(item.get('icon', ''))
        iw, ih = _num(ctl, 'imagewidth', 0), _num(ctl, 'imageheight', 0)
        icon_shift = 0.0
        if iw and ih and (pix is not None or item.get('reserve_icon')):
            icon_x = _num(ctl, 'iconoffsetx', 0)
            if pix is not None:
                painter.drawPixmap(QRectF(row_rect.x() + icon_x, row_rect.y() + _num(ctl, 'iconoffsety', 0), iw, ih),
                                   pix, QRectF(pix.rect()))
            icon_shift = icon_x + iw   # the first text column starts behind the icon / its reserved space
        # up to three text columns: 1 = title/name, 2 = time/number, 3 = description
        for n, suffix in ((1, ''), (2, '2'), (3, '3')):
            text = item.get('label%d' % n, '')
            if not text or ctl.get('textvisible%d' % n, 'true').lower() == 'false':
                continue
            font = skin.qfont(ctl.get('font' + suffix))
            painter.setFont(font)
            ox = _num(ctl, 'textoffsetx' + suffix, _num(ctl, 'textoffsetx', 0) if n == 1 else 0)
            if n == 1:
                ox += icon_shift
            oy_key = 'textoffsety' + suffix if ('textoffsety' + suffix) in ctl else 'textoffsety'
            single_line = item_h <= font.pixelSize() * 2.2
            has_oy = (oy_key in ctl) and not (single_line and n < 3)
            oy = _num(ctl, oy_key, 0)
            if not single_line and not _num(ctl, 'textoffsety', 0) and not _num(ctl, 'textoffsety3', 0):
                # tall rows without explicit offsets: title on top, description wrapped below it
                if n == 2 and 'textoffsetx2' not in ctl:
                    continue                      # no column of its own: the host leaves it out
                has_oy = True
                oy = 0 if n == 1 else QFontMetrics(skin.qfont(ctl.get('font'))).height() + 2
            color = ctl.get(('selectedcolor' if highlighted else 'textcolor') + suffix) or \
                ctl.get('selectedcolor' if highlighted else 'textcolor') or ('FF000000' if highlighted else 'FFFFFFFF')
            painter.setPen(parse_color(color))
            text_rect = QRectF(row_rect.x() + ox, row_rect.y() + (oy if has_oy else 0),
                               row_rect.width() - ox - 6, (item_h - oy) if has_oy else item_h)
            vflag = Qt.AlignTop if has_oy else Qt.AlignVCenter
            hflag = Qt.AlignRight if (n == 1 and ctl.get('align1', '').lower() == 'right') else Qt.AlignLeft
            flags = int(hflag | vflag) | (int(Qt.TextWordWrap) if n == 3 else 0)
            painter.save()
            painter.setClipRect(text_rect.intersected(row_rect))
            painter.drawText(text_rect, flags, text)
            painter.restore()
    painter.restore()


class OSDList:
    """Items + selection/scroll state of one list control"""

    def __init__(self):
        self.items = []
        self.selected = 0
        self.top = 0
        self._rows = 8

    def visible_rows(self, step):
        return self._rows

    def set_items(self, items, selected=0):
        self.items = items
        self.selected = max(0, min(selected, len(items) - 1)) if items else 0
        self.top = 0
        self._scroll_into_view()

    def move(self, delta):
        if not self.items:
            return False
        new = max(0, min(len(self.items) - 1, self.selected + delta))
        changed = new != self.selected
        self.selected = new
        self._scroll_into_view()
        return changed

    def _scroll_into_view(self):
        if self.selected < self.top:
            self.top = self.selected
        elif self.selected >= self.top + self._rows:
            self.top = self.selected - self._rows + 1

    @property
    def current(self):
        return self.items[self.selected] if self.items else None


class OSDScreen:
    """Runtime state of an interactive OSD window: which list has focus,
    selections, and the remote-control actions that move around."""

    def __init__(self, skin, key, on_ok=None, on_change=None):
        self.skin, self.key = skin, key
        self.group = 'tv'   # 'tv' / 'fav': which group logo + title the window shows
        self.on_ok, self.on_change = on_ok, on_change
        self.window = skin.window(key)
        self.lists = {}
        self.values = {}
        self.focus = None
        for ctl in self.window.controls if self.window else []:
            if ctl.get('type', '').lower() == 'listcontrol':
                lst = OSDList()
                item_h = (_num(ctl, 'itemheight', 40) or 40) + _num(ctl, 'space', 0)
                lst._rows = max(1, int(_rect(ctl).height() // item_h))
                self.lists[ctl.get('id')] = lst
                self._ctl_by_id = getattr(self, '_ctl_by_id', {})
                self._ctl_by_id[ctl.get('id')] = ctl
        default = self.window.default_focus if self.window else ''
        self.focus = default if default in self.lists else next(iter(self.lists), None)

    def handle(self, action):
        """action: up/down/left/right/ok/back/pageup/pagedown. True if used."""
        lst = self.lists.get(self.focus)
        ctl = getattr(self, '_ctl_by_id', {}).get(self.focus, {})
        if lst is None:
            return False
        if action in ('up', 'down', 'pageup', 'pagedown'):
            step = {'up': -1, 'down': 1, 'pageup': -lst._rows, 'pagedown': lst._rows}[action]
            if lst.move(step) and self.on_change:
                self.on_change(self.focus, lst.current)
            return True
        if action in ('left', 'right'):
            target = ctl.get(action, '')
            if target in self.lists and target != self.focus:
                self.focus = target
            return True
        if action == 'ok' and self.on_ok:
            self.on_ok(self.focus, lst.current)
            return True
        return False


DEFAULT_MENU = [  # the usual HTPC home entries, used when no windowdef.xml is provided
    ('2', 'Channel EPG', 'Program', 'home_epg.png', ''),
    ('1', 'Channel Window', 'Channels', 'home_channels.png', ''),
    ('15', 'Cam Menu Window', 'CAM Menu', 'home_cam.png', ''),
    ('603', 'Recordings Window', 'Recordings', 'home_recordings.png', ''),
    ('4', 'Timer Window', 'Timer', 'home_timer.png', ''),
    ('102', 'Clock Button', 'Clock', 'home_clock.png', ''),
    ('600', 'Timeline Window', 'TimeLine', 'home_timeline.png', ''),
    ('3', 'EPG Now Window', "What's now", 'home_now.png', ''),
    ('6', 'Movies Window', 'theMovies', 'home_videos.png', ''),
]


def ensure_windowdef(folder):
    """Writes OSDskins/windowdef.xml (the menu template shared by all skins)
    when it is missing. It can be edited, e.g. to add a Kodi entry:
    <Window Name="Kodi" Text="Kodi" ID="-3" Parent="0"><Image>home_kodi.png</Image>
    <Application>path to kodi</Application></Window> (the skin needs home_kodi.png)."""
    path = os.path.join(folder, 'windowdef.xml')
    if os.path.exists(path):
        return path
    try:
        os.makedirs(folder, exist_ok=True)
        lines = ['<?xml version="1.0" encoding="utf-8"?>', '<WindowDefs>', '  <Version>1.07</Version>',
                 '  <Windows>', '    <Window Name="Home Window" Text="Home" ID="0"/>']
        for i, n, t, img, app in DEFAULT_MENU:
            lines.append('    <Window Name="%s" Text="%s" ID="%s" Parent="0">' %
                         (n, t.replace("'", '&apos;'), i))
            lines.append('      <Image>%s</Image>' % img)
            lines.append('    </Window>')
        lines += ['  </Windows>', '</WindowDefs>', '']
        with open(path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
    except OSError:
        pass
    return path


def load_menu_entries(windowdef_path=None):
    """Menu entries of a windowdef.xml in file order. Every entry has a parent:
    '0' = main menu, otherwise the ID of the entry whose sub menu it belongs to
    (1000 = Media Center, 24 = System, 8 = Settings). Windows without a Parent or
    with <enabled>0</enabled> are left out. Falls back to a built-in list.
    Each entry: id, name, text, image, application, script, parent."""
    entries = []
    if windowdef_path and os.path.isfile(windowdef_path):
        try:
            for win in ET.parse(windowdef_path).getroot().iter('Window'):
                parent = win.get('Parent')
                if parent is None or (win.findtext('enabled') or '1').strip() == '0':
                    continue
                entries.append({'id': win.get('ID') or '', 'name': win.get('Name') or '',
                                'text': win.get('Text') or win.get('Name') or '',
                                'image': (win.findtext('Image') or '').strip(),
                                'application': (win.findtext('Application') or '').strip(),
                                'script': (win.findtext('Script') or '').strip(),
                                'parent': parent})
        except ET.ParseError:
            entries = []
    if not any(e['parent'] == '0' for e in entries):
        entries = [{'id': i, 'name': n, 'text': t, 'image': img, 'application': app,
                    'script': '', 'parent': '0'} for i, n, t, img, app in DEFAULT_MENU]
    return entries


# DVBViewer shows no now/next or channel text in menu windows, so those labels stay empty
NO_TV_INFO = {'channelname': '', 'channelnr': '', 'tv.now.start': '', 'tv.now.title': '', 'tv.now.percentage': '',
              'tv.now.remain': '', 'tv.now.description': '', 'tv.next.start': '', 'tv.next.title': ''}


class OSDMenuScreen:
    """The home menu with its sub menus. How a level looks is up to the skin:
    a ring (focused entry in the middle, two neighbours on each side, drawn via
    #menufocusimage(+/-N) placeholders; '+N' is the slot on the left, i.e. the
    entry BEFORE the focus) or a vertical list drawn by the Menu control itself."""

    def __init__(self, skin, items, on_ok=None, on_change=None):
        self.skin, self.key = skin, 'home'
        self.all_items = items
        self.on_ok, self.on_change = on_ok, on_change
        self.lists, self.focus, self.values = {}, None, {}
        self.stack = []
        self.items, self.index, self.window_key = [], 0, 'home'
        self._open_level('0')

    def _open_level(self, parent, index=0):
        self.parent = parent
        self.items = [e for e in self.all_items if e['parent'] == parent] or \
            [e for e in self.all_items if e['parent'] == '0']
        self.index = min(index, len(self.items) - 1)
        top = parent == '0' and skin_has(self.skin, 'homemain')
        self.window_key = 'homemain' if top else 'home'
        self._update()

    def can_go_up(self):
        return bool(self.stack)

    def go_up(self):
        if self.stack:
            parent, index = self.stack.pop()
            self._open_level(parent, index)
            return True
        return False

    def _item(self, offset):
        return self.items[(self.index + offset) % len(self.items)]

    def _update(self):
        owner = next((e for e in self.all_items if e['id'] and e['id'] == self.parent), None)
        values = dict(NO_TV_INFO, currentwindow=owner['name'] if owner else 'Home Window')
        n = len(self.items)
        for offset in (-2, -1, 0, 1, 2):
            suffix = '' if offset == 0 else '%+d' % offset
            if n < 5 and abs(offset) > n // 2:   # don't repeat entries of a short menu
                values['menufocusimage' + suffix] = ''
                values['menufocustext' + suffix] = ''
                continue
            item = self._item(-offset)
            values['menufocusimage' + suffix] = self.skin.menu_icon(item.get('image', ''))
            values['menufocustext' + suffix] = item.get('display', item.get('text', ''))
        self.values = values

    def is_list(self):
        """True when the skin draws this level as a vertical list (then Up/Down move, else Left/Right)"""
        window = self.skin.window(self.window_key)
        for ctl in (window.controls if window else []):
            if ctl.get('type', '').lower() == 'menu':
                return menu_is_list(self.skin, ctl)
        return False

    def handle(self, action):
        if action in ('left', 'right', 'up', 'down'):
            if (action in ('up', 'down')) != self.is_list():
                return True
            step = -1 if action in ('left', 'up') else 1
            self.index = (self.index + step) % len(self.items)
            self._update()
            if self.on_change:
                self.on_change(self.items[self.index])
            return True
        if action == 'ok':
            item = self.items[self.index]
            if (item.get('script') or '').lower() == 'previouswindow':
                return self.go_up() or True
            if item.get('id') and any(e['parent'] == item['id'] for e in self.all_items):
                self.stack.append((self.parent, self.index))
                self._open_level(item['id'])
                return True
            if self.on_ok:
                self.on_ok(item)
            return True
        return False


def skin_has(skin, key):
    return skin.window(key) is not None


# DVB content descriptor, first level (EN 300 468), for the genre line of a timeline cell
GENRE_NAMES = {1: 'movie/drama', 2: 'news/current affairs', 3: 'show/game show', 4: 'sports',
               5: "children's/youth programmes", 6: 'music/ballet/dance', 7: 'arts/culture',
               8: 'social/political issues/economics', 9: 'education/science/factual topics',
               10: 'leisure hobbies'}


def genre_text(event):
    """Genre line of an EPG event ('' if it has none)"""
    genre = event.get('genre') or event.get('category')
    if isinstance(genre, (list, tuple)) and genre:
        genre = genre[0]
    if isinstance(genre, int):
        return GENRE_NAMES.get((genre >> 4) & 15, '')
    return genre if isinstance(genre, str) else ''


class OSDTimeline:
    """The timeline window: channels as rows, programmes as cells on a two hour
    time axis. DVBViewer draws that grid itself and takes only positions, fonts
    and colours from template controls of the skin (ids 2, 7, 18, 23-30, 40, 25),
    which is what _draw_timeline_grid reads. The channel being watched sits in the
    middle row, the grid starts at the half hour before now and the marker shows now."""
    SPAN = 120 * 60

    def __init__(self, skin, channels, events_fn, current_uuid='', on_ok=None):
        self.skin, self.key = skin, 'timeline'
        self.channels, self.events_fn, self.on_ok = channels, events_fn, on_ok
        self.lists, self.focus, self.values = {}, None, {}
        self.window = skin.window('timeline')
        self.rows = self._row_count()
        self.index = next((i for i, c in enumerate(channels) if c.get('uuid') == current_uuid), 0)
        self.now = time.time()
        self.cursor = self.now
        self.start = self._floor(self.now)
        self.event = None
        self._select()

    # -- template geometry -----------------------------------------------
    def template(self, ident, kind=None):
        for ctl in (self.window.controls if self.window else []):
            if ctl.get('id') == ident and (kind is None or ctl.get('type', '').lower() == kind):
                return ctl
        return None

    def _row_count(self):
        panel, logo, name = self.template('2', 'image'), self.template('7'), self.template('18', 'label')
        if not (panel and logo and name):
            return 5
        header = _num(logo, 'y') - _num(panel, 'y')
        row_h = _num(name, 'y') + _num(name, 'height') - _num(logo, 'y')
        return max(1, round((_num(panel, 'height') - header) / row_h)) if row_h > 0 else 5

    @staticmethod
    def _floor(t):
        return t - t % 1800

    # -- data ---------------------------------------------------------------
    def last_stop(self):
        return max((ev.get('stop', 0) for c in self.channels[:1] for ev in self.events(c)), default=self.now)

    def channel(self, offset=0):
        return self.channels[(self.index + offset) % len(self.channels)]

    def events(self, channel):
        return self.events_fn(channel)

    def _event_at(self, channel, t):
        events = self.events(channel)
        for ev in events:
            if ev.get('start', 0) <= t < ev.get('stop', 0):
                return ev
        return next((ev for ev in events if ev.get('start', 0) >= t), None)

    def _select(self):
        self.event = self._event_at(self.channel(), self.cursor)
        if self.event is not None and not (self.start <= self.event['start'] < self.start + self.SPAN) \
                and not (self.event['start'] <= self.start < self.event['stop']):
            self.start = self._floor(max(self.event['start'], self.now - 1800) if self.event['start'] < self.now
                                     else self.event['start'])
        ev = self.event or {}
        title = ev.get('title')
        if isinstance(title, dict):
            title = next(iter(title.values()), '')
        desc = ev.get('description') or ev.get('summary') or ''
        if isinstance(desc, dict):
            desc = next(iter(desc.values()), '')
        when = ''
        if ev:
            a, b = time.localtime(ev['start']), time.localtime(ev['stop'])
            when = '%s %d. %02d:%02d-%02d:%02d' % (QLocale().dayName(a.tm_wday + 1, QLocale.ShortFormat),
                                                  a.tm_mday, a.tm_hour, a.tm_min, b.tm_hour, b.tm_min)
        self.values = {'tv.guide.title': title or '', 'tv.guide.time': when, 'tv.guide.description': desc,
                       'mr.currentwindowtitle': 'Timeline', 'channelname': '', 'tv.now.start': '',
                       'tv.now.title': '', 'tv.guide.chlogo': ''}

    # -- remote control -----------------------------------------------------------
    def handle(self, action):
        if not self.channels:
            return False
        if action in ('up', 'down', 'pageup', 'pagedown'):
            step = {'up': -1, 'down': 1, 'pageup': -self.rows, 'pagedown': self.rows}[action]
            self.index = (self.index + step) % len(self.channels)
            self._select()
            return True
        if action in ('left', 'right'):
            events = self.events(self.channel())
            if self.event in events:
                i = events.index(self.event) + (-1 if action == 'left' else 1)
                if 0 <= i < len(events):
                    self.cursor = events[i]['start']
                    if self.cursor < self.start:
                        self.start = self._floor(self.cursor)
                    elif self.cursor >= self.start + self.SPAN - 600:
                        self.start = self._floor(self.cursor)
                    self._select()
            return True
        if action == 'ok' and self.on_ok:
            self.on_ok(self.channel())
            return True
        return False


def _timeline_cell_images(skin, state):
    """(body strip, left cap, right cap) of a programme cell from the skin's arrow_*.png images:
    state '' = normal, 'light' = running, 'selected' = chosen. None when the skin lacks them."""
    cache = skin.__dict__.setdefault('_cell_images', {})
    if state not in cache:
        mid = ('_' + state) if state else ''
        left, right = skin.pixmap('arrow%s_left.png' % mid), skin.pixmap('arrow%s_right.png' % mid)
        if left is None or right is None:
            cache[state] = None
        else:
            # the body repeats the inner edge column of the caps (a 1 px strip, stretched)
            strip = left.copy(left.width() - 1, 0, 1, left.height())
            cache[state] = (strip, left, right)
    return cache[state]


def _draw_timeline_grid(painter, skin, screen, panel):
    """Channels, time axis, programme cells and the 'now' marker inside the panel rectangle"""
    t = screen.template
    logo, name, head = t('7'), t('18', 'label'), t('40', 'label')
    title_t, genre_t = t('24', 'label'), t('30', 'label') or t('23', 'label')
    if not (logo and name):
        return
    header = _num(logo, 'y') - panel.y()
    row_h = _num(name, 'y') + _num(name, 'height') - _num(logo, 'y')
    left = _num(head, 'x') if head else panel.x() + panel.width() * 0.15
    right = panel.right()
    ppm = (right - left) / (screen.SPAN / 60.0)
    t0, t1 = screen.start, screen.start + screen.SPAN
    painter.save()
    painter.setClipRect(QRectF(panel.x() - 40, panel.y() - 80, panel.width() + 80, panel.height() + 160))

    # time axis labels + day / interval texts
    if head:
        painter.setFont(skin.qfont(head.get('font')))
        painter.setPen(parse_color(head.get('textcolor'), 'FFFFFFFF'))
        align = Qt.AlignRight if head.get('align', '').lower() == 'right' else Qt.AlignLeft
        for i in range(4):
            stamp = time.localtime(t0 + i * 1800)
            box = QRectF(left + i * 30 * ppm, _num(head, 'y'), _num(head, 'width', 140), _num(head, 'height', 30))
            painter.drawText(box, int(align | Qt.AlignVCenter), '%02d:%02d' % (stamp.tm_hour, stamp.tm_min))
    day_ctl, span_ctl = t('6', 'spincontrol'), t('8', 'spincontrol')
    for ctl, text in ((day_ctl, None), (span_ctl, '(2/4)')):
        if ctl is None:
            continue
        tiny = _num(ctl, 'width') < 24            # arrow-only spin buttons: the text starts at the control
        if text is not None and tiny:
            continue                              # (no text shown for the interval)
        if text is None:
            a = time.localtime(t0)
            days = max(1, int((screen.last_stop() - screen.now) // 86400) + 1)
            d = max(1, int((screen._floor(t0) - screen._floor(screen.now - screen.now % 86400)) // 86400) + 1)
            day = '%s %d.%d' % (QLocale().dayName(a.tm_wday + 1, QLocale.ShortFormat), a.tm_mday, a.tm_mon)
            text = day if tiny else '(%d/%d) %s' % (min(d, days), days, day)
        painter.setFont(skin.qfont(ctl.get('font') or (head or {}).get('font')))
        painter.setPen(parse_color(ctl.get('textcolor') or (head or {}).get('textcolor'), 'FFFFFFFF'))
        x = _num(ctl, 'x') if tiny else _num(ctl, 'x') + _num(ctl, 'width') + 4
        box = QRectF(x, _num(ctl, 'y'), 220, _num(ctl, 'height'))
        painter.drawText(box, int(Qt.AlignLeft | Qt.AlignVCenter), text)

    # rows
    middle = screen.rows // 2
    for r in range(screen.rows):
        channel = screen.channel(r - middle)
        top = panel.y() + header + r * row_h
        # logo (when known) and channel name
        logo_pix = skin.pixmap(channel.get('logo', ''))
        if logo_pix is not None:
            painter.drawPixmap(QRectF(_num(logo, 'x'), top, _num(logo, 'width'), _num(logo, 'height')),
                               logo_pix, QRectF(logo_pix.rect()))
        painter.setFont(skin.qfont(name.get('font')))
        painter.setPen(parse_color(name.get('textcolor'), 'FFFFFFFF'))
        label = QRectF(_num(name, 'x'), top + (_num(name, 'y') - _num(logo, 'y')), _num(name, 'width'), _num(name, 'height'))
        painter.drawText(label, int(Qt.AlignLeft | Qt.AlignVCenter),
                         QFontMetrics(painter.font()).elidedText(channel.get('name', ''), Qt.ElideRight, int(label.width())))
        # programme cells
        for ev in screen.events(channel):
            if ev.get('stop', 0) <= t0 or ev.get('start', 0) >= t1:
                continue
            x0 = left + (max(ev['start'], t0) - t0) / 60.0 * ppm
            x1 = left + (min(ev['stop'], t1) - t0) / 60.0 * ppm
            cell = QRectF(x0 + 1, top + 1, max(2.0, x1 - x0 - 2), row_h - 3)
            selected = ev is screen.event and r == middle
            running = ev['start'] <= screen.now < ev['stop']
            state = 'selected' if selected else ('light' if running else '')
            imgs = _timeline_cell_images(skin, state)
            size = min(row_h * 0.22, 16)
            cap = cell.height() * 38.0 / 52.0 if imgs else size * 2
            if imgs:
                body, cap_l, cap_r = imgs
                painter.drawPixmap(cell, body, QRectF(body.rect()))
                if ev['start'] < t0 and cell.width() > cap * 1.5:
                    painter.drawPixmap(QRectF(cell.left(), cell.top(), cap, cell.height()), cap_l, QRectF(cap_l.rect()))
                if ev['stop'] > t1 and cell.width() > cap * 1.5:
                    painter.drawPixmap(QRectF(cell.right() - cap, cell.top(), cap, cell.height()), cap_r, QRectF(cap_r.rect()))
            else:
                grad = QLinearGradient(cell.topLeft(), cell.bottomLeft())
                if selected:
                    grad.setColorAt(0, QColor(110, 170, 205)); grad.setColorAt(0.5, QColor(60, 120, 160))
                    grad.setColorAt(1, QColor(30, 75, 110))
                elif running:
                    grad.setColorAt(0, QColor(120, 120, 120)); grad.setColorAt(0.5, QColor(70, 70, 70))
                    grad.setColorAt(1, QColor(35, 35, 35))
                else:
                    grad.setColorAt(0, QColor(60, 60, 60)); grad.setColorAt(0.5, QColor(30, 30, 30))
                    grad.setColorAt(1, QColor(14, 14, 14))
                painter.fillRect(cell, grad)
                painter.setPen(QPen(QColor(150, 150, 150, 160), 1))
                painter.drawLine(cell.topLeft(), cell.topRight())
                painter.setPen(QPen(QColor(0, 0, 0, 200), 1))
                painter.drawRect(cell)
                # arrows: the programme continues beyond the visible part
                mid = cell.center().y()
                painter.setPen(Qt.NoPen)
                painter.setBrush(QColor(210, 210, 210, 200))
                if ev['start'] < t0:
                    painter.drawPolygon(QPolygonF([QPointF(cell.left() + 3, mid), QPointF(cell.left() + 3 + size, mid - size),
                                                   QPointF(cell.left() + 3 + size, mid + size)]))
                if ev['stop'] > t1:
                    painter.drawPolygon(QPolygonF([QPointF(cell.right() - 3, mid), QPointF(cell.right() - 3 - size, mid - size),
                                                   QPointF(cell.right() - 3 - size, mid + size)]))
                painter.setBrush(Qt.NoBrush)
            # texts
            cap_w = cap if imgs else size
            pad = 8 + (cap_w + 4 if ev['start'] < t0 else 0)
            width = cell.width() - pad - 8 - (cap_w + 4 if ev['stop'] > t1 else 0)
            if width < 14:
                continue
            title = ev.get('title')
            if isinstance(title, dict):
                title = next(iter(title.values()), '')
            light = selected or running
            cell_title = (title_t if light else (t('26', 'label') or title_t)) or {}
            cell_genre = (t('23', 'label') if light else t('30', 'label')) or genre_t or cell_title
            font = skin.qfont(title_t.get('font') if title_t else cell_title.get('font'))
            painter.setFont(font)
            tcolor = cell_title.get('textselectedcolor') if selected else cell_title.get('textcolor')
            painter.setPen(parse_color(tcolor or cell_title.get('textcolor'), 'FFFFFFFF'))
            line = font.pixelSize() * 1.3
            has_genre = bool(genre_text(ev)) and row_h >= line * 2.2
            y = cell.top() + (cell.height() - line * (2 if has_genre else 1)) / 2
            fm = QFontMetrics(font)
            painter.drawText(QRectF(cell.left() + pad, y, width, line), int(Qt.AlignLeft | Qt.AlignVCenter),
                             fm.elidedText(title or '', Qt.ElideRight, int(width)))
            if has_genre:
                painter.setPen(parse_color(cell_genre.get('textcolor') or cell_title.get('textcolor'), 'FFDDDDDD'))
                painter.drawText(QRectF(cell.left() + pad, y + line, width, line), int(Qt.AlignLeft | Qt.AlignVCenter),
                                 fm.elidedText(genre_text(ev), Qt.ElideRight, int(width)))

    # marker for the current time
    marker = t('25', 'image')
    x = left + (screen.now - t0) / 60.0 * ppm
    if marker is not None and left <= x <= right:
        pix = skin.pixmap(marker.get('texture', ''))
        w, h = max(1.0, _num(marker, 'width', 2)), _num(marker, 'height', panel.height())
        if pix is not None:
            painter.drawPixmap(QRectF(x - w / 2, _num(marker, 'y'), w, h), pix, QRectF(pix.rect()))
        else:
            painter.setPen(QPen(QColor(255, 60, 60), 2))
            painter.drawLine(QPointF(x, panel.y() + header - 6), QPointF(x, panel.bottom()))
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
        super().__init__(parent, Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.WindowTransparentForInput |
                         Qt.WindowDoesNotAcceptFocus)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.skin = None
        self.screen = None  # OSDScreen drawn on the 'screen' layer
        self.picture = None  # QPixmap shown on the 'picture' layer
        self.opacity = 1.0  # user setting: how see-through the whole OSD is
        self.notice_text = ''
        self.values = {}
        self.layers = {}  # key -> deadline (time.monotonic()), None = stay
        from PyQt5.QtCore import QTimer
        self._timer = QTimer(self)
        self._timer.setInterval(200)
        self._timer.timeout.connect(self._expire)
        # Never float over other programs: hide while our app isn't the active one
        from PyQt5.QtGui import QGuiApplication
        QGuiApplication.instance().applicationStateChanged.connect(self._app_state_changed)

    def show_layer(self, skin, key, values, area_rect, timeout_ms=4000):
        from PyQt5.QtGui import QGuiApplication
        if QGuiApplication.applicationState() != Qt.ApplicationActive:
            return  # don't pop up over other programs
        """area_rect: QRect in global screen coordinates (the video area)"""
        import time
        self.skin, self.values = skin, values
        self.layers[key] = time.monotonic() + timeout_ms / 1000.0 if timeout_ms else None
        self.setGeometry(area_rect)
        self.show()
        self.raise_()
        self.update()
        self._timer.start()

    def _app_state_changed(self, state):
        if state != Qt.ApplicationActive:
            self.hide()
        elif self.layers:
            self.show()
            self.update()

    def set_opacity(self, value):
        self.opacity = max(0.1, min(1.0, float(value)))
        self.update()

    def show_notice(self, skin, text, area_rect, timeout_ms=3000):
        self.notice_text = text
        self.show_layer(skin, 'notice', self.values, area_rect, timeout_ms)

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

    def _paint_notice(self, painter):
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)
        font = QFont()
        font.setPixelSize(max(14, int(self.height() * 0.035)))
        painter.setFont(font)
        width = painter.fontMetrics().horizontalAdvance(self.notice_text) + 60
        rect = QRectF((self.width() - width) / 2, self.height() * 0.82, width, font.pixelSize() * 2.2)
        painter.setBrush(QColor(20, 20, 20, 215))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(rect, 10, 10)
        painter.setPen(QColor(255, 255, 255))
        painter.drawText(rect, Qt.AlignCenter, self.notice_text)
        painter.restore()

    def paintEvent(self, event):
        if self.skin is None:
            return
        painter = QPainter(self)
        painter.setOpacity(self.opacity)
        for key in list(self.layers):
            if key == 'notice':
                self._paint_notice(painter)
            elif key == 'picture':
                if self.picture is not None and not self.picture.isNull():
                    painter.save()
                    painter.setOpacity(1.0)
                    painter.fillRect(self.rect(), QColor(0, 0, 0))
                    scaled = self.picture.scaled(self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    painter.drawPixmap((self.width() - scaled.width()) // 2,
                                       (self.height() - scaled.height()) // 2, scaled)
                    painter.restore()
            elif key == 'screen':
                if self.screen is not None:
                    render(painter, self.skin, getattr(self.screen, 'window_key', self.screen.key), {**self.values, **self.screen.values},
                           self.width(), self.height(), self.screen)
            else:
                render(painter, self.skin, key, self.values, self.width(), self.height())
        painter.end()
