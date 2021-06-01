import sublime
# import sublime_plugin
import os
import re
import socket
from socket import error as socket_error
import errno

# ===============================================================================

DEPTH = [2, {}]

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
            return v.substr(sublime.Region(line.a, line.a + 1)) in [" ", r"\t"]

        while True:
            line = v.line(v.sel()[0].b)
            if line.b == v.size():                  # end of CodeMap
                NavigateCodeMap.keep_going_up(v)    # select one line up
                break
            line = v.line(v.sel()[0].b + 1)         # get next line
            if indented() or line.empty():
                v.run_command("move", {"by": "lines", "forward": True})
            else:
                v.run_command("move", {"by": "lines", "forward": True})
                break

    def keep_going_up(v):

        def indented():
            return v.substr(sublime.Region(line.a, line.a + 1)) in [" ", r"\t"]

        while True:
            line = v.line(v.sel()[0].a)
            if line.a == 0:                         # begin of CodeMap
                NavigateCodeMap.keep_going_down(v)  # select one line down
                break
            line = v.line(v.sel()[0].a - 1)         # get previous line
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
    Guess = None
    Using_tabs = False

    def evaluate(file, extension, view=None, universal=False):
        global DEPTH

        sets = settings()
        if file in DEPTH[1]:
            DEPTH[0] = DEPTH[1][file]
        else:
            DEPTH[0] = sets.get('depth')

        # Before checking the file extension, try to guess from the sysntax associated to the view
        if view:
            syntax = os.path.splitext(os.path.split(view.settings().get('syntax'))[1])[0]
            mappers = [m[0] for m in sets.get('syntaxes')]
            for i, m in enumerate(mappers):
                if m.lower() == syntax.lower():
                    universal_mapper.mapping = mappers[i]
                    syntax = sets.get(mappers[i])['syntax']
                    try:
                        with open(file, "r", encoding='utf8') as f:
                            content = f.read()
                        return (universal_mapper.generate(content), syntax)
                    except Exception as err:
                        print(err)
                        return None

        # last resort
        if universal:
            universal_mapper.mapping = "universal"
            syntax = sets.get("universal")['syntax']
            return (universal_mapper.generate(file), syntax)

        # unsupported file types
        unsupported = [syn for syn in sets.get('exclusions')]

        # get mappers/extensions defined in the settings
        mappers = [m[0] for m in sets.get('syntaxes')]
        exts = [m[1] for m in sets.get('syntaxes')]

        # TODO: universal_mapper.Guess
        universal_mapper.Guess = None

        # attempt to map a known file type as defined in the settings
        if extension in unsupported:
            return ("Unsupported file type", "Packages/Text/Plain text.tmLanguage")

        elif extension in exts:
            map = mappers[exts.index(extension)]
            universal_mapper.mapping = map

            mapper = sets.get(map)
            if not mapper:  # wrong config
                return None

            try:
                with open(file, "r", encoding='utf8') as f:
                    file = f.read()
                return (universal_mapper.generate(file), mapper['syntax'])
            except Exception as err:
                print(err)
                return None

        # not a recognized file type, will maybe return here later for fallback
        else:
            return None

    # -----------------

    def generate(file):

        # -----------------

        def is_func(patterns, string):

            # patterns is a collection of regex matching definitions to test a given string against.
            # Each item (definition) consist of a few regex expressions to identify a syntax declaration
            # and transform groom the regex match into a presentable item in the code map tree
            # Sample:
            #     [
            # 1.      "^(class |function |export class |interface ).*$", 
            # 2.      "[(:{].*$",                                        
            # 3.      "",
            # 4.      false
            #      ]
            # 1. Pattern to detect if the string is a declaration (e.g. a class). It is if it matches the pattern
            # 2. Replacement pattern to be used against a declaration string
            # 3. Replacement value to be used against a declaration string
            # 4. instead of testing string test its last matching+grooming result. Only applicable if multiple 
            #    patterns are defined. 
            #    Basically it is like this:
            #      take the pattern def ind apply it on the string, save the matching result
            #      take the next pattern and apply it to on the last match from the prev matching
            #      . . .
            # Note the line text that is tested with regex is left trimmed before the test. Meaning that if your 
            # code has line " say_hello():" the text that is tested with regex is "say_hello():"

            def search(string, popped=False):
                r = pat[0].search(string) 
                if r:
                    if pat[1] or pat[2]:
                        r = pat[1].sub(pat[2], string)
                    else:
                        r = r.group(0)
                elif popped:
                    r = string
                else:
                    r = ""
                return r

            matches = []
            for pat in patterns:
                if pat[3] and matches:
                    r = search(matches.pop(), popped=True)
                else:
                    r = search(string)
                matches.append(r)
            match = max(matches)
            return match

        # -----------------

        def find_indent(line, tab):
            i = re.match(tab + r"+", line)
            if i:
                x, ni = re.subn(tab, "", i.group(0))
                if universal_mapper.Using_tabs:
                    ...
                elif indent_size and ni % indent_size:
                    # skip incorrect indents
                    return 0
            else:
                return 0
            if ni:
                indents.append(ni)
                min_ind = min(indents)
                return int(ni / min_ind)
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
            # always add ' ' to let text/line_num separation for the cases when "line numbers before" is true
            if mapping != "universal":
                return suf+" "
            elif guess == "python":
                return "() "
            else:
                return " "
        # -----------------

        def nl(line):
            if new_line_before and mapping != "universal":
                nl = re.match(new_line_before, line)
            elif guess == "python" and line.lstrip()[:5] == "class":
                nl = True
            else:
                return ""

            nl = "\n" if nl else ""
            return nl
        # -----------------

        Map, indents = '', []
        line_num, printed_lines = 0, []
        lines = file.split('\n')

        mapping, guess = universal_mapper.mapping, universal_mapper.Guess

        if universal_mapper.Using_tabs:
            tab, indent_size = "\t", 1
        else:
            tab, indent_size = " ", settings().get(mapping)['indent']

        oblig_indent = settings().get(mapping)['obligatory indent']
        new_line_before = settings().get(mapping)['empty line in map before']
        npos = settings().get(mapping)['line numbers before']
        pre = settings().get(mapping)['prefix']
        suf = settings().get(mapping)['suffix']
        patterns = settings().get(mapping)['regex']
        for pat in patterns:
            pat[0] = re.compile(pat[0])
            pat[1] = re.compile(pat[1])

        for line in lines:
            line_num += + 1

            if len(line) == 0:
                continue

            _line = is_func(patterns, line.lstrip())
            # _line = is_func(patterns, line)
            if not _line:
                continue
            indent = find_indent(line, tab)
            line = obl_indent(line, indent)

            if indent <= DEPTH[0]:
                line = nl(_line) + tab * indent * indent_size + prefix() + _line + suffix()
                printed_lines.append((line, line_num))

        if not printed_lines:
            # empty space so it doesn't return None
            return " "

        max_length = max(len(line[0]) for line in printed_lines)
        if max_length > 40:
            max_length = 40
        for line in printed_lines:
            if len(line) > max_length:
                line = line[0:max_length - 2] + '...'
            spc = 1 if line[0][0] == "\n" else 0
            string = line[0] + ' ' * (max_length - len(line[0])) + ' ' * spc
            if len(string) < 25:
                string += ' ' * (25 - len(string))
            if npos:
                num = str(line[1])
                Map += num + ':   ' + string + num + '\n'
            else:
                Map += string + '    :' + str(line[1]) + '\n'

        if Map[0] == '\n':
            Map = Map[1:]

        return Map


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
