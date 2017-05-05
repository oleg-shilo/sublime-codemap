import sublime
import sublime_plugin
import codecs
import os
import shutil
import sys
import zipfile
from os import path
from sublime import Region
import socket
import subprocess
import errno
from socket import error as socket_error

# version = 1.0.8

if sys.version_info < (3, 3):
    raise RuntimeError('CodeMap works with Sublime Text 3 only.')

# ============================================================
py_syntax = 'Packages/Python/Python.tmLanguage'
md_syntax = 'Packages/Text/Plain text.tmLanguage'
cs_syntax = 'Packages/C#/C#.tmLanguage'
MAPPERS = None
# -------------------------
def is_compressed_package():
    packages_dir = sublime.packages_path()
    plugin_dir = os.path.dirname(__file__)
    return not plugin_dir.startswith(packages_dir)
# -------------------------
def mapper_path(syntax):
    return os.path.join(sublime.packages_path(), 'User', 'CodeMap', 'custom_mappers', 'code_map.'+syntax+'.py')
# -------------------------
def syntax_path(syntax):
    return os.path.join(sublime.packages_path(), 'User', 'CodeMap', 'custom_languages', syntax+'.sublime-syntax')
# -------------------------
def plugin_loaded():

    global MAPPERS

    default_mappers = ['md', 'py']        
    custom_languages = ['md']        

    dst = os.path.join(sublime.packages_path(), 'User', 'CodeMap')
    mpdir = os.path.join(dst, 'custom_mappers')
    lng_dir = os.path.join(dst, 'custom_languages')

    if not os.path.isdir(dst): os.mkdir(dst)
    if not os.path.isdir(mpdir): os.mkdir(mpdir)
    if not os.path.isdir(lng_dir): os.mkdir(lng_dir)

    if is_compressed_package():  
        # package was installed via Package Control
        pack = os.path.join(sublime.installed_packages_path(), 'CodeMap.sublime-package')
        if not os.path.isfile(pack): # package was installed via git repository
            pack = os.path.join(sublime.installed_packages_path(), 'sublime-codemap.sublime-package') 

        zip = zipfile.ZipFile(pack)
        
        for syntax in default_mappers: 
            if not os.path.isfile(mapper_path(syntax)): 
                zip.extract('custom_mappers/code_map.'+syntax+'.py', dst)

        for syntax in custom_languages: 
            if not os.path.isfile(syntax_path(syntax)): 
                zip.extract('custom_languages/'+syntax+'.sublime-syntax', dst)

    else:  
        # package was installed manually
        plugin_dir = os.path.dirname(__file__)

        for syntax in default_mappers: 
            src_mapper = os.path.join(plugin_dir, 'custom_mappers', 'code_map.'+syntax+'.py')
            dst_mapper = mapper_path(syntax)
            if not os.path.isfile(dst_mapper): 
                shutil.copyfile(src_mapper, dst_mapper) 

        for syntax in custom_languages: 
            src_syntax = os.path.join(plugin_dir, 'custom_languages', syntax+'.sublime-syntax')
            dst_syntax = syntax_path(syntax)
            if not os.path.isfile(syntax): 
                shutil.copyfile(src_syntax, dst_syntax) 

    # make a list of the available mappers
    MAPPERS = os.listdir(mpdir)
# -------------------------
def settings():
    return sublime.load_settings("code_map.sublime-settings")
# -------------------------
def code_map_file():

    plugin_dir = ''

    if hasattr(sublime, 'cache_path'):
        plugin_dir = sublime.cache_path()
    else:
        plugin_dir = 'cache'
        plugin_dir = os.path.join(os.getcwd(), plugin_dir)

    data_dir = path.join(plugin_dir, 'CodeMap', 'CodeMap.Data', str(sublime.active_window().id()))
    if not path.exists(data_dir):
        os.makedirs(data_dir)
    return path.join(data_dir, 'Code - Map')
# -----------------
def set_layout_columns(count, coll_width=0.75):

    if count == 1:
        sublime.active_window().run_command("set_layout", {"cells": [[0, 0, 1, 1]], "cols": [0.0, 1.0], "rows": [0.0, 1.0]})

    elif count == 2:
         sublime.active_window().run_command("set_layout", {"cells": [[0, 0, 1, 1], [1, 0, 2, 1]], "cols": [0.0, coll_width, 1.0], "rows": [0.0, 1.0]})

    elif count == 3:
         sublime.active_window().run_command("set_layout", {"cells": [[0, 0, 1, 1], [1, 0, 2, 1], [2, 0, 3, 1]], "cols": [0.0, 0.33, 0.66, 1.0], "rows": [0.0, 1.0]})

    elif count == 4:
         sublime.active_window().run_command("set_layout", {"cells": [[0, 0, 1, 1], [1, 0, 2, 1], [2, 0, 3, 1], [3, 0, 4, 1]], "cols": [0.0, 0.25, 0.5, 0.75, 1.0], "rows": [0.0, 1.0]})
# -----------------
def centre_line_of(view, region):
    (first_row,c) = view.rowcol(region.begin())
    (last_row,c) = view.rowcol(region.end())
    return int(first_row + (last_row - first_row)/2)
# -----------------
def get_code_map_view():
    for v in sublime.active_window().views():
        if v.file_name() == code_map_file():
            return v
# -----------------
def refresh_map_for(view):
    file = view.file_name()
    if code_map_generator.can_map(file):
        code_map_view = get_code_map_view()
        if code_map_view:
            code_map_view.run_command('code_map_generator', {"source": file })

# ===============================================================================
class event_listener(sublime_plugin.EventListener):
    map_closed_group = -1
    pre_close_active = None
    can_close = False
    # -----------------
    def on_load(self, view):
        if view.file_name() != code_map_file():
            refresh_map_for(view)
    # -----------------
    def on_pre_close(self, view):
        if view.file_name() == code_map_file():
            event_listener.map_closed_group, x = sublime.active_window().get_view_index(view)
            if len(sublime.active_window().views_in_group(event_listener.map_closed_group)) == 1:
                event_listener.can_close = True
    # -----------------
    def on_close(self, view):

        def close_codemap_group():
            """Removes the Code Map group, and scales up the rest of the layout"""
            layout = window.get_layout()
            cols = layout['cols']
            cells = layout['cells']
            last_col = len(cols) - 1
            map_width = cols[len(cols) - 2]

            for i, col in enumerate(cols):
                if col > 0:
                    cols[i] = col/map_width

            del cols[last_col]
            del cells[len(cells) - 1]
            window.run_command("set_layout", layout)

        def focus_source_code():
            if event_listener.pre_close_active:
                window.focus_group(event_listener.pre_close_active[0])
                window.focus_view(event_listener.pre_close_active[1])

        enabled = settings().get('close_empty_group_on_closing_map', False)

        if event_listener.can_close and enabled and view.file_name() == code_map_file() and event_listener.map_closed_group != -1:
            window = sublime.active_window()
            event_listener.can_close = False
            close_codemap_group()
            sublime.set_timeout(focus_source_code, 100)

        event_listener.map_closed_group = -1
    # -----------------
    def on_post_save_async(self, view):
        refresh_map_for(view)
    # -----------------
    def on_activated_async(self, view):
        refresh_map_for(view)
    # -----------------
    def on_post_text_command(self, view, command_name, args):
        # process double-click on code map view
        if view.file_name() == code_map_file():
            if command_name == 'drag_select' and 'by' in args.keys() and args['by'] == 'words':
                point = view.sel()[0].begin()
                line_region = view.line(point)
                line_text = view.substr(line_region)

                view.sel().clear()
                view.sel().add(line_region)

                line_num = 1
                try:
                    line_num = int(line_text.split(':')[-1].strip().split(' ')[-1])
                except:
                    pass

                just_loaded = False
                source_code_view = None

                if code_map_generator.source:
                    source_code_view = sublime.active_window().find_open_file(code_map_generator.source)
                    if not source_code_view:
                        source_code_view = sublime.active_window().open_file(code_map_generator.source)
                        just_loaded = True

                if source_code_view:
                    sublime.status_message('Navigating to clicked item...')
                    point = source_code_view.text_point(line_num-1, 0)
                    new_selection = source_code_view.line(point)

                    source_code_view.sel().clear()
                    source_code_view.sel().add(new_selection)
                    source_code_view.show_at_center(new_selection)

                    if just_loaded:
                        def move_to_first_group():
                            group, index = sublime.active_window().get_view_index(source_code_view)
                            if group == 1:
                                sublime.active_window().set_view_index(source_code_view, 0, 0)
                            sublime.active_window().focus_view(source_code_view)

                        sublime.set_timeout_async(move_to_first_group, 30)
                    else:
                        sublime.active_window().focus_view(source_code_view)

# ===============================================================================
from importlib.machinery import SourceFileLoader
class code_map_generator(sublime_plugin.TextCommand):
    # -----------------
    source = None
    positions = {}
    # -----------------
    def get_maper(file):
        # Note that the default map syntax is Python. It just looks better then others
        if file:
            if file.lower().endswith('.cs') and 'CSSCRIPT_SYNTAXER_PORT' in os.environ.keys():
                return csharp_mapper.generate, py_syntax

            try:
                pre, ext = os.path.splitext(file)
                extension = ext[1:].lower()

                script = 'code_map.'+extension+'.py'
                if script in MAPPERS:
                    script = mapper_path(extension)
                    mapper = SourceFileLoader(extension+"_mapper", script).load_module()
                    syntax = mapper.map_syntax if hasattr(mapper, 'map_syntax') else py_syntax
                    
                    return mapper.generate, syntax

            except Exception as e:
                print(e)

            if file.lower().endswith('.py'):
                return python_mapper.generate, py_syntax

    def can_map(file):
        return code_map_generator.get_maper(file) != None
    # -----------------
    def run(self, edit, **args):
        code_map_view = self.view

        # remember old position
        oldSource = code_map_generator.source
        if oldSource:
            center_line = centre_line_of(code_map_view, code_map_view.visible_region())
            selected_line = None

            if len(code_map_view.sel()) > 0 and code_map_view.sel()[0]:
                selected_line = code_map_view.sel()[0]

            code_map_generator.positions[oldSource] = (center_line, selected_line)

        # generate new map
        source = args['source']
        map = ""
        map_syntax = py_syntax

        try:
            (generate, syntax) = code_map_generator.get_maper(source)
            map = generate(source)
            map_syntax = syntax

        except Exception as err:
            print ('code_map.generate:', err)

        all_text = sublime.Region(0, code_map_view.size())
        code_map_view.replace(edit, all_text, map)
        code_map_view.set_scratch(True)
        code_map_generator.source = source

        if code_map_generator.source in code_map_generator.positions.keys():
            (center_line, selection) = code_map_generator.positions[code_map_generator.source]

            if center_line:
                point = code_map_view.text_point(center_line, 0)
                code_map_view.sel().clear()
                code_map_view.show_at_center(point)

                if selection:
                    code_map_view.sel().add(selection)

                else:
                    code_map_view.sel().add(Region(0,0))

        code_map_view.assign_syntax(map_syntax)

# ===============================================================================
class scroll_to_left(sublime_plugin.TextCommand):
    # -----------------
    def code_map_view(next_focus_view=None):

        def do():
            get_code_map_view().run_command('scroll_to_left')

        sublime.set_timeout(do, 100)
    # -----------------
    def run(self, edit):
        region = self.view.visible_region()
        y = self.view.text_to_layout(region.begin())[1]
        self.view.set_viewport_position((0, y), False)

# ===============================================================================
class synch_code_map(sublime_plugin.TextCommand):
    # -----------------
    def run(self, edit):
        map_view = get_code_map_view()

        if map_view and len(map_view.sel()) > 0:
            code_view_line, _ = self.view.rowcol(self.view.sel()[0].begin())

            prev_member_line_num = 0
            prev_map_line = None

            lines = map_view.lines(sublime.Region(0, map_view.size()))

            for line in lines:
                link = map_view.substr(line).split(':')[-1]

                member_line_num = None
                try:
                    member_line_num = int(link)
                except:
                    continue

                if member_line_num and member_line_num > code_view_line:
                    break

                else:
                    prev_member_line_num = member_line_num
                    prev_map_line = line

            map_view.sel().clear()
            map_view.sel().add(prev_map_line)
            map_view.show_at_center(prev_map_line)
            map_view.window().focus_view(map_view)
            scroll_to_left.code_map_view(self.view)

# ===============================================================================
class show_code_map(sublime_plugin.TextCommand):
    # -----------------
    def run(self, edit):

        def create_codemap_group():
            """Adds a column on the right, and scales down the rest of the layout"""
            layout = self.view.window().get_layout()
            cols = layout['cols']
            cells = layout['cells']
            last_col = len(cols) - 1
            last_row = len(layout['rows']) - 1
            width = 1 - settings().get("codemap_width")

            for i, col in enumerate(cols):
                if col > 0:
                    cols[i] = col*width

            cols.append(1)
            newcell = [last_col, 0, last_col + 1, last_row]
            cells.append(newcell)
            window.run_command("set_layout", layout)
            groups = window.num_groups()
            return (groups + 1)

        window = self.view.window()
        groups = window.num_groups()
        current_group = window.active_group()
        current_view = self.view

        code_map_view = get_code_map_view()

        if not code_map_view:
            code_map_group = 1

            show_in_new_group = settings().get("show_in_new_group", True)

            if not show_in_new_group:
                if groups == 1:
                    set_layout_columns(2)
                    groups = window.num_groups()

            else:
                code_map_group = create_codemap_group()

            with open(code_map_file(), "w") as file:
                file.write('')

            code_map_view = window.open_file(code_map_file())
            code_map_view.settings().set("word_wrap", False)
            window.set_view_index(code_map_view, code_map_group, 0)
            code_map_view.sel().clear()

            code_map_view.settings().set("gutter", False)

            def focus_source_code():
                window.focus_group(current_group)
                window.focus_view(current_view)

            sublime.set_timeout_async(focus_source_code, 100)

        else:
            # close group only if codemap is the only file in it
            code_map_group = window.get_view_index(code_map_view)[0]
            if len(window.views_in_group(code_map_group)) == 1:
                event_listener.pre_close_active = [current_group, current_view]
                event_listener.can_close = True
            window.focus_view(code_map_view)
            window.run_command("close_file")


# ===============================================================================
class csharp_mapper():
    # -----------------
    def send_syntax_request(file, operation):
        try:
            syntaxerPort = int(os.environ.get('CSSCRIPT_SYNTAXER_PORT', 'not_configured'))
            if syntaxerPort == 'not_configured':
                return None

            clientsocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            clientsocket.connect(('localhost', syntaxerPort))
            request = '-client:{0}\n-op:{1}\n-script:{2}'.format(os.getpid(), operation, file)
            clientsocket.send(request.encode('utf-8'))
            response = clientsocket.recv(1024*5)
            return response.decode('utf-8')
        except socket_error as serr:
            if serr.errno == errno.ECONNREFUSED:
                print(serr)
    # -----------------
    def generate(file):
        return csharp_mapper.send_syntax_request(file, 'codemap').replace('\r', '')

# ===============================================================================
class python_mapper():
    # -----------------
    def generate(file):

        def str_of(count, char):
            text = ''
            for i in range(count):
                text = text + char
            return text

        # Pasrse
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
                indent_level = len(line) - len(code_line);

                if code_line.startswith('class '):
                    last_type = 'class'
                    last_indent = indent_level
                    info = (line_num,
                            'class',
                            line.split('(')[0].split(':')[0].rstrip(),
                            indent_level)

                elif code_line.startswith('def '):
                    if last_type == 'def' and indent_level > last_indent:
                        continue #local def
                    last_type = 'def'
                    last_indent = indent_level
                    info = (line_num,
                            'def',
                            line.split('(')[0].rstrip()+'()',
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
        for line, content_type, content, indent,  in members:
            if indent != last_indent:
                if last_type == 'class' and content_type != 'class':
                    pass
                else:
                    map = map+'\n'
            else:
                if content_type == 'class':
                    map = map+'\n'

            preffix = str_of(indent, ' ')
            lean_content = content[indent:]
            suffix = str_of(item_max_length-len(content), ' ')
            # suffix = ' '
            # print(item_max_length)
            map = map + preffix + lean_content + suffix +' :'+str(line) +'\n'
            last_indent = indent
            last_type = content_type

        return map