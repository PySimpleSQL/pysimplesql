# **pysimplesql** Version Information


## <v2.3.0>
### Released 01/30/23
renames set_Mline_size to set_mline_size
adds user defined icon packs
adds duplicate to available record actions
adds set_ttk_theme and get_ttk_theme
moved some informational popups to quick messages
Big thanks to ssweber for these great contributions!

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
