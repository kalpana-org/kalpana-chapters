import itertools
from operator import itemgetter
import os.path
import re
import shutil

from PyQt4 import QtCore, QtGui

from libsyntyche.common import read_json, parse_stylesheet, read_file, make_sure_config_exists
from pluginlib import GUIPlugin


class UserPlugin(GUIPlugin):
    def __init__(self, objects, get_path):
        super().__init__(objects, get_path)
        self.pluginpath = get_path()
        self.configpath = objects['settings manager'].get_config_directory()
        self.sidebar = Sidebar(objects['textarea'], self.error)
        objects['mainwindow'].inner_h_layout.addWidget(self.sidebar)
        self.hotkeys = {'Ctrl+R': self.sidebar.toggle}
        self.commands = {':': (self.sidebar.goto_line_or_chapter, 'Go to line or chapter (:c12 to go to chapter 12)')}
        objects['textarea'].cursorPositionChanged.connect(\
                self.sidebar.update_active_chapter)

    def read_config(self):
        # config
        configfile = os.path.join(self.configpath, 'kalpana-chapters.conf')
        make_sure_config_exists(configfile, os.path.join(self.pluginpath, 'default_config.json'))
        self.sidebar.settings = read_json(configfile)
        # stylesheet
        cssfile = os.path.join(self.configpath, 'kalpana-chapters.css')
        make_sure_config_exists(cssfile, os.path.join(self.pluginpath, 'default_theme.css'))
        self.sidebar.setStyleSheet(parse_stylesheet(read_file(cssfile)))


class Sidebar(QtGui.QListWidget):
    def __init__(self, textarea, error):
        super().__init__()
        self.textarea = textarea
        self.error = error
        self.setDisabled(True)
        self.default_item_bg = None
        self.chapters_detected = False
        self.hide()

    def toggle(self):
        if self.isVisible():
            self.hide()
        else:
            self.update_list()
            self.show()

    def update_list(self):
        self.clear()
        prefix = self.settings['prologue name']
        trigger = self.settings['trigger chapter string']
        chapter_strings = self.settings['chapter strings']
        text = self.textarea.toPlainText().splitlines()
        if not text:
            self.chapters_detected = False
            return
        # Find all remotely possible lines (linenumber, text)
        rough_list = list(filter(lambda t:t[1].startswith(trigger),
                                 zip(itertools.count(1), text)))
        if not rough_list:
            self.chapters_detected = False
            return
        # Find only those that match the regexes
        # Match to every rawstring possible, but overwrite earlier if needed
        out = {}
        for pair in chapter_strings: # all combinations
            for s in pair['raw']: # all rawstrings
                rx = re.compile(s)
                for x in rough_list: # all lines
                    if rx.match(x[1]):
                        out[x[0]] = pair['format'].format(**rx.match(x[1]).groupdict()).strip()
        self.linenumbers, chapterlist = zip(*sorted(out.items(), key=itemgetter(0)))
        chapter_lengths = get_chapter_wordcounts(self.linenumbers, text)
        format = lambda x: x[0] + '\n   ' + str(x[1])
        items = list(map(format, zip(chapterlist, chapter_lengths)))
        if self.linenumbers[0] > 1:
            wc = len(re.findall(r'\S+', '\n'.join(text[:self.linenumbers[0]-1])))
            self.linenumbers = [0] + list(self.linenumbers)
            items.insert(0, prefix + '\n   ' + str(wc))
        self.addItems(items)
        self.mod_items_fonts(bold=True)
        self.setFixedWidth(self.sizeHintForColumn(0)+5)
        self.mod_items_fonts(bold=False)
        self.item(0).setFont(mod_font(self.item(0), bold=True))
        self.chapters_detected = True

    def update_active_chapter(self):
        if not self.count() or not self.isVisible():
            return
        pos = self.textarea.textCursor().blockNumber()+1
        self.mod_items_fonts(bold=False)
        for n, ch in list(enumerate(self.linenumbers))[::-1]:
            if pos >= ch:
                i = self.item(n)
                i.setFont(mod_font(i, True))
                break

    def goto_line_or_chapter(self, arg):
        if arg.isdigit():
            self.textarea.goto_line(int(arg))
        elif re.match(r'c\d+', arg):
            self.update_list()
            if not self.chapters_detected:
                self.error('No chapters detected')
                return
            chapter = int(arg[1:])
            if chapter in range(len(self.linenumbers)):
                self.textarea.goto_line(self.linenumbers[chapter])
            else:
                self.error('Invalid chapter number')
        else:
            self.error('Invalid line or chapter number')

    def mod_items_fonts(self, bold):
        for item_nr in range(self.count()):
            i = self.item(item_nr)
            i.setFont(mod_font(i, bold))


def mod_font(item, bold):
    font = item.font()
    font.setBold(bold)
    return font

def get_chapter_wordcounts(real_chapter_lines, text):
    chapter_lines = list(real_chapter_lines) + [len(text)]
    return [len(re.findall(r'\S+', '\n'.join(text[chapter_lines[i]:chapter_lines[i+1]-1])))
            for i in range(len(chapter_lines)-1)]
