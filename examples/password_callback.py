#!/usr/bin/python3
import PySimpleGUI as sg
import pysimplesql as ss                               # <=== PySimpleSQL lines will be marked like this.  There's only a few!
import logging
logger=logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)               # <=== You can set the logging level here (NOTSET,DEBUG,INFO,WARNING,ERROR,CRITICAL)

frm = ss.Form(':memory:', sql_script='example.sql')      # <=== load the database and bind it to the window
# NOTE: ":memory:" is a special database URL for in-memory databases

# Here are our callback functions
def enable(db,win):
    res=sg.popup_get_text('Enter password for edit mode.\n(Hint: it is 1234)')
    return True if res=='1234' else False
def disable(db,win):
    res = sg.popup_yes_no('Are you sure you want to disabled edit mode?')
    return True if res == 'Yes' else False

# Define our layout. We will use the ss.record convenience function to create the controls
layout = [
    frm.record('Restaurant.name'),
    frm.record('Restaurant.location'),
    frm.record('Restaurant.fkType', sg.Combo, size=(30,10), auto_size_text=False)]
sub_layout = [
    frm.selector('selector1','Item',size=(35,10))+
    [sg.Col([frm.record('Item.name'),
         frm.record('Item.fkMenu', sg.Combo, size=(30,10), auto_size_text=False),
         frm.record('Item.price'),
         frm.record('Item.description', sg.MLine, (30, 7))
    ])],
    frm.actions('act_item','Item', edit_protect=False,navigation=False,save=False, search=False)
]
layout += [[sg.Frame('Items', sub_layout)]]
layout += [frm.actions('act_restaurant','Restaurant')]

# Initialize our window and database, then bind them together
win = sg.Window('places to eat', layout, finalize=True)
frm.bind(win)

# Set our callbacks
# See documentation for a full list of callbacks supported
frm.set_callback('edit_enable', enable)
frm.set_callback('edit_disable', disable)

while True:
    event, values = win.read()

    if ss.process_events(event, values):                  # <=== let PySimpleSQL process its own events! Simple!
        logger.info('PySimpleDB event handler handled the event!')
    elif event == sg.WIN_CLOSED or event == 'Exit':
        frm=None              # <= ensures proper closing of the sqlite database and runs a database optimization at close
        break
    else:
        logger.info(f'This event ({event}) is not yet handled.')





