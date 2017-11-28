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
if 'TypeScript' in installed:
    map_syntax = 'Packages/TypeScript/TypeScript.tmLanguage'
else:
    # fallback as TypeScript is not installed
    map_syntax = 'Packages/Python/Python.tmLanguage'

def generate(file):
    return ts_mapper.generate(file)

class ts_mapper():
    # -----------------
    def generate(file):

        def str_of(count, char):
            text = ''
            for i in range(count):
                text = text + char
            return text

        # Pasrse
        item_max_length = 0
        members = []

        try:

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

                def parse_as_class(keyword, line):
                    if code_line.startswith(keyword+' ') or code_line.startswith('export '+keyword+' ') :
                        last_type = keyword
                        last_indent = indent_level
                        if code_line.startswith('export '+keyword+' '):
                            line = line.replace('export '+keyword+' ', keyword+' ')

                        display_line = line.rpartition('implements')[0]
                        if not display_line:
                            display_line = line.rpartition('{')[0]
                        if not display_line:
                            display_line = line.rstrip()

                        # class CSScriptHoverProvider implements HoverProvider {
                        info = (line_num,
                                keyword,
                                display_line.split('(')[0].split(':')[0].rstrip()+' {}', # suffix brackets make it valid TS syntax
                                indent_level)
                        return info

                # miss C# here :)
                # info = parse_as_class('class', line) ??
                #        parse_as_class('interface', line) ??
                #        parse_as_class('whatever', line)

                info = parse_as_class('class', line)

                if not info:
                    info = parse_as_class('interface', line)

                if info:
                    pass

                elif code_line.startswith('function ') or code_line.startswith('export function ') :
                    if last_type == 'function' and indent_level > last_indent:
                        continue # private class functions
                    last_type = 'function'
                    last_indent = indent_level
                    info = (line_num,
                            'function',
                            line.split('(')[0].rstrip()+'()',
                            indent_level)

                elif code_line.startswith('public '):
                    last_type = 'public '
                    last_indent = indent_level
                    info = (line_num,
                            'public ',
                            line.replace('public ', '').split('(')[0].rstrip()+'()',
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
        for line, content_type, content, indent in members:
            extra_line = ''
            if indent == last_indent:
                if content_type != last_type:
                    extra_line = '\n'
            elif content_type == 'class' or content_type == 'interface':
                extra_line = '\n'

            preffix = str_of(indent, ' ')
            lean_content = content[indent:]
            suffix = str_of(item_max_length-len(content), ' ')
            map = map + extra_line + preffix + lean_content + suffix +' :'+str(line) +'\n'
            last_indent = indent
            last_type = content_type

        # print(map)
        return map