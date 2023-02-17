import PySimpleGUI as sg
import pysimplesql as ss                              # <=== PySimpleSQL lines will be marked like this.  There's only a few!
import logging
logger=logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)               # <=== You can set the logging level here (NOTSET,DEBUG,INFO,WARNING,ERROR,CRITICAL)

# POSTGRES EXAMPLE
# Note: Postgres is funny about case sensitivity.  To keep this simple, table names in this example are lower case.

# -------------------------
# CREATE PYSIMPLEGUI LAYOUT
# -------------------------
# Define the columns for the table selector
headings=['id','Date:              ','Mood:      ','Title:                                 ']
visible=[0,1,1,1] # Hide the id column
layout=[
    [ss.selector('sel_journal','journal',sg.Table,num_rows=10,headings=headings,visible_column_map=visible)],
    [ss.actions('act_journal','journal')],
    [ss.record('journal.entry_date')],
    #[ss.record('journal.mood_id', sg.Combo, label='My mood:', size=(30,10), auto_size_text=False)],
    [ss.record('journal.title')],
    [ss.record('journal.entry', sg.MLine, size=(71,20))]
]
win=sg.Window('Journal (external)  example', layout, finalize=True)

elephant_postgres = {
    'host':'queenie.db.elephantsql.com',
    'user':'yunaahtj',
    'password':'OMX8u8CDKNVTrldLbnBFsUjxkArTg4Wj',
    'database':'yunaahtj'
}

driver=ss.Postgres(**elephant_postgres)
frm=ss.Form(driver, bind=win)   #<=== Here is the magic!
# Note:  sql_script is only run if journal.frm does not exist!  This has the effect of creating a new blank
# database as defined by the sql_script file if the database does not yet exist, otherwise it will use the database!

# Reverse the default sort order so new journal entries appear at the top
frm['journal'].set_order_clause('ORDER BY entry_date DESC')
# Set the column order for search operations.  By default, only the column designated as the description column is searched
frm['journal'].set_search_order(['entry_date','title','entry'])

# ---------
# MAIN LOOP
# ---------
while True:
    event, values = win.read()

    if ss.process_events(event, values):                  # <=== let PySimpleSQL process its own events! Simple!
        logger.info(f'PySimpleDB event handler handled the event {event}!')
    elif event == sg.WIN_CLOSED or event == 'Exit':
        frm.close()              # <= ensures proper closing of the sqlite database and runs a database optimization
        break
    else:
        logger.info(f'This event ({event}) is not yet handled.')
win.close()

"""
I hope that you enjoyed this simple demo of a Journal database.  
Without comments, this could have been done in about30 lines of code! Seriously - a full database-backed
usable program! The combination of PySimpleSQL and PySimpleGUI is very fun, fast and powerful!

Learnings from this example:
- Using Query.set_search_order() to set the search order of the query for search operations.
- creating a default/empty database with an external sql script with the sql_script keyword argument to ss.Form()
- using Form.record() and Form.selector() functions for easy GUI element creation
- using the label keyword argument to Form.record() to define a custom label
- using Tables as Form.selector() element type
- changing the sort order of Queries

------------------------------------------------------------------------------------------------------------------------
BELOW IS THE SQL CODE USED TO CREATE THE POSTGRES DATABASE FOR THIS EXAMPLE
------------------------------------------------------------------------------------------------------------------------
DROP TABLE IF EXISTS journal;
DROP TABLE IF EXISTS mood;

CREATE TABLE mood(
    "id"            SERIAL NOT NULL PRIMARY KEY,
    "name"          TEXT
);

CREATE TABLE journal(
    "id"            SERIAL NOT NULL PRIMARY KEY,
    "entry_date"    DATE DEFAULT CURRENT_DATE,
    "mood_id"       INTEGER,
    "title"         TEXT DEFAULT 'New Entry',
    "entry"         TEXT,
    FOREIGN KEY (mood_id) REFERENCES mood(id) 
);

INSERT INTO mood (name) VALUES ('Happy');
INSERT INTO mood (name) VALUES ('Sad');
INSERT INTO mood (name) VALUES ('Angry');
INSERT INTO mood (name) VALUES ('Content');
INSERT INTO journal (mood_id,title,entry)VALUES (1,'My first entry!','I am excited to write my thoughts every day');
INSERT INTO journal (mood_id,title,entry)VALUES (1,'My second entry!','This is still exciting!');
"""

