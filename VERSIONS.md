# **pysimplesql** Version Information

## <V3.0.0>
### Released ?/?/23
This version introduces **many** new features that take pysimplesql to the next level.  Please see the documentation for
more information on these new features. Another big thanks to **ssweber** for tons of help through sharing ideas, helping
with the butden of writing code throut issuing pull requests and sharing the vision of bringing rapid and easy database 
application development to the masses.
#### New Features
- Duplicate record action now supported.  Quickly and easily insert a new record from an existing one to have most of
your data already filled in for you.  This can be a real timesaver for some use cases.
- Multiple database support is here!  SQLite, MySQL and PostgreSQL are all not supported.  Using pysimplesql, your
projects can now seamlessly transition from one database type to another, as they are fully abstracted and a single
interface handles all of the complexity of dealing with mutliple database types. This includes a fully abstracted
ResultSet that works the same across all database implementations!
- New Transform system allows data manipulation as it's read from and written to the database.  For example, if dates
are stored as a timestamp in the database, it can be transformed into a string representation when it is read from the
database so that it displays correctly in the GUI, then transformed back to a timestamp when written back to the 
database.  The use cases for transforms are actually limitless! 
- New ColumnInfo class exposes information on table columns.  This includes they SQLType of the column (VARCHAR, INT, etc)
the default value of the column as defined in the SQL definition, whether notnull is set on the column, and if the column
is a primary key.  You can access this information through Query.column_info property (form['table'].column_info)
- New support for virtual rows and columns in pysimplesql.  This allows for the addition of rows and columns that don't
actually exist in the database but may be useful for your application.  The new insert_record() method actually uses
a virtual row to display the row to the user before actual insertion into the database.
- The prompt save system had a major overhaul - all of pysimplesql's internal record changing methods (previous, next,
first, last, etc) now prompt for changes before making the record change so that changed/inserted data is not lost accidentally
- Table element selectors can now sort data by column by clicking on the table header. This is a 3-click system that 
cycles through these 3 sort orders: ASC, DESC, and original sort as returned by the SQL database.  See documentation for
the new TableHeader class and examples for creating sortable table headers.
- Markers are now displayed for new records, required entries (notnull columns), and column sorting on Table elements.
![image](https://github.com/PySimpleSQL/pysimplesql/raw/abstracted_database/doc_screenshots/marker_showcase_window.png)
- New iconpack system allows for changing the look of your project easily and efficiently.  Add custom button images to
auto-generated buttons (save, previous, next, edit_protect, and so on). Also use custom unicode character markers for
things like the new record marker, the required entry marker, and the sort ASC/DESC marker.
- reduced the amount of default logging. Its mostly limited to logging database queries
- tons of docstring improvements and overall documentation improvements
- Examples updated to show new features
#### Bug Fixes
Scrollbars will now follow selected rows in PySimpleGUI elements (more of a new feature than a bug fix)
Fixes for checkboxes not always working correctly when checking for changes for prompt_save
various bug fixes in the prompt_save system
Bug fix for similar names used in multiple selectors
Bug fix for primary keys that start at 1 vs at 0
Various optimizations and performance increases
### Reverse Compatibility
The order of some parameters have changed to make parameter order more universal.  Now, if a function or method deals
with the database (table, column, etc), that parameter is listed first.  As a result, the parameter order of 
ss.actions() and ss.selector() have changed to be more in line with ss.record()

The process for creating a form has changed slightly.  Previous versions of pysimplesql only supported SQLite.  Now,
with 4 different database drivers available, the process has changed a little.  The new work flow is:
1) Create your layout and PySimpleGUI window
2) **new** Define your driver. For example, for SQLite: driver = SQLite(":memory:"...)
3) **slightly different** Create your form, binding the driver to the window: frm = Form(driver, win)

## <v2.3.0>
### Released 02/03/23
renames set_Mline_size to set_mline_size
adds user defined icon packs
adds duplicate to available record actions
adds set_ttk_theme and get_ttk_theme
moved some informational popups to quick messages
New prompt_save() feature at both the Query and Form level
Big thanks to ssweber for many of these great ideas and contributions!
informational logging cut down to a sane amount
Several bug fixes in the record save system
Changes to fix the prompt_save functionality, including a records_changed() method to easily check if records have changed.
Improved address book example to use this new method to selectively enable or disable the save button.

## <v2.02>
### Released 01/23/23
Add set_Mline_size to set default Multiline size via pull request

## <v2.01>
### Released 9/16/2022
Some minor improvements when it comes to the keygen and garbage collecting.  ss.record() now supports Comboboxes that are not
bound to a foreign key field.  ss.record() now also supports sg.Image() as well.
-ss.record() using images can work in two ways.  If pointed to a field that is a string value, it treats the string like a 
filepath and loads the image at the specified path.  If pointed to a field that is binary data, then the binary data is passed
in for image display.  Added a small example of how this may work in your own application along with a nifty function to limit
image size for either storage or display purposes (see examples/image_store.py)
- ss.record() using Comboboxes can now take in a list of values.  This is especially useful in situations where there is no
primary key <-> foreign key relationship on the field, but you would still like to limit the values that can be stored.  Setting
the readonly=True keyword parameter will limit options to the passed-in list.
- Added some internal changes, mostly revolving around the keygen (which is responsible for ensuring that the same key is not
used multiple times).  There is now a Form.close() method that safely closes out the form by resetting the keygen for elements
associated with the form, and Query instances that are assocated with the form. This makes it much easier to re-use window layouts
as the keygen will reset, and we won't be keeping old Query objects lying around hiding from the garbage collector.


## <v2.0>
### Released <9/15/2022>
- Big change, moving from a Database/Table topology to a Form/Query topology.  Aliases for Database/Table will be available to avoid breaking code as much as possible.
I had to kick this around quite a bit, and in the end the new topology makes more sense, especially when you get into using multiple Forms and Queries against the same tables.
- The above being said, the way records are created is chaging slightly, as well as how the Form is bound to the Window.  
- By default, auto-generated queries have the same name as the underlying table
- Tons of documentation improvements
- Prompt saves when dirty records are present.  This will also be an option for Query object so that the feature can be turned on and off.
- Forms and Queries now track created instances.  They can be accessed with Form.instances and Query.instances
- pysimplesql.update_elements() master function will update elements for all forms.  Form.update_elements() still remains, and only updates elements for that specific Form instance.
- pysimplesql.process_events() master function will process events for all forms.  Form.process_events() still remains, and only processes events for that specific Form instance.
- Examples and tutorials updated to work with new changes
