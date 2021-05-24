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
    "entry_date"    INTEGER DEFAULT (strftime('%s', 'now')), --Store date information as a unix epoch timestamp
    "mood_id"       INTEGER,
    "title"         TEXT DEFAULT "New Entry",
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
INSERT INTO Journal (id,mood_id,title,entry)VALUES (1,1,"My first entry!","I am excited to write my thoughts every day")
"""

# -------------------------
# CREATE PYSIMPLEGUI LAYOUT
# -------------------------
# Define the columns for the table selector
headings=['id','Date:              ','Mood:      ','Title:                                 ']
visible=[0,1,1,1] # Hide the id column
layout=[
    ss.selector('sel_journal','Journal',sg.Table,num_rows=10,headings=headings,visible_column_map=visible),
    ss.actions('act_journal','Journal'),
    ss.record('Journal.entry_date'),
    ss.record('Journal.mood_id', sg.Combo, size=(30,10), auto_size_text=False),
    ss.record('Journal.title'),
    ss.record('Journal.entry', sg.MLine, size=(71,20))
]
win=sg.Window('Journal example', layout, finalize=True)
db=ss.Database(':memory:', win,  sql_commands=sql) #<=== Here is the magic!
# Note:  sql_commands in only run if journal.db does not exist!  This has the effect of creating a new blank
# database as defined by the sql_commands if the database does not yet exist, otherwise it will use the database!

# Reverse the default sort order so new journal entries appear at the top
db['Journal'].set_order_clause('ORDER BY entry_date DESC')
# Set the column order for search operations.  By default, only the column designated as the description column is searched
db['Journal'].set_search_order(['entry_Date','title','entry'])

# ------------------------------------------------------
# SET UP CALLBACKS FOR ENCODING/DECODING UNIX TIMESTAMPS
# ------------------------------------------------------
# Decode from unix epoch to readable date
def cb_date_decode():
    # Decode the timestamp to a readable date
    logger.info(f'In callback, decoding date...')
    if db['Journal']['entry_date']:
        win['Journal.entry_date'].update(datetime.utcfromtimestamp(db['Journal']['entry_date']).strftime('%m/%d/%y'))
    else:
        win['Journal.entry_date'].update('')

# Encode readable date to unix epoch
def cb_date_encode():
    logger.info(f'In callback, encoding date...')
    win['Journal.entry_date'].update(
        datetime.strptime(win['Journal.entry_date'].Get(), '%m/%d/%y').replace(tzinfo=timezone.utc).timestamp())
    return True # Return true, as this will be a callback to before_save

# Override the default element update routines for the table
def cb_table_update():
    # Update the table element
    logger.info(f"In callback, updating the table element")
    if not db['Journal']['entry_date']:
        lst = [['', '', '', '']] # build an empty list
        win['Journal.entry_date'].update(lst)
        ss.eat_events(win) # This must be calld anytime the update method is used on a table
        return
    lst = []
    # Make sure we have up-to-date results
    for r in db['Journal'].rows:
        lst.append([r['id'], datetime.utcfromtimestamp(r['entry_date']).strftime('%m/%d/%y'), db['Mood'].get_description_for_pk(r['mood_id']), r['title']])

    # Get the primary key to select.  We have to use the list above instead of getting it directly
    # from the table, as the data has yet to be updated
    pk = db['Journal']['id']
    index = 0
    for v in lst:
        if v[0] == pk:
            break
        index += 1

    win['sel_journal'].update(lst, select_rows=[index])
    ss.eat_events(win) # This must be calld anytime the update method is used on a table

# set our callbacks!
db.set_callback('Journal.entry_date',cb_date_decode)        # decode the date when this element updates...
db['Journal'].set_callback('before_save',cb_date_encode)    # encode the date before saving the record...
#db.set_callback('sel_journal',cb_table_update)          # Override the default element update for the table to display correct dates there too!
                                                            # *******COMMENT/UNCOMMENT LINE ABOVE TO SEE THE TABLE CHANGE HOW IT DISPLAYS DATE INFO!!!*******
db.update_elements()                                        # Manually update the elements so the callbacks trigger on initial run

# ---------
# MAIN LOOP
# ---------
while True:
    event, values = win.read()

    if db.process_events(event, values):                  # <=== let PySimpleSQL process its own events! Simple!
        logger.info(f'PySimpleDB event handler handled the event {event}!')
    elif event == sg.WIN_CLOSED or event == 'Exit':
        db=None              # <= ensures proper closing of the sqlite database and runs a database optimization
        break
    else:
        logger.info(f'This event ({event}) is not yet handled.')

"""
I hope that you enjoyed this simple demo of a Journal database.  
This example builds on the journal_internal.py example to show how callbacks can be used to manipulate date
in between the GUI and the database (in this case, the database is storing dates as unix epoch; We use callbacks
to convert the unix epoch to and from a human readable format!)
Without comments and embedded SQL script, this could have been done in well under 70 lines of code, even with all of the
callback additions from the original journal_internal.py!

Learnings from this example:
- Using callbacks to manipulate data presented to the GUI, and to manipiulate GUI data going back to the database
- Using Table.set_search_order() to set the search order of the table for search operations.
- embedding sql commands in code for table creation
- creating a default/empty database with sql commands
- using ss.record() and ss.selector() functions for easy GUI element creation
- using Tables as ss.selector() element types
- eating events when calling Table.update
- changing the sort order of database tables
- before_update callbacks
- GUI element callbacks
- forcing elements to update with fresh data with db.update_elements()
- retreiving the description field from a table if the primary key is known with Table.get_description_for_pk()
"""