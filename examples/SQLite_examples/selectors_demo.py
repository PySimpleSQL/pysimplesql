# To keep examples concise, avoid Black formatting. Remove # fmt: off to use Black formatting.
# fmt: off

import PySimpleGUI as sg
import pysimplesql as ss                               # <=== PySimpleSQL lines will be marked like this.  There's only a few!
import logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)  # <=== You can set the logging level here (NOTSET,DEBUG,INFO,WARNING,ERROR,CRITICAL)

# Create a small table just for demo purposes. In your own program, you would probably
# use a pre-made database on the filesystem instead.
sql='''
CREATE TABLE "Colors"(
    "id" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    "name" TEXT DEFAULT "New Color",
    "example" TEXT,
    "primary_color" INTEGER DEFAULT 0
);
INSERT INTO "Colors" ("name","example","primary_color") VALUES ("Orange","Traffic cones are orange.",0);
INSERT INTO "Colors" ("name","example","primary_color") VALUES ("Green","Grass is green.",0);
INSERT INTO "Colors" ("name","example","primary_color") VALUES ("Red","Apples are red.",1);
INSERT INTO "Colors" ("name","example","primary_color") VALUES ("Purple","Plums are purple.",0);
INSERT INTO "Colors" ("name","example","primary_color") VALUES ("Brown","Dirt is brown.",0);
INSERT INTO "Colors" ("name","example","primary_color") VALUES ("Black","Black is the absense of all color.",0);
INSERT INTO "Colors" ("name","example","primary_color") VALUES ("Yellow","Bananas are yellow.",1);
INSERT INTO "Colors" ("name","example","primary_color") VALUES ("White","White is the presence of all color",0);
INSERT INTO "Colors" ("name","example","primary_color") VALUES ("Blue","The ocean is blue",1);
'''

description = """
Many different types of PySimpleGUI elements can be used as Selector controls to select database records.
Navigation buttons, the Search box, ListBoxes, ComboBoxes, Sliders and dataset can all be set to control
record navigation. Multiple selectors can be used simultaneously and they will all work together in harmony.
Try each selector on this frm and watch it all just work!
"""

# PySimpleGUI™ layout code
table_builder = ss.TableBuilder(num_rows=10)
table_builder.add_column('name', 'Name', width=10)
table_builder.add_column('example', 'Example', width=40)
table_builder.add_column('primary_color', 'Primary Color?', width=15)

record_columns = [
    [ss.field('Colors.name', label='Color name:')],
    [ss.field('Colors.example', label='Example usage: ')],
    [ss.field('Colors.primary_color', element=sg.CBox, label='Primary Color?')],
]
selectors = [
    [ss.selector('Colors', element=table_builder, key='tableSelector')],
    [ss.selector('Colors', size=(15, 10), key='selector1')],
    [ss.selector('Colors', element=sg.Slider, size=(26, 18), key='selector2'),
     ss.selector('Colors', element=sg.Combo, size=(30, 10), key='selector3')],


]
layout = [
    [sg.Text(description)],
    [sg.Frame('Test out all of these selectors and watch the magic!', selectors)],
    [sg.Col(record_columns,vertical_alignment='t')],
    [ss.actions('Colors', 'colorActions')]
]

win = sg.Window('Record Selector Demo', layout, finalize=True)
driver = ss.Driver.sqlite(':memory:', sql_commands=sql)
frm= ss.Form(driver, bind_window=win)  # <=== Here is the magic!

frm['Colors'].set_search_order(['name', 'example'])  # the search box will search in both the name and example columns
while True:
    event, values = win.read()

    if ss.process_events(event, values):  # <=== let PySimpleSQL process its own events! Simple!
        logger.info(f'PySimpleDB event handler handled the event {event}!')
    elif event == sg.WIN_CLOSED or event == 'Exit':
        frm.close()   # <= ensures proper closing of the sqlite database and runs a database optimization
        break
    else:
        logger.info(f'This event ({event}) is not yet handled.')
win.close()
