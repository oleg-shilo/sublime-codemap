## Debugging (Sublime Text + VS Code)

Step-through debugging runs `debugpy` inside Sublime's plugin host, with VS Code attaching as the client. Tested on Windows with Sublime Text build 4213+ (Python 3.14 plugin host).

### Setup

1. **Install debugpy** into the host's library folder. Find it by running this in the Sublime console (`` Ctrl+` ``):

```python
   import sys; print([p for p in sys.path if "Lib" in p])
```

   Then install into the `Lib\python314` entry from PowerShell:

```powershell
   pip install debugpy --target "$env:APPDATA\Sublime Text\Lib\python314"
```

   Verify in the console: `import debugpy; print(debugpy.__version__)`

2. **Add a debug server command** at `Packages\User\debug_server.py`:

```python
   import sublime_plugin

   PYTHON_EXE = r"C:\Path\To\Python\python.exe"  # a real interpreter, not plugin_host
   PORT = 5678


   class StartDebugServerCommand(sublime_plugin.ApplicationCommand):
       def run(self):
           import debugpy
           try:
               debugpy.configure(python=PYTHON_EXE)
               debugpy.listen(("127.0.0.1", PORT))
           except RuntimeError as e:
               print("debugpy:", e)  # listen() works once per host session
               return
           print("debugpy listening on port", PORT)
```

3. **Add `.vscode/launch.json`** in the plugin folder opened in VS Code:

```jsonc
   {
     "version": "0.2.0",
     "configurations": [
       {
         "name": "Attach to Sublime Text",
         "type": "debugpy",
         "request": "attach",
         "connect": { "host": "127.0.0.1", "port": 5678 },
         "justMyCode": false
       }
     ]
   }
```

   `justMyCode` must be `false`. With `true`, breakpoints in plugin files stay grey because debugpy misclassifies code under Sublime's data folder as library code.

### Usage

1. In the Sublime console, run `sublime.run_command("start_debug_server")` and wait for `debugpy listening on port 5678`.
2. In VS Code, select **Attach to Sublime Text** and press **F5**.
3. Set a breakpoint in your plugin and trigger the command.

Sublime's UI freezes while paused in a synchronous command; it resumes when you continue.

### Notes

- `listen()` works once per host session. After restarting Sublime or the plugin host, run `start_debug_server` and re-attach.
- Saving plugin files reloads them without ending the debug session.
- Make sure the file open in VS Code is the same path Sublime loads (check `__file__`). Use `pathMappings` in `launch.json` if you work from a symlink or separate repo.
- The "frozen modules" warning at startup is harmless for debugging your own code.