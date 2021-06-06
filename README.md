# **pysimplesql** User's Manual

## DISCLAIMER:
While **pysimplesql** works with and was inspired by the excellent PySimpleGUI™ project, it has no affiliation.

## Rapidly build and deploy database applications in Python
**pysimplesql** binds PySimpleGUI™ to sqlite3 databases for rapid, effortless database application development. Makes a great
replacement for MS Access or Libre Office Base! Have the full power and language features of Python while having the 
power and control of managing your own codebase. **pysimplesql** not only allows for super simple automatic control (not one single
line of SQL needs written to use **pysimplesql**), but also allows for very low level control for situations that warrant it.

## History
**pysimplesql** was conceived after having used PySimpleGUI™ to prototype a GUI in Python.  After some time it became apparent that
my approach of prototyping in one language, just to implement it in another wasn't very efficient and didn't make much sense.
I had taken this approach many times in the past due to the lack of a good RAD (Rapid Application Development) tool when it comes
to making database front ends in Python.  Rather than spending my time porting my prototype over, one time I decided to try my hand
at creating such a tool - and this is what I ended up with.
Now make no mistake - I'm not a good project maintainer, and my goal was never to launch an open source project in the first place!
The more I used this combination of **pysimplesql** and PySimpleGUI™ for my own database projects, the more I realized how many others 
would benefit from it. With that being said, I will do my best to maintain and improve this tool over time.  Being new to open source
as well as hosting projects like this, I have a lot to learn moving forward.  Your patience is appreciated.

# Lets do this!

## Install
NOTE: I will try to keep current progress updated on Pypi so that pip installs the latest version.
However, the single **pysimplesql.py** file can just as well be copied directly into the root folder of your own project.
```
pip install PySimpleGUI
pip install **pysimplesql**
or
pip3 install PySimpleGUI
pip3 install **pysimplesql**
```

**pysimplesql** is now in active development and constantly changing. When an update is available, a message similar to 
the following will be displayed in the output of the program:

```***** pysimplesql update to v0.0.5 available! Just run pip3 install pysimplesql --upgrade *****```

Be sure to update the package when you get this message, or from time to time with
the following command:
```
pip install pysimplesql --upgrade
```
or
```
pip3 install pysimplesql --upgrade
```

### This Code

```python
import PySimpleGUI as sg
import pysimplesql as ss                               # <=== pysimplesql lines will be marked like this.  There's only a few!
import logging
logger=logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)               # <=== You can set the logging level here (NOTSET,DEBUG,INFO,WARNING,ERROR,CRITICAL)

# Define our layout. We will use the ss.record convenience function to create the controls
layout = [
    ss.record('Restaurant.name'),
    ss.record('Restaurant.location'),
    ss.record('Restaurant.fkType', sg.Combo, size=(30,10), auto_size_text=False)]
sub_layout = [
    ss.selector('selector1','Item',size=(35,10))+
    [sg.Col([ss.record('Item.name'),
         ss.record('Item.fkMenu', sg.Combo, size=(30,10), auto_size_text=False),
         ss.record('Item.price'),
         ss.record('Item.description', sg.MLine, (30, 7))
    ])],
    ss.actions('actions1','Item', edit_protect=False,navigation=False,save=False, search=False)
]
layout += [[sg.Frame('Items', sub_layout)]]
layout += [ss.actions('actions2','Restaurant')]

# Initialize our window and database, then bind them together
win = sg.Window('places to eat', layout, finalize=True)
db = ss.Database(':memory:', win,sql_script='example.sql')      # <=== load the database and bind it to the window
# NOTE: ":memory:" is a special database URL for in-memory databases

while True:
    event, values = win.read()

    if db.process_events(event, values):                  # <=== let pysimplesql process its own events! Simple!
        logger.info('PySimpleDB event handler handled the event!')
    elif event == sg.WIN_CLOSED or event == 'Exit':
        db=None              # <= ensures proper closing of the sqlite database and runs a database optimization at close
        break
    else:
        logger.info(f'This event ({event}) is not yet handled.')

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

Like PySimpleGUI™, **pysimplesql** supports subscript notation, so your code can access the data easily in the format of db['Table']['column'].
In the example above, you could get the current item selection with the following code:
```python
selected_restaurant=db['Restaurant']['name']
selected_item=db['Item']['name']
```
or via the PySimpleGUI™ control elements with the following:
```python
selected_restaurant=win['Restaurant.name']
selected_item=win['Item.name']
```
### It really is that simple.  All of the heavy lifting is done in the background!

To get the best possible experience with **pysimplesql**, the magic is in the schema of the database.
The automatic functionality of **pysimplesql** relies on just a couple of things:
- foreign key constraints on the database tables (lets **pysimplesql** know what the relationships are, though manual relationship mapping is also available)
- a CASCADE ON UPDATE constraint on any tables that should automatically refresh child tables when parent tables are 
changed
- PySimpleGUI™ control keys need to be named {table}.{column} for automatic mapping.  Of course, manual mapping is 
supported as well. @Database.record() is a convenience function/"custom element" to make adding records quick and easy!
- The field 'name', (or the 2nd column of the database in the absence of a 'name' column) is what will display in 
comboxes for foreign key relationships.  Of course, this can be changed manually if needed, but truly the simplictiy of 
**pysimplesql** is in having everything happen automatically!

Here is another example sqlite table that shows the above rules at work.  Don't let this scare you, there are plenty of
tools to create your database without resorting to raw SQL commands. These commands here are just shown for completeness
(Creating the sqlite database is only done once anyways) 
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
    -- then pysimplesql will pick them up!
    -- note: ON UPDATE CASCADE only needed if you want automatic GUI refreshing
    -- (i.e. not every constraint needs them, like fields that will populate comboboxes for example)
    FOREIGN KEY(fkBook) REFERENCES Book(pkBook) ON UPDATE CASCADE
);
```

### But wait, there's more!
The above is literally all you have to know for working with simple and even moderate databases.  However, there is a 
lot of power in learning what is going on under the hood.  Starting with the fully automatic example above, we will work
backwards and unravel things to explain what is available to you for more control at a lower level.

#### **pysimplesql** elements:
Referencing the example above, look at the following:
```python
# convience function for rapid front-end development
ss.record('Restaurant', 'name') # Table name, field name parameters

# could have been written like this:
[sg.Text('Name:',size=(15,1)),sg.Input('',key='Restaurant.name',size=(30,1), metadata={'type': TYPE_RECORD})]
```
As you can see, the @Database.record() convenience function simplifies making record controls that adhere to the
**pysimplesql** naming convention of Table.column. Also notice that **pysimplesql** temporarily makes use of the PySimpleGUI metadata keyword argument - but don't worry, this is only during initial setup and the element's metadata
will still be available to you in your own program.
There is even more you can do with this. The @Database.record() 
method can take a PySimpleGUI™ control element as a parameter as well, overriding the defaul Input() element.
See this code which creates a combobox instead:
```python
ss.record('Restaurant.fkType', sg.Combo)]
```
Furthering that, the functions @Database.set_text_size() and @Database.set_control_size() can be used before calls to 
@Database.record() to have custom sizing of the control elements.  Even with these defaults set, the size parameter of 
@Database.record() will override the default control size, for plenty of flexibility.

Place those two functions just above the layout definition shown in the example above and then run the code again

```python
# set the sizing for the Restaurant section
ss.set_text_size(10, 1)
ss.set_control_size(90, 1)
layout = [
    ss.record('Restaurant.name'),
    ss.record('Restaurant.location'),
    ss.record('Restaurant.fkType', sg.Combo, size=(30,10), auto_size_text=False)]
sub_layout = [
    ss.selector('selector1','Item',size=(35,10))+
    [sg.Col([ss.record('Item.name'),
         ss.record('Item.fkMenu', sg.Combo, size=(30,10), auto_size_text=False),
         ss.record('Item.price'),
         ss.record('Item.description', sg.MLine, (30, 7))  # Override the default size for this element!
    ])],
    ss.actions('actions1','Item', edit_protect=False,navigation=False,save=False, search=False)
]
layout += [[sg.Frame('Items', sub_layout)]]
layout += [ss.actions('actions2','Restaurant')]
```
![image](https://user-images.githubusercontent.com/70232210/91287363-a71ea680-e75d-11ea-8b2f-d240c1ec2acf.png)
You will see that now, the controls were resized using the new sizing rules.  Notice however that the 'Description'
field isn't as wide as the others.  That is because we overridden the control size for just that single control (see code above).

Lets see one more example.  This time we will fix the oddly sized 'Description' field, as well as make the 'Restaurant' 
and 'Items' sections with their own sizing

```python
# set the sizing for the Restaurant section
ss.set_text_size(10, 1)
ss.set_control_size(90, 1)
layout = [
    ss.record('Restaurant.name'),
    ss.record('Restaurant.location'),
    ss.record('Restaurant.fkType', sg.Combo, size=(30,10), auto_size_text=False)]
sub_layout = [
    ss.selector('selector1','Item',size=(35,10))+
    [sg.Col([ss.record('Item.name'),
         ss.record('Item.fkMenu', sg.Combo, size=(30,10), auto_size_text=False),
         ss.record('Item.price'),
         ss.record('Item.description', sg.MLine, (50,10))  # Override the default size for this element!
    ])],
    ss.actions('actions1','Item', edit_protect=False,navigation=False,save=False, search=False)
]
layout += [[sg.Frame('Items', sub_layout)]]
layout += [ss.actions('actions2','Restaurant')]
```
![image](https://user-images.githubusercontent.com/70232210/91288080-8e62c080-e75e-11ea-8438-86035d4d6609.png)




### Binding the window to the element
Referencing the same example above, the window and database were bound with this one single line:
```python
db = ss.Database(':memory:', 'example.sql', win) # Load in the database and bind it to win
```
The above is a one-shot approach and all most users will ever need!
The above could have been written as:
```python
db=ss.Database(':memory:', 'example.sql') # Load in the database
db.auto_bind(win) # automatically bind the window to the database
```

db.auto_bind() likewise can be peeled back to it's own components and could have been written like this:
```python
db.auto_add_tables()
db.auto_add_relationships()
db.auto_map_controls(win)
db.auto_map_events(win)
db.requery_all()
db.update_controls()
```

And finally, that brings us to the lowest-level functions for binding the database.
This is how you can MANUALLY map tables, relationships, controls and events to the database.
The above auto_map_* functions could have been manually achieved as follows:
```python
# Add the tables you want pysimplesql to handle.  The function db.auto_add_tables() will add all tables found in the database 
# by default.  However, you may only need to work with a couple of tables in the database, and this is how you would do that
db.add_table('Restaurant','pkRestaurant','name') # add the table Restaurant, with it's primary key field, and descriptive field (for comboboxes)
db.add_table('Item','pkItem','name') # Note: While I personally prefer to use the pk{Table} and fk{Table} naming
db.add_table('Type','pkType','name') #       conventions, it's not necessary for pySimpleSQL
db.add_table('Menu','pkMenu','name') #       These could have just as well been restaurantID and itemID for example

# Set up relationships
# Notice below that the first relationship has the last parameter to True.  This is what the ON UPDATE CASCADE constraint accomplishes.
# Basically what it means is that then the Restaurant table is requeried, the associated Item table will automatically requery right after.
# This is what allows the GUI to seamlessly update all of the control elements when records are changed!
# The other relationships have that parameter set to False - they still have a relationship, but they don't need requeried automatically
db.add_relationship('LEFT JOIN', 'Item', 'fkRestaurant', 'Restaurant', 'pkRestaurant', True) 
db.add_relationship('LEFT JOIN', 'Restaurant', 'fkType', 'Type', 'pkType', False)
db.add_relationship('LEFT JOIN', 'Item', 'fkMenu', 'Menu', 'pkMenu', False)

# Map our controls
# Note that you can map any control to any Table/field combination that you would like.
# The {Table}.{field} naming convention is only necessary if you want to use the auto-mapping functionality of pysimplesql!
db.map_control(win['Restaurant.name'],'Restaurant','name')
db.map_control(win['Restaurant.location'],'Restaurant','location')
db.map_control(win['Restaurant.fkType'],'Type','pkType')
db.map_control(win['Item.name'],'Item','name')
db.map_control(win['Item.fkRestaurant'],'Item','fkRestaurant')
db.map_control(win['Item.fkMenu'],'Item','fkMenu')
db.map_control(win['Item.price'],'Item','price')
db.map_control(win['Item.description'],'Item','description')

# Map out our events
# In the above example, this was all done in the background, as we used convenience functions to add record navigation buttons.
# However, we could have made our own buttons and mapped them to events.  Below is such an example
db.map_event('Edit.Restaurant.First',db['Restaurant'].First) # button control with the key of 'Edit.Restaurant.First'
                                                             # mapped to the Table.First method
db.map_event('Edit.Restaurant.Previous',db['Restaurant'].Previous)
db.map_event('Edit.Restaurant.Next',db['Restaurant'].Next)
db.map_event('Edit.Restaurant.Last',db['Restaurant'].Last)
# and so on...
# In fact, you can use the event mapper however you want to, mapping control names to any function you would like!
# Event mapping will be covered in more detail later...

# This is the magic function which populates all of the controls we mapped!
# For your convience, you can optionally use the function Database.set_callback('update_controls',function) to set a callback function
# that will be called every time the controls are updated.  This allows you to do custom things like update
# a preview image, change control parameters or just about anythong you want!
db.update_elements()
```

As you can see, there is a lot of power in the auto functionality of pysimplesql, and you should take advantage of it any time you can.  Only very specific cases need to reach this lower level of manual configuration and mapping!

# BREAKDOWN OF ADVANCED FUNCTIONALITY
**pysimplesql** does much more than just bridge the gap between PySimpleGUI™ and Sqlite databases! In full, **pysimplesql** contains:
* Convenience functions for simplifying PySimpleGUI™ layout code
* Control binding between PySimpleGUI™ controls and Sqlite database fields
* Automatic requerying of related tables
* Record navigation - Such as First, Previous, Next, Last, Searching and selector controls
* Callbacks allow your own functions to expand control over your own database front ends
* Event Mapping

We will break each of these down below to give you a better understanding of how each of these features works.
## Convenience Functions
There are currently only a few convenience functions to aid in quickly creating PySimpleGUI™ layout code
Database.set_text_size(width,height) - Sets the PySimpleGUI™ text size for subsequent calls to Database.record(). Defaults to (15,1) otherwise.

Database.set_control_size(width, height) - Sets the PySImpleGUI™ control size for subsequent calls to Database.record(). Defaults to (30,1) otherwise.

Database.record(table, field,control_type=None,size=None,text_label=None)- This is a convenience function for creating a PySimpleGUI™ text element and a PySimpleGUI™ Input element inline for purposes of displaying a record from the database.  This function also creates the naming convention (table.column) in the control's key parameter that **pysimplesql** uses for advanced automatic functionality. The optional control_type parameter allows you to bind control types other than Input to a database field.  Checkboxes, listboxes and other controls entered here will override the default Input control. The size parameter will override the default control size that was set with Database.set_control_size().  Lastly, the text_label parameter will prefix a text field before the control.

Database.actions()-

## Control Binding

## Automatic Requerying

## Record Navigation
**pysimplesql** includes a convenience function for adding record navigation buttons to your project.  For lower level control or a custom look, you may want to learn how to do this on your own.  Lets start with the convenience function and work backwards from there to see how you can implement your own record navigation controls.

The convenience function pysimplesql.actions() is a swiss army knife when it comes to generating PySimpleGUI™ layout code for your record navigation controls.  With it, you can add First, Previous, Next and Last record navigation buttons, a search box, edit protection modes, and record actions such as Insert, Save and Delete (Or any combination of these items).  Under the hood, the actions() convenience function uses the Event Mapping features of **pysimplesql**, and your own code can do this too!
See the code below on example usage of the **pysimplesql**.actions() convenience function

```python
#!/usr/bin/python3
import PySimpleGUI as sg
import pysimplesql as ss

# Create a small table just for demo purposes
sql = '''
CREATE TABLE "Fruit"(
    "id" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
	"name" TEXT DEFAULT "New Fruit"
);
INSERT INTO "Fruit" ("name") VALUES ("Apple");
INSERT INTO "Fruit" ("name") VALUES ("Orange");
INSERT INTO "Fruit" ("name") VALUES ("Banana");
INSERT INTO "Fruit" ("name") VALUES ("Kiwi");
'''

# PySimpleGUI™ layout code to create your own navigation buttons
table = 'Fruit'  # This is the table in the database that you want to navigate
layout = [
    ss.record(table, 'name', label='Fruit Name'),  # pysimplesql.record() convenience function for easy record creation!
    ss.actions(table)  # pysimplesql.actions() convenience function for easy navigation controls!
]

win = sg.Window('Navigation demo', layout, finalize=True)
# note: Since win was passed as a parameter, binding is automatic (including event mapping!)
# Also note, in-memory databases can be created with ":memory:"!
db = ss.Database(':memory:', win, sql_commands=sql)

while True:
    event, values = win.read()
    if db.process_events(event, values):  # <=== let pysimplesql process its own events! Simple!
        print(f'PySimpleDB event handler handled the event {event}!')
    elif event == sg.WIN_CLOSED or event == 'Exit':
        db = None  # <= ensures proper closing of the sqlite database and runs a database optimization
        break
    else:
        print(f'This event ({event}) is not yet handled.')
```
Simple!
But as stated earlier, **pysimplesql**.actions is a swiss army knife!  Experiment with the code ablove, trying all of these variations to see all of goodness this convenience functions provides!

```python
ss.actions(table, search=False)
ss.actions(table, save=False)
ss.actions(table, edit_protect=False)
ss.actions(table, insert=False)
ss.actions(table, delete=False, save=False) 
```


See example below of how your can make your own record navigation controls instead of using the **pysimplesql**.actions() convenience function:

```python
#!/usr/bin/python3
import PySimpleGUI as sg
import pysimplesql as ss

# Create a small table just for demo purposes
sql = '''
CREATE TABLE "Fruit"(
    "id" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
	"name" TEXT DEFAULT "New Fruit"
);
INSERT INTO "Fruit" ("name") VALUES ("Apple");
INSERT INTO "Fruit" ("name") VALUES ("Orange");
INSERT INTO "Fruit" ("name") VALUES ("Banana");
INSERT INTO "Fruit" ("name") VALUES ("Kiwi");
'''

# PySimpleGUI™ layout code to create your own navigation buttons
table = 'Fruit'  # This is the table in the database that you want to navigate
layout = [
    ss.record(table, 'name', label='Fruit Name'),  # pysimplesql.record() convenience function for easy record creation!
    # Below we will create navigation buttons manually, naming the key so that the automatic event mapper will map the events
    [sg.Button('<<', key=f'btnFirst', size=(1, 1), metadata=meta = {'type': ss.TYPE_EVENT, 'event_type': ss.EVENT_FIRST, 'table': table, 'function': None}),
     sg.Button('<', key=f'btnPrevious', size=(1, 1), metadata=meta = {'type': ss.TYPE_EVENT, 'event_type': ss.EVENT_PREVIOUS, 'table': table, 'function': None}),
     sg.Button('>', key=f'btnNext', size=(1, 1), metadata=meta = {'type': ss.TYPE_EVENT, 'event_type': ss.EVENT_NEXT, 'table': table, 'function': None}),
     sg.Button('>>', key=f'btnLast', size=(1, 1), metadata=meta = {'type': ss.TYPE_EVENT, 'event_type': ss.EVENT_LAST, 'table': table, 'function': None})
     ]
]

win = sg.Window('Navigation demo', layout, finalize=True)
# note: Since win was passed as a parameter, binding is automatic (including event mapping!)
# Also note, in-memory databases can be created with ":memory:"!
db = ss.Database(':memory:', win, sql_commands=sql)

while True:
    event, values = win.read()
    if db.process_events(event, values):  # <=== let pysimplesql process its own events! Simple!
        print(f'PySimpleDB event handler handled the event {event}!')
    elif event == sg.WIN_CLOSED or event == 'Exit':
        db = None  # <= ensures proper closing of the sqlite database and runs a database optimization
        break
    else:
        print(f'This event ({event}) is not yet handled.')
```
Notice the metadata use in the navigation buttons above.  This is so that the Automatic event mapping of **pysimplesql** will handle these.  Valid event_types can be found right at the start of the pysimplesql.py file.

Peeling this back further, you can rewrite the same without the special metadata used by the automatic event mapper, then manually map them in the event mapper yourself...

```python
#!/usr/bin/python3
import PySimpleGUI as sg
import pysimplesql as ss

# Create a small table just for demo purposes
sql = '''
CREATE TABLE "Fruit"(
    "id" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
	"name" TEXT DEFAULT "New Fruit"
);
INSERT INTO "Fruit" ("name") VALUES ("Apple");
INSERT INTO "Fruit" ("name") VALUES ("Orange");
INSERT INTO "Fruit" ("name") VALUES ("Banana");
INSERT INTO "Fruit" ("name") VALUES ("Kiwi");
'''

# PySimpleGUI™ layout code to create your own navigation buttons
table = 'Fruit'  # This is the table in the database that you want to navigate
layout = [
    ss.record(table, 'name', label='Fruit Name'),  # pysimplesql.record() convenience function for easy record creation!
    # Below we will create navigation buttons manually, naming the key so that the automatic event mapper will map the events
    [
        sg.Button('<<', key=f'btnFirst', size=(1, 1)),
        sg.Button('<', key=f'btnPrevious', size=(1, 1)),
        sg.Button('>', key=f'btnNext', size=(1, 1)),
        sg.Button('>>', key=f'btnLast', size=(1, 1))
    ]
]

win = sg.Window('Navigation demo', layout, finalize=True)
# note: Since win was passed as a parameter, binding is automatic (including event mapping!)
# Also note, in-memory databases can be created with ":memory:"!
db = ss.Database(':memory:', win, sql_commands=sql)

# Manually map the events, since we did not adhere to the naming convention that the automatic mapper expects
db.map_event('btnFirst', db[table].first)
db.map_event('btnPrevious', db[table].previous)
db.map_event('btnNext', db[table].next)
db.map_event('btnLast', db[table].last)

while True:
    event, values = win.read()
    if db.process_events(event, values):  # <=== let pysimplesql process its own events! Simple!
        print(f'PySimpleDB event handler handled the event {event}!')
    elif event == sg.WIN_CLOSED or event == 'Exit':
        db = None  # <= ensures proper closing of the sqlite database and runs a database optimization
        break
    else:
        print(f'This event ({event}) is not yet handled.')
```

Lastly, you can rewrite the same and handle the events yourself instead of relying on **pysimplesql**'s event mapper

```python
#!/usr/bin/python3
import PySimpleGUI as sg
import pysimplesql as ss

# Create a small table just for demo purposes
sql = '''
CREATE TABLE "Fruit"(
    "id" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
	"name" TEXT DEFAULT "New Fruit"
);
INSERT INTO "Fruit" ("name") VALUES ("Apple");
INSERT INTO "Fruit" ("name") VALUES ("Orange");
INSERT INTO "Fruit" ("name") VALUES ("Banana");
INSERT INTO "Fruit" ("name") VALUES ("Kiwi");
'''

# PySimpleGUI™ layout code to create your own navigation buttons
table = 'Fruit'  # This is the table in the database that you want to navigate
layout = [
    ss.record(table, 'name', label='Fruit Name'),  # pysimplesql.record() convenience function for easy record creation!
    # Below we will create navigation buttons manually, naming the key so that the automatic event mapper will map the events
    [
        sg.Button('<<', key=f'btnFirst', size=(1, 1)),
        sg.Button('<', key=f'btnPrevious', size=(1, 1)),
        sg.Button('>', key=f'btnNext', size=(1, 1)),
        sg.Button('>>', key=f'btnLast', size=(1, 1))
    ]
]

win = sg.Window('Navigation demo', layout, finalize=True)
# note: Since win was passed as a parameter, binding is automatic (including event mapping!)
# Also note, in-memory databases can be created with ":memory:"!
db = ss.Database(':memory:', win, sql_commands=sql)

while True:
    event, values = win.read()
    # Manually handle our record selector events, bypassing the event mapper completely
    if db.process_events(event, values):  # <=== let pysimplesql process its own events! Simple!
        print(f'PySimpleDB event handler handled the event {event}!')
    elif event == 'btnFirst':
        db[table].first()
    elif event == 'btnPrevious':
        db[table].previous()
    elif event == 'btnNext':
        db[table].next()
    elif event == 'btnLast':
        db[table].last()
    elif event == sg.WIN_CLOSED or event == 'Exit':
        db = None  # <= ensures proper closing of the sqlite database and runs a database optimization
        break
    else:
        print(f'This event ({event}) is not yet handled.')

```

Whether you want to use the **pysimplesql**.actions() convenience function, write your own navigation button layout code, use the auto event mapper, manually map the events, or handle the events yourself, you have plenty of options for flexibility writing your navigation button code!  Of course, the convenience function is very flexible and has attractive icons in the buttons, and really should be used in most cases.
## Callbacks

## Event Mapping

*
