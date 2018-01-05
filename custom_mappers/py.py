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