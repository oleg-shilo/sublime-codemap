import sublime
# import sublime_plugin
import os
import re
import codecs
import socket
from socket import error as socket_error
import errno

# ===============================================================================

EXTENSION, DEPTH = "", [2, {}]

# ===============================================================================


def settings():
    return sublime.load_settings("code_map.sublime-settings")

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
    '''Prevent Max Pane from managing windows, unblock after PUI is closed'''

    try:
        s = sublime.load_settings("max_pane_share.sublime-settings")
        s.set('block_max_pane', mode)
    except:
        return

# ===============================================================================


class NavigateCodeMap():

    def highlight_line(v):
        line = v.line(v.sel()[0].a)
        v.sel().clear()
        v.sel().add(sublime.Region(line.a, line.b))

    def keep_going_down(v):

        def indented():
            return v.substr(sublime.Region(line.a, line.a+1)) in [" ", r"\t"]

        while True:
            line = v.line(v.sel()[0].b)
            if line.b == v.size():
                NavigateCodeMap.keep_going_up(v)
                break
            line = v.line(v.sel()[0].b+1)
            if indented() or line.empty():
                v.run_command("move", {"by": "lines", "forward": True})
            else:
                v.run_command("move", {"by": "lines", "forward": True})
                break

    def keep_going_up(v):

        def indented():
            return v.substr(sublime.Region(line.a, line.a+1)) in [" ", r"\t"]

        while True:
            line = v.line(v.sel()[0].a)
            if line.a == 0:
                NavigateCodeMap.keep_going_down(v)
                break
            line = v.line(v.sel()[0].a-1)
            if indented() or line.empty():
                v.run_command("move", {"by": "lines", "forward": False})
            else:
                v.run_command("move", {"by": "lines", "forward": False})
                break

    def up(v, fast):
        v.run_command("move_to", {"to": "bol", "extend": False})
        if not fast:
            v.run_command("move", {"by": "lines", "forward": False})
            if v.line(v.sel()[0]).empty():
                v.run_command("move", {"by": "lines", "forward": False})
        else:
            NavigateCodeMap.keep_going_up(v)

    def down(v, fast):
        v.run_command("move_to", {"to": "bol", "extend": False})
        v.run_command("move", {"by": "lines", "forward": True})
        line = v.line(v.sel()[0])
        if not fast:
            if line.b == v.size():
                v.run_command("move", {"by": "lines", "forward": False})
            elif line.empty():
                v.run_command("move", {"by": "lines", "forward": True})
        else:
            NavigateCodeMap.keep_going_down(v)

# ===============================================================================


class universal_mapper():

    def evaluate(file, extension, universal=False):
        global EXTENSION, DEPTH

        sets = settings()
        if file in DEPTH[1]:
            DEPTH[0] = DEPTH[1][file]
        else:
            DEPTH[0] = sets.get('depth')

        # last resort
        if universal:
            universal_mapper.mapping = "universal"
            EXTENSION = extension
            syntax = sets.get("universal")['syntax']
            return (universal_mapper.generate(file), syntax)

        # unsupported file types
        unsupported = [syn for syn in sets.get('exclusions')]

        # get mappers/extensions defined in the settings
        mappers = [syn for syn in sets.get('syntaxes')]
        exts = [ext[1] for ext in mappers]
        mappers = [mapper[0] for mapper in mappers]

        # TODO: universal_mapper.guess
        universal_mapper.guess = None

        # attempt to map a known file type as defined in the settings
        if extension in unsupported:
            return ("Unsupported file type",
                    "Packages/Text/Plain text.tmLanguage")

        elif extension in exts:
            map = mappers[exts.index(extension)]
            universal_mapper.mapping = map
            syntax = sets.get(map)['syntax']

            try:
                with codecs.open(file, "r", encoding='utf8') as f:
                    file = f.read()
                return (universal_mapper.generate(file), syntax)
            except Exception as err:
                print(err)
                return None

        # not a recognized file type, will maybe return here later for fallback
        else:
            return None

    # -----------------

    def generate(file):

        # -----------------

        def is_func(string):

            def search(string):
                r = re.search(pat[0], string)
                if r:
                    if pat[1] or pat[2]:
                        r = re.sub(pat[1], pat[2], string)
                    else:
                        r = r.group(0)
                else:
                    r = ""
                return r

            matches = []
            patterns = settings().get(mapping)['regex']
            for pat in patterns:
                if pat[3] and matches:
                    r = search(matches.pop())
                else:
                    r = search(string)
                matches.append(r)
            match = max(matches)
            return match

        # -----------------

        def find_indent(line):
            i = re.match(r"\s+?", line)
            if i:
                x, ni = re.subn(r"\s(?:[^\S])", "", line)
            else:
                return 0
            if ni:
                indents.append(ni)
                min_ind = min(indents)
                return int(ni/min_ind)
            else:
                return 0
        # -----------------

        def obl_indent(line, indent):

            if oblig_indent:
                if indent:
                    return line.lstrip()
                else:
                    return ""
            else:
                return line.lstrip()

        # -----------------

        def prefix():
            if mapping != "universal":
                return pre
            elif guess == "python":
                return ""
            else:
                return ""
        # -----------------

        def suffix():
            if mapping != "universal":
                return suf
            elif guess == "python":
                return "()"
            else:
                return ""
        # -----------------

        def nl(line):
            if mapping != "universal":
                nl = re.match(new_line_before, line)
            elif guess == "python" and line.lstrip()[:5] == "class":
                nl = True
            else:
                return ""

            nl = "\n" if nl else ""
            return nl
        # -----------------

        lines = file.split('\n')
        map, indents = '', []
        mapping = universal_mapper.mapping
        guess = universal_mapper.guess
        oblig_indent = settings().get(mapping)['obligatory indent']
        indent_size = settings().get(mapping)['indent']
        new_line_before = settings().get(mapping)['empty line in map before']
        npos = settings().get(mapping)['line numbers before']
        pre = settings().get(mapping)['prefix']
        suf = settings().get(mapping)['suffix']

        line_num = 0
        printed_lines = []

        for line in lines:
            line_num = line_num + 1

            if len(line) == 0:
                continue

            indent = find_indent(line)
            line = obl_indent(line, indent)
            line = is_func(line)

            if line and indent <= DEPTH[0]:
                line = nl(line) + ' '*indent*indent_size + \
                       prefix() + line + suffix()
                printed_lines.append((line, line_num))

        if not printed_lines:
            return "Decoding failed."

        max_length = max(len(line[0]) for line in printed_lines)
        if max_length > 40:
            max_length = 40
        for line in printed_lines:
            if len(line) > max_length:
                line = line[0:max_length-2] + '...'
            spc = 1 if line[0][0] == "\n" else 0
            string = line[0]+' '*(max_length-len(line[0]))+' '*spc
            if len(string) < 25:
                string += ' '*(25-len(string))
            if npos:
                num = str(line[1])
                map += num + ':   ' + string + num+'\n'
            else:
                map += string + '    :' + str(line[1])+'\n'

        return map


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
            print('CodeMap-py:', err)
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
            map = map + preffix + lean_content + \
                suffix + ' :' + str(line) + '\n'
            last_indent = indent
            last_type = content_type

        return map
