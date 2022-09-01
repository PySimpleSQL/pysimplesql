import PySimpleGUI as sg
import pysimplesql as ss                               # <=== PySimpleSQL lines will be marked like this.  There's only a few!
import logging
logger=logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)               # <=== You can set the logging level here (NOTSET,DEBUG,INFO,WARNING,ERROR,CRITICAL)


# Define our layout. We will use the Form.record convenience function to create the controls
layout = [
    ss.record('Restaurant.name'),
    ss.record('Restaurant.location'),
    ss.record('Restaurant.fkType', sg.Combo, size=(30,10), auto_size_text=False)]
sub_layout = [
    ss.selector('selector1','Item',size=(35,10))+
    [sg.Col([ss.record('Item.name'),
         ss.record('Item.fkMenu', sg.Combo, size=(30,10), auto_size_text=False),
         ss.record('Item.price'),
         ss.record('Item.description', sg.MLine,size=(30, 7))
    ])],
    ss.actions('actions1','Item', edit_protect=False,navigation=False,save=False, search=False)
]
layout += [[sg.Frame('Items', sub_layout)]]
layout += [ss.actions('actions2','Restaurant')]

# Initialize our window and database, then bind them together
win = sg.Window('places to eat', layout, finalize=True)
# Create our Form
frm = ss.Form(':memory:', sql_script='example.sql', bind=win)      # <=== load the database
# NOTE: ":memory:" is a special database URL for in-memory databases


while True:
    event, values = win.read()

    if ss.process_events(event, values):                  # <=== let PySimpleSQL process its own events! Simple!
        logger.info('PySimpleDB event handler handled the event!')
    elif event == sg.WIN_CLOSED or event == 'Exit':
        frm=None              # <= ensures proper closing of the sqlite database and runs a database optimization at close
        break
    else:
        logger.info(f'This event ({event}) is not yet handled.')
