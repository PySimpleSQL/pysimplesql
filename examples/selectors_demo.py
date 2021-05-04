#!/usr/bin/python3
import PySimpleGUI as sg
import pysimplesql as ss                               # <=== PySimpleSQL lines will be marked like this.  There's only a few!
print(sg.sys.version)
# Create a small table just for demo purposes. In your own program, you would probably
# use a premade database on the filesystem instead.
sql='''
CREATE TABLE "Colors"(
    "id" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
	"name" TEXT DEFAULT "New Fruit",
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

# PySimpleGUI™ layout code to create your own navigation buttons
record_columns=[
    ss.record("Colors",'name',label='Color name:'),
    ss.record("Colors","example",label="Example usage:"),
    ss.record("Colors",'primary_color',label="Primary Color?",control=sg.CBox),
]

layout = [
    ss.selector("Colors", size=(10,10))+[sg.Col(record_columns,vertical_alignment='t')],
    ss.actions("Colors"),
    ss.selector("Colors",control=sg.Slider,size=(50,18))+ss.selector("Colors",control=sg.Combo)
]

win=sg.Window('Record Selector Demo', layout, finalize=True)
# note: Since win was passed as a parameter, binding is automatic (including event mapping!)
# Also note, in-memory databases can be created with ":memory:"!
db=ss.Database(':memory:', win, sql_commands=sql)



while True:
    event, values = win.read()
    # Manually handle our record selector events, bypassing the event mapper completely
    if db.process_events(event, values):                  # <=== let PySimpleSQL process its own events! Simple!
        print(f'PySimpleDB event handler handled the event {event}!')
    elif event == sg.WIN_CLOSED or event == 'Exit':
        db=None              # <= ensures proper closing of the sqlite database and runs a database optimization
        break
    else:
        print(f'This event ({event}) is not yet handled.')