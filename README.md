![image](https://user-images.githubusercontent.com/70232210/91427413-dd2a5c00-e82b-11ea-8a3d-dc706149422d.png)
# PySimpleGUI User's Manual

## Rapidly build and deploy database applications in Python
Binds PySimpleGUI to sqlite3 databases for rapid, effortless database application development. Makes a great
replacement for MS Access or Libre Office Base! Have the full power and language features of Python while having the 
power and control of managing your own codebase.


# Jump-Start

## Install
NOTE: PySimpleSQL is not yet on PyPi, but will be soon!
```
pip install PySimpleGUI
pip install pysimplesql
pip install sqlite3
or
pip3 install PySimpleGUI
pip3 install pysimplesql
pip3 install sqlite3
```

### This Code

```python
#!/usr/bin/python3
import PySimpleGUI as sg
import pysimplesql as ss                               # <=== PySimpleSQL lines will be marked like this.  There's only a few!

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
db = ss.Database(':memory:', 'example.sql', win)      # <=== load the database and bind it to the window

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

Like PySimpleGUI, pySimpleSQL supports subscript notation, so your code can access the data easily in the format of db['Table']['field'].
In the example above, you could get the current item selection with the following code:
```python
selected_restaurant=db['Restaurant'].['name']
selected_item=db['Item']['name']
```
or via the PySimpleGUI control elements with the following:
```python
selected_restaurant=win['Restaurant.name']
selected_item=win['Item.name']
```
### Any Questions?  It's that simple.

To get the best possible experience with PySimpleSQL, the magic is in the schema of the database.
The automatic functionality of PySimpleSQL relies on just a couple of things:
- foreign key constraints on the database tables (lets PySimpleSQL know what the relationships are)
- a CASCADE ON UPDATE constraint on any tables that should automatically refresh child tables when parent tables are 
refreshed
- PySimpleGUI control keys need to be named {table}.{field} for automatic mapping.  Of course, manual mapping is 
supported as well. @Database.record() is a convenience function/"custom control" to make adding records quick and easy!
- The field 'name', (or the 2nd column of the database in the absence of a 'name' column) is what will display in 
comboxes for foreign key relationships.  Of course, this can be changed manually if needed, but truly the simplictiy of 
PySimpleSQL is in having everything happen automatically!

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
    -- then PySimpleSQL will pick them up!
    -- note: ON UPDATE CASCADE only needed if you want automatic GUI refreshing
    -- (i.e. not every constraint needs them, like fields that will populate comboboxes for example)
    FOREIGN KEY(fkBook) REFERENCES Book(pkBook) ON UPDATE CASCADE
);
```

### But wait, there's more!
The above is literally all you have to know for working with simple and even moderate databases.  However, there is a 
lot of power in learning what is going on under the hood!  Starting with the fully automatic example above, we will work
backwards to explain what is available to you for more control.

#### PySimpleGUI elements:
Referencing the example above, look at the following:
```python
# convience function for rapid front-end development
ss.record('Restaurant', 'name') # Table name, field name parameters

# could have been written like this:
[sg.Text('Name:',size=(15,1)),sg.Input('',key='Restaurant.name',size=(30,1))]
```
As you can see, the @Database.record() convenience function simplifies making record controls that adhere to the
PySimpleSQL naming convention of Table.field. In fact, there is even more you can do with this. The @Database.record() 
function can take a PySimpleGUI control element as a parameter as well, overriding the defaul Input() element.
See this code which creates a combobox instead:
```python
ss.record('Restaurant', 'fkType', sg.Combo)]
```
Furthering that, the functions @Database.set_text_size() and @Database.set_control_size() can be used before calls to 
@Database.record() to have custom sizing of the control elements.  Even with these defaults set, the size parameter of 
@Database.record() will override the default control size, for plenty of flexibility.

Place those two functions just above the layout definition shown in the example above and then run the code again
```python
ss.set_text_size(10,1)    # Set the text/label size for all subsequent calls
ss.set_control_size(50,1) # set the control size for all subsequent calls
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
You will see that now, the controls were resized using the new sizing rules.  Notice however that the 'Description'
field isn't as wide as the others.  That is because we overridden the control size for just that single control.

Lets see one more example.  This time we will fix the oddly sized 'Description' field, as well as make the 'Restaurant' 
and 'Items' sections with their own sizing
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
self.auto_add_relationships()
self.auto_map_controls(win)
self.auto_map_events(win)
self.requery_all()
self.update_controls()
```

And finally, that brings us to the lower-level functions for binding the database.
This is how you can MANUALLY map tables, relationships, controls and events to the database.
The above auto_map_* functions could have been manually achieved as follows:
```python
# Add the tables you want PySimpleSQL to handle.  The function db.auto_add_tables() will add all tables found in the database 
# by default.  However, you may only need to work with a couple of tables in the database, and this is how you would do that
db.add_table('Restaurant','pkRestaurant','name') # add the table Restaurant, with it's primary key field, and descriptive field (for comboboxes)
db.add_table('Item','pkItem','name') # Note: While I personally prefer to use the pk{Table} and fk{Table} naming
db.add_table('Type','pkType','name') #       conventions, it's not necessary for pySimpleSQL
db.add_table('Menu','pkMenu','name') #       These could have just as well been restaurantID and itemID for example

# Set up relationships
# Notice below that the first relationship has the last parameter to True.  This is what the ON UPDATE CASCADE constraint accomplishes.
# Basically what it means is that then the Restaurant table is requeries, the associated Item table will automatically requery right after.
# This is what allows the GUI to seamlessly update all of the control elements when records are changed!
# The other relationships have that parameter set to False - they still have a relationship, but they don't need requeried automatically
db.add_relationship('LEFT JOIN', 'Item', 'fkRestaurant', 'Restaurant', 'pkRestaurant', True) 
db.add_relationship('LEFT JOIN', 'Restaurant', 'fkType', 'Type', 'pkType', False)
db.add_relationship('LEFT JOIN', 'Item', 'fkMenu', 'Menu', 'pkMenu', False)

# Map our controls
# Note that you can map any control to any Table/field combination that you would like.
# The {Table}.{field} naming convention is only necessary if you want to use the auto-mapping functionality of PySimpleSQL!
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
db.update_controls()
```

As you can see, there is a lot of power in the auto functionality of PySimpleSQL, and you should take advantage of it any time you can.  Only very specific cases need to reach this lower level of manual configuration and mapping!