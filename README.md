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
- PySimpleGUI control keys need to be named {table}.{field} for automatic mapping.  Of course, manual mapping is supported as well. ss.record() is a convenience function/"custom control" to make adding records quick and easy!
- The field 'name', (or the 2nd parameter in the absense of a 'name' field) is what will display in comboxes for foreing key relationships.  Of course, this can be changed manually if needed, but truly the simplictiy of PySimpleSQL is in having everything happen automatically!

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
);
```

### But wait, there's more!
The above is literally all you have to know for working with simple and even moderate databases.  However, there is a lot of power in learning what is going on under the hood!  Starting with the example above, we will work backwards to explain what is available to you for more control.

#### PySimpleGUI elements:
Referencing the example above, look at the following:
```python
# convience function for rapid front-end development
ss.record('Restaurant', 'name') # Table name, field name parameters

# could have been written like this:
[sg.Text('Name:',size=(15,1)),sg.Input('',key='Restaurant.name',size=(30,1))]
```
As you can see, the ss.record() convenience function simplifies making record controls that adhere to the PySimpleSQL naming convention of Table.field.
In fact, there is even more you can do with this. The ss.record() function can take a PySimpleGUI control element as a parameter as well, overriding the defaul Input() element.
See this code which creates a combobox instead:
```python
ss.record('Restaurant', 'fkType', sg.Combo)]
```
If you remember from the code above, the database had a constraint on Restaurant.fkType to Type.pkType.  This means that PySimpleSQL will automatically handle updating this combobox element with all of the entries from the Type table!
Furthering that, the functions ss.set_default_text_size() and ss.set_default_control_size() can be used before calls to ss.record() to have custom sizing of the control elements.  Even with these defaults set, the size parameter of record() will override the default control size, for plenty of flexibility!
