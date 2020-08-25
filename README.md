# PySimpleGUI User's Manual

## Python database front-ends for humans - Binds PySimpleGUI to sqlite3 (MySQL planned) databases for rapid, effortless database application development!

# Jump-Start

## Install

```
pip install pysimplegui
or
pip3 install pysimplegui
```

### This Code

```python
#!/usr/bin/python3
import PySimpleGUI as sg
import PySimpleSQL as ss                               # <=== PySimpleSQL lines will be marked like this.  There's only a few!

# Define our layout. We will use the ss.record convenience function to create the controls
layout = [
    ss.record('Restaurant', 'name'),
    ss.record('Restaurant', 'location'),
    ss.record('Restaurant', 'fkType', sg.Combo)]
sub_layout = [
    [sg.Listbox(values=(), size=(35, 10), key="SELECTOR.Item", select_mode=sg.LISTBOX_SELECT_MODE_SINGLE, enable_events=True),
    sg.Col(
        [ss.record('Item', 'name'),
         ss.record('Item', 'fkMenu', sg.Combo),
         ss.record('Item', 'price'),
         ss.record('Item', 'description', sg.MLine, (30, 7))
         ])],
    ss.record_actions('Item', False)
]
layout += [[sg.Frame('Items', sub_layout)]]
layout += [ss.record_navigation('Restaurant',protect=True,search=True,save=True)]

# Initialize our window and database, then bind them together
win = sg.Window('places to eat', layout, finalize=True)
db = ss.Database(':memory:', 'example2.sql', win)      # <=== load the database and bind it to the window

while True:
    event, values = win.read()
    if db.process_events(event, values):                  # <=== let PySimpleSQL process its own events! Simple!
        print('PySimpleDB event handler handled the event!')
    elif event == sg.WIN_CLOSED or event == 'Exit':
        break
    else:
        print(f'This event ({event}) is not yet handled.')
```
### Makes This fully operational database front-end

![image](https://user-images.githubusercontent.com/70232210/91227678-e8c73700-e6f4-11ea-83ee-4712e687bfb4.png)

### Any Questions?  It's that simple.

To get the easiest experience with PySimpleSQL, the magic is in the database creation.
The automatic functionality of PySimpleSQL relies on just a couple of things:
- foreign key constraints on the database tables
- a CASCADE ON UPDATE constraint on any tables that should automatically refresh in the GUI
See sample below:
- PySimpleGUI control keys need to be named {table}.{field} for automatic mapping.  Of course, manual mapping is supported as well. ss.record() is a convenience function/"custom control" to make adding records quick and easy!


```sql
CREATE TABLE "Book"(
    "pkBook" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    "title" TEXT,
    "author" TEXT
);
CREATE TABLE "Chapter"(
    "pkChapter" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    "title" TEXT,
    "fkBook" INTEGER,
    "startPage" INTEGER,
    -- SECRET SAUCE BELOW! If you have foreign key constraints set on the database,
    -- then PySimpleSQL will pick them up!
    -- note: ON UPDATE CASCADE only needed if you want automatic GUI refreshing
    -- (i.e. not every constraint needs them, like fields that will populate comboboxes for example)
    FOREIGN KEY(fkBook) REFERENCES Book(pkBook) ON UPDATE CASCADE
);```


