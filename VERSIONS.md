# **pysimplesql** Version Information

## <develop>
### Released <release_Date>
- Big change, moving from a Database/Table topology to a Form/Query topology.  Aliases for Database/Table will be available to avoid breaking code as much as possible
- The above being said, the way records are created is chaging slightly, as well as how the Form is bound to the Window.  
- New prefix_queries parameter can prefix auto-generated queries.  By default, auto-generated queries have the same name as the underlying table.  By using this parameter,
you can now have a prefix, I.e. qryRestaurant instead of Restaurant.
I had to kick this around quite a bit, and in the end the new topology makes more sense, especially when you get into using multiple Forms and Queries against the same tables.
- Tons of documentation improvements
- Prompt saves when dirty records are present.  This will also be an option for Query object so that the feature can be turned on and off.
- Forms and Queries now track created instances.  They can be accessed with Form.instances and Query.instances
- pysimplesql.update_elements() master function will update elements for all forms.  Form.update_elements() still remains, and only updates elements for that specific Form instance.
- pysimplesql.process_events() master function will process events for all forms.  Form.process_events() still remains, and only processes events for that specific Form instance.
