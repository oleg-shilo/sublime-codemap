# Custom mapper sample for CodeMap plugin
#
# This script defines a mandatory `def generate(file)` and global variable map_syntax:
# - `def generate(file)`
#    The routine analyses the file content and produces the 'code map' representing the content structure.
#    In this case it builds the list of sections (lines that start with `#` character) in the md file.
#
# - `map_syntax`
#    Optional attribute that defines syntax highlight to be used for the code map text
#
# The map format: <item title>:<item position in source code>
#
# You may need to restart Sublime Text to reload the mapper

import codecs

# you can create custom syntaxes for codemap visuals, this is an example
map_syntax = 'Packages/User/CodeMap/custom_languages/md.sublime-syntax'

def generate(file):
    return md_mapper.generate(file)

class md_mapper():

    def generate(file):
        map = ''

        try:

            with codecs.open(file, "r") as f:
                lines = f.read().split('\n')

            line_num = 0

            for line in lines:
                line_num = line_num + 1
                line = line.lstrip()

                if len(line) == 0:
                    continue

                if line.startswith("#"):
                    max = 20
                    line = line[0:max]+'...'
                    for i in range(0, (max+3) - len(line)):
                        line = line + ' '

                    map = map + line + '    :' + str(line_num)+'\n'

        except Exception as err:
            print (err)

        return map



