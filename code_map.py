import sublime
import sublime_plugin
import os
import shutil
import sys
import zipfile
from os import path
from sublime import Region
from importlib.machinery import SourceFileLoader
import CodeMap.code_map_support as Mapper
from CodeMap.code_map_support import NavigateCodeMap as Nav

# version = 1.0.8

if sys.version_info < (3, 3):
    raise RuntimeError('CodeMap works with Sublime Text 3 only.')

# ============================================================

py_syntax = 'Packages/Python/Python.tmLanguage'
md_syntax = 'Packages/Text/Plain text.tmLanguage'
cs_syntax = 'Packages/C#/C#.tmLanguage'
MAPPERS = None

# -------------------------


def plugin_loaded():
    global MAPPERS, ACTIVE

    ACTIVE = True if get_code_map_view() else False

    default_mappers = ['md', 'py']
    custom_languages = ['md']
    ipath = sublime.installed_packages_path()
    Mapper.EXTENSION, Mapper.DEPTH = "", [settings().get('depth'), {}]

    dst = path.join(sublime.packages_path(), 'User', 'CodeMap')
    mpdir = path.join(dst, 'custom_mappers')
    lng_dir = path.join(dst, 'custom_languages')

    if not path.isdir(dst):
        os.mkdir(dst)
    if not path.isdir(mpdir):
        os.mkdir(mpdir)
    if not path.isdir(lng_dir):
        os.mkdir(lng_dir)

    if is_compressed_package():
        # package was installed via Package Control
        pack = path.join(ipath(), 'CodeMap.sublime-package')
        # package was installed via git repository
        if not path.isfile(pack):
            pack = path.join(ipath(), 'sublime-codemap.sublime-package')

        zip = zipfile.ZipFile(pack)

        for syntax in default_mappers:
            if not path.isfile(mapper_path(syntax)):
                zip.extract('custom_mappers/code_map.'+syntax+'.py', dst)

        for syntax in custom_languages:
            if not path.isfile(syntax_path(syntax)):
                zip.extract('custom_languages/'+syntax+'.sublime-syntax', dst)

    else:
        # package was installed manually
        plugin_dir = path.dirname(__file__)

        for syntax in default_mappers:
            src_mapper = path.join(
                plugin_dir, 'custom_mappers', 'code_map.'+syntax+'.py')
            dst_mapper = mapper_path(syntax)
            if not path.isfile(dst_mapper):
                shutil.copyfile(src_mapper, dst_mapper)

        for syntax in custom_languages:
            src_syntax = path.join(
                plugin_dir, 'custom_languages', syntax+'.sublime-syntax')
            dst_syntax = syntax_path(syntax)
            if not path.isfile(syntax):
                shutil.copyfile(src_syntax, dst_syntax)

    # make a list of the available mappers
    MAPPERS = os.listdir(mpdir)

# -------------------------


def is_compressed_package():
    plugin_dir = path.dirname(__file__)
    return not plugin_dir.startswith(sublime.packages_path())


def mapper_path(syntax):
    return path.join(sublime.packages_path(), 'User', 'CodeMap',
                     'custom_mappers', 'code_map.'+syntax+'.py')


def syntax_path(syntax):
    return path.join(sublime.packages_path(), 'User', 'CodeMap',
                     'custom_languages', syntax+'.sublime-syntax')


def settings():
    return sublime.load_settings("code_map.sublime-settings")


def win():
    return sublime.active_window()

# -------------------------


def code_map_file():

    dst = path.join(sublime.packages_path(), 'User', 'CodeMap')
    return path.join(dst, 'Code - Map')

# -----------------


def get_code_map_view():
    for v in win().views():
        if v.file_name() == code_map_file():
            return v

# -----------------


def refresh_map_for(view):
    file = view.file_name()
    if file and code_map_generator.can_map(file):
        map_view = get_code_map_view()
        if map_view:
            map_view.run_command('code_map_generator', {"source": file})

            # avoid certain error messages
            try:
                if map_view.sel():
                    lines = map_view.split_by_newlines(
                        map_view.sel()[0])
                if len(lines) > 1:
                    map_view.sel().clear()
            except:
                map_view.sel().clear()

# -----------------


def synch_map(v, give_back_focus=True):

    def go():
        map_view = get_code_map_view()

        if map_view and map_view.size() > 0:
            code_view_line, _ = v.rowcol(v.sel()[0].a)

            prev_map_line = None

            lines = map_view.lines(sublime.Region(0, map_view.size()))

            for line in lines:
                link = map_view.substr(line).split(':')[-1]

                member_line_num = None
                try:
                    member_line_num = int(link)
                except:
                    continue

                # added +1 so that it works for the first line of the function
                if member_line_num and member_line_num > code_view_line+1:
                    break

                else:
                    prev_map_line = line

            map_view.sel().clear()
            if prev_map_line:
                map_view.sel().add(prev_map_line)
                map_view.show(prev_map_line.a)
                map_view.window().focus_view(map_view)

    # apply a timeout to the whole function, add an additional timeout if it's
    # necessary to focus back to the original view
    sublime.set_timeout(go, 10)
    if give_back_focus:
        sublime.set_timeout(lambda: win().focus_view(v), 10)

# -----------------


def navigate_to_line(map_view, give_back_focus=False):
    try:
        point = map_view.sel()[0].a
    except:
        # no idea why this happens, it's a workaround
        point = 0
        CodeMapListener.skip = True
        win().focus_view(map_view)

    line_region = map_view.line(point)
    line_text = map_view.substr(line_region)

    line_num = 1
    try:
        line_num = int(line_text.split(':')[-1].strip(
            ).split(' ')[-1])
    except:
        pass

    source_code_view = None

    if code_map_generator.source:
        source_code_view = win().find_open_file(
            code_map_generator.source)
        if not source_code_view:
            source_code_view = win().open_file(
                code_map_generator.source)

    if source_code_view:
        sublime.status_message('Navigating to clicked item...')
        point = source_code_view.text_point(line_num-1, 0)
        new_selection = source_code_view.line(point)
        source_code_view.sel().clear()
        source_code_view.sel().add(new_selection)
        source_code_view.show_at_center(new_selection)

        if not give_back_focus:
            return
        else:
            win().focus_view(source_code_view)

# =============================================================================


class code_map_generator(sublime_plugin.TextCommand):

    # -----------------

    source = None
    positions = {}

    # -----------------

    def get_mapper(file):
        # Default map syntax is Python. It just looks better than others
        global using_universal_mapper

        if file:
            if file.lower().endswith('.cs'):
                if 'CSSCRIPT_SYNTAXER_PORT' in os.environ.keys():
                    return Mapper.csharp_mapper.generate, py_syntax

            try:
                using_universal_mapper = True
                pre, ext = path.splitext(file)
                extension = ext[1:].lower()

                # try with mappers defined in the settings first
                mapper = Mapper.universal_mapper.evaluate(
                                                file, extension)
                if mapper:
                    return mapper

                # try with mappers defined in files next
                script = 'code_map.'+extension+'.py'

                if script in MAPPERS:

                    using_universal_mapper = False
                    script = mapper_path(extension)
                    mapper = SourceFileLoader(
                        extension+"_mapper", script).load_module()
                    syntax = mapper.map_syntax if hasattr(
                        mapper, 'map_syntax') else py_syntax

                    return mapper.generate, syntax

                # if nothing helps, use the universal mapping
                return Mapper.universal_mapper.evaluate(
                                    file, extension, universal=True)

            except Exception as e:
                print(e)

            if file.lower().endswith('.py'):
                return Mapper.python_mapper.generate, py_syntax

    def can_map(file):
        if path.basename(file) == "Code - Map":
            return None
        return code_map_generator.get_mapper(file) is not None

    # -----------------

    def run(self, edit, **args):
        map_view = self.view

        map_view.set_read_only(False)

        # remember old position
        oldSource = code_map_generator.source
        if oldSource:
            selected_line = None
            viewport_position = map_view.text_to_layout(
                                    map_view.visible_region().a)[1]

            if len(map_view.sel()) > 0 and map_view.sel()[0]:
                selected_line = map_view.sel()[0]

            code_map_generator.positions[oldSource] = (
                viewport_position, selected_line)

        # generate new map
        source = args['source']
        map = ""
        map_syntax = py_syntax

        try:
            if using_universal_mapper:
                (map, syntax) = code_map_generator.get_mapper(source)
                map_syntax = syntax
            else:
                (generate, syntax) = code_map_generator.get_mapper(source)
                map = generate(source)
                map_syntax = syntax

        except Exception as err:
            print('code_map.generate:', err)

        all_text = sublime.Region(0, map_view.size())
        map_view.replace(edit, all_text, map)
        map_view.set_scratch(True)
        code_map_generator.source = source

        if code_map_generator.source in code_map_generator.positions.keys():
            (viewport_position, selection) = code_map_generator.positions[
                                                code_map_generator.source]

            if viewport_position:
                map_view.sel().clear()
                map_view.set_viewport_position((0, viewport_position), False)

                if selection:
                    map_view.sel().add(selection)
                else:
                    map_view.sel().add(Region(0, 0))

        map_view.assign_syntax(map_syntax)
        map_view.set_read_only(True)

# ===============================================================================


class code_map_increase_depth(sublime_plugin.TextCommand):

    def run(self, edit):

        file = self.view.file_name()
        d = settings().get('depth')
        fD = Mapper.DEPTH[1]

        if file in fD and fD[file] < 4:
            fD[file] += 1
        elif d < 4:
            fD[file] = d + 1

        refresh_map_for(self.view)
        synch_map(self.view)


class code_map_decrease_depth(sublime_plugin.TextCommand):

    def run(self, edit):

        file = self.view.file_name()
        d = settings().get('depth')
        fD = Mapper.DEPTH[1]

        if file in fD and fD[file] > 0:
            fD[file] -= 1
        elif d > 0:
            fD[file] = d - 1

        refresh_map_for(self.view)
        synch_map(self.view)


class navigate_code_map(sublime_plugin.TextCommand):

    def run(self, edit, direction=None, start=False, stop=False, fast=False):

        def scroll():
            v = CodeMapListener.nav_view
            line = v.line(v.sel()[0].a)
            v.show_at_center(line.a)

        v = self.view
        cm = get_code_map_view()
        CodeMapListener.skip = True

        if start:
            if not CodeMapListener.nav_view or not CodeMapListener.navigating:
                CodeMapListener.nav_view = v
                CodeMapListener.navigating = True
                synch_map(v, give_back_focus=False)
                sublime.set_timeout(
                    lambda: navigate_to_line(cm, give_back_focus=False), 10)
            else:
                return

        elif direction == "up":
            Nav.up(cm, fast)
            v.window().run_command('drag_select', {"by": "words"})
            sublime.set_timeout(scroll, 20)

        elif direction == "down":
            Nav.down(cm, fast)
            v.window().run_command('drag_select', {"by": "words"})
            sublime.set_timeout(scroll, 20)

        elif stop:
            win().focus_view(CodeMapListener.nav_view)
            CodeMapListener.nav_view = None
            CodeMapListener.navigating = False

# ===============================================================================


class synch_code_map(sublime_plugin.TextCommand):

    # -----------------

    def run(self, edit):

        if ACTIVE:
            refresh_map_for(self.view)
            synch_map(self.view)

# ===============================================================================


class show_code_map(sublime_plugin.TextCommand):

    # -----------------

    def run(self, edit):
        global ACTIVE

        # -----------------

        def create_codemap_group():
            '''Adds a column on the right, and scales down the layout'''
            layout = win().get_layout()
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
            groups = w.num_groups()
            w.run_command("set_layout", layout)
            sublime.set_timeout(lambda: Mapper.block_max_pane(False), 10)
            return (groups + 1)

        # -----------------

        def reset_layout(reduce):
            '''Removes the Code Map group, and scales up the layout'''
            layout = w.get_layout()
            cols = layout['cols']
            width = 1 - settings().get("codemap_width")

            w.set_view_index(get_code_map_view(), 0, 0)
            if reduce:
                for i, col in enumerate(cols):
                    if col > 0:
                        cols[i] = col/width

                cols[-2] = 1.0
                del cols[-1]
                del layout['cells'][-1]

            Mapper.block_max_pane(True)
            w.run_command("set_layout", layout)
            sublime.set_timeout(lambda: Mapper.block_max_pane(False), 10)

        # -----------------

        w = win()
        Mapper.block_max_pane(True)
        groups = w.num_groups()
        current_group = w.active_group()
        current_view = self.view
        map_view = get_code_map_view()

        if not map_view:            # opening Code Map

            ACTIVE = True

            show_in_new_group = settings().get("show_in_new_group", True)

            if not show_in_new_group:
                if groups == 1:
                    code_map_group = 1
                    Mapper.set_layout_columns(2)
                    groups = 2

            else:
                code_map_group = create_codemap_group()

            with open(code_map_file(), "w") as file:
                file.write('')

            map_view = w.open_file(code_map_file())
            map_view.settings().set("margin", 8)
            map_view.settings().set("word_wrap", False)
            map_view.settings().set("gutter", False)
            map_view.settings().set("draw_white_space", "none")
            w.set_view_index(map_view, code_map_group, 0)
            map_view.sel().clear()

            def focus_source_code():
                w.focus_group(current_group)
                w.focus_view(current_view)

            sublime.set_timeout_async(focus_source_code, 10)

        else:                       # closing Code Map
            ACTIVE = False

            CodeMapListener.active_view = current_view
            CodeMapListener.active_group = current_group
            w.focus_view(map_view)

            # close group only if codemap is the only file in it
            enabled = settings().get('close_empty_group_on_closing_map', False)
            if enabled:
                CodeMapListener.closing_code_map = True
                cm_group = w.get_view_index(get_code_map_view())[0]
                alone_in_group = len(w.views_in_group(cm_group)) == 1
                reset_layout(reduce=alone_in_group)

            w.run_command("close_file")


# =============================================================================

class code_map_select_line(sublime_plugin.TextCommand):

    def run(self, edit):

        point = self.view.sel()[0].a
        line_region = self.view.line(point)
        self.view.sel().clear()
        self.view.sel().add(line_region)
        sublime.set_timeout_async(
            lambda: self.view.sel().add(line_region), 100)

# =============================================================================


class CodeMapListener(sublime_plugin.EventListener):
    active_view, active_group = None, None
    closing_code_map, opening_code_map = False, False
    nav_view, navigating, skip = None, False, False

    # -----------------

    def on_deactivated(self, view):

        if CodeMapListener.navigating and not CodeMapListener.skip:
            CodeMapListener.nav_view = None
            CodeMapListener.navigating = False
            CodeMapListener.skip = True
        elif CodeMapListener.skip:
            CodeMapListener.skip = False

    # -----------------

    def on_load(self, view):

        if ACTIVE and view.file_name() != code_map_file():
            refresh_map_for(view)

    # -----------------

    def on_close(self, view):

        if not CodeMapListener.closing_code_map:
            return

        def focus_source_code():
            if CodeMapListener.active_view:
                w.focus_group(CodeMapListener.active_group)
                w.focus_view(CodeMapListener.active_view)

        w = win()
        sublime.set_timeout(focus_source_code, 10)
        CodeMapListener.closing_code_map = False
    # -----------------

    def on_post_save_async(self, view):

        if ACTIVE:
            refresh_map_for(view)
            synch_map(view)

    # -----------------

    def on_activated_async(self, view):

        if ACTIVE and view != get_code_map_view():

            if view != CodeMapListener.active_view:

                CodeMapListener.active_view = view
                refresh_map_for(view)

    # -----------------

    def on_text_command(self, view, command_name, args):
        '''Process double-click on code map view'''

        if ACTIVE:
            if view.file_name() == code_map_file():
                if command_name == 'drag_select' and 'by' in args.keys(
                                               ) and args['by'] == 'words':

                    f = False if CodeMapListener.navigating else True
                    navigate_to_line(view, give_back_focus=f)
                    return ("code_map_select_line", None)

    # -----------------

    def on_query_context(self, view, key, operator, operand, match_all):

        if CodeMapListener.navigating:
            if key == "code_map_nav":
                return True
            else:
                CodeMapListener.navigating = False
        return None
