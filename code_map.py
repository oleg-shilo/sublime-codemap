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


def is_compressed_package():
    plugin_dir = path.dirname(__file__)
    return not plugin_dir.startswith(packages_dir)


def mapper_path(syntax):
    return path.join(packages_dir, 'User', 'CodeMap', 'custom_mappers',
                                   'code_map.'+syntax+'.py')


def syntax_path(syntax):
    return path.join(packages_dir, 'User', 'CodeMap', 'custom_languages',
                                   syntax+'.sublime-syntax')


def settings():
    return sublime.load_settings("code_map.sublime-settings")


def win():
    return sublime.active_window()

# -------------------------


def plugin_loaded():

    global MAPPERS, packages_dir

    default_mappers = ['md', 'py']
    custom_languages = ['md']
    ipath = sublime.installed_packages_path()
    packages_dir = sublime.packages_path()
    Mapper.EXTENSION, Mapper.DEPTH = "", [settings().get('depth'), {}]

    dst = path.join(packages_dir, 'User', 'CodeMap')
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


def code_map_file():

    dst = path.join(packages_dir, 'User', 'CodeMap')
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
        code_map_view = get_code_map_view()
        if code_map_view:
            code_map_view.run_command('code_map_generator', {"source": file})

            # avoid certain error messages
            try:
                if code_map_view.sel():
                    lines = code_map_view.split_by_newlines(
                        code_map_view.sel()[0])
                if len(lines) > 1:
                    code_map_view.sel().clear()
            except:
                code_map_view.sel().clear()

# -----------------


def synch_map(v, focus=True):

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
    if focus:
        sublime.set_timeout(lambda: win().focus_view(v), 10)


def navigate_to_line(view, focus=False):
    try:
        point = view.sel()[0].a
    except:
        # no idea why this happens, it's a workaround
        point = 0
        CodeMapListener.skip = True
        win().focus_view(view)

    line_region = view.line(point)
    line_text = view.substr(line_region)

    view.sel().clear()
    view.sel().add(line_region)

    line_num = 1
    try:
        line_num = int(line_text.split(':')[-1].strip(
            ).split(' ')[-1])
    except:
        pass

    just_loaded = False
    source_code_view = None

    if code_map_generator.source:
        source_code_view = win().find_open_file(
            code_map_generator.source)
        if not source_code_view:
            source_code_view = win().open_file(
                code_map_generator.source)
            just_loaded = True

    if source_code_view:
        sublime.status_message('Navigating to clicked item...')
        point = source_code_view.text_point(line_num-1, 0)
        new_selection = source_code_view.line(point)

        source_code_view.sel().clear()
        source_code_view.sel().add(new_selection)
        source_code_view.show_at_center(new_selection)

        if not focus:
            return

        if just_loaded:
            def move_to_first_group():
                group, index = win(
                    ).get_view_index(source_code_view)
                if group == 1:
                    win().set_view_index(source_code_view, 0, 0)
                win().focus_view(source_code_view)

            sublime.set_timeout_async(move_to_first_group, 30)
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
        code_map_view = self.view

        code_map_view.set_read_only(False)

        # remember old position
        oldSource = code_map_generator.source
        if oldSource:
            center_line = Mapper.centre_line_of(
                code_map_view, code_map_view.visible_region())
            selected_line = None

            if len(code_map_view.sel()) > 0 and code_map_view.sel()[0]:
                selected_line = code_map_view.sel()[0]

            code_map_generator.positions[oldSource] = (
                center_line, selected_line)

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
            print ('code_map.generate:', err)

        all_text = sublime.Region(0, code_map_view.size())
        code_map_view.replace(edit, all_text, map)
        code_map_view.set_scratch(True)
        code_map_generator.source = source

        if code_map_generator.source in code_map_generator.positions.keys():
            (center_line, selection) = code_map_generator.positions[
                                                code_map_generator.source]

            if center_line:
                point = code_map_view.text_point(center_line, 0)
                code_map_view.sel().clear()
                code_map_view.show_at_center(point)

                if selection:
                    code_map_view.sel().add(selection)

                else:
                    code_map_view.sel().add(Region(0, 0))

        code_map_view.assign_syntax(map_syntax)
        code_map_view.set_read_only(True)

# ===============================================================================


class code_map_scroll_to_left(sublime_plugin.TextCommand):

    # -----------------

    def code_map_view(next_focus_view=None):

        def do():
            get_code_map_view().run_command('code_map_scroll_to_left')

        sublime.set_timeout(do, 10)

    # -----------------

    def run(self, edit):
        region = self.view.visible_region()
        y = self.view.text_to_layout(region.a)[1]
        self.view.set_viewport_position((0, y), False)


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
            y = v.text_to_layout(line.a)[1]
            v.set_viewport_position((0, y-200), False)

        v = self.view
        cm = get_code_map_view()
        CodeMapListener.skip = True

        if start:
            if not CodeMapListener.nav_view:
                CodeMapListener.nav_view = v
                CodeMapListener.navigating = True
                synch_map(v, focus=False)
                sublime.set_timeout(
                    lambda: navigate_to_line(cm, focus=False), 10)
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

            synch_map(self.view)

# ===============================================================================


class show_code_map(sublime_plugin.TextCommand):

    # -----------------

    def run(self, edit):

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

        def reset_layout(reduce):
            '''Removes the Code Map group, and scales up the layout'''
            layout = w.get_layout()
            cols = layout['cols']
            width = 1 - settings().get("codemap_width")

            for i, col in enumerate(cols):
                if col > 0:
                    cols[i] = col/width

            w.set_view_index(get_code_map_view(), 0, 0)
            if reduce:
                cols[-2] = 1.0
                del cols[-1]
                del layout['cells'][-1]
            else:
                cols[-1] = 1.0

            Mapper.block_max_pane(True)
            w.run_command("set_layout", layout)
            sublime.set_timeout(lambda: Mapper.block_max_pane(False), 10)

        Mapper.block_max_pane(True)
        w = win()
        groups = w.num_groups()
        current_group = w.active_group()
        current_view = self.view

        code_map_view = get_code_map_view()

        if not code_map_view:

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

            code_map_view = w.open_file(code_map_file())
            code_map_view.settings().set("word_wrap", False)
            code_map_view.settings().set("gutter", False)
            code_map_view.settings().set("draw_white_space", "none")
            w.set_view_index(code_map_view, code_map_group, 0)
            code_map_view.sel().clear()

            def focus_source_code():
                w.focus_group(current_group)
                w.focus_view(current_view)

            sublime.set_timeout_async(focus_source_code, 10)

        else:
            CodeMapListener.active_view = current_view
            CodeMapListener.active_group = current_group
            w.focus_view(code_map_view)

            # close group only if codemap is the only file in it
            enabled = settings().get('close_empty_group_on_closing_map', False)
            if enabled:
                CodeMapListener.closing_code_map = True
                group = w.get_view_index(code_map_view)[0]
                alone_in_group = len(w.views_in_group(group)) == 1
                reset_layout(reduce=alone_in_group)

            w.run_command("close_file")


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

        if view.file_name() != code_map_file():
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
        refresh_map_for(view)
        synch_map(view)

    # -----------------

    def on_activated_async(self, view):

        if view != get_code_map_view() and view != CodeMapListener.active_view:
            CodeMapListener.active_view = view
            refresh_map_for(view)

    # -----------------

    def on_post_text_command(self, view, command_name, args):
        # process double-click on code map view
        if view.file_name() == code_map_file():
            if command_name == 'drag_select' and 'by' in args.keys(
                                           ) and args['by'] == 'words':

                f = False if CodeMapListener.navigating else True
                navigate_to_line(view, focus=f)

    # -----------------

    def on_query_context(self, view, key, operator, operand, match_all):

        if CodeMapListener.navigating:
            if key == "code_map_nav":
                return True
            else:
                CodeMapListener.navigating = False
        return None
