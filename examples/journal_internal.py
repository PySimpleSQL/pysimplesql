import PySimpleGUI as sg
import pysimplesql as ss                              # <=== PySimpleSQL lines will be marked like this.  There's only a few!
import logging
logger=logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)               # <=== You can set the logging level here (NOTSET,DEBUG,INFO,WARNING,ERROR,CRITICAL)

# -------------------------------------
# CREATE A SIMPLE DATABASE TO WORK WITH
# -------------------------------------
sql="""
CREATE TABLE Journal(
    "id"            INTEGER NOT NULL PRIMARY KEY,
    "entry_date"    INTEGER DEFAULT (date('now')), 
    "mood_id"       INTEGER,
    "title"         TEXT DEFAULT "New Entry",
    "entry"         TEXT,
    FOREIGN KEY (mood_id) REFERENCES Mood(id) --This line is important to the automatic functionality of PySimpleSQL~
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
    [ss.selector('sel_journal','Journal',sg.Table,num_rows=10,headings=headings,visible_column_map=visible)],
    [ss.actions('act_journal','Journal')],
    [ss.record('Journal.entry_date')],
    [ss.record('Journal.mood_id', sg.Combo, label='My mood:', size=(30,10), auto_size_text=False)],
    [ss.record('Journal.title')],
    [ss.record('Journal.entry', sg.MLine, size=(71,20))]
]
win=sg.Window('Journal (internal) example', layout, finalize=True)
frm=ss.Form(':memory:', sql_commands=sql, bind=win) #<=== Here is the magic!
# Note:  sql_commands in only run if journal.frm does not exist!  This has the effect of creating a new blank
# database as defined by the sql_commands if the database does not yet exist, otherwise it will use the database!

# Reverse the default sort order so new journal entries appear at the top
frm['Journal'].set_order_clause('ORDER BY entry_date DESC')
# Set the column order for search operations.  By default, only the column designated as the description column is searched
frm['Journal'].set_search_order(['entry_date','title','entry'])

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
Without comments and embedded SQL script, this could have been done in well under 50 lines of code! Seriously - a full database-backed
usable program! The combination of PySimpleSQL and PySimpleGUI is very fun, fast and powerful!

Learnings from this example:
- Using Query.set_search_order() to set the search order of the query for search operations.
- embedding sql commands in code for table creation
- creating a default/empty database with sql commands with the sql_commands keyword argument to ss.Form()
- using Form.record() and Form.selector() functions for easy GUI element creation
- using the label keyword argument to Form.record() to define a custom label
- using Tables as Form.selector() element types
- changing the sort order of database queries
"""