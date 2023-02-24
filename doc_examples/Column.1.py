# Get the of the first column selecting a `Column` from the stored `ColumnInfo` collection
col_name = frm['Journal'].column_info[0]['name'] # uses subscript notation
col_name = frm['Journal'].column_info[0].name    # uses the name property

# Get the default value stored in the database for the 'title' column
default = frm['Journal'].column_info['title'].default