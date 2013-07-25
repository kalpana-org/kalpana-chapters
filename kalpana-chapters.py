import itertools
import os.path
import re
import shutil

from PyQt4 import QtCore, QtGui

from libsyntyche.common import read_json
from pluginlib import GUIPlugin


class UserPlugin(GUIPlugin):
    def __init__(self, objects, get_path):
        settings = read_config(get_path(),
            objects['settings manager'].get_config_directory())
        sidebar = Sidebar(settings, objects['textarea'])
        objects['mainwindow'].inner_h_layout.addWidget(sidebar)
        self.hotkeys = {'Ctrl+R': sidebar.update_list}

def read_config(pluginpath, configpath):
    configfile = os.path.join(configpath, 'kalpana-chapters.conf')
    if not os.path.exists(configfile):
        shutil.copyfile(os.path.join(pluginpath, 'defaultconfig.json'),
                        configfile)
    return read_json(configfile)


class Sidebar(QtGui.QListWidget):
    def __init__(self, settings, textarea):
        super().__init__()
        self.settings = settings
        self.textarea = textarea
        self.itemActivated.connect(self.goto_chapter)

    def update_list(self):
        self.clear()
        trigger = self.settings['trigger_chapter_string']
        chapter_rx = re.compile(self.settings['raw_chapter_string'])
        format_str = self.settings['formatted_chapter_string']
        text = self.textarea.toPlainText().splitlines()
        flist = filter(lambda t:t[1].startswith(trigger),
                       zip(itertools.count(1), text))
        self.linenumbers, chapterlist =\
                zip(*list(filter(lambda x:chapter_rx.match(x[1]), flist)))

        chapter_lengths = get_chapter_wordcounts(self.linenumbers, text)

        format = lambda x: format_str.format(**chapter_rx.match(x[0]).groupdict())+'\n'+str(x[1])
        self.addItems(list(map(format, zip(chapterlist, chapter_lengths))))

        self.setFixedWidth(self.sizeHintForColumn(0)+5)


    def goto_chapter(self, _):
        self.textarea.goto_line(self.linenumbers[self.currentRow()])


def get_chapter_wordcounts(real_chapter_lines, text):
    chapter_lines = list(real_chapter_lines) + [len(text)]
    return [len(re.findall(r'\S+', '\n'.join(text[chapter_lines[i]:chapter_lines[i+1]-1])))
            for i in range(len(chapter_lines)-1)]
