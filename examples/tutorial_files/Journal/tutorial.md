#Database Applications with PySimpleGUI 

This is a simple tutorial to show how easy database interaction can be by using PySImpleGUI and **pysimplesql** together.
For this tutorial, we are going to build a simple Journal/Diary application to show how quickly a database front end can
be realized. In this Journal, we are going to track the date, an entry, a title for the entry, and even allow the user to
select a mood for the day.

***DISCLAIMER***: While the names are similar, PySimpleGUI and **pysimplesql** have no affiliation.  The **pysimplesql** 
project was inspired by PySimpleGUI however, and strives for the same ease-of-use!

##Lets get started!
First, lets make sure we have both PySimpleGUI and pysimplesql installed:
```python
pip install PySimpleGUI
pip install pysimplesql
````
or 
```python
pip3 install PySimpleGUI
pip3 install pysimplesql
```





Ok, now with the prerequisites out of the way, lets build our application.  I like to start with a rough version, then add features
later (data validation, etc.).  I'm going to use that approach here.  With that said, create a file "journal.py" with the 
following contents (or get the file [here](https://raw.githubusercontent.com/PySimpleSQL/pysimplesql/master/examples/tutorial_files/scripts/v1/journal.py))
```python
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

# -------------------------
# CREATE PYSIMPLEGUI LAYOUT
# -------------------------
# Define the columns for the table selector
headings=['id','Date:              ','Mood:      ','Title:                                 ']
visible=[0,1,1,1] # Hide the id column
layout=[
    ss.selector('sel_journal','Journal',sg.Table,num_rows=10,headings=headings,visible_column_map=visible),
    ss.actions('act_journal','Journal', edit_protect=False), # These are your database controls (Previous, Next, Save, Insert, etc!)
    ss.record('Journal.entry_date', label='Date:'),
    ss.record('Journal.mood_id', sg.Combo, label='My mood:', size=(30,10), auto_size_text=False),
    ss.record('Journal.title'),
    ss.record('Journal.entry', sg.MLine, size=(71,20))
]

win=sg.Window('Journal example', layout, finalize=True)
db=ss.Database(':memory:', win, sql_commands=sql) #<=== Here is the magic!
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
![v1](https://github.com/PySimpleSQL/pysimplesql/raw/master/examples/tutorial_files/Journal/v1/journal.png)
The code above is all you need for a quick database front end!  If you're not a database expert, don't worry!  Don't let
the embedded SQL in this example scare you. There are many tools available to help you build your own databases - but I 
personally like to stick to raw SQL commands.  Also keep in mind that SQL code does not have to be embedded, as it can be
loaded externally as well. Existing databases won't even need any of this SQL at all! With that said, 
There are a couple of things to point out in the SQL above.  First, notice the FOREIGN KEY constraint.  This is what tells
**pysimplesql** what the relationships are in the database.  These can be manually mapped as well if you are working with
an already existing database that did not define it's foreign key constraints - but since we are starting fresh this is 
the best way to go. Also notice the DEFAULT title.  New records created with **pysimplesql** will use this when available.


 Go ahead and run the program!  **It's literally a fully functioning program already** - though we will add onto it to improve
 things a bit.  Make a few entries by using the insert button to create them.  Notice that at first the elements are disabled,
 as there is no record yet selected. This all happens automatically! Explore the interface a bit too to get familiar with
how everything works.  **pysimplesql** was even smart enough to put an edit button next to the mood combo box so that new
moods can be created or existing ones edited or deleted (see below).
![quick editor](https://github.com/PySimpleSQL/pysimplesql/raw/master/examples/tutorial_files/Journal/v1/quick_edit.png)

 
## Next improvement - cleaning up the interface
The first iteration of our design is already working and functional.  In this improvement, we will fine-tune the GUI to 
be just a bit cleaner. Mainly, we will fix two issues that stick out to me:
- The title input element would look nice if it were as wide as the entry MLine element
- The sorting in the table selector would be nice if it were reversed so that new entries appeared at the top rather than
the bottom. 
- The search function only searches in the title column
  
See code below for the simple changes to make these fixes happen (or get the file [here](https://raw.githubusercontent.com/PySimpleSQL/pysimplesql/master/examples/tutorial_files/scripts/v2/journal.py)):
```python
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

# -------------------------
# CREATE PYSIMPLEGUI LAYOUT
# -------------------------
# Define the columns for the table selector
headings=['id','Date:              ','Mood:      ','Title:                                 ']
visible=[0,1,1,1] # Hide the id column
layout=[
    ss.selector('sel_journal','Journal',sg.Table,num_rows=10,headings=headings,visible_column_map=visible),
    ss.actions('act_journal','Journal', edit_protect=False), # These are your database controls (Previous, Next, Save, Insert, etc!)
    ss.record('Journal.entry_date', label='Date:'),
    ss.record('Journal.mood_id', sg.Combo, label='My mood:', size=(30,10), auto_size_text=False),
    ss.record('Journal.title', size=(71,1)),
    ss.record('Journal.entry', sg.MLine, size=(71,20))
]

win=sg.Window('Journal example', layout, finalize=True)
db=ss.Database(':memory:', win, sql_commands=sql) #<=== Here is the magic!
# Note:  ':memory:' is a special address for in-memory databases

# Reverse the default sort order so new journal entries appear at the top
db['Journal'].set_order_clause('ORDER BY entry_date DESC')
# Set the column order for search operations.  By default, only the column designated as the description column is searched
db['Journal'].set_search_order(['entry_date','title','entry'])

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
![v2](https://github.com/PySimpleSQL/pysimplesql/raw/master/examples/tutorial_files/Journal/v2/journal.png)

Now that's better!  Now the interface looks a little cleaner, the sorting of the selector table looks better and the search 
function is much more usable!

## Next improvement - persistance of the data
Up until now, the database has been created in-memory.  In-memory databases wipe clean after each use, and therefore would
be a pretty poor choice for a Journal application!  We will now fix that issue and start saving the data to the hard drive.

See code below for the changes to make our data persistent! (or get the file [here](https://raw.githubusercontent.com/PySimpleSQL/pysimplesql/master/examples/tutorial_files/scripts/v3/journal.py)):

```python
# import PySimpleGUI and pysimplesql
import PySimpleGUI as sg
import pysimplesql as ss

# --------------------------
# CREATE OUR DATABASE SCHEMA
# --------------------------
# Note that databases can be created from files as well instead of just embedded commands, as well as existing databases.
sql = """
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

# -------------------------
# CREATE PYSIMPLEGUI LAYOUT
# -------------------------
# Define the columns for the table selector
headings = ['id', 'Date:              ', 'Mood:      ', 'Title:                                 ']
visible = [0, 1, 1, 1]  # Hide the id column
layout = [
 ss.selector('sel_journal', 'Journal', sg.Table, num_rows=10, headings=headings, visible_column_map=visible),
 ss.actions('act_journal', 'Journal', edit_protect=False),
 # These are your database controls (Previous, Next, Save, Insert, etc!)
 ss.record('Journal.entry_date', label='Date:'),
 ss.record('Journal.mood_id', sg.Combo, label='My mood:', size=(30, 10), auto_size_text=False),
 ss.record('Journal.title', size=(71, 1)),
 ss.record('Journal.entry', sg.MLine, size=(71, 20))
]

win = sg.Window('Journal example', layout, finalize=True)
db = ss.Database('../../journal.db', win, sql_commands=sql)  # <=== ONE SIMPLE CHANGE!!!
# Now we just give the new databasase a name - "journal.db" in this case.  If journal.db is not present
# when this code is run, then a new one is created using the commands supplied to the sql_commands keyword argument.
# If journal.db does exist, then it is used and the sql_commands are not run at all.

# Reverse the default sort order so new journal entries appear at the top
db['Journal'].set_order_clause('ORDER BY entry_date DESC')
# Set the column order for search operations.  By default, only the column designated as the description column is searched
db['Journal'].set_search_order(['entry_date', 'title', 'entry'])

# ---------
# MAIN LOOP
# ---------
while True:
 event, values = win.read()

 if db.process_events(event, values):  # <=== let PySimpleSQL process its own events! Simple!
  print(f'pysimpledb event handler handled the event {event}!')
 elif event == sg.WIN_CLOSED or event == 'Exit':
  db = None  # <= ensures proper closing of the sqlite database and runs a database optimization
  break
 else:
  print(f'This event ({event}) is not yet handled.')
```
![v3](https://github.com/PySimpleSQL/pysimplesql/raw/master/examples/tutorial_files/Journal/v3/journal.png)

Go ahead and run the program now, make some new entries and save them.  Close and reopen the program and you'll see that
data is now persisting on the hard drive!

## Next improvment - Data Validation
Right now, the user can type pretty much anything for the date.  We should fix this to ensure that dates entered are uniform
and sort correctly.  We will use the before_save callback to validate this data.  If our callback returns True, then the
save will be allowed to proceed.

See code below for the changes to validate our data! (or get the file [here](https://raw.githubusercontent.com/PySimpleSQL/pysimplesql/master/examples/tutorial_files/scripts/v4/journal.py)):
```python
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

# -------------------------
# CREATE PYSIMPLEGUI LAYOUT
# -------------------------
# Define the columns for the table selector
headings=['id','Date:              ','Mood:      ','Title:                                 ']
visible=[0,1,1,1] # Hide the id column
layout=[
    ss.selector('sel_journal','Journal',sg.Table,num_rows=10,headings=headings,visible_column_map=visible),
    ss.actions('act_journal','Journal', edit_protect=False), # These are your database controls (Previous, Next, Save, Insert, etc!)
    ss.record('Journal.entry_date', label='Date:'),
    ss.record('Journal.mood_id', sg.Combo, label='My mood:', size=(30,10), auto_size_text=False),
    ss.record('Journal.title', size=(71,1)),
    ss.record('Journal.entry', sg.MLine, size=(71,20))
]

win=sg.Window('Journal example', layout, finalize=True)
db=ss.Database('journal.db', win, sql_commands=sql) #<=== ONE SIMPLE CHANGE!!!
# Now we just give the new databasase a name - "journal.db" in this case.  If journal.db is not present
# when this code is run, then a new one is created using the commands supplied to the sql_commands keyword argument.
# If journal.db does exist, then it is used and the sql_commands are not run at all.

# Reverse the default sort order so new journal entries appear at the top
db['Journal'].set_order_clause('ORDER BY entry_date DESC')
# Set the column order for search operations.  By default, only the column designated as the description column is searched
db['Journal'].set_search_order(['entry_date','title','entry'])

# ---------------
# DATA VALIDATION
# ---------------
def cb_validate():
    date=win['Journal.entry_date'].Get()
    if date[4] == '-' and date[7]=='-' and len(date)==10:   # Make sure the date is 10 digits and has two dashes in the right place
        if str.isdigit(date[:4]):                           # Make sure the first 4 digits represent a year
            if str.isdigit(date[5:7]):                      # Make sure the month are digits
                if str.isdigit(date[-2:]):                  # Make sure the days are digits
                    return True                             # If so, we can save!

    # Validation failed!  Deny saving of changes!
    sg.popup('Invalid date specified! Please try again')
    return False

#  Set the callback to run before save
db['Journal'].set_callback('before_save',cb_validate)

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
![v4](https://github.com/PySimpleSQL/pysimplesql/raw/master/examples/tutorial_files/Journal/v4/journal.png)

Now run the example again.  You can now see that we are validating our expected date format using the simple callback 
features of **pysimplesql**!

# LEARNINGS FROM THIS TUTORIAL
- How to install and import **pysimplesql** into your project
- How to use the FOREIGN KEY and DEFAULT constraints in your SQL schema
- How to embed SQL schema code right in your program
- using the ss.record(), ss.selector() and ss.actions convenience functions to simplify construction of your PySimpleGUI
layouts and ensure they work automatically with **pysimplesql**
- How to change default control size with the size=(w,h) keyword argument to ss.record()
- How to change sort order of tables with db[table].set_order_clause()
- How to change the search order of tables with db[table].set_search_order()]
- How to use the callback system to create a simple validation callback

Any ideas on improvements for this tutorial of the simple Journal application?  Just drop an email to pysimplesql@gmail.com!