import itertools
from operator import itemgetter
import os.path
import re
import shutil

from PyQt4 import QtCore, QtGui

from libsyntyche.common import read_json
from pluginlib import GUIPlugin


class UserPlugin(GUIPlugin):
    def __init__(self, objects, get_path):
        self.pluginpath = get_path()
        self.configpath = objects['settings manager'].get_config_directory()
        self.sidebar = Sidebar(objects['textarea'])
        objects['mainwindow'].inner_h_layout.addWidget(self.sidebar)
        self.hotkeys = {'Ctrl+R': self.sidebar.toggle}
        objects['textarea'].cursorPositionChanged.connect(\
                self.sidebar.update_active_chapter)

    def read_config(self):
        configfile = os.path.join(self.configpath, 'kalpana-chapters.conf')
        if not os.path.exists(configfile):
            shutil.copyfile(os.path.join(self.pluginpath, 'defaultconfig.json'),
                            configfile)
        self.sidebar.settings = read_json(configfile)


class Sidebar(QtGui.QListWidget):
    def __init__(self, textarea):
        super().__init__()
        self.textarea = textarea
        self.itemActivated.connect(self.goto_chapter)
        self.default_item_bg = None
        self.hide()

    def toggle(self):
        if self.isVisible():
            self.hide()
            self.textarea.setFocus()
        else:
            self.setFocus()
            self.update_list()

    def update_list(self):
        self.clear()
        trigger = self.settings['trigger_chapter_string']
        chapter_strings = self.settings['chapter_strings']
        text = self.textarea.toPlainText().splitlines()
        if not text:
            return
        # Find all remotely possible lines (linenumber, text)
        rough_list = list(filter(lambda t:t[1].startswith(trigger),
                                 zip(itertools.count(1), text)))
        if not rough_list:
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
        self.addItems(list(map(format, zip(chapterlist, chapter_lengths))))
        self.setFixedWidth(self.sizeHintForColumn(0)+5)
        self.show()

    def update_active_chapter(self):
        if not self.count() or not self.isVisible():
            return
        if not self.default_item_bg:
            self.default_item_bg = self.item(0).backgroundColor()
        pos = self.textarea.textCursor().blockNumber()+1
        for item_nr in range(self.count()):
            self.item(item_nr).setBackgroundColor(self.default_item_bg)
        for n, ch in list(enumerate(self.linenumbers))[::-1]:
            if pos >= ch:
                self.item(n).setBackgroundColor(QtCore.Qt.darkGreen)
                break

    def goto_chapter(self, _):
        self.textarea.goto_line(self.linenumbers[self.currentRow()])


def get_chapter_wordcounts(real_chapter_lines, text):
    chapter_lines = list(real_chapter_lines) + [len(text)]
    return [len(re.findall(r'\S+', '\n'.join(text[chapter_lines[i]:chapter_lines[i+1]-1])))
            for i in range(len(chapter_lines)-1)]
