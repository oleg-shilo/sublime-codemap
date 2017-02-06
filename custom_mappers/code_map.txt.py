# Custom mapper sample for CodeMap plugin
# This script defines a mandatory 'def generate(file)' routine that analyses the file
# content and produces the 'code map' representing the content structure. In this case it builds
# the list of paragraphs (new lines) in the text file
#
# The map format: <item title>:<item position in source code>
#
# In order to activate the mapper its script meeds to be mapped to the supported file type (extension) in the 
# .sublime-settings file:
# "codemap_<extension>_mapper": "<path to the script implementing the mapper>"
#   Example: "codemap_txt_mapper": "c:/st3/plugins/codemap/custom_mappers/code_map.txt.py",

import codecs

def generate(file):
    return txt_mapper.generate(file) 

class txt_mapper():

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

                line = line[0:10]+'...'
                for i in range(0, 13 - len(line)):    
                    line = line + ' ' 

                map = map + line + '    :' + str(line_num)+'\n'

        except Exception as err:
            print (err)

        return map



        