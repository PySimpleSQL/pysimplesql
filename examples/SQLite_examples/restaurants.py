import PySimpleGUI as sg
import pysimplesql as ss                # <=== PySimpleSQL lines will be marked like this.  There's only a few!
import logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)  # <=== Set the logging level here (NOTSET,DEBUG,INFO,WARNING,ERROR,CRITICAL)


# Define our layout. We will use the Form.field() convenience function to create the controls
layout = [
    [ss.field('Restaurant.name')],
    [ss.field('Restaurant.location')],
    [ss.field('Restaurant.fkType', sg.Combo, size=(30, 10), auto_size_text=False)]
]
sub_layout = [
    [ss.selector('Item', size=(35, 10))],
    [
        sg.Col(
            layout=[
                [ss.field('Item.name')],
                [ss.field('Item.fkMenu', sg.Combo, size=(30, 10), auto_size_text=False)],
                [ss.field('Item.price')],
                [ss.field('Item.description', sg.MLine, size=(30, 7))]
            ]
        )
    ],
]
layout.append([sg.Frame('Items', sub_layout)])
layout.append([ss.actions('Restaurant', edit_protect=False)])

# Initialize our window and database, then bind them together
win = sg.Window('Places to eat', layout, finalize=True)
# Set up our driver. # NOTE: ":memory:" is a special database URL for in-memory databases
driver = ss.Sqlite(':memory:', sql_script='restaurants.sql')
# Create our Form
frm = ss.Form(driver, bind_window=win)  # <=== load the database

while True:
    event, values = win.read()

    if ss.process_events(event, values):                  # <=== let PySimpleSQL process its own events! Simple!
        logger.info('PySimpleDB event handler handled the event!')
    elif event == sg.WIN_CLOSED or event == 'Exit':
        frm.close()  # <= ensures proper closing of the sqlite database and runs a database optimization at close
        break
    else:
        logger.info(f'This event ({event}) is not yet handled.')
win.close()
