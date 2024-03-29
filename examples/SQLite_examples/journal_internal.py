# To keep examples concise, avoid Black formatting. Remove # fmt: off to use Black formatting.
# fmt: off

import PySimpleGUI as sg
import pysimplesql as ss  # <=== PySimpleSQL lines will be marked like this.  There's only a few!
import logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)  # <=== Set the logging level here (NOTSET,DEBUG,INFO,WARNING,ERROR,CRITICAL)

# -------------------------------------
# CREATE A SIMPLE DATABASE TO WORK WITH
# -------------------------------------
sql = """
DROP TABLE IF EXISTS Journal;
DROP TABLE IF EXISTS Mood;

CREATE TABLE Journal(
    "id"            INTEGER NOT NULL PRIMARY KEY,
    "title"         TEXT DEFAULT 'New Entry',
    "entry_date"    DATE NOT NULL DEFAULT (date('now')),
    "mood_id"       INTEGER NOT NULL,
    "entry"         TEXT,
    FOREIGN KEY (mood_id) REFERENCES Mood(id) --This line is important to the automatic functionality of PySimpleSQL~
);
CREATE TABLE Mood(
    "id"            INTEGER NOT NULL PRIMARY KEY,
    "name"          TEXT
);
INSERT INTO Mood VALUES (1,'Happy');
INSERT INTO Mood VALUES (2,'Sad');
INSERT INTO Mood VALUES (3,'Angry');
INSERT INTO Mood VALUES (4,'Content');
INSERT INTO Journal (id, entry_date, mood_id, title, entry) VALUES (1, '2023-02-05', 1, 'Research Started!','I am excited to start my research on a large data');
INSERT INTO Journal (id, entry_date, mood_id, title, entry) VALUES (2, '2023-02-06', 2, 'Unexpected result!', 'The experiment yielded a result that was not at all what I expected.');
INSERT INTO Journal (id, entry_date, mood_id, title, entry) VALUES (3, '2023-02-06', 1, 'Eureka!', 'I think I have discovered something amazing. Need to run more tests to confirm.');
INSERT INTO Journal (id, entry_date, mood_id, title, entry) VALUES (4, '2023-02-07', 4, 'Serendipity', 'Sometimes the best discoveries are made by accident.');
INSERT INTO Journal (id, entry_date, mood_id, title, entry) VALUES (5, '2023-02-07', 3, 'Unexpected complication', 'The experiment had an unexpected complication that may affect the validity of the results.');
INSERT INTO Journal (id, entry_date, mood_id, title, entry) VALUES (6, '2023-02-07', 2, 'Need more data', 'The initial results are promising, but I need more data to confirm my hypothesis.');
INSERT INTO Journal (id, entry_date, mood_id, title, entry) VALUES (7, '2023-02-08', 1, 'Feeling optimistic', 'I have a good feeling about the experiment. Will continue with the tests.');
INSERT INTO Journal (id, entry_date, mood_id, title, entry) VALUES (8, '2023-02-08', 4, 'Implications for industry', 'If my discovery holds up, it could have huge implications for the industry.');
INSERT INTO Journal (id, entry_date, mood_id, title, entry) VALUES (9, '2023-02-08', 3, 'Need to rethink approach', 'The initial approach did not yield the desired results. Will need to rethink my strategy.');
INSERT INTO Journal (id, entry_date, mood_id, title, entry) VALUES (10, '2023-02-09', 2, 'Long way to go', 'I have a long way to go before I can confidently say that I have made a significant discovery.');
INSERT INTO Journal (id, entry_date, mood_id, title, entry) VALUES (11, '2023-02-09', 1, 'Small breakthrough', 'I had a small breakthrough today. It is a step in the right direction.');
INSERT INTO Journal (id, mood_id, title, entry) VALUES (12, 4, 'I Found the Solution!', 'I can finally stop worrying about SQL syntax and focus on my research. pysimplesql is the best Python library for working with databases, and it saved me so much time and effort!');

"""

# -------------------------
# CREATE PYSIMPLEGUI LAYOUT
# -------------------------
# Define the columns for the table selector using the TableHeading convenience class.
table_builder = ss.TableBuilder(
    num_rows = 10,
    sort_enable=True, # Click a header to sort
    allow_cell_edits=True, # Double-click a cell to make edits
    style=ss.TableStyler(row_height=25)
    )
table_builder.add_column('title', 'Title', width=40)
table_builder.add_column('entry_date', 'Date', width=10)
table_builder.add_column('mood_id', 'Mood', width=20)

layout = [
    [ss.selector('Journal', table_builder)],
    [ss.actions('Journal')],
    [ss.field('Journal.entry_date'),
        sg.CalendarButton(
            "Select Date", close_when_date_chosen=True, target="Journal.entry_date",  # <- target matches field() name
            format="%Y-%m-%d", size=(10, 1), key='datepicker'
        )
    ],
    [ss.field('Journal.mood_id', sg.Combo, size=(30, 10), label='My mood:', auto_size_text=False)],
    [ss.field('Journal.title')],
    [ss.field('Journal.entry', sg.MLine, size=(71, 20))]
]
win = sg.Window('Journal (internal) example', layout, finalize=True)
driver = ss.Driver.sqlite('Journal.db', sql_commands=sql)
# Here is the magic!
frm = ss.Form(
    driver,
    bind_window=win,
    live_update=True # this updates the `Selector`, sg.Table as we type in fields!
    )
# Note:  sql_commands in only run if Journal.db does not exist!  This has the effect of creating a new blank
# database as defined by the sql_commands if the database does not yet exist, otherwise it will use the database!

# Reverse the default sort order so new journal entries appear at the top
frm['Journal'].set_order_clause('ORDER BY entry_date ASC')
# Set the column order for search operations.  By default, only the designated description column is searched
frm['Journal'].set_search_order(['entry_date', 'title', 'entry'])
# Requery the data since we made changes to the sort order
frm['Journal'].requery()

# ------------------------------------------
# How to Edit Protect your sg.CalendarButton
# ------------------------------------------
# By default, action() includes an edit_protect() call, that disables edits in the window.
# You can toggle it off with:
frm.edit_protect()  # Comment this out to edit protect elements when the window is created.
# Set initial CalendarButton state to the same as pysimplesql elements
win['datepicker'].update(disabled=frm.get_edit_protect())
# Then watch for the 'edit_protect' event in your Main Loop

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
        if "edit_protect" in event:
            win['datepicker'].update(disabled=frm.get_edit_protect())
    else:
        logger.info(f'This event ({event}) is not yet handled.')

"""
I hope that you enjoyed this simple demo of a Journal database.
Without comments and embedded SQL script, this could have been done in well under 50 lines of code! Seriously - a full
database-backed usable program! The combination of PySimpleSQL and PySimpleGUI is very fun, fast and powerful!

Learnings from this example:
- Using DataSet.set_search_order() to set the search order of the query for search operations.
- embedding sql commands in code for table creation
- creating a default/empty database with sql commands with the sql_commands keyword argument to ss.Form()
- using Form.record() and Form.selector() functions for easy GUI element creation
- using the label keyword argument to Form.record() to define a custom label
- using Tables as Form.selector() element types
- changing the sort order of database dataset
- Adding and edit-protecting a sg.CalendarButton
"""
