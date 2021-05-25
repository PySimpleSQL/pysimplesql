# import PySimpleGUI and pysimplesql
import PySimpleGUI as sg
import pysimplesql as ss

# -------------------------
# CREATE PYSIMPLEGUI LAYOUT
# -------------------------
# Define the columns for the table selector
headings=['id','Date:              ','Mood:      ','Title:                                 ']
visible=[0,1,1,1] # Hide the id column
layout=[
    ss.selector('sel_journal','Journal',sg.Table,num_rows=10,headings=headings,visible_column_map=visible),
    ss.actions('act_journal','Journal', edit_protect=False), # These are your database controls (Previous, Next, Save, Insert, etc!)
    ss.record('Journal.entry_date', label='Date:'),
    ss.record('Journal.mood_id', sg.Combo, label='My mood:', size=(30,10), auto_size_text=False),
    ss.record('Journal.title'),
    ss.record('Journal.entry', sg.MLine, size=(71,20))
]

win=sg.Window('Journal example', layout, finalize=True)
db=ss.Database(':memory:', win, sql_script='journal.sql') #<=== Here is the magic!
# Note:  ':memory:' is a special address for in-memory databases

# ---------
# MAIN LOOP
# ---------
while True:
    event, values = win.read()

    if db.process_events(event, values):                  # <=== let PySimpleSQL process its own events! Simple!
        print(f'pysimpledb event handler handled the event {event}!')
    elif event == sg.WIN_CLOSED or event == 'Exit':
        db=None              # <= ensures proper closing of the sqlite database and runs a database optimization
        break
    else:
        print(f'This event ({event}) is not yet handled.')