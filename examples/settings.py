import PySimpleGUI as sg
import pysimplesql as ss

# Settings are typically stored as key, value pairs in databases.
# This example will show you how to use pysimplesql to interact with key, value information in databases
sql="""
CREATE TABLE "Settings"(
    "id" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
	"key" TEXT, 
	"value" TEXT,
	"description" TEXT
);
-- There is nothing special about the key and value column names, they can literally be anything.
INSERT INTO SETTINGS VALUES (1,'company_name','My company','Enter your company name here.');
INSERT INTO SETTINGS VALUES (2,'debug_mode',True,'Check if you would like debug mode enabled.');
INSERT INTO SETTINGS VALUES (3,'antialiasing', True,'Would you like to render with antialiasing?');
INSERT INTO SETTINGS VALUES (4, 'query_retries', 3,'Retry queries this many times before aborting.');
"""

frm = ss.Form('Settigs.db', sql_commands=sql)      # <=== load the database
# Note: we are not binding this Form to a window yet, as the window has not yet been created.
# Creating the form now will help us get values for the tooltips during layout creation below!.

# When using Form.record() to create entries based on key/value pairs, it just uses an extended syntax.
# Where Form.record('Settings.value') would return the value column from the Settings table FOR THE CURRENT RECORD,
# the extended syntax of Form.record('Settings.value?key=first_name') will return the value column from the Settings
# table where the key column is equal to 'first_name'.  This is basically the equivalent in SQL as the statement
# SELECT value FROM Settings WHERE key='first_name';
layout=[
    [sg.Text('APPLICATION SETTINGS')],
    [sg.HorizontalSeparator()],
    [ss.record('Settings.value?key=company_name', tooltip = frm['Settings'].get_keyed_value('description', 'key', 'company_name'))],
    # Notice how we can use get_keyed_value() to retrieve values from keys in the query.  We are using it to set tooltips.
    [sg.Text('')],
    [ss.record('Settings.value?key=debug_mode',sg.CBox, tooltip=frm['Settings'].get_keyed_value('description', 'key', 'debug_mode'))],
    [sg.Text('')],
    [ss.record('Settings.value?key=antialiasing', sg.CBox, tooltip=frm['Settings'].get_keyed_value('description', 'key', 'antialiasing'))],
    [sg.Text('')],
    [ss.record('Settings.value?key=query_retries', tooltip=frm['Settings'].get_keyed_value('description', 'key', 'query_retries'))],
    # For the actions, we don't want to offer users to insert or delete records from the settings table,
    # and there is no use for navigation buttons due to the key,value nature of the data.  Therefore, we will
    # disable all actions (default=False) except for the Save action (save=True)
    [ss.actions('nav','Settings',default=False, save=True)]
]

# Initialize our window then bind it to the Form
win = sg.Window('Preferences: Application Settings', layout, finalize=True)
frm.bind(win)

print(frm['Settings'].get_keyed_value('description', 'key', 'debug_mode'))

while True:
    event, values = win.read()

    if ss.process_events(event, values):                  # <=== let PySimpleSQL process its own events! Simple!
       print(f'PySimpleDB event handler handled the event {event}!')
    elif event == sg.WIN_CLOSED or event == 'Exit':
        frm=None              # <= ensures proper closing of the sqlite database and runs a database optimization at close
        break
    else:
        print(f'This event ({event}) is not yet handled.')

"""
This example showed how to easily access key,value information stored in queries.  A classic example of this is with
storing settings for your own program

Learnings from this example:
- embedding sql commands in code for table creation
- creating a default/empty database with sql commands with the sql_commands keyword argument to ss.Form()
- Creating a form without binding to a window, then later binding the form to a window with a separate statement
- using ss.record() and ss.actions() functions for easy GUI element creation
- using the extended key naming syntax for keyed records (Query.value_column?key_column=key_value)
- using the Query.get_keyed_value() method for keyed data retrieval
"""