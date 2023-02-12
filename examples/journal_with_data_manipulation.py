import PySimpleGUI as sg
import pysimplesql as ss                              # <=== PySimpleSQL lines will be marked like this.  There's only a few!
from datetime import datetime
from datetime import timezone
import logging
logger=logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)               # <=== You can set the logging level here (NOTSET,DEBUG,INFO,WARNING,ERROR,CRITICAL)

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
# Define the columns for the table selector
headings=['id','Date:              ','Mood:      ','Title:                                 ']
visible=[0,1,1,1] # Hide the id column
layout=[
    [ss.selector('sel_journal','Journal',sg.Table,num_rows=10,headings=headings,visible_column_map=visible)],
    [ss.actions('act_journal','Journal',edit_protect=False)],
    [ss.record('Journal.entry_date')],
    [ss.record('Journal.mood_id', sg.Combo, size=(30,10), auto_size_text=False)],
    [ss.record('Journal.title')],
    [ss.record('Journal.entry', sg.MLine, size=(71,20))]
]
win=sg.Window('Journal example', layout, finalize=True)
frm=ss.Form(':memory:', sql_commands=sql, bind=win) #<=== Here is the magic!
# Reverse the default sort order so new journal entries appear at the top
frm['Journal'].set_order_clause('ORDER BY entry_date DESC')
# Set the column order for search operations.  By default, only the column designated as the description column is searched
frm['Journal'].set_search_order(['entry_date','title','entry'])

# ------------------------------------------------------
# SET UP TRANSFORM FOR ENCODING/DECODING UNIX TIMESTAMPS
# ------------------------------------------------------
# Encode/Decode to/from unix epoch to readable date on database read/write
def tform_date(row,encode):
    col = 'entry_date'
    if col in row:
        msg = f'Transforming {col} from {row[col]}'
        print(msg)
        if encode == ss.TFORM_DECODE:
            row[col] = datetime.utcfromtimestamp(row[col]).strftime('%m/%d/%y')
        else:
            row[col] = datetime.strptime(row[col], '%m/%d/%y').replace(tzinfo=timezone.utc).timestamp()
        print(f'{msg} to {row[col]}')


# Use our new transform!
frm['Journal'].set_transform(tform_date)
frm['Journal'].requery()


# ---------
# MAIN LOOP
# ---------
while True:
    event, values = win.read()

    if ss.process_events(event, values):                  # <=== let PySimpleSQL process its own events! Simple!
        logger.info(f'PySimpleDB event handler handled the event {event}!')
    elif event == sg.WIN_CLOSED or event == 'Exit':
        frm=None              # <= ensures proper closing of the sqlite database and runs a database optimization
        break
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
- Using Query.set_search_order() to set the search order of the table for search operations.
- embedding sql commands in code for table creation
- creating a default/empty database with sql commands
- using ss.record() and ss.selector() functions for easy GUI element creation
- using Tables as ss.selector() element types
- eating events when calling Query.update
- changing the sort order of database queries
- before_update callbacks
- GUI element callbacks
- forcing elements to update with fresh data with frm.update_elements()
- retreiving the description field from a table if the primary key is known with Query.get_description_for_pk()
"""