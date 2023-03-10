import PySimpleGUI as sg
import pysimplesql as ss                 # <=== PySimpleSQL lines will be marked like this.  There's only a few!
import logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)  # <=== Set the logging level here (NOTSET,DEBUG,INFO,WARNING,ERROR,CRITICAL)


# Zip code validation
def validate_zip():
    zipcode = win['Addresses.zip'].get()
    if len(zipcode) != 5:
        sg.popup('Check your zip code and try again!', title="Zip code validation failed!")
        return False
    return True


# -------------------------------------
# CREATE A SIMPLE DATABASE TO WORK WITH
# -------------------------------------
# Note that this is only one of several ways to create a database.   This technique is embedding the commands right in
# your own program.  You can also read commands in from an SQL file, or just connect to an existing database with no
# need for any SQL statements at all.
sql = """
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
INSERT INTO State VALUES (4, "CA");
INSERT INTO State VALUES (5, "TX");
INSERT INTO State VALUES (6, "FL");
INSERT INTO State VALUES (7, "IL");
INSERT INTO State VALUES (8, "MI");

INSERT INTO Addresses VALUES (1, 2, "John", "Smith", "123 Main St.","Suite A","Cleveland",1,44101);
INSERT INTO Addresses VALUES (2, 1, "Sally", "Jones", "111 North St.","Suite A","Pittsburgh",2,44101);
INSERT INTO Addresses VALUES (3, 3, "David", "Johnson", "456 Elm St.","Apt 1","Albany",3,12084);
INSERT INTO Addresses VALUES (4, 4, "Bob", "Johnson", "456 Main St.","Suite B","Los Angeles",1,90001);
INSERT INTO Addresses VALUES (5, 3, "Mary", "Davis", "789 Elm St.","Apt 2","New York City",2,10001);
INSERT INTO Addresses VALUES (6, 2, "Tom", "Lee", "456 West St.","Suite 101","Houston",3,77001);
INSERT INTO Addresses VALUES (7, 1, "Emily", "Wilson", "123 Oak Ave.","Unit 5","Detroit",2,48201);
INSERT INTO Addresses VALUES (8, 1, "David", "Brown", "222 Main St.","Apt 3","Columbus",4,43201);
INSERT INTO Addresses VALUES (9, 3, "Lisa", "Taylor", "555 North St.","Suite C","Chicago",6,60601);
INSERT INTO Addresses VALUES (10, 4, "Steven", "Harris", "777 Beach Blvd.","Apt 10","Miami",5,33101);
INSERT INTO Addresses VALUES (11, 2, "Rachel", "Moore", "444 Pine St.","Apt 1","Philadelphia",7,19101);
"""

# -------------------------
# CREATE PYSIMPLEGUI LAYOUT
# -------------------------
# Define the columns for the table selector.  This will allow entries to be sorted by column!
headings = ss.TableHeadings()
headings.add_column('firstName', 'First name:', 15)
headings.add_column('lastName', 'Last name:', 15)
headings.add_column('city', 'City:', 13)
headings.add_column('fkState', 'State:', 5)

layout = [
    [ss.selector("Addresses", sg.Table, headings=headings, num_rows=10)],
    [ss.field("Addresses.fkGroupName", sg.Combo, size=(30, 10), auto_size_text=False)],
    [ss.field("Addresses.firstName", label="First name:")],
    [ss.field("Addresses.lastName", label="Last name:")],
    [ss.field("Addresses.address1", label="Address 1:")],
    [ss.field("Addresses.address2", label="Address 2:")],
    [ss.field("Addresses.city", size=(23, 1), label="City/State:"),
     ss.field("Addresses.fkState", element=sg.Combo, size=(3, 10), no_label=True, quick_editor=False)],
    [sg.Text("Zip:"+" "*63), ss.field("Addresses.zip", size=(6, 1), no_label=True)],
    [ss.actions("Addresses", edit_protect=False, duplicate=True)]
]
win = sg.Window('Address book example', layout, finalize=True, ttk_theme=ss.themepack.ttk_theme)
# Connect to a database
driver = ss.Sqlite(':memory:', sql_commands=sql)
# Create our frm
frm = ss.Form(driver, bind_window=win)

# Use a callback to validate the zip code
frm['Addresses'].set_callback('before_save', validate_zip)

# ---------
# MAIN LOOP
# ---------
while True:
    event, values = win.read(timeout=100)

    if event == sg.WIN_CLOSED or event == 'Exit':
        frm.close()  # <= ensures proper closing of the sqlite database and runs a database optimization
        win.close()
        break
    elif event == "__TIMEOUT__":
        # Use a timeout (as set in win.read() above) to check for changes and enable/disable the save button on the fly.
        # This could also be done by enabling events in the input controls, but this is much simpler.
        dirty = frm['Addresses'].records_changed()
        win['Addresses:db_save'].update(disabled=not dirty)
    elif "edit_protect" in event:
        win['datepicker'].update(disabled=frm.get_edit_protect())
    elif ss.process_events(event, values):  # <=== let PySimpleSQL process its own events! Simple!
        logger.info(f'PySimpleDB event handler handled the event {event}!')
    else:
        logger.info(f'This event ({event}) is not yet handled.')
win.close()


"""
I hope that you enjoyed this simple demo of a Journal database.  
Without comments and embedded SQL script, this could have been done in well under 50 lines of code! Seriously - a full 
database-backed usable program! The combination of pysimplesql and PySimpleGUI is very fun, fast and powerful!

Learnings from this example:
- Using `ss.Form.set_search_order()` to set the search order of the table for search operations.
- embedding sql commands in code for table creation
- creating a default/empty database with sql commands with the sql_commands keyword argument to `ss.Form()`
- using ss.field() and ss.selector() functions for easy GUI element creation
- using the label keyword argument to ss.field() to define a custom label
- using Tables as ss.selector() element types
- changing the sort order of `ss.Form()` dataset
- using a before_save callback to validate data
- using `ss.Form.records_changed()` to check for changed records on the fly, enabling/disabling the save button
"""