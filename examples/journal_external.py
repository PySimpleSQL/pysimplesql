import PySimpleGUI as sg
import pysimplesql as ss                              # <=== PySimpleSQL lines will be marked like this.  There's only a few!
import logging
logger=logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)               # <=== You can set the logging level here (NOTSET,DEBUG,INFO,WARNING,ERROR,CRITICAL)

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
    ss.record('Journal.mood_id', sg.Combo, label='My mood:', size=(30,10), auto_size_text=False),
    ss.record('Journal.title'),
    ss.record('Journal.entry', sg.MLine, size=(71,20))
]
win=sg.Window('Journal example', layout, finalize=True)
db=ss.Database('journal.db', win,  sql_script='journal.sql') #<=== Here is the magic!
# Note:  sql_script is only run if journal.db does not exist!  This has the effect of creating a new blank
# database as defined by the sql_script file if the database does not yet exist, otherwise it will use the database!

# Reverse the default sort order so new journal entries appear at the top
db['Journal'].set_order_clause('ORDER BY entry_date DESC')
# Set the column order for search operations.  By default, only the column designated as the description column is searched
db['Journal'].set_search_order(['entry_date','title','entry'])

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
Without comments, this could have been done in about30 lines of code! Seriously - a full database-backed
usable program! The combination of PySimpleSQL and PySimpleGUI is very fun, fast and powerful!

Learnings from this example:
- Using Table.set_search_order() to set the search order of the table for search operations.
- creating a default/empty database with an external sql script with the sql_script keyword argument to ss.Database()
- using ss.record() and ss.selector() functions for easy GUI element creation
- using the label keyword argument to ss.record() to define a custom label
- using Tables as ss.selector() element types
- changing the sort order of database tables
"""