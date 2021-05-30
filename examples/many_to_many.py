import PySimpleGUI as sg
import pysimplesql as ss                               # <=== PySimpleSQL lines will be marked like this.  There's only a few!
import logging
logger=logging.getLogger(__name__)
logging.basicConfig(level=logging.CRITICAL)               # <=== You can set the logging level here (NOTSET,DEBUG,INFO,WARNING,ERROR,CRITICAL)

sql='''
CREATE TABLE "Color"(
    "id" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
	"name" TEXT DEFAULT "New Color"
);
CREATE TABLE "Person"(
    'id' INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    "name" TEXT DEFAULT "New Person"
);
CREATE TABLE "FavoriteColor"(
    "id" INTEGER PRIMARY KEY AUTOINCREMENT, --M2M tables still need a primary key
    "person_id" INTEGER NOT NULL DEFAULT 1,
    "color_id" INTEGER NOT NULL DEFAULT 1,
    FOREIGN KEY (person_id) REFERENCES Person(id),
    FOREIGN KEY (color_id) REFERENCES Color(id)
);

INSERT INTO "Color" ("name") VALUES ("Orange");
INSERT INTO "Color" ("name") VALUES ("Green");
INSERT INTO "Color" ("name") VALUES ("Red");
INSERT INTO "Color" ("name") VALUES ("Purple");
INSERT INTO "Color" ("name") VALUES ("Brown");
INSERT INTO "Color" ("name") VALUES ("Black");
INSERT INTO "Color" ("name") VALUES ("Yellow");
INSERT INTO "Color" ("name") VALUES ("White");
INSERT INTO "Color" ("name") VALUES ("Blue");

INSERT INTO "Person" ("name") VALUES ("Jim");
INSERT INTO "Person" ("name") VALUES ("Sally");
INSERT INTO "Person" ("name") VALUES ("Pat");

INSERT INTO "FavoriteColor" VALUES (1,1,1);
INSERT INTO "FavoriteColor" VALUES (2,1,2);
INSERT INTO "FavoriteColor" VALUES (3,1,4);
INSERT INTO "FavoriteColor" VALUES (4,2,3);
INSERT INTO "FavoriteColor" VALUES (5,2,5);
INSERT INTO "FavoriteColor" VALUES (6,2,6);
INSERT INTO "FavoriteColor" VALUES (7,3,7);
INSERT INTO "FavoriteColor" VALUES (8,3,6);
INSERT INTO "FavoriteColor" VALUES (9,3,4);
'''

person_layout=[
    ss.selector('sel_person','Person', size=(48,10)),
    ss.actions('act_person','Person',edit_protect=False, search=False),
    ss.record('Person.name', label_above=True)
]
color_layout=[
    ss.selector('sel_color','Color', size=(48,10)),
    ss.actions('act_color','Color',edit_protect=False, search=False),
    ss.record('Color.name', label_above=True)
]
headings=['ID (this will be hidden)','Person            ','Favorite Color     ']
vis=[0,1,1]
favorites_layout=[
    ss.selector('sel_favorite','FavoriteColor',sg.Table,num_rows=10,headings=headings,visible_column_map=vis),
    ss.actions('act_favorites','FavoriteColor',edit_protect=False, search=False),
    ss.record('FavoriteColor.person_id', label='Person:',element=sg.Combo, size=(30,10), auto_size_text=False),
    ss.record('FavoriteColor.color_id', label='Color:',element=sg.Combo, size=(30,10), auto_size_text=False)
]
layout=[
    [sg.Frame('Person Editor', layout=person_layout)],
    [sg.Frame('Color Editor', layout=color_layout)],
    [sg.Frame('Everyone can have multiple favorite colors!',layout=favorites_layout)]
]

# Initialize our window and database, then bind them together
win = sg.Window('Many-to-many table test', layout, finalize=True)
db = ss.Database(':memory:', win, sql_commands=sql)      # <=== load the database and bind it to the window
# NOTE: ":memory:" is a special database URL for in-memory databases

while True:
    event, values = win.read()

    if ss.process_events(event, values):                  # <=== let PySimpleSQL process its own events! Simple!
        logger.info('PySimpleDB event handler handled the event!')
    elif event == sg.WIN_CLOSED or event == 'Exit':
        db=None              # <= ensures proper closing of the sqlite database and runs a database optimization at close
        break
    else:
        logger.info(f'This event ({event}) is not yet handled.')