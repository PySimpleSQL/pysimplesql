# To keep examples concise, avoid Black formatting. Remove # fmt: off to use Black formatting.
# fmt: off

import PySimpleGUI as sg
import pysimplesql as ss                               # <=== PySimpleSQL lines will be marked like this.  There's only a few!
import logging
logger=logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)               # <=== You can set the logging level here (NOTSET,DEBUG,INFO,WARNING,ERROR,CRITICAL)

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
    "id" INTEGER PRIMARY KEY AUTOINCREMENT, --M2M dataset still need a primary key
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
    [ss.selector('Person', size=(48, 10), key='sel_person')],
    [ss.actions('act_person', 'Person', edit_protect=False, search=False)],
    [ss.field('Person.name', label_above=True)]
]
color_layout=[
    [ss.selector('Color', size=(48, 10), key='sel_color')],
    [ss.actions('Color', 'act_color', edit_protect=False, search=False)],
    [ss.field('Color.name', label_above=True)]
]
headings=['ID (this will be hidden)','Person            ','Favorite Color     ']
vis=[0,1,1]
favorites_layout=[
    [ss.selector('FavoriteColor', sg.Table, key='sel_favorite', num_rows=10, headings=headings, visible_column_map=vis)],
    [ss.actions('act_favorites', 'FavoriteColor', edit_protect=False, search=False)],
    [ss.field('FavoriteColor.person_id', element=sg.Combo, size=(30, 10), label='Person:', auto_size_text=False)],
    [ss.field('FavoriteColor.color_id', element=sg.Combo, size=(30, 10), label='Color:', auto_size_text=False)]
]
layout=[
    [sg.Frame('Person Editor', layout=person_layout)],
    [sg.Frame('Color Editor', layout=color_layout)],
    [sg.Frame('Everyone can have multiple favorite colors!',layout=favorites_layout)]
]

# Initialize our window and database, then bind them together
win = sg.Window('Many-to-many table test', layout, finalize=True)
driver=ss.Sqlite(':memory:', sql_commands=sql)
frm = ss.Form(driver, bind_window=win)  # <=== load the database into the Form
# NOTE: ":memory:" is a special database URL for in-memory databases


while True:
    event, values = win.read()

    if ss.process_events(event, values):                  # <=== let PySimpleSQL process its own events! Simple!
        logger.info(f'PySimpleDB event handler handled the event {event}')
    elif event == sg.WIN_CLOSED or event == 'Exit':
        frm.close()              # <= ensures proper closing of the sqlite database and runs a database optimization at close
        break
    else:
        logger.info(f'This event ({event}) is not yet handled.')
win.close()
