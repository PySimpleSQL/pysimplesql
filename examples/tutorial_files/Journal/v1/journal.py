# To keep examples concise, avoid Black formatting. Remove # fmt: off to use Black formatting.
# fmt: off

# import PySimpleGUI and pysimplesql
import PySimpleGUI as sg
import pysimplesql as ss


# --------------------------
# CREATE OUR DATABASE SCHEMA
# --------------------------
# Note that databases can be created from files as well instead of just embedded commands, as well as existing databases.
sql="""
CREATE TABLE Journal(
    "id"            INTEGER NOT NULL PRIMARY KEY,
    "entry_date"    INTEGER DEFAULT (date('now')),
    "mood_id"       INTEGER,
    "title"         TEXT DEFAULT "New Entry",
    "entry"         TEXT,
    FOREIGN KEY (mood_id) REFERENCES Mood(id) --This line is important to the automatic functionality of pysimplesql~
);
CREATE TABLE Mood(
    "id"            INTEGER NOT NULL PRIMARY KEY,
    "name"          TEXT
);

-- Lets pre-populate some moods into our database
-- The list doesn't need to be overdone, as the user will be able to add their own too!
INSERT INTO Mood VALUES (1,"Happy");
INSERT INTO Mood VALUES (2,"Sad");
INSERT INTO Mood VALUES (3,"Angry");
INSERT INTO Mood VALUES (4,"Emotional");
INSERT INTO Mood VALUES (5,"Content");
INSERT INTO Mood VALUES (6,"Curious");
"""
frm= ss.Form(':memory:')  #<=== Here is the magic!
# Note:  ':memory:' is a special address for in-memory databases

# -------------------------
# CREATE PYSIMPLEGUI LAYOUT
# -------------------------
# Define the columns for the table selector
headings=['id','Date:              ','Mood:      ','Title:                                 '] # The width of the headings defines column width!
visible=[0,1,1,1] # Hide the id column
layout=[
    frm.selector('sel_journal','Journal',sg.Table,num_rows=10,headings=headings,visible_column_map=visible),
    frm.actions('act_journal','Journal', edit_protect=False), # These are your database controls (Previous, Next, Save, Insert, etc!)
    frm.record('Journal.entry_date', label='Date:'),
    frm.record('Journal.mood_id', sg.Combo, label='My mood:', size=(30,10), auto_size_text=False),
    frm.record('Journal.title'),
    frm.record('Journal.entry', sg.MLine, size=(71,20))
]

win=sg.Window('Journal example', layout, finalize=True)
frm.bind(win)

# ---------
# MAIN LOOP
# ---------
while True:
    event, values = win.read()

    if ss.process_events(event, values):                  # <=== let PySimpleSQL process its own events! Simple!
        print(f'pysimpledb event handler handled the event {event}!')
    elif event == sg.WIN_CLOSED or event == 'Exit':
        frm.close()              # <= ensures proper closing of the sqlite database and runs a database optimization
        break
    else:
        print(f'This event ({event}) is not yet handled.')
win.close()
