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

# When using ss.record() to create entries based on key/value pairs, it just uses an extended syntax.
# Where ss.record('Settings.value') would return the value column from the Settings table FOR THE CURRENT RECORD,
# the extended syntax of ss.record('Settings.value?key=first_name will return the value column from the Settings
# table where the key column is equal to 'first_name'.  This is basically the equivalent in SQL as the statement
# SELECT value FROM Settings WHERE key='first_name';
layout=[
    [sg.Text('APPLICATION SETTINGS')],
    [sg.HorizontalSeparator()],
    ss.record('Settings.value?key=company_name'),
    [sg.Text('')],
    ss.record('Settings.value?key=debug_mode',sg.CBox),
    [sg.Text('')],
    ss.record('Settings.value?key=antialiasing', sg.CBox),
    [sg.Text('')],
    ss.record('Settings.value?key=query_retries'),
    # For the actions, we don't want to offer users to insert or delete records from the settings table,
    # and there is no use for navigation buttons due to the key,value nature of the data.  Therefore, we will
    # disable all actions (default=False) except for the Save action (save=True)
    ss.actions('nav','Settings',default=False, save=True)
]

# Initialize our window and database, then bind them together
win = sg.Window('Preferences: Application Settings', layout, finalize=True)
db = ss.Database('Settigs.db', win, sql_commands=sql)      # <=== load the database and bind it to the window

# Now that the database is loaded, lets set our tool tips using the description column.
# The Table.get_keyed_value can return the value column where the key column equals a specific value as well.
win['Settings.value?key=company_name'].set_tooltip(db['Settings'].get_keyed_value('description','key','company_name'))
win['Settings.value?key=debug_mode'].set_tooltip(db['Settings'].get_keyed_value('description','key','debug_mode'))
win['Settings.value?key=antialiasing'].set_tooltip(db['Settings'].get_keyed_value('description','key','antialiasing'))
win['Settings.value?key=query_retries'].set_tooltip(db['Settings'].get_keyed_value('description','key','query_retries'))

while True:
    event, values = win.read()

    if db.process_events(event, values):                  # <=== let PySimpleSQL process its own events! Simple!
       print(f'PySimpleDB event handler handled the event {event}!')
    elif event == sg.WIN_CLOSED or event == 'Exit':
        db=None              # <= ensures proper closing of the sqlite database and runs a database optimization at close
        break
    else:
        print(f'This event ({event}) is not yet handled.')