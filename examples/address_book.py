import PySimpleGUI as sg
import pysimplesql as ss                              # <=== PySimpleSQL lines will be marked like this.  There's only a few!
import logging
logger=logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)               # <=== You can set the logging level here (NOTSET,DEBUG,INFO,WARNING,ERROR,CRITICAL)

# Zip code validation
def validate_zip():
    zip=win['Addresses.zip'].get()
    if len(zip)!=5:
        sg.popup('Check your zip code and try again!',title="Zip code validation failed!")
        return False
    return True
# -------------------------------------
# CREATE A SIMPLE DATABASE TO WORK WITH
# -------------------------------------
sql="""
CREATE TABLE Addresses(
    "pkAddresses"   INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    "fkGroupName"   INTEGER,
    "firstName"     Text,
    "lastName"      Text,
    "address1"      Text,
    "address2"      Text,
    "city"          Text,
    "fkState"       INTEGER,
    "zip"           INTEGER,
    FOREIGN KEY (fkGroupName) REFERENCES GroupName(pkGroupName),
    FOREIGN KEY (fkState) REFERENCES State(pkState)
);

CREATE TABLE GroupName(
    "pkGroupName"       INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    "name"          Text
);

CREATE TABLE State(
    "pkState"       INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    "name"          TEXT
);

INSERT INTO GroupName VALUES (1,"Family");
INSERT INTO GroupName VALUES (2,"Friends");
INSERT INTO GroupName VALUES (3,"Coworkers");
INSERT INTO GroupName VALUES (4,"Local businesses");

INSERT INTO State VALUES (1, "OH");
INSERT INTO State VALUES (2, "PA");
INSERT INTO State VALUES (3, "NY");

INSERT INTO Addresses VALUES (1, 2, "John", "Smith", "123 Main St.","Suite A","Cleveland",1,44101);
INSERT INTO Addresses VALUES (2, 1, "Sally", "Jones", "111 North St.","Suite A","Pittsburgh",2,44101);
"""

# -------------------------
# CREATE PYSIMPLEGUI LAYOUT
# -------------------------
# Define the columns for the table selector
columns=['pkAddresses','firstName','lastName','city','fkState']
headings=['pk','First name:    ','Last name:     ','City:        ','State']
visible=[0,1,1,1,1] # Hide the primary key column
layout=[
    [ss.selector("sel","Addresses",sg.Table, headings=headings,visible_column_map=visible, columns=columns,num_rows=10)],
    [ss.record("Addresses.fkGroupName",sg.Combo,auto_size_text=False, size=(30,10))],
    [ss.record("Addresses.firstName", label="First name:")],
    [ss.record("Addresses.lastName", label="Last name:")],
    [ss.record("Addresses.address1", label="Address 1:")],
    [ss.record("Addresses.address2", label="Address 2:")],
    [ss.record("Addresses.city", label="City/State:", size=(23,1)) ,ss.record("Addresses.fkState",element=sg.Combo, no_label=True, quick_editor=False, size=(3,10))],
    [sg.Text("Zip:"+" "*63), ss.record("Addresses.zip", no_label=True,size=(6,1))],
    [ss.actions("browser","Addresses",edit_protect=False, duplicate=True)]
]
win=sg.Window('Journal example', layout, finalize=True, ttk_theme=ss.get_ttk_theme())
# Create our frm
frm=ss.Form(':memory:', sql_commands=sql, bind=win)


# Use a callback to validate the zip code
frm['Addresses'].set_callback('before_save',validate_zip)

# ---------
# MAIN LOOP
# ---------
while True:
    event, values = win.read(timeout=100)

    if event == "__TIMEOUT__":
        # Use a timeout (As set in win.read() above) to check for changes and enable/disable the save button on the fly.
        # This could also be done by enabling events in the input controls, but this is much simpler (but less optimized)
        dirty = frm['Addresses'].records_changed()
        win['browser.db_save'].update(disabled=dirty)
        if dirty:
            win['browser.db_save'].update(disabled=False)
        else:
            win['browser.db_save'].update(disabled=True)
        # The above could have been written as below, but it's less verbose. Your choice!
        # win['browser.db_save'].update(disabled=not dirty)
    elif ss.process_events(event, values):                  # <=== let PySimpleSQL process its own events! Simple!
        logger.info(f'PySimpleDB event handler handled the event {event}!')
    elif event == sg.WIN_CLOSED or event == 'Exit':
        frm=None              # <= ensures proper closing of the sqlite database and runs a database optimization
        break
    else:
        logger.info(f'This event ({event}) is not yet handled.')



"""
I hope that you enjoyed this simple demo of a Journal database.  
Without comments and embedded SQL script, this could have been done in well under 50 lines of code! Seriously - a full database-backed
usable program! The combination of PySimpleSQL and PySimpleGUI is very fun, fast and powerful!

Learnings from this example:
- Using Query.set_search_order() to set the search order of the table for search operations.
- embedding sql commands in code for table creation
- creating a default/empty database with sql commands with the sql_commands keyword argument to ss.Form()
- using ss.record() and ss.selector() functions for easy GUI element creation
- using the label keyword argument to ss.record() to define a custom label
- using Tables as ss.selector() element types
- changing the sort order of database queries
"""