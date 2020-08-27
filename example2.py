#!/usr/bin/python3
import PySimpleGUI as sg
import PySimpleSQL as ss                               # <=== PySimpleSQL lines will be marked like this.  There's only a few!

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
    ss.record_actions('Item', False)
]
layout += [[sg.Frame('Items', sub_layout)]]
layout += [ss.record_navigation('Restaurant',protect=True,search=True,save=True)]

# Initialize our window and database, then bind them together
win = sg.Window('places to eat', layout, finalize=True)
db = ss.Database('example2.db', win, sql_file='example2.sql')      # <=== load the database and bind it to the window

while True:
    event, values = win.read()
    if db.process_events(event, values):                  # <=== let PySimpleSQL process its own events! Simple!
        print('PySimpleDB event handler handled the event!')
    elif event == sg.WIN_CLOSED or event == 'Exit':
        break
    else:
        print(f'This event ({event}) is not yet handled.')
