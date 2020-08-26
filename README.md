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
along with this sqlite table
```sql
DROP TABLE IF EXISTS "Restaurant";
DROP TABLE IF EXISTS "Item";
DROP TABLE IF EXISTS "Type";
DROP TABLE IF EXISTS "Menu";

CREATE TABLE "Restaurant"(
	"pkRestaurant" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
	"name" TEXT DEFAULT "New Restaurant",
	"location" TEXT,
	"fkType" INTEGER,
	FOREIGN KEY(fkType) REFERENCES Type(pkType)
);

CREATE TABLE "Item"(
	"pkItem" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
	"name" TEXT DEFAULT "New Item",
	"fkRestaurant" INTEGER,
	"fkMenu" INTEGER,
	"price" TEXT,
	"description" TEXT,
	FOREIGN KEY(fkRestaurant) REFERENCES Restaurant(pkRestaurant) ON UPDATE CASCADE,
	FOREIGN KEY(fkMenu) REFERENCES Menu(pkMenu)
);

CREATE TABLE "Type"(
	"pkType" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
	"name" TEXT DEFAULT "New Type"
);

CREATE TABLE "Menu"(
	"pkMenu" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
	"name" TEXT DEFAULT "New Menu"
);

INSERT INTO "Menu" VALUES (1,"Breakfast");
INSERT INTO "Menu" VALUES (2,"Lunch");
INSERT INTO "Menu" VALUES (3,"Dinner");

INSERT INTO "Type" VALUES (1,"Fast Food");
INSERT INTO "Type" VALUES (2,"Fine Dining");
INSERT INTO "Type" VALUES (3,"Hole in the wall");
INSERT INTO "Type" VALUES (4,"Chinese Food");

INSERT INTO "Restaurant" VALUES (1,"McDonalds","Seatle WA",1);
INSERT INTO "Item" VALUES (1,"Hamburger",1,2,"$4.99","Not flame broiled");
INSERT INTO "Item" VALUES (2,"Cheeseburger",1,2,"$5.99","With or without pickles");
INSERT INTO "Item" VALUES (3,"Big Breakfast",1,1,"$6.99","Your choice of bacon or sausage");

INSERT INTO "Restaurant" VALUES (2,"Chopstix","Cleveland OH",4);
INSERT INTO "Item" VALUES (4,"General Tso",2,3,"$7.99","Our best seller!");
INSERT INTO "Item" VALUES (5,"Teriaki Chicken",2,3,"$5.99","Comes on a stick");
INSERT INTO "Item" VALUES (6,"Sticky Rice",2,2,"$6.99","Our only lunch option, sorry!");

INSERT INTO "Restaurant" VALUES (3,"Jimbos","Lexington KY",3);
INSERT INTO "Item" VALUES (7,"Breakfast Pizza",3,1,"$11.99","Pizza in the morning");
INSERT INTO "Item" VALUES (8,"Lunch Pizza",3,3,"$12.99","Pizza at noon");
INSERT INTO "Item" VALUES (9,"Dinner Pizza",3,3,"$16.99","Whatever we did not sell earlier in the day");

```
### Makes This fully operational database front-end

![image](https://user-images.githubusercontent.com/70232210/91227678-e8c73700-e6f4-11ea-83ee-4712e687bfb4.png)

### Any Questions?  It's that simple.

To get the easiest experience with PySimpleSQL, the magic is in the database creation.
The automatic functionality of PySimpleSQL relies on just a couple of things:
- foreign key constraints on the database tables
- a CASCADE ON UPDATE constraint on any tables that should automatically refresh in the GUI
- PySimpleGUI control keys need to be named {table}.{field} for automatic mapping.  Of course, manual mapping is supported as well. ss.record() is a convenience function/"custom control" to make adding records quick and easy!
- The field 'name', (or the 2nd column of the database in the absense of a 'name' column) is what will display in comboxes for foreing key relationships.  Of course, this can be changed manually if needed, but truly the simplictiy of PySimpleSQL is in having everything happen automatically!

Here is another example sqlite table that shows the above rules at work.  Don't let this scare you, there are plenty of tools to create your database without resorting to raw SQL commands. These commands here are just shown for completeness (Creating the sqlite database is only done once anyways) 
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
The above is literally all you have to know for working with simple and even moderate databases.  However, there is a lot of power in learning what is going on under the hood!  Starting with the fully automatic example above, we will work backwards to explain what is available to you for more control.

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
Furthering that, the functions ss.set_text_size() and ss.set_control_size() can be used before calls to ss.record() to have custom sizing of the control elements.  Even with these defaults set, the size parameter of record() will override the default control size, for plenty of flexibility!

Place the two functions below just abovethe layout definition shown in the example above and then run the code again
```python
ss.set_text_size(10,1)
ss.set_control_size(50,1)
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
         ss.record('Item', 'description', sg.MLine, (30, 7)) #Override the default size for this element!
         ])],
    ss.record_actions('Item', False)
]
layout += [[sg.Frame('Items', sub_layout)]]
layout += [ss.record_navigation('Restaurant',protect=True,search=True,save=True)]
```
![image](https://user-images.githubusercontent.com/70232210/91287363-a71ea680-e75d-11ea-8b2f-d240c1ec2acf.png)
You will see that now, the controls were resized using the new sizing rules.  Notice however that the 'Description' field isn't as wide as the others.  That is because we overridden the control size for just that single control.

Lets see one more example.  This time we will fix the oddly sized 'Description' field, as well as make the 'Restaurant' and 'Items' sections with their own sizing
```python
# set the sizing for the Restaurant section
ss.set_text_size(10,1)
ss.set_control_size(90,1)
layout = [
    ss.record('Restaurant', 'name'),
    ss.record('Restaurant', 'location'),
    ss.record('Restaurant', 'fkType', sg.Combo)]
# set the sizing for the Items section
ss.set_text_size(10,1)
ss.set_control_size(50,1)
sub_layout = [
    [sg.Listbox(values=(), size=(35, 10), key="SELECTOR.Item", select_mode=sg.LISTBOX_SELECT_MODE_SINGLE, enable_events=True),
    sg.Col(
        [ss.record('Item', 'name'),
         ss.record('Item', 'fkMenu', sg.Combo),
         ss.record('Item', 'price'),
         ss.record('Item', 'description', sg.MLine, (50, 10)) #Override the default size for this element
         ])],
    ss.record_actions('Item', False)
]
layout += [[sg.Frame('Items', sub_layout)]]
layout += [ss.record_navigation('Restaurant',protect=True,search=True,save=True)]
```
![image](https://user-images.githubusercontent.com/70232210/91288080-8e62c080-e75e-11ea-8438-86035d4d6609.png)


### Binding the window to the element
Referencing the example above, the window and database were bound with this line:
```python
db = ss.Database(':memory:', 'example2.sql', win)
```
The above in a one-shot approach, and could have been written as:
```python
db=ss.Database(':memory:', 'example2.sql') # Load in the database
db.auto_bind(win) # automatically bind the window to the database
```

Furthering that, db.auto_bind() could have been done like this:
```python
db.auto_add_tables()
self.auto_add_relationships()
self.auto_map_controls(win)
self.auto_map_events(win)
self.requery_all()
self.update_controls()
```

And finally, that brings us to the lower-level functions for binding the database. The above could have been done manually like so:
```python
db.add_table('Restaurant','pkRestaurant','name') # add the table Restaurant, with it's primary key field, and descriptive field (for comboboxes)
db.add_table('Item','pkItem','name') # Note: While I personally prefer to use the pk{Table} and fk{Table} naming
db.add_table('Type','pkType','name') #       conventions, it's not necessary for pySimpleSQL
db.add_table('Menu','pkMenu','name') #       These could have just as well been restaurantID and itemID for example
db.add_relationship()...
db.map_control()...
db.map_event()...
db.update_controls()...
```

As you can see, there is a lot of power in the auto functionality of PySimpleSQL, and you should take advantage of it any time you can.  Only very specific cases need to reach this lower level of manual mapping!