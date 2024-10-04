# Satisfactory Planner

## Applying Satisfactory Updates

`read_docs.py` in Data folder requires that `/Path/To/Satisfactory/CommunityResources/Docs/Docs.json` (these will be coded for your locale, e.g. `en-GB` - pick the matching one) is present in the project directory.

Running that will create the data.json file for this model. (read_docs.py out of date for 1.0, some manual input was needed until an update can be made.)

## Setup

- Install Python 3.8.5 or later. [link](https://www.python.org/downloads/)
- Install `glpk` open-source solver onto your computer. [link](https://ftp.gnu.org/gnu/glpk/?C=N;O=D) or for Windows: [link](https://winglpk.sourceforge.net/)
- Set the path where GLPK is installed.

On Windows:

1. Open System Control Panel (Win+X, then select System).
2. Go to Advanced System Settings.
3. Click on Environment Variables.
4. Click New under System variables.
5. Enter the path to the glpsol.exe: 
Variable Name: GLPK_PATH
Variable Value: (example, E:\\Applications\\pyomo glpk\\glpk-4.65\\w64).
6. Restart your PC after setting the variable.

Install the required packages using pip:

```bash
pip install -r requirements.txt
pip install pyinstaller
```

You may wish to use a Python [Virtual Environment](https://docs.python.org/3/library/venv.html) to avoid polluting your system Python installation.

## Usage

Run `gui.py` to open the program.

```bash
python gui.py
```

`main.py` is the translator to the model and runs the solver.
`model.py` creates the model for the solver.

The Saves file contains the saved settings states by the user.

## Build a static executable using PyInstaller

```bash
pyinstaller --onefile --windowed --icon=icon.ico --collect-all pyomo --name SatisfactoryPlanner --distpath . gui.py
```
