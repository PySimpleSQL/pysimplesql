#!/usr/bin/python3
import PySimpleGUI as sg
import pysimplesql as ss                               # <=== PySimpleSQL lines will be marked like this.  There's only a few!
import logging
logger=logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)               # <=== You can set the logging level here (NOTSET,DEBUG,INFO,WARNING,ERROR,CRITICAL)

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
Navigation buttons, the Search box, ListBoxes, ComboBoxes, Sliders and tables can all be set to control
record navigation. Multiple selectors can be used simultaneously and they will all work together in harmony. Try each selector
on this form and watch it all just work!
"""

# PySimpleGUI™ layout code
headings=['id','Name     ','Example                                          ','Primary Color?'] # Table column widths can be set by the spacing of the headings!
visible=[0,1,1,1] # Hide the primary key column in the table
record_columns=[
    ss.record('Colors.name',label='Color name:'),
    ss.record('Colors.example',label='Example usage: '),
    ss.record('Colors.primary_color',label= 'Primary Color?',element=sg.CBox),
]
selectors=[
    ss.selector('tableSelector', 'Colors', element=sg.Table, headings=headings, visible_column_map=visible,num_rows=10)+
    ss.selector('selector1','Colors', size=(15,10)),
    ss.actions('colorActions','Colors'),
    ss.selector('selector2','Colors',element=sg.Slider,size=(26,18))+ss.selector('selector3','Colors',element=sg.Combo, size=(30,10)),
]
layout = [
    [sg.Text(description)],
    [sg.Frame('Test out all of these selectors and watch the magic!',selectors)],
    [sg.Col(record_columns,vertical_alignment='t')],
]

win=sg.Window('Record Selector Demo', layout, finalize=True)
db=ss.Database(':memory:', win, sql_commands=sql) #<=== Here is the magic!
# note: Since win was passed as a parameter, binding is automatic (including event mapping!)
# Also note, in-memory databases can be created with ":memory:"!

db['Colors'].set_search_order(['name','example']) # the search box will search in both the name and example columns
while True:
    event, values = win.read()

    if db.process_events(event, values):                  # <=== let PySimpleSQL process its own events! Simple!
        logger.info(f'PySimpleDB event handler handled the event {event}!')
    elif event == sg.WIN_CLOSED or event == 'Exit':
        db=None              # <= ensures proper closing of the sqlite database and runs a database optimization
        break
    else:
        logger.info(f'This event ({event}) is not yet handled.')