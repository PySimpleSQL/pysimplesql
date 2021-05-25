#Database Applications with PySimpleGUI 

This is a simple tutorial to show how easy database interaction can be by using PySImpleGUI and **pysimplesql** together.

***DISCLAIMER***: While the names are similar, PySimpleGUI and **pysimplesql** have no affiliation.  The **pysimplesql** 
project was inspired by PySimpleGUI however, and strives for the same ease-of-use!

##Lets get started!
For this tutorial, we are going to build a simple Journal/Diary application to show how quickly a database front end can
be realized. In this Journal, we are going to track the date, an entry, a title for the entry, and even allow the user to
select a mood for the day.

Lets first start with a database to work with.  If you're not a database expert, don't worry!  There are many tools available
to help you build your own databases - but I personally like to stick to raw SQL commands.

Create a file named "journal.sql" with the following contents:
```SQL
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
```

There are a couple of things to point out in the SQL above.  First, notice the FOREIGN KEY constraint.  This is what tells
**pysimplesql** what the relationships are in the database.  These can be manually mapped as well if you are working with
an already existing database that did not define it's foreign key constraints - but since we are starting fresh this is 
the best way to go. Also notice the DEFAULT title.  New records created with **pysimplesql** will use this when available.

Next, lets make sure we have both PySimpleGUI and pysimplesql installed:
```python
pip install PySimpleGUI
pip install pysimplesql

or 

pip3 install PySimpleGUI
pip3 install pysimplesql
```

Ok, now with the database and prerequisites out of the way, lets build our application.  I like to start with a rough version, then add features
later (data validation, etc.).  I'm going to use that approach here.  With that said, create a file "journal.py" with the 
following contents:
```python
# import PySimpleGUI and pysimplesql
import PySimpleGUI as sg
import pysimplesql as ss

# -------------------------
# CREATE PYSIMPLEGUI LAYOUT
# -------------------------
# Define the columns for the table selector
headings=['id','Date:              ','Mood:      ','Title:                                 ']
visible=[0,1,1,1] # Hide the id column
layout=[
    ss.selector('sel_journal','Journal',sg.Table,num_rows=10,headings=headings,visible_column_map=visible),
    ss.actions('act_journal','Journal'), # These are your database controls (Previous, Next, Save, Insert, etc!)
    ss.record('Journal.entry_date', label='Date:'),
    ss.record('Journal.mood_id', sg.Combo, label='My mood:', size=(30,10), auto_size_text=False),
    ss.record('Journal.title'),
    ss.record('Journal.entry', sg.MLine, size=(71,20))
]

win=sg.Window('Journal example', layout, finalize=True)
db=ss.Database(':memory:', win, sql_script='journal.sql') #<=== Here is the magic!
# Note:  ':memory:' is a special address for in-memory databases

# ---------
# MAIN LOOP
# ---------
while True:
    event, values = win.read()

    if db.process_events(event, values):                  # <=== let PySimpleSQL process its own events! Simple!
        print(f'pysimpledb event handler handled the event {event}!')
    elif event == sg.WIN_CLOSED or event == 'Exit':
        db=None              # <= ensures proper closing of the sqlite database and runs a database optimization
        break
    else:
        print(f'This event ({event}) is not yet handled.')

```
 Go ahead and run the program!