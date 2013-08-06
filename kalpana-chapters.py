import itertools
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
        chapter_rx = re.compile(self.settings['raw_chapter_string'])
        format_str = self.settings['formatted_chapter_string']
        text = self.textarea.toPlainText().splitlines()
        if not text:
            return
        flist = list(filter(lambda t:t[1].startswith(trigger),
                               zip(itertools.count(1), text)))
        if not flist:
            return
        flist2 = list(filter(lambda x:chapter_rx.match(x[1]), flist))
        if not flist2:
            return
        self.linenumbers, chapterlist = zip(*flist2)
        chapter_lengths = get_chapter_wordcounts(self.linenumbers, text)
        format = lambda x: format_str.format(**chapter_rx.match(x[0]).groupdict())+'\n   '+str(x[1])
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
