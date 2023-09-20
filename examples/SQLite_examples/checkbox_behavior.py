# fmt: off
import logging
import PySimpleGUI as sg

sg.change_look_and_feel("SystemDefaultForReal")
sg.set_options(font=("Roboto", 11))  # Set the font and font size for the table

import pysimplesql as ss # noqa: E402

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)  # <=== Set the logging level here (NOTSET,DEBUG,INFO,WARNING,ERROR,CRITICAL)

sql = """
CREATE TABLE checkboxes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    bool_none BOOLEAN,
    bool_true BOOLEAN Default True,
    bool_false BOOLEAN Default False,
    int_none INTEGER,
    int_true INTEGER Default 1,
    int_false INTEGER Default 0,
    text_none TEXT,
    text_true TEXT Default "True",
    text_false TEXT Default "False"
);

INSERT INTO checkboxes (bool_none, bool_true, bool_false, int_none, int_true, int_false, text_none, text_true, text_false)
VALUES (NULL,True,False,NULL,1,0,NULL,"True","False");
"""

# -------------------------
# CREATE PYSIMPLEGUI LAYOUT
# -------------------------
# Create a table heading object
table_builder = ss.TableBuilder(allow_cell_edits=True)

# Add columns to the table heading
table_builder.add_column('id', 'id', width=5)

columns = ['bool_none', 'bool_true', 'bool_false', 'int_none', 'int_true', 'int_false', 'text_none', 'text_true', 'text_false']

for col in columns:
    table_builder.add_column(col, col, width=8)

fields = []
for col in columns:
    fields.append([ss.field(f'checkboxes.{col}', sg.Checkbox, size=(20, 10), label={col})])

layout = [
    [sg.Text('This test shows pysimplesql checkbox behavior.')],
    [sg.Text('Each column is labeled as type: bool=BOOLEAN, int=INTEGER, text=TEXT')],
    [sg.Text("And the DEFAULT set for new records, no default set, True,1,'True', or False,0,'False'")],
    [ss.selector('checkboxes', table_builder, row_height=25)],
    [ss.actions('checkboxes', edit_protect=False)],
    fields,
]

win = sg.Window('Checkbox Test', layout, finalize=True)
driver = ss.Driver.sqlite(":memory:", sql_commands=sql)
# Here is the magic!
frm = ss.Form(
    driver,
    bind_window=win,
    live_update=True # this updates the `Selector`, sg.Table as we type in fields!
    )

# ---------
# MAIN LOOP
# ---------
while True:
    event, values = win.read()

    if event == sg.WIN_CLOSED or event == 'Exit':
        frm.close()  # <= ensures proper closing of the sqlite database and runs a database optimization
        win.close()
        break
    elif ss.process_events(event, values):  # <=== let PySimpleSQL process its own events! Simple!
        logger.info(f'PySimpleDB event handler handled the event {event}!')
    else:
        logger.info(f'This event ({event}) is not yet handled.')
