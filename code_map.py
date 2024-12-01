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

# version = 1.0.16

if sys.version_info < (3, 3):
    raise RuntimeError('CodeMap works with Sublime Text 3 only.')

# ============================================================

py_syntax = 'Packages/Python/Python.tmLanguage'
md_syntax = 'Packages/Markdown/Markdown.sublime-syntax'
cs_syntax = 'Packages/C#/C#.tmLanguage'
txt_syntax = 'Packages/Text/Plain text.tmLanguage'
CUSTOM_MAPPERS = None
ACTIVE = False
TEMP_VIDS = []
TEMP_VIEWS = {}
CURRENT_TEMP_ID = None
code_map_file = None

# -------------------------


def plugin_loaded():
    global ACTIVE, CUSTOM_MAPPERS, using_universal_mapper, code_map_file

    map_view = get_code_map_view()
    if map_view:
        ACTIVE = True
        CodeMapListener.map_group = win().get_view_index(map_view)[0]

    using_universal_mapper = True
    code_map_file = path.join(sublime.packages_path(), 'User', 'CodeMap', 'Code - Map')

    default_mappers = ['md', 'py', 'ts']
    custom_languages = ['md']
    Mapper.DEPTH = [settings().get('depth'), {}]

    user_folder = path.join(sublime.packages_path(), 'User')
    dst = path.join(user_folder, 'CodeMap')
    mpdir = path.join(dst, 'custom_mappers')
    lng_dir = path.join(dst, 'custom_languages')

    if not path.isdir(dst):
        os.mkdir(dst)
    if not path.isdir(mpdir):
        os.mkdir(mpdir)
    if not path.isdir(lng_dir):
        os.mkdir(lng_dir)

    # rename legacy mappers (if any)
    for syntax in default_mappers:
        mapper_script = mapper_path(syntax)
        mapper_script_legacy = mapper_path(syntax, 'code_map.')

        if path.isfile(mapper_script_legacy):
            try:
                os.rename(mapper_script_legacy, mapper_script)
            except:
                pass

    if is_compressed_package():
        ipath = sublime.installed_packages_path()
        # package was installed via Package Control
        pack = path.join(ipath, 'CodeMap.sublime-package')
        # package was installed via git repository
        if not path.isfile(pack):
            pack = path.join(ipath, 'sublime-codemap.sublime-package')

        zip = zipfile.ZipFile(pack)

        for syntax in default_mappers:
            if not path.isfile(mapper_path(syntax)):
                zip.extract('custom_mappers/'+syntax+'.py', dst)

        for syntax in custom_languages:
            if not path.isfile(syntax_path(syntax)):
                zip.extract('custom_languages/'+syntax+'.sublime-syntax', dst)

        # copy the context keymap file in the User subfolder
        if not path.isfile(dst + os.sep + 'Default.sublime-keymap'):
            zip.extract('Default.sublime-keymap', dst)

    else:
        # package was installed manually
        plugin_dir = path.dirname(__file__)

        for syntax in default_mappers:
            src_mapper = path.join(plugin_dir, 'custom_mappers', syntax+'.py')
            dst_mapper = mapper_path(syntax)
            if not path.isfile(dst_mapper):
                shutil.copyfile(src_mapper, dst_mapper)

        for syntax in custom_languages:
            src_syntax = path.join(plugin_dir, 'custom_languages', syntax+'.sublime-syntax')
            dst_syntax = syntax_path(syntax)
            if not path.isfile(syntax):
                shutil.copyfile(src_syntax, dst_syntax)

        # copy the context keymap file in the User subfolder
        if not path.isfile(dst + os.sep + 'Default.sublime-keymap'):
            src_keymap = path.join(plugin_dir, 'Default.sublime-keymap')
            dst_keymap = path.join(dst, 'Default.sublime-keymap')
            shutil.copyfile(src_keymap, dst_keymap)

    # make a list of the available mappers
    CUSTOM_MAPPERS = os.listdir(mpdir)

    # reactivate on start-up
    reactivate()

# -------------------------


def is_compressed_package():
    plugin_dir = path.dirname(__file__)
    return not plugin_dir.startswith(sublime.packages_path())


def mapper_path(syntax, prefix=None):
    prefix_str = ''
    if prefix:
        prefix_str = prefix
    return path.join(sublime.packages_path(), 'User', 'CodeMap', 'custom_mappers', prefix_str + syntax+'.py')


def syntax_path(syntax):
    return path.join(sublime.packages_path(), 'User', 'CodeMap', 'custom_languages', syntax+'.sublime-syntax')


def settings():
    return sublime.load_settings("code_map.sublime-settings")


def win():
    return sublime.active_window()


def get_group(view):
    return win().get_view_index(view)[0]

    # I wish C# style checking was possible with Python:
    # return view?.window()?.get_view_index(view)[0]


def reactivate():
    global ACTIVE

    map_view = get_code_map_view()
    if map_view:
        CodeMapListener.map_group = win().get_view_index(map_view)[0]
        map_view.show(0)    # scroll up the map
        ACTIVE = True

# -------------------------


def is_code_map(view):
    return view.file_name() == code_map_file

def is_code_map_visible():
    map = get_code_map_view()
    if map:
        return map == win().active_view_in_group(get_group(map))

def get_code_map_view():
    for v in win().views():
        if v.file_name() == code_map_file:
            return v

# -----------------


def reset_globals():
    global ACTIVE, CURRENT_TEMP_ID, TEMP_VIDS, TEMP_VIEWS

    TEMP_VIDS, TEMP_VIEWS, CURRENT_TEMP_ID = [], {}, None
    ACTIVE = False
    CodeMapListener.navigating = False
    CodeMapListener.skip = False

# -----------------


def create_codemap_group():
    """Adds a column on the right, and scales down the layout."""
    w = win()
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


def reset_layout():
    """Removes the Code Map group, and scales up the layout."""
    w = win()
    layout = w.get_layout()
    cols = layout['cols']
    width = 1 - settings().get("codemap_width")

    alone_in_group = len(win().views_in_group(CodeMapListener.map_group)) == 0

    if alone_in_group:
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


def refresh_map_for(view, from_view=False):
    global CURRENT_TEMP_ID

    # -----------------

    def clear_map_selection():
        # avoid certain error messages and clear abnormal selections
        try:
            if map_view.sel():
                lines = map_view.split_by_newlines(map_view.sel()[0])
            if len(lines) > 1:
                map_view.sel().clear()
        except:
            map_view.sel().clear()

    # -----------------

    def generate_from(file):
        global Generated_Map

        map = code_map_generator.get_mapper(file, view)
        if map:
            Generated_Map = map
            map_view.run_command('code_map_generator', {"source": file})
            clear_map_selection()

    # -----------------

    file = view.file_name()
    map_view = get_code_map_view()
    CURRENT_TEMP_ID = None

    w = sublime.active_window()
    widget = view.settings().get('is_widget')
    transient = view == w.transient_view_in_group(w.active_group())
    is_in_same_group = get_group(map_view) == get_group(view)

    # indentation type for current view
    Mapper.universal_mapper.Using_tabs = not view.settings().get('translate_tabs_to_spaces')

    if not map_view or widget or transient or is_in_same_group:
        return
    elif file and path.basename(file) == "Code - Map":
        return
    elif file and os.path.isfile(file):
        generate_from(file)

    # buffer is bound to a non-existent path, render from view
    # 'or file' here is not a mistake (it's used for files in zipped archives)
    elif view.id() in TEMP_VIDS or file or from_view:
        if view.id() not in TEMP_VIDS:
            TEMP_VIDS.append(view.id())
        CURRENT_TEMP_ID = view.id()
        map_view.run_command('code_map_generator', {"source": view.id()})
        clear_map_selection()
    scroll_left(map_view)

# -----------------


def synch_map(v, give_back_focus=True):

    def go():
        # no valid view, or view has changed since the function has been called
        if not v or v != win().active_view():
            return

        map_view = get_code_map_view()

        if map_view and map_view.size() > 0:
            code_view_line, _ = v.rowcol(v.sel()[0].a)
            prev_map_line = None

            lines = map_view.lines(Region(0, map_view.size()))

            entries = []
            index = 0
            for line in lines:
                link = map_view.substr(line).split(':')[-1]

                try:
                    entries.append((int(link), line))
                except:
                    continue

            entries.sort(key=lambda tup: tup[0])

            for member_line_num, line in entries:
                # added +1 so that it works for the first line of the function
                if member_line_num > code_view_line + 1:
                    break
                else:
                    prev_map_line = line

            map_view.sel().clear()
            if prev_map_line:
                map_view.sel().add(prev_map_line)
                map_view.show(prev_map_line.a)
                map_view.window().focus_view(map_view)

        if give_back_focus:
            win().focus_view(v)

    sublime.set_timeout(go, 10)

# -----------------


def focus_source_code():
    if CodeMapListener.active_view:
        w = win()
        w.focus_view(CodeMapListener.active_view)

# -----------------

def get_last_session_map_source():
    try:
        with open(code_map_file+'.source', "r") as file:
             return file.read()
    except:
        return None

def set_last_session_map_source(source):
    try:
        with open(code_map_file+'.source', "w") as file:
             file.write(source if source else "")
    except:
        pass

def scroll(v):
    line = v.line(v.sel()[0].a)
    v.show(line.a, True)

def scroll_left(v):
    viewport_position = v.text_to_layout(v.visible_region().a)[1]
    v.set_viewport_position((0, viewport_position), False)

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
        line_num = int(line_text.split(':')[-1].strip().split(' ')[-1])
    except:
        # navigate only if a valid map node is clicked or has caret
        return

    if CURRENT_TEMP_ID:
        source_code_view = TEMP_VIEWS[CURRENT_TEMP_ID]
    else:
        source_code_view = None

        if not code_map_generator.source:
            code_map_generator.source = get_last_session_map_source()

        if code_map_generator.source:
            source_code_view = win().find_open_file(code_map_generator.source)
            if not source_code_view:
                source_code_view = win().open_file(code_map_generator.source)


    if source_code_view:
        sublime.status_message('Navigating to selected item...')
        point = source_code_view.text_point(line_num-1, 0)
        new_selection = source_code_view.line(point)
        source_code_view.sel().clear()
        source_code_view.sel().add(new_selection)
        source_code_view.show_at_center(new_selection)

        sublime.set_timeout(lambda: scroll(source_code_view), 20)

        # again, no idea why the map loses its selection when selecting a
        # region that is before the first map node, but this fixes it
        try:
            point = map_view.sel()[0].a
        except:
            map_view.sel().add(Region(0, 0))
            Nav.highlight_line(map_view)

        if give_back_focus:
            win().focus_view(source_code_view)
    else:
        sublime.message_dialog('Initialize code map first. For example by saving the document.')

# =============================================================================

class code_map_marshaler(sublime_plugin.WindowCommand):
    """This command marshals the specified routine call by wrapping it into the WindowCommand. It
    allows the routine to be invoked either in the main ST3 thread or asynchronously from an
    alternate thread.

    Sample: code_map_marshaler.invoke(lambda: print('test'))
    """

    _actions = {}

    def _invoke(action, delay, async):
        import uuid
        action_id = str(uuid.uuid4())
        code_map_marshaler._actions[action_id] = (action, delay)
        win().run_command("code_map_marshaler", {"action_id": action_id, "async": async})

    def invoke(action, delay=10):
        code_map_marshaler._invoke(action, delay, False)

    def invoke_async(action, delay=10):
        code_map_marshaler._invoke(action, delay, True)

    def run(self, **args):
        async = args['async']
        action_id = args['action_id']
        action, delay = code_map_marshaler._actions.pop(action_id)
        if async:
            sublime.set_timeout_async(action, delay)
        else:
            sublime.set_timeout(action, delay)

# =============================================================================


class code_map_generator(sublime_plugin.TextCommand):

    # -----------------

    source = None
    positions = {}

    # -----------------

    def get_mapper(file, view=None):
        """"In addition to the file path, the current view syntax is passed to the function, to
        attempt detection from it rather than the file extension alone."""

        # Default map syntax is Python. It just looks better than others
        global using_universal_mapper

        if file:
            if file.lower().endswith('.cs'):
                syntaxer = sublime.load_settings("cs-script.sublime-settings").get('syntaxer_port')

                if syntaxer:
                    using_universal_mapper = False
                    return Mapper.csharp_mapper.generate, py_syntax

            try:
                using_universal_mapper = True
                pre, ext = path.splitext(file)
                extension = ext[1:].lower()

                # try with mappers defined in the settings first
                # pass also the current view syntax, so that it will be checked too
                mapper = Mapper.universal_mapper.evaluate(file, extension, view)
                if mapper:
                    return mapper

                # try with mappers defined in files next
                script = extension+'.py'

                # print('trying to get...', script)

                if script in CUSTOM_MAPPERS:

                    using_universal_mapper = False
                    script = mapper_path(extension)
                    mapper = SourceFileLoader(extension + "_mapper", script).load_module()
                    syntax = mapper.map_syntax if hasattr(mapper, 'map_syntax') else py_syntax

                    return mapper.generate, syntax

                # if nothing helps, try using the universal mapping
                return Mapper.universal_mapper.evaluate(file, extension, universal=True)

            except Exception as e:
                print(e)

    # -----------------

    def view_to_map(view):
        """Not a physical file, try to generate map directly from view content."""

        file_syntax = view.settings().get('syntax')
        supported = Mapper.settings().get('syntaxes')
        supported.remove(['universal', ""])     # restrict to custom defined syntaxes

        for i, syntax in enumerate(supported):
            if syntax[0].lower() in file_syntax.lower():
                Mapper.universal_mapper.mapping = supported[i][0]
                break
        else:
            return ("Could not decode view.", txt_syntax)

        content = view.substr(Region(0, view.size()))
        # skip Mapper.universal_mapper.evaluate, generate directly from view content
        mapper = Mapper.universal_mapper.generate(content)
        if mapper:
            TEMP_VIEWS[view.id()] = view
            return (mapper, file_syntax)
        else:
            return ("Could not decode view.", txt_syntax)

    # -----------------

    def run(self, edit, **args):
        global Generated_Map

        if self.view == None:
            return

        map_view = self.view
        map_view.set_read_only(False)

        # remember old position
        oldSource = code_map_generator.source
        if oldSource:
            selected_line = None
            viewport_position = map_view.text_to_layout(map_view.visible_region().a)[1]

            if len(map_view.sel()) > 0 and map_view.sel()[0]:
                selected_line = map_view.sel()[0]

            code_map_generator.positions[oldSource] = (viewport_position, selected_line)

        # generate new map
        source = args['source']
        map_syntax = py_syntax
        map = None
        
        try:
            # it's the id of the temporary view
            if type(source) != str:
                for v in sublime.active_window().views():
                    if v.id() == source:
                        (map, map_syntax) = code_map_generator.view_to_map(v)

            else:
                # use temp map that has been generated, then delete it
                map = Generated_Map
                Generated_Map = None
                if not map:
                    # probably not necessary but to be sure
                    map = code_map_generator.get_mapper(source)

                """using_universal_mapper variable is set in get_mapper, when
                it comes back here the script knows already where to go."""

                # refresh map -> get_mapper -> sets variable -> then here

                """This detour seems necessary to me because the variable
                can't be set here, it can only be set where the file type is
                being evaluated, but how the result must be processed is
                defined here."""

                if using_universal_mapper:
                    (map, map_syntax) = map
                else:
                    (generate, map_syntax) = map
                    try:
                        map = generate(source)
                    except Exception as e:
                        print('Custom mapper failure')
                        raise e

        except Exception as err:
            print('code_map.generate:', err)

        all_text = Region(0, map_view.size())

        if map_view == None:
            return

        if map == None:
            map = ''
        
        map = map.replace('<null>', "...")                

        map_view.replace(edit, all_text, map)
        map_view.set_scratch(True)
        code_map_generator.source = source

        set_last_session_map_source(source)

        if code_map_generator.source in code_map_generator.positions.keys():
            (viewport_position, selection) = code_map_generator.positions[code_map_generator.source]

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

        win().status_message('  Current CodeMap Depth: %d' % fD[file])
        refresh_map_for(self.view)
        synch_map(self.view)

# ===============================================================================


class code_map_decrease_depth(sublime_plugin.TextCommand):

    def run(self, edit):

        file = self.view.file_name()
        d = settings().get('depth')
        fD = Mapper.DEPTH[1]

        if file in fD and fD[file] > 0:
            fD[file] -= 1
        elif d > 0:
            fD[file] = d - 1

        win().status_message('  Current CodeMap Depth: %d' % fD[file])
        refresh_map_for(self.view)
        synch_map(self.view)

# ===============================================================================


class navigate_code_map(sublime_plugin.TextCommand):

    def run(self, edit, direction=None, start=False, stop=False, fast=False):

        if not ACTIVE:
            map_view = get_code_map_view()
            if map_view:
                win().status_message('  CodeMap: Synch the map first.')
            else:
                win().status_message('  CodeMap is currently closed.')
            return

        v = self.view
        cm = get_code_map_view()
        CodeMapListener.skip = True

        if start:
            if not CodeMapListener.nav_view or not CodeMapListener.navigating:
                CodeMapListener.nav_view = v
                CodeMapListener.navigating = True
                synch_map(v, give_back_focus=False)
                sublime.set_timeout(lambda: navigate_to_line(cm, give_back_focus=False), 10)
            else:
                return

        elif direction == "up":
            Nav.up(cm, fast)
            v.window().run_command('drag_select', {"by": "words"})

        elif direction == "down":
            Nav.down(cm, fast)
            v.window().run_command('drag_select', {"by": "words"})

        elif stop:
            win().focus_view(CodeMapListener.nav_view)
            CodeMapListener.nav_view = None
            CodeMapListener.navigating = False

# ===============================================================================


class synch_code_map(sublime_plugin.TextCommand):
    """This command also activates the CodeMap if the view is present, but CodeMap is inactive
    because ST has just been restarted, or the project has been switched."""
    # -----------------

    def run(self, edit, from_view=False):
        global ACTIVE

        if not ACTIVE and get_code_map_view():
            ACTIVE = True

        if ACTIVE:

            if self.view != get_code_map_view():
                # ignore view in the map_view group as in this case
                # the source and map cannot be visible at the same time
                if get_group(self.view) == CodeMapListener.map_group:
                    # only prepare the views(make visible) for the future synch
                    win().focus_view(get_code_map_view())
                    win().focus_view(CodeMapListener.active_view)

                else:
                    # sync doc -> map
                    refresh_map_for(self.view, from_view)
                    synch_map(self.view)

            else:
                # (an alternative approach when the sych is always ->)
                # sync doc <- map
                self.view.run_command("code_map_select_line")
                f = not CodeMapListener.navigating
                navigate_to_line(self.view, give_back_focus=f)

# ===============================================================================


class show_code_map(sublime_plugin.TextCommand):

    # -----------------

    def run(self, edit):
        global ACTIVE, CURRENT_TEMP_ID, TEMP_VIDS, TEMP_VIEWS, CUSTOM_MAPPERS

        w = win()
        Mapper.block_max_pane(True)
        groups = w.num_groups()
        current_view = self.view
        map_view = get_code_map_view()

        if not map_view:            # opening Code Map

            ACTIVE = True
            CUSTOM_MAPPERS = os.listdir(path.join(sublime.packages_path(), 'User', 'CodeMap', 'custom_mappers'))

            CodeMapListener.active_view = current_view

            code_map_group = -1
            last_group = w.num_groups()-1
            # look for Favorites in last group
            for view in w.views_in_group(last_group):
                file = view.file_name()
                if file and os.path.basename(file) == 'Favorites':
                    code_map_group = last_group

            # Favorites not found
            if code_map_group == -1:
                show_in_new_group = settings().get("show_in_new_group", True)

                if not show_in_new_group:
                    if groups == 1:
                        code_map_group = 1
                        CodeMapListener.map_group = 1
                        Mapper.set_layout_columns(2)
                        groups = 2

                    else:
                        # the most right group
                        code_map_group = groups - 1

                else:
                    code_map_group = create_codemap_group()
                    CodeMapListener.map_group = code_map_group

            with open(code_map_file, "w") as file:
                file.write('')

            try:
                map_view = w.open_file(code_map_file, transient)
            except Exception as e:
                try:
                    map_view = w.open_file(code_map_file)
                except Exception as e1:
                    pass
                pass
            


            # default margin: 8
            map_view.settings().set("margin", settings().get('codemap_margin', 8))

            # allow custom font face/size, it's optional and it doesn't need to be in settings
            if settings().has('codemap_font_size'):
                map_view.settings().set("font_size", settings().get('codemap_font_size'))
            if settings().has('codemap_font_face'):
                map_view.settings().set("font_face", settings().get('codemap_font_face'))

            map_view.settings().set("word_wrap", False)
            map_view.settings().set("gutter", False)
            map_view.settings().set("draw_white_space", "none")
            w.set_view_index(map_view, code_map_group, 0)
            map_view.sel().clear()

            w.run_command("synch_code_map")
            focus_source_code()

        elif ACTIVE:                       # closing Code Map

            CodeMapListener.active_view = current_view
            g, i = w.get_view_index(map_view)
            w.run_command("close_by_index", {"group": g, "index": i})
            focus_source_code()

# =============================================================================


class code_map_select_line(sublime_plugin.TextCommand):

    def run(self, edit):
        if self.view:
            point = self.view.sel()[0].a
            line_region = self.view.line(point)
            self.view.sel().clear()
            self.view.sel().add(line_region)
            sublime.set_timeout_async(lambda: self.view.sel().add(line_region), 10)

# =============================================================================


class CodeMapListener(sublime_plugin.EventListener):
    active_view, map_view, map_group = None, None, None
    closing_code_map, opening_code_map = False, False
    nav_view, navigating, skip = None, False, False

    # -----------------

    def on_deactivated(self, view):

        if ACTIVE:
            if CodeMapListener.navigating and not CodeMapListener.skip:
                CodeMapListener.nav_view = None
                CodeMapListener.navigating = False
                CodeMapListener.skip = True
            elif CodeMapListener.skip:
                CodeMapListener.skip = False

    # -----------------

    def on_load(self, view):
        global ACTIVE

        if ACTIVE and view.file_name() != code_map_file:
            refresh_map_for(view)

        # CodeMap file has been loaded but it's currently inactive
        elif get_code_map_view():
            reactivate()

    # -----------------

    def on_close(self, view):

        if ACTIVE and view.file_name() == code_map_file:

            # Issue #35: Issue + Possible Solution:
            #            Toggling Code Map with show_code_map cmd causes active view / file to close
            #            ( whether using the keybind or calling directly )
            view.set_scratch(False)

            reset_globals()
            if settings().get('close_empty_group_on_closing_map', False):
                reset_layout()
            sublime.set_timeout_async(focus_source_code)

            # try to reactivate, in case another window with Codemap is open,
            # or a new workspace has been loaded
            sublime.set_timeout_async(lambda: reactivate())

    # -----------------

    def on_post_save_async(self, view):

        if ACTIVE:  # map view is opened
            refresh_map_for(view)

            # synch_map brings map_view into focus so call it only
            # if it is not hidden behind other views
            if is_code_map_visible():
                synch_map(view)

        # CodeMap file has been loaded but it's currently inactive
        elif get_code_map_view():
            reactivate()

    # -----------------

    def on_activated_async(self, view):

        if ACTIVE:

            if view == get_code_map_view():
                CodeMapListener.map_group = win().get_view_index(view)[0]
                return

            # ignore view in the map_view group as in this case
            # the source and map cannot be visible at the same time
            view_group = win().get_view_index(view)[0]

            if view_group == CodeMapListener.map_group:
                pass

            elif view != CodeMapListener.active_view:

                CodeMapListener.active_view = view
                refresh_map_for(view)

    # -----------------

    def on_text_command(self, view, command_name, args):
        """Process double-click on code map view."""

        if ACTIVE:

            double_click = command_name == 'drag_select' and 'by' in args and args['by'] == 'words'

            if double_click and view.file_name() == code_map_file:
                code_map_marshaler.invoke(lambda:
                    navigate_to_line(view, give_back_focus = not CodeMapListener.navigating))
                return ("code_map_select_line", None)

    # -----------------

    def on_window_command(self, window, command_name, args):
        """
        Prone to crash when switching projects.
        Resetting variables and stopping until CodeMap file is found again.
        """

        reset = [
            "prompt_open_project_or_workspace",
            "prompt_select_workspace",
            "open_recent_project_or_workspace",
            "close_workspace",
            "project_manager"
        ]

        if ACTIVE and command_name in reset:
            reset_globals()

    # -----------------

    def on_query_context(self, view, key, operator, operand, match_all):

        if ACTIVE and CodeMapListener.navigating:
            if key == "code_map_nav":
                return True
            else:
                CodeMapListener.navigating = False
        return None
