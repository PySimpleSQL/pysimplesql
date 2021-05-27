import PySimpleGUI as sg
import pysimplesql as ss                               # <=== PySimpleSQL lines will be marked like this.  There's only a few!
import logging
logger=logging.getLogger(__name__)
logging.basicConfig(level=logging.CRITICAL)               # <=== You can set the logging level here (NOTSET,DEBUG,INFO,WARNING,ERROR,CRITICAL)

sql="""
CREATE TABLE "Settings"(
    "id" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
	"key" TEXT,
	"value" TEXT
);
INSERT INTO SETTINGS VALUES (1,'company_name','My company');
INSERT INTO SETTINGS VALUES (2,'debug_mode',True);
INSERT INTO SETTINGS VALUES (3,'antialiasing', True);
INSERT INTO SETTINGS VALUES (4, 'query_retries', 3);
"""

layout=[
    [sg.Text('APPLICATION SETTINGS')],
    [sg.HorizontalSeparator()],
    ss.record('Settings.value?key=company_name'),
    ss.record('Settings.value?key=debug_mode',sg.CBox),
    ss.record('Settings.value?key=antialiasing', sg.CBox),
    ss.record('Settings.value?key=query_retries'),
    ss.actions('nav','Settings',default=False, save=True)
]

# Initialize our window and database, then bind them together
win = sg.Window('Key,Value Example', layout, finalize=True)
db = ss.Database('kv.db', win, sql_commands=sql)      # <=== load the database and bind it to the window
# NOTE: ":memory:" is a special database URL for in-memory databases

while True:
    event, values = win.read()

    if db.process_events(event, values):                  # <=== let PySimpleSQL process its own events! Simple!
        logger.info('PySimpleDB event handler handled the event!')
    elif event == sg.WIN_CLOSED or event == 'Exit':
        db=None              # <= ensures proper closing of the sqlite database and runs a database optimization at close
        break
    else:
        logger.info(f'This event ({event}) is not yet handled.')