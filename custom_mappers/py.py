# Custom mapper sample for CodeMap plugin
# This script defines a mandatory `def generate(file)` and module attribute map_syntax:
# - `def generate(file)`
#    The routine analyses the file content and produces the 'code map' representing the content structure.
#    In this case it builds the list of sections (lines that start with `#` character) in the py file.
#
# - `map_syntax`
#    Optional attribute that defines syntax highlight to be used for the code map text
#
# The map format: <item title>:<item position in source code>
#
# You may need to restart Sublime Text to reload the mapper

import codecs
import sublime

# ================================
# This is a default custom mapper that is included as part of the plugin distro. 
# Set is_default_mapper to False if you are want to maintain this mapper by yourself 
# (e.g. the mapper's updates will not be processed delivered automatically).
is_default_mapper = True 
mapper_version = "1.0"
# ================================

try:
    installed = sublime.load_settings('Package Control.sublime-settings').get('installed_packages')
except:
    installed = []

# `map_syntax` is a syntax highlighting that will be applied to CodeMap at runtime
# you can set it to the custom or built-in language definitions
if 'MagicPython' in installed:
    map_syntax = 'Packages/MagicPython/grammars/MagicPython.tmLanguage'
else:
    # fallback as MagicPython is not installed
    map_syntax = 'Packages/Python/Python.tmLanguage'

def generate(file):
    return python_mapper.generate(file)

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

                # skip empty lines
                if not code_line:
                    continue

                # check for multiline string start/end
                if not is_comment:
                    if code_line.startswith('"""') or code_line.startswith("'''"):
                        is_multiline_string = not is_multiline_string
                    if is_multiline_string:
                        continue
                if code_line.startswith('#'):
                    is_comment = True
                else:
                    is_comment = False

                if is_comment or is_multiline_string:
                    continue

                info = None
                indent_level = len(line) - len(code_line);

                if code_line.startswith('class '):
                    last_type = 'class'
                    last_indent = indent_level
                    info = (line_num,
                            'class',
                            line.split('(')[0].split(':')[0].rstrip(),
                            indent_level)

                elif code_line.startswith('def ') or code_line.startswith('async def '):

                    if last_type == 'def' and indent_level > last_indent:
                        continue #local def
                    last_type = 'def'
                    last_indent = indent_level

                    display_text = line.split('(')[0].rstrip()+'()'
                    display_text = display_text.replace('async def ', 'def ')

                    info = (line_num,
                            'def',
                            display_text,
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