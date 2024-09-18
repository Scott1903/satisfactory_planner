For Satisfactory updates:
read_docs.py in Data folder requires Satisfactory/CommunityResources/Docs/Docs.json file copied into the same dir.  Running that will create the data.json file for this model.  (read_docs.py out of date for 1.0, some manual input was needed until an update can be made.)

Install 'glpk' open-source solver onto your computer.

Set the path where GLPK is installed.

On Windows:

1. Open System Control Panel (Win+X, then select System).
2. Go to Advanced System Settings.
3. Click on Environment Variables.
4. Click New under System variables.
5. Enter the path to the glpsol.exe: 
Variable Name: GLPK_PATH
Variable Value: (example, E:\\Applications\\pyomo glpk\\glpk-4.65\\w64).
6. Restart your PC after setting the variable.

Run gui.py to open the program.

main.py is the translator to the model and runs the solver.
model.py creates the model for the solver.

The Saves file contains the saved settings states by the user.

CREATE .EXE:
pyinstaller --onefile --windowed --icon=icon.ico --collect-all pyomo --name SatisfactoryPlanner gui.py
