import sublime
# import sublime_plugin
import os
import codecs
import socket
from socket import error as socket_error
import errno


def centre_line_of(view, region):
    (first_row, c) = view.rowcol(region.begin())
    (last_row, c) = view.rowcol(region.end())
    return int(first_row + (last_row - first_row) / 2)

# -----------------


def set_layout_columns(count, coll_width=0.75):

    if count == 1:
        sublime.active_window().run_command("set_layout", {
            "cells": [[0, 0, 1, 1]],
            "cols": [0.0, 1.0],
            "rows": [0.0, 1.0]
        })

    elif count == 2:
        sublime.active_window().run_command("set_layout", {
            "cells": [[0, 0, 1, 1], [1, 0, 2, 1]],
            "cols": [0.0, coll_width, 1.0],
            "rows": [0.0, 1.0]
        })

    elif count == 3:
        sublime.active_window().run_command("set_layout", {
            "cells": [[0, 0, 1, 1], [1, 0, 2, 1], [2, 0, 3, 1]],
            "cols": [0.0, 0.33, 0.66, 1.0],
            "rows": [0.0, 1.0]
        })

    elif count == 4:
        sublime.active_window().run_command("set_layout", {
            "cells": [[0, 0, 1, 1], [1, 0, 2, 1], [2, 0, 3, 1], [3, 0, 4, 1]],
            "cols": [0.0, 0.25, 0.5, 0.75, 1.0],
            "rows": [0.0, 1.0]
        })

# -----------------


def block_max_pane(mode):
    """Prevent Max Pane from managing windows, unblock after PUI is closed"""

    try:
        s = sublime.load_settings("max_pane_share.sublime-settings")
        s.set('block_max_pane', mode)
    except:
        return


# ===============================================================================

class csharp_mapper():

    def send_syntax_request(file, operation):
        try:
            syntaxerPort = int(os.environ.get(
                'CSSCRIPT_SYNTAXER_PORT', 'not_configured'))
            if syntaxerPort == 'not_configured':
                return None

            clientsocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            clientsocket.connect(('localhost', syntaxerPort))
            request = '-client:{0}\n-op:{1}\n-script:{2}'.format(
                os.getpid(), operation, file)
            clientsocket.send(request.encode('utf-8'))
            response = clientsocket.recv(1024 * 5)
            return response.decode('utf-8')
        except socket_error as serr:
            if serr.errno == errno.ECONNREFUSED:
                print(serr)

    # -----------------

    def generate(file):
        return csharp_mapper.send_syntax_request(
            file, 'codemap').replace('\r', '')

# ===============================================================================


class python_mapper():

    def generate(file):

        def str_of(count, char):
            text = ''
            for i in range(count):
                text = text + char
            return text

        # Parse
        item_max_length = 0

        try:
            members = []

            with codecs.open(file, "r", encoding='utf8') as f:
                lines = f.read().split('\n')

            line_num = 0
            last_type = ''
            last_indent = 0
            for line in lines:
                line = line.replace('\t', '    ')
                line_num = line_num + 1
                code_line = line.lstrip()

                info = None
                indent_level = len(line) - len(code_line)

                if code_line.startswith('class '):
                    last_type = 'class'
                    last_indent = indent_level
                    info = (line_num,
                            'class',
                            line.split('(')[0].split(':')[0].rstrip(),
                            indent_level)

                elif code_line.startswith('def '):
                    if last_type == 'def' and indent_level > last_indent:
                        continue    # local def
                    last_type = 'def'
                    last_indent = indent_level
                    info = (line_num,
                            'def',
                            line.split('(')[0].rstrip() + '()',
                            indent_level)

                if info:
                    length = len(info[2])
                    if item_max_length < length:
                        item_max_length = length
                    members.append(info)

        except Exception as err:
            print ('CodeMap-py:', err)
            members.clear()

        # format
        map = ''
        last_indent = 0
        last_type = ''
        for line, content_type, content, indent, in members:
            if indent != last_indent:
                if last_type == 'class' and content_type != 'class':
                    pass
                else:
                    map = map + '\n'
            else:
                if content_type == 'class':
                    map = map + '\n'

            preffix = str_of(indent, ' ')
            lean_content = content[indent:]
            suffix = str_of(item_max_length - len(content), ' ')
            # suffix = ' '
            # print(item_max_length)
            map = map + preffix + lean_content + \
                suffix + ' :' + str(line) + '\n'
            last_indent = indent
            last_type = content_type

        return map
