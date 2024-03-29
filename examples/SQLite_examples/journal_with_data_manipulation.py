# To keep examples concise, avoid Black formatting. Remove # fmt: off to use Black formatting.
# fmt: off

import PySimpleGUI as sg
import pysimplesql as ss  # <=== PySimpleSQL lines will be marked like this.  There's only a few!
from datetime import datetime
from datetime import timezone
import logging
logger=logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)  # <=== You can set the logging level here (NOTSET,DEBUG,INFO,WARNING,ERROR,CRITICAL)

# -------------------------------------
# CREATE A SIMPLE DATABASE TO WORK WITH
# -------------------------------------
sql="""
CREATE TABLE Journal(
    "id"            INTEGER NOT NULL PRIMARY KEY,
    "title"         TEXT DEFAULT "New Entry",
    "entry_date"    INTEGER DEFAULT (strftime('%s', 'now')), --Store date information as a unix epoch timestamp
    "mood_id"       INTEGER,
    "entry"         TEXT,
    FOREIGN KEY (mood_id) REFERENCES Mood(id)
);
CREATE TABLE Mood(
    "id"            INTEGER NOT NULL PRIMARY KEY,
    "name"          TEXT
);
INSERT INTO Mood VALUES (1,"Happy");
INSERT INTO Mood VALUES (2,"Sad");
INSERT INTO Mood VALUES (3,"Angry");
INSERT INTO Mood VALUES (4,"Content");
INSERT INTO Journal (id,mood_id,title,entry)VALUES (1,1,"My first entry!","I am excited to write my thoughts every day");
INSERT INTO Journal (id,mood_id,title,entry)VALUES (2,4,"My 2nd entry!","I feel like Doogie Howser ");
"""
# -------------------------
# CREATE PYSIMPLEGUI LAYOUT
# -------------------------
# Define the columns for the table selector using the TableHeading convenience class.  This will also allow sorting!
table_builder = ss.TableBuilder(num_rows=10)
table_builder.add_column('title', 'Title', width=40)
table_builder.add_column('entry_date', 'Date', width=10)
table_builder.add_column('mood_id', 'Mood', width=20)

layout=[
    [ss.selector('Journal', table_builder, key='sel_journal')],
    [ss.actions('Journal', 'act_journal', edit_protect=False)],
    [ss.field('Journal.entry_date')],
    [ss.field('Journal.mood_id', sg.Combo, size=(30, 10), auto_size_text=False)],
    [ss.field('Journal.title')],
    [ss.field('Journal.entry', sg.MLine, size=(71, 20))]
]
win=sg.Window('Journal example', layout, finalize=True)

driver = ss.Driver.sqlite(':memory:',sql_commands=sql) # Create a new database connection
frm= ss.Form(driver, bind_window=win)  #<=== Here is the magic!
# Reverse the default sort order so new journal entries appear at the top
frm['Journal'].set_order_clause('ORDER BY entry_date DESC')
# Set the column order for search operations.  Normally only the column designated as the description column is searched
frm['Journal'].set_search_order(['entry_date','title','entry'])

# ------------------------------------------------------
# SET UP TRANSFORM FOR ENCODING/DECODING UNIX TIMESTAMPS
# ------------------------------------------------------
# Encode/Decode to/from unix epoch to readable date on database read/write
frm['Journal'].set_transform(ss.simple_transform)

transform_dict = {'entry_date' : {
    'decode' : lambda row,col: datetime.utcfromtimestamp(int(row[col])).strftime('%m/%d/%y'),
    'encode' : lambda row,col: datetime.strptime(row[col], '%m/%d/%y').replace(tzinfo=timezone.utc).timestamp(),
    }}

frm['Journal'].add_simple_transform(transform_dict)

frm['Journal'].requery()


# ---------
# MAIN LOOP
# ---------
while True:
    event, values = win.read()

    if event == sg.WIN_CLOSED or event == 'Exit':
        frm.close()              # <= ensures proper closing of the sqlite database and runs a database optimization
        win.close()
        break
    elif ss.process_events(event, values):                  # <=== let PySimpleSQL process its own events! Simple!
        logger.info(f'PySimpleDB event handler handled the event {event}!')
    else:
        logger.info(f'This event ({event}) is not yet handled.')

"""
I hope that you enjoyed this simple demo of a Journal database.
This example builds on the journal_internal.py example to show how transforms can be used to manipulate data
in between the GUI and the database (in this case, the database is storing dates as unix epoch; We use a transform
to convert the unix epoch to and from a human readable format!)
Without comments and embedded SQL script, this could have been done in well under 50 lines of code, even the transform
addition from the original journal_internal.py!

Learnings from this example:
- Using transforms to manipulate data presented to the GUI, and to manipiulate GUI data going back to the database
- Using DataSet.set_search_order() to set the search order of the table for search operations.
- embedding sql commands in code for table creation
- creating a default/empty database with sql commands
- using ss.record() and ss.selector() functions for easy GUI element creation
- using Tables as ss.selector() element types
- eating events when calling DataSet.update
- changing the sort order of database dataset
- before_update callbacks
- GUI element callbacks
- forcing elements to update with fresh data with frm.update_elements()
- retreiving the description field from a table if the primary key is known with DataSet.get_description_for_pk()
"""
