import PySimpleGUI as sg
import pysimplesql as ss                               # <=== PySimpleSQL lines will be marked like this.  There's only a few!
import logging
logger=logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)               # <=== You can set the logging level here (NOTSET,DEBUG,INFO,WARNING,ERROR,CRITICAL)

# Create our form
# NOTE: ":memory:" is a special database URL for in-memory databases
frm=ss.Form(":memory:", sql_script='example.sql', prefix_queries='q')

# Define our layout. We will use the Form.record convenience function to create the controls
layout = [
    frm.record('qRestaurant.name'),
    frm.record('qRestaurant.location'),
    frm.record('qRestaurant.fkType', sg.Combo, size=(30,10), auto_size_text=False)]
sub_layout = [
    frm.selector('selector1','qItem',size=(35,10))+
    [sg.Col([frm.record('qItem.name'),
         frm.record('qItem.fkMenu', sg.Combo, size=(30,10), auto_size_text=False),
         frm.record('qItem.price'),
         frm.record('qItem.description', sg.MLine, (30, 7))
    ])],
    frm.actions('actions1','qItem', edit_protect=False,navigation=False,save=False, search=False)
]
layout += [[sg.Frame('Items', sub_layout)]]
layout += [frm.actions('actions2','qRestaurant')]

# Initialize our window then bind to the form
win = sg.Window('places to eat', layout, finalize=True)
frm.bind(win)   # <=== Binding the Form to the Window is easy!


while True:
    event, values = win.read()

    if ss.process_events(event, values):                  # <=== let PySimpleSQL process its own events! Simple!
        logger.info('PySimpleDB event handler handled the event!')
    elif event == sg.WIN_CLOSED or event == 'Exit':
        db=None              # <= ensures proper closing of the sqlite database and runs a database optimization at close
        break
    else:
        logger.info(f'This event ({event}) is not yet handled.')
