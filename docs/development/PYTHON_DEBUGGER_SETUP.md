# 🎯 Python Debugger & Streamlit Setup - Complete Guide

## ✅ What Was Done

Your VS Code Python debugger has been fully configured to:

1. ✅ **Automatically activate your virtual environment** (`.venv/bin/activate`)
2. ✅ **Properly set PYTHONPATH** to include `src/` directory  
3. ✅ **Launch Streamlit app directly from VS Code** with F5
4. ✅ **Support full debugging** with breakpoints, stepping, and variable inspection
5. ✅ **Configure additional helper tasks** for common operations

## 📁 Files Created

### Core Configuration Files (in `.vscode/`)

- **`launch.json`** - Debug launch configurations using `debugpy`
- **`settings.json`** - Python interpreter and environment setup
- **`tasks.json`** - Predefined tasks for running/testing
- **`extensions.json`** - Recommended VS Code extensions
- **`README.md`** - Comprehensive documentation
- **`QUICK_START.md`** - Quick reference guide

### Helper Files (in repo root)

- **`docs/development/VSCODE_DEBUG_SETUP.md`** - This complete setup guide
- **`verify_debug_setup.py`** - Script to verify everything works
- **`scripts/vscode-debug.sh`** - Helper script for common commands

## 🚀 How to Use - Quick Start

### Option 1: Using VS Code Debug UI (Recommended)

1. **Set a breakpoint** by clicking the left gutter (red dot appears)
2. **Press F5** (or Cmd+Shift+D → select config → play button)
3. **Select "Python: Run Streamlit App"** from dropdown
4. **App launches** at `http://localhost:8501`

### Option 2: Using Command Palette

1. **Cmd+Shift+P** → "Debug: Start Debugging"
2. **Select "Python: Run Streamlit App"**
3. **App launches**

### Option 3: Using Terminal Commands

```bash
# Start the app
./scripts/vscode-debug.sh run

# Start with debug logging
./scripts/vscode-debug.sh debug

# Run tests
./scripts/vscode-debug.sh test

# Verify setup
./scripts/vscode-debug.sh verify
```

## 🔧 Available Configurations

### Launch Configurations (F5)

| Name | Purpose | Logging |
|------|---------|---------|
| Python: Run Streamlit App | Normal execution | Standard |
| Python: Debug Streamlit App | Development debugging | Debug level |
| Python: Debug Current File | Debug any Python file | Standard |
| Python: Debug Workflow | Debug workflow module | Standard |

### Available Tasks (Cmd+Shift+P → Tasks: Run Task)

| Task | Command | Purpose |
|------|---------|---------|
| Streamlit: Run App | `streamlit run app.py` | Start app |
| Python: Run Tests | `pytest tests/ -v` | Run test suite |
| Python: Run Database Setup | `python scripts/init_default_jobs.py` | Initialize DB |
| Python: Lint with Pylint | `pylint src/ --exit-zero` | Code quality |
| Python: Format with Black | `black src/ --line-length 100` | Format code |

## 🎮 Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| **F5** | Start/Resume debugging |
| **Shift+F5** | Stop debugging |
| **F10** | Step over (execute current line) |
| **F11** | Step into (enter function) |
| **Shift+F11** | Step out (exit function) |
| **Cmd+K Cmd+I** | Show hover info |
| **Cmd+Shift+D** | Open Run and Debug panel |
| **Cmd+Shift+P** | Open Command Palette |
| **Cmd+Shift+`** | Open/Toggle terminal |

## 🐛 Debugging Workflow

### Setting Breakpoints

1. Click in the **left gutter** next to any line number
2. Red dot appears indicating breakpoint is set
3. Right-click breakpoint to set **conditional breakpoints**

### Running Debugger

1. Press **F5** or select configuration from Run and Debug panel
2. Code executes normally until it hits a breakpoint
3. **Debug panel opens** showing:
   - Local variables
   - Call stack
   - Watch expressions
   - Debug console

### Inspecting Variables

- **Hover** over any variable to see its value
- **Debug Console** (Ctrl+Shift+Y) - Execute Python code live
- **Variables panel** - See all local/global variables
- **Watch panel** - Add specific variables to watch

### Stepping Through Code

- **F10** - Step over (next line)
- **F11** - Step into (enter function call)
- **Shift+F11** - Step out (exit current function)
- **Cmd+Shift+P** → "Debug: Continue" - Resume execution

## 🔍 Debug Console Tips

The Debug Console allows you to execute Python code while paused at a breakpoint:

```python
# Check variable values
my_var

# Call functions
len(politicians)

# Modify variables
x = 42

# Execute statements
for item in collection:
    print(item)

# Import modules
import json
json.dumps(my_var)
```

## ⚙️ How It All Works

### Virtual Environment Activation

```json
// In launch.json
"python": "${workspaceFolder}/.venv/bin/python"
```

VS Code uses this specific Python path, automatically activating the venv.

### PYTHONPATH Configuration

```json
// In settings.json
"python.analysis.extraPaths": ["${workspaceFolder}/src"]

// In launch.json
"env": {
    "PYTHONPATH": "${workspaceFolder}/src:${env:PYTHONPATH}"
}
```

This ensures imports like `from politician_trading.config import ...` work correctly.

### Streamlit Execution

```json
// In launch.json
"module": "streamlit",
"args": ["run", "${workspaceFolder}/app.py"]
```

Runs `streamlit run app.py` with the debugger attached.

## ✅ Verification

### Quick Check

```bash
python verify_debug_setup.py
```

Should show:

- ✅ Virtual environment is activated
- ✅ src/ is in PYTHONPATH
- ✅ Required modules installed
- ✅ VS Code config files exist
- ✅ Project modules import correctly

### Manual Test

1. Set a breakpoint on line 1 of `app.py`
2. Press F5 → Select "Python: Run Streamlit App"
3. Code should pause at your breakpoint
4. Debug panel should show

## 🆘 Troubleshooting

### Issue: "Python interpreter not found"

**Solution**:

1. Cmd+Shift+P → "Python: Select Interpreter"
2. Choose the one ending in `.venv/bin/python`
3. Reload window

### Issue: "Module not found" / "Cannot find politician_trading"

**Solution**:

1. Verify PYTHONPATH is set: `echo $PYTHONPATH`
2. Should include `/path/to/repo/src`
3. Check `.vscode/settings.json` has `extraPaths`

### Issue: Streamlit won't start / "Address already in use"

**Solution**:

```bash
# Kill any existing Streamlit process
lsof -ti:8501 | xargs kill -9

# Or change port in .streamlit/config.toml
[server]
port = 8502
```

### Issue: Breakpoints not working

**Checklist**:

- ✅ Using `debugpy` type (not `python`)
- ✅ `justMyCode` is set correctly
- ✅ Code file is saved
- ✅ Breakpoint is in main code (not stdlib)

### Issue: Debug Console not responding

**Solution**:

1. Stop debugger (Shift+F5)
2. Restart debugging (F5)
3. Try again

## 📚 Recommended Workflow

### For Development

1. Open VS Code
2. Press **F5** → Select "Python: Debug Streamlit App"
3. App launches with debug logging
4. Set breakpoints as needed
5. Click UI to trigger code paths
6. Code pauses at breakpoints
7. Inspect variables in Debug panel

### For Testing

1. **Cmd+Shift+P** → "Tasks: Run Task"
2. Select **"Python: Run Tests"**
3. Results appear in terminal

### For Deploying

1. Use the Makefile: `make`
2. Or manually activate: `source .venv/bin/activate`
3. Run: `streamlit run app.py`

## 📖 Additional Resources

- [VS Code Debugging Guide](https://code.visualstudio.com/docs/editor/debugging)
- [VS Code Python Extension](https://marketplace.visualstudio.com/items?itemName=ms-python.python)
- [Debugpy Documentation](https://github.com/microsoft/debugpy)
- [Streamlit Developer Guide](https://docs.streamlit.io/)

## 🎉 You're All Set

Everything is configured and ready. Just press **F5** and start debugging!

**Questions?** See `.vscode/README.md` or `.vscode/QUICK_START.md`

---

**Next Steps:**

1. ✅ Press F5 and select "Python: Run Streamlit App"
2. ✅ App should launch at <http://localhost:8501>
3. ✅ Set breakpoints in your code
4. ✅ Click UI buttons to trigger code
5. ✅ Code pauses at breakpoints for inspection
6. ✅ Use F10/F11 to step through code
7. ✅ Debug Console to execute code live

Happy debugging! 🚀
