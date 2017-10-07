# Sublime CodeMap

A plugin for displaying the code map (code structure tree) in the [Sublime Text 3](http://sublimetext.com "Sublime Text") editor.

This plugin is a port of [PyMap](https://marketplace.visualstudio.com/items?itemName=OlegShilo.PyMap) Visual Studio extension. 

Plugin currently supports building the code tree for Python. Support for C# is in the pipeline. The design of plugin allows integration of the user defined _tree building_ algorithm for other languages. The _custom syntax_ integration infrastructure and and samples will  be available in the next release. 

## Installation

Note the plugin was developed and tested against ST3 but not ST2.

*__Package Control__*

You can install the pluging [Package Control](https://packagecontrol.io/packages/CodeMap).

*__Manual__*

* Remove the package, if installed, using Package Control.
* Add a repository: `https://github.com/oleg-shilo/sublime-codemap.git`
* Install `sublime-codemap` with Package Control. 
* Restart Sublime editor if required

You can also install the plugin by cloning `sublime-codemap` repository into your Packages folder or manually placing the download package there.

## Usage
The plugin uses a dedicated view group __Code - Map__ (on right side) to mimic a "side bar" with the content (code tree) that represents code structure of the active view content in the primary view group. 

The code tree automatically refreshes on saving the active document or switching the tabs. The usage is quite simple. You can double-click a node in the code tree and this will trigger navigation to the corresponding area in the code (in active document). Alternatively you can synchronize code tree node selection with the current caret position in the document by triggering `sync_code_map` command either from _Command Palette_ or by the configured shortcut.

To start working with CodeMap just make the map view visible (e.g. [alt+m, alt+m]) and set the focus to the code view.

![](images/image1.gif)

## Command Palette

Press `cmd+shift+p`. Type `codemap` to see the available commands:

* *Toggle Visibility* - Show/Hide CodeMap view. 
The CodeMap view is always placed in the most right column (group) of the active window. If the layout has only a single column then the plugin automatically switches in the "2-columns" layout. You can also configure plugin (via setting 'close_empty_group_on_closing_map') to hide the group on closing the CodeMap view when it is the only view in the group.

* *Reveal in CodeMap* - Select code tree node that corresponds the caret position in the code (active view)

## Custom mapping

You can extend the built-in functionality with custom mappers. Custom mapper is a Python script, which defines a mandatory `def generate(file)` routine that analyses a given file content and produces a 'code map' representing the content structure. 

You can find the [code_map.md.py](custom_mappers/code_map.md.py) sample in the source code. This mapper builds the list of markdown sections in the given text file.
In order to activate the mapper its script needs to be mapped to the supported file type (extension) in the _code_\__map.sublime-settings_ file:
`"codemap_<extension>_mapper": "<path to the script implementing the mapper>"`

  Example: `"codemap_md_mapper": "c:/st3/plugins/codemap/custom_mappers/code_map.md.py"`
   
### Universal Mapper

The _universal mapper_ is a generic Regex based mapper that can be used as an alternative for dedicated custom mappers. The mapping algorithm(s) of the _universal mapper_ is defined in the plugin settings file instead of the _python_ file as for dedicated mappers. 

The availability of _universal mapper_ can be controlled via corresponding setting value:

```json
"using_universal_mapper": true
``` 

If it is enabled the plugin will try to use _universal mapper_ mapping algorithm first and only if it's not available the plugin will try to locate a dedicated custom mapper based on the active document file extension.

Below is a simple example of adding _universal mapper_ support for TypeScript:

Add file extension and name of the algorithm section to the `syntaxes` section:
```json
"syntaxes":     [
                        ["universal",   ""],
                        ["text",        "txt"],
                        ["typescript",  "ts"],
                        ["python",      "py"]
                ],
```

Create a new `typescript` section an fill it with the the following content:  
```json
"typescript": {
                "regex":
                [
                    [
                        "^(class |function |export class |interface ).*$",
                        "[(:{].*$",
                        "",
                        false
                    ]
                ],
                "indent": 4,
                "obligatory indent": false,
                "empty line in map before": "class",
                "line numbers before": false,
                "prefix": "",
                "suffix": "()",
                "syntax": "Packages/TypeScript/TypeScript.tmLanguage"
             },
```  

## Settings

You can also configure plugin to:
1. Hide the group on closing the CodeMap view when it is the only view in the group.
2. Always place CodeMap view in the individual most-right column. Only up to 4 columns layout is supported.

_code_\__map.sublime-settings_

```js
{
    "close_empty_group_on_closing_map": true, 
    "show_in_new_group": true
}
```
