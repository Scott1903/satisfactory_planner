For Satisfactory updates:
read_docs.py in Data folder requires Satisfactory/CommunityResources/Docs/Docs.json file copied into the same dir.  Running that will create the data.json file for this model.  (Beacons have to be manually added in Update 8)

Run gui.py to open the program.

main.py is the translator to the model and runs the solver.
model.py creates the model for the solver.

The Saves file contains the saved settings states by the user.

CREATE .EXE:
pyinstaller --onefile --windowed --icon=icon.ico --collect-all pyomo --name SatisfactoryPlanner gui.py
