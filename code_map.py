import sublime
import sublime_plugin
import codecs
import os
import shutil
import sys
from os import path
from sublime import Region
import socket
import subprocess
import errno
from socket import error as socket_error

# version = 1.0.1

# ============================================================
def code_map_file():
    plugin_dir = os.path.dirname(__file__)
    data_dir = path.join(plugin_dir, 'CodeMap.Data', str(sublime.active_window().id()))
    if not path.exists(data_dir):
        os.makedirs(data_dir)
    return path.join(data_dir, 'Code - Map')
# -----------------
def set_layout_columns(count, coll_width=0.75):
    if count == 1:
        sublime.active_window().run_command("set_layout", {"cells": [[0, 0, 1, 1]], "cols": [0.0, 1.0], "rows": [0.0, 1.0]})
    elif count == 2:
        sublime.active_window().run_command("set_layout", {"cells": [[0, 0, 1, 1], [1, 0, 2, 1]], "cols": [0.0, coll_width, 1.0], "rows": [0.0, 1.0]})
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
            code_map_view.run_command('code_map_generator', {"source": file})
# -----------------
def set_syntax(view, language):
    view.run_command("set_file_type", {"syntax": 'Packages/'+language+'/'+language+'.tmLanguage'})
    
# ===============================================================================
class event_listener(sublime_plugin.EventListener):
    map_view_next_focus = None
    # -----------------
    def on_load(self, view): 
        if view.file_name() == code_map_file():
            soucre_view = view.window().active_view_in_group(0)

            if soucre_view and code_map_generator.can_map(soucre_view.file_name()):
                view.window().focus_view(soucre_view)
                set_syntax(view, 'Python')
    # -----------------
    def on_load(self, view): 
        if view.file_name() != code_map_file():
            refresh_map_for(view)
    # -----------------
    def on_close(self, view): 
        groups = sublime.active_window().num_groups()
        if groups > 1 and len(sublime.active_window().views_in_group(1)) == 0:
            set_layout_columns(1)
    # -----------------
    def on_activated(self, view):
        if view.file_name() == code_map_file():
            # Python syntax highlight just happens to be very suitable for the code map content
            set_syntax(view, 'Python')
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
        if file:
            if file.lower().endswith('.py'):
                return python_mapper.generate

            if file.lower().endswith('.cs') and 'CSSCRIPT_SYNTAXER_PORT' in os.environ.keys():
                return csharp_mapper.generate

            try:
                pre, ext = os.path.splitext(file)
                extension = ext[1:].lower() 

                script = sublime.active_window().active_view().settings().get('codemap_'+extension+'_mapper', None)
                if script:
                    mapper = SourceFileLoader(extension+"_mapper", script).load_module()
                    return mapper.generate

            except Exception as e:
                print(e)

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

        try: 
            generate = code_map_generator.get_maper(source)
            map = generate(source)

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
        groups = sublime.active_window().num_groups()
        original_focus = sublime.active_window().active_view() # note current focused view

        code_map_view = get_code_map_view()

        if not code_map_view:
            if groups == 1:
                set_layout_columns(2) 

            with open(code_map_file(), "w") as file: 
                file.write('')
            
            code_map_view = sublime.active_window().open_file(code_map_file())
            code_map_view.settings().set("word_wrap", False)
            sublime.active_window().set_view_index(code_map_view, 1, 0)
            code_map_view.sel().clear()
        
            code_map_view.window().focus_view(code_map_view)
            
            def focus_source_code():
                original_focus.window().focus_view(original_focus)
            
            sublime.set_timeout_async(focus_source_code, 100)   
                
        else:
            code_map_view.window().focus_view(code_map_view)
            code_map_view.window().run_command("close_file")


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

            with codecs.open(file, "r") as f:
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

                if code_line.startswith('class'):
                    last_type = 'class'
                    last_indent = indent_level
                    info = (line_num, 
                            'class', 
                            line.split('(')[0].split(':')[0].rstrip(), 
                            indent_level) 

                elif code_line.startswith('def'):
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
            print (err)
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