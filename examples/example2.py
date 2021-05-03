#!/usr/bin/python3
import PySimpleGUI as sg
import pysimplesql as ss                               # <=== PySimpleSQL lines will be marked like this.  There's only a few!
import logging
logger=logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)               # <=== You can set the logging level here (NOTSET,DEBUG,INFO,WARNING,ERROR,CRITICAL)

# Define our layout. We will use the ss.record convenience function to create the controls
layout = [
    ss.record('Restaurant', 'name'),
    ss.record('Restaurant', 'location'),
    ss.record('Restaurant', 'fkType', sg.Combo)]
sub_layout = [
    [sg.Listbox(values=(), size=(35, 10), key="SELECTOR.Item", select_mode=sg.LISTBOX_SELECT_MODE_SINGLE, enable_events=True),
    sg.Col(
        [ss.record('Item', 'name'),
         ss.record('Item', 'fkMenu', sg.Combo),
         ss.record('Item', 'price'),
         ss.record('Item', 'description', sg.MLine, (30, 7))
         ])],
    ss.actions('Item', navigation=False, search=False)
]
layout += [[sg.Frame('Items', sub_layout)]]
layout += [ss.actions('Restaurant')]

# Initialize our window and database, then bind them together
win = sg.Window('places to eat', layout, finalize=True)
db = ss.Database('example.db', win)      # <=== load the database and bind it to the window
# NOTE: If you want to read in SQL commands and create a database instead of opening an existing one, just pass it in!
# db = ss.Database('example.db', win, sql_file='example.sql')      # <=== load the database and bind it to the window

while True:
    event, values = win.read()
    if db.process_events(event, values):                  # <=== let PySimpleSQL process its own events! Simple!
        print('PySimpleDB event handler handled the event!')
    elif event == sg.WIN_CLOSED or event == 'Exit':
        db=None              # <= ensures proper closing of the sqlite database and runs a database optimization
        break
    else:
        print(f'This event ({event}) is not yet handled.')
