"""
# **pysimplesql** User's Manual

## DISCLAIMER:
While **pysimplesql** works with and was inspired by the excellent PySimpleGUI™ project, it has no affiliation.

## Rapidly build and deploy database applications in Python
**pysimplesql** binds PySimpleGUI to various databases for rapid, effortless database application development. Makes a great
replacement for MS Access or Libre Office Base! Have the full power and language features of Python while having the
power and control of managing your own codebase. **pysimplesql** not only allows for super simple automatic control (not one single
line of SQL needs written to use **pysimplesql**), but also allows for very low level control for situations that warrant it.
"""
#!/usr/bin/python3

# TODO: Make a list of controls to enable/disable along with edit_protect.  This would be a pretty cool feature

# The first two imports are for docstrings
from __future__ import annotations
from typing import List, Union, Optional, Tuple, Callable, Dict
from datetime import date, datetime
import PySimpleGUI as sg
import functools
import os.path
import logging
from types import SimpleNamespace ## for iconpacks
import pysimplesql ## Needed for quick_edit pop-ups
# Load database backends if present
supported_databases = ['SQLite3','MySQL','PostgreSQL']
failed_modules = 0
try:
    import sqlite3
except ModuleNotFoundError:
    failed_modules += 1
try:
    import mysql.connector
except ModuleNotFoundError:
    failed_modules += 1
try:
    import psycopg2
    import psycopg2.extras
except ModuleNotFoundError:
    failed_modules += 1
if failed_modules == len(supported_databases):
    RuntimeError(f"You muse have at least one of the following databases installed to use PySimpleSQL:\n{', '.join(supported_databases)} ")




logger = logging.getLogger(__name__)

# ---------------------------
# Types for automatic mapping
#----------------------------
TYPE_RECORD:int   =1
TYPE_SELECTOR:int =2
TYPE_EVENT:int    =3

# -----------------
# Transform actions
# -----------------
TFORM_ENCODE:int = 1
TFORM_DECODE:int = 0

# -----------
# Event types
# -----------
# Custom events (requires 'function' dictionary key)
EVENT_FUNCTION:int          = 0
# Query-level events (requires 'table' dictionary key)
EVENT_FIRST:int             = 1
EVENT_PREVIOUS:int          = 2
EVENT_NEXT:int              = 3
EVENT_LAST:int              = 4
EVENT_SEARCH:int            = 5
EVENT_INSERT:int            = 6
EVENT_DELETE:int            = 7
EVENT_DUPLICATE:int         = 13
EVENT_SAVE:int              = 8
EVENT_QUICK_EDIT:int        = 9
# Form-level events
EVENT_SEARCH_DB:int         = 10
EVENT_SAVE_DB:int           = 11
EVENT_EDIT_PROTECT_DB:int   = 12

# ----------------
# GENERIC BITMASKS
# ----------------
# Can be used with other bitmask values
SHOW_MESSAGE:int  = 4096

# ---------------------------
# PROMPT_SAVE RETURN BITMASKS
# ---------------------------
PROMPT_SAVE_DISCARDED:int = 1
PROMPT_SAVE_PROCEED:int   = 2
PROMPT_SAVE_NONE:int      = 4

# ---------------------------
# RECORD SAVE RETURN BITMASKS
# ---------------------------
SAVE_FAIL:int    = 1 # Save failed due to callback
SAVE_SUCCESS:int = 2 # Save was successful
SAVE_NONE:int    = 4 # There was nothing to save

# ----------------------
# SEARCH RETURN BITMASKS
# ----------------------
SEARCH_FAILED:int   = 1 # No result was found
SEARCH_RETURNED:int = 2 # A result was found
SEARCH_ABORTED:int  = 4 # The search was aborted, likely during a callback
SEARCH_ENDED:int    = 8 # We have reached the end of the search



def eat_events(win:sg.Window) -> None:
    """
    Eat extra events emitted by PySimpleGUI.Query.update().

    Call this function directly after update() is run on a Query element. The reason is that updating the selection or values
    will in turn fire more changed events, adding up to an endless loop of events.  This function eliminates this problem
    TODO: Determine if this is fixed yet in PySimpleSQL (still not fixed as of 3/2/23)

    :param win: A PySimpleGUI Window instance
    :returns: None
    """
    while True:
        event,values=win.read(timeout=1)
        if event=='__TIMEOUT__':
            break
    return

# TODO: Combine TableRow and ElementRow into one class for simplicity
class TableRow(list):
    """
    This is a convenience class used by Tables to associate a primary key with a row of information
    Note: This is typically not used by the end user.
    """
    def __init__(self, pk:int, *args, **kwargs):
        self.pk = pk
        super().__init__(*args, **kwargs)

    def __str__(self):
        return str(self[:])

    def __repr__(self):
        # Add some extra information that could be useful for debugging
        return f'TableRow(pk={self.pk}): {super().__repr__()}'

class ElementRow:
    """
    This is a convenience class used by listboxes and comboboxes to to associate a primary key with a row of information
    Note: This is typically not used by the end user.
    """
    def __init__(self, pk:int, val:Union[str,int]):
        self.pk = pk
        self.val = val

    def __repr__(self):
        return str(self.val)

    def __str__(self):
        return str(self.val)

    def get_pk(self):
        # Return the primary key portion of the row
        return self.pk

    def get_val(self):
        # Return the value portion of the row
        return self.val

    def get_instance(self):
        # Return this instance of the row
        return self


class Relationship:
    """
    This class is used to track primary/foreign key relationships in the database.

    See the following for more information: `Form.add_relationship` and `Form.auto_add_relationships`
    Note: This class is not typically used the end user,
    """
    def __init__(self, join:str, child_table:str, fk_column:Union[str,int], parent_table:str, pk_column:Union[str,int],
                 update_cascade:bool, driver:SQLDriver) -> Relationship:
        """
        Initialize a new Relationship instance

        :param join: The join type. I.e. "LEFT JOIN", "INNER JOIN", etc.
        :param child_table: The table name of the child table
        :param fk_column: The child table's foreign key column
        :param parent_table: The table name of the parent table
        :param pk_column: The parent table's primary key column
        :param driver: A `SQLDriver` instance
        :returns: A `Relationship` instance
        """
        self.join = join
        self.child_table = child_table
        self.fk_column = fk_column
        self.parent_table = parent_table
        self.pk_column = pk_column
        self.update_cascade = update_cascade
        self.driver = driver

    def __str__(self):
        """
        Return a join clause when cast to a string
        """
        return self.driver.relationship_to_join_clause(self)


class Query:
    """
    This class is used for an internal representation of database queries/tables. `Query` instances are added by the
    following `Form` methods: `Form.add_table` `Form.auto_add_tables`
    A `Query` is synonymous for a SQL Table (though you can technically have multiple `Query` objects referencing the
    same table, with each `Query` object having its own sorting, where clause, etc.)
    Note: While users will interact with Query objects often in pysimplesql, they typically aren't created manually by
    the user.
    """
    instances=[] # Track our own instances

    def __init__(self, name:str, frm_reference:Form, table:str, pk_column:str, description_column:str,
                 query:Optional[str]= '', order:Optional[str]= '', filtered:bool=True, prompt_save:bool=True,
                 autosave=False) -> Query:
        """
        Initialize a new `Query` instance

        :param name: The name you are assigning to this query (I.e. 'qry_people')
        :param frm_reference: This is a reference to the @ Form object, for convenience
        :param table: Name of the table
        :param pk_column: The name of the column containing the primary key for this table
        :param description_column: The name of the column used for display to users (normally in a combobox or listbox)
        :param query: You can optionally set an inital query here. If none is provided, it will default to
               "SELECT * FROM {query}"
        :param order: The sort order of the returned query. If none is provided it will default to
               "ORDER BY {description_column} ASC"
        :param filtered: (optional) If True, the relationships will be considered and an appropriate WHERE clause will
               be generated. False will display all records in query.
        :param prompt_save: (optional) Prompt to save changes when dirty records are present
        :param autosave: (optional) Default:False. True to autosave when changes are found without prompting the user
        :returns: A `Query` instance
        """
        # todo finish the order processing!
        Query.instances.append(self)
        self.driver = frm_reference.driver
        # No query was passed in, so we will generate a generic one
        if query == '':
            query = self.driver.default_query(table)
        # No order was passed in, so we will generate generic one
        if order == '':
            order = self.driver.default_order(description_column)

        self.name:str = name
        self.frm:Form = frm_reference
        self._current_index:int = 0
        self.table:str = table # TODO: refactor to table_name
        self.pk_column:str = pk_column
        self.description_column:str = description_column
        self.query:str = query # TODO: refactor to query_str
        self.order:str = order # TODO: refactor to order_clause
        self.join:str = ''  # TODO: refactor to join_clause
        self.where:str = '' # In addition to the generated where clause! TODO: refactor to where_clause
        self.dependents:list = []
        self.column_info:ColumnInfo = [] # ColumnInfo collection
        self.rows:ResultSet = []
        self.search_order:List[str] = []
        self.selector:List[str] = []
        self.callbacks:Dict[str:Callable[[Form,sg.Window],bool]] = {}
        self.transform:Callable[[ResultRow,Union[TFORM_ENCODE, TFORM_DECODE]],None] = None
        self.filtered:bool = filtered
        self._prompt_save:bool = prompt_save
        self._simple_transform = {} # TODO: typehint after researching
        self.autosave:bool = autosave

    # Override the [] operator to retrieve columns by key
    def __getitem__(self, key:str):
        return self.get_current(key)

    # Make current_index a property so that bounds can be respected
    @property
    def current_index(self):
        return self._current_index

    @current_index.setter
    # Keeps the current_index in bounds
    def current_index(self, val:int):
        if val > len(self.rows) - 1:
            self._current_index = len(self.rows) - 1
        elif val < 0:
            self._current_index = 0
        else:
            self._current_index = val

    @classmethod
    def purge_form(cls,frm:Form, reset_keygen:bool) -> None:
        """
        Purge the tracked instances related to frm

        :param frm: the `Form` to purge query instances from
        :param reset_keygen: Reset the keygen after purging?
        :returns: None
        """
        global keygen
        new_instances=[]
        selector_keys=[]

        for i in Query.instances:
            if i.frm!=frm:
                new_instances.append(i)
            else:
                logger.debug(f'Removing Query {i.name} related to {frm.driver.__class__.__name__}')
                # we need to get a list of elements to purge from the keygen
                for s in i.selector:
                    selector_keys.append(s['element'].key)


        # Reset the keygen for selectors and elements from this Form
        # This is probably a little hack-ish, perhaps I should relocate the keygen?
        if reset_keygen:
            for k in selector_keys:
                keygen.reset_key(k)
            keygen.reset_from_form(frm)
        # Update the internally tracked instances
        Query.instances=new_instances

    def set_prompt_save(self,value:bool) -> None:
        """
        Set the prompt to save action when navigating records

        :param value: a boolean value, True to prompt to save, False for no prompt to save
        :returns: None
        """
        self._prompt_save=value

    def set_search_order(self, order:List[str]) -> None:
        """
        Set the search order when using the search box.

        This is a list of column names to be searched, in order

        :param order: A list of column names to search
        :returns: None
        """
        self.search_order = order

    def set_callback(self, callback:str, fctn:Callable[[Form, sg.Window], bool]) -> None:
        """
        Set Query callbacks. A runtime error will be thrown if the callback is not supported.

        The following callbacks are supported:
            before_save   called before a record is saved. The save will continue if the callback returns true, or the
                          record will rollback if the callback returns false.
            after_save    called after a record is saved. The save will commit to the database if the callback returns
                          true, else it will rollback the transaction
            before_update Alias for before_save
            after_update  Alias for after_save
            before_delete called before a record is deleted.  The delete will move forward if the callback returns true,
                          else the transaction will rollback
            after_delete  called after a record is deleted. The delete will commit to the database if the callback
                          returns true, else it will rollback the transaction
            before_duplicate called before a record is duplicate.  The duplicate will move forward if the callback
                             returns true, else the transaction will rollback
            after_duplicate  called after a record is duplicate. The duplicate will commit to the database if the
                             callback returns true, else it will rollback the transaction
            before_search called before searching.  The search will continue if the callback returns True
            after_search  called after a search has been performed.  The record change will undo if the callback returns
                          False
            record_changed called after a record has changed (previous,next, etc.)

        :param callback: The name of the callback, from the list above
        :param fctn: The function to call.  Note, the function must take in two parameters, a `Form` instance, and a
                     `PySimpleGUI.Window` instance, and return True or False
        :returns: None
        """
        logger.info(f'Callback {callback} being set on table {self.table}')
        supported = [
            'before_save', 'after_save', 'before_delete', 'after_delete', 'before_duplicate', 'after_duplicate',
            'before_update', 'after_update',  # Aliases for before/after_save
            'before_search', 'after_search', 'record_changed'
        ]
        if callback in supported:
            # handle our convenience aliases
            callback = 'before_save' if callback == 'before_update' else callback
            callback = 'after_save' if callback == 'after_update' else callback
            self.callbacks[callback] = fctn
        else:
            raise RuntimeError(f'Callback "{callback}" not supported.')

    def set_transform(self, fn:callable) -> None:
        """
        Set a transform on the data for this `Query`.

        Here you can set custom a custom transform to both decode data from the
        database and encode data written to the database. This allows you to have dates stored as timestamps in the database,
        yet work with a human-readable format in the GUI and within PySimpleSQL. This transform happens only while PySimpleSQL
        actually reads from or writes to the database.

        :param fn: A callable function to preform encode/decode. This function should take two arguments: row (which will
        be populated by a dictionary of the row data), and an encode parameter (1 to endode, 0 to decode - see constants
        `TFORM_ENCODE` and `TFORM_DECODE`). Note that this transform works on one row at a time.
        See the example `journal_with_data_manipulation.py` for a usage example.
        :returns: None
        """
        self.transform = fn

    def set_query(self, query_str:str) -> None:
        """
        Set the query string for the `Query`.

        This is more for advanced users.  It defaults to "SELECT * FROM {table}; You can override the default with this method

        :param query_str: The query string you would like to associate with the table
        :returns: None
        """
        logger.debug(f'Setting {self.table} query to {query_str}')
        self.query = query_str



    def set_join_clause(self, clause:str) -> None:
        """
        Set the `Query` object's join string.

        This is more for advanced users, as it will automatically generate from the Relationships that have been set otherwise.

        :param clause: The join clause, such as "LEFT JOIN That on This.pk=That.fk"
        :returns: None
        """
        logger.debug(f'Setting {self.table} join clause to {clause}')
        self.join = clause

    def set_where_clause(self, clause:str) -> None:
        """
        Set the `Query` object's where clause.

        This is ADDED TO the auto-generated where clause from Relationship data

        :param clause: The where clause, such as "WHERE pkThis=100"
        :returns: None
        """
        logger.debug(f'Setting {self.table} where clause to {clause}')
        self.where = clause

    def set_order_clause(self, clause:str) -> None:
        """
        Set the `Query` object's order clause.

        This is more for advanced users, as it will automatically generate from the Relationships that have been set otherwise.

        :param clause: The order clause, such as "Order by name ASC"
        :returns: None
        """
        logger.debug(f'Setting {self.table} order clause to {clause}')
        self.order = clause

    def update_column_info(self,column_info:ColumnInfo=None) -> None:
        """
        Generate column names for the query.  This may need done, for example, when a manual query using joins
        is used.

        This is more for advanced users.
        :param column_info: (optional) A `ColumnInfo` instance. Defaults to being generated by the `SQLDriver`
        :returns: None
        """
        # Now we need to set  new column names, as the query could have changed
        if column_info!=None:
            self.column_info=column_info
        else:
            self.column_info = self.driver.column_info(self.table)

    def set_description_column(self, column_name:str) -> None:
        """
        Set the `Query` object's description column.

        This is the column that will display in Listboxes, Comboboxes, Tables, etc.
        By default,this is initialized to either the 'description','name' or 'title' column, or the 2nd column of the
        table if none of those columns exist.
        This method allows you to specify a different column to use as the description for the record.

        :param column_name: The name of the column to use
        :returns: None
        """
        self.description_column = column_name

    def records_changed(self, recursive=True, column_name:str=None) -> bool:
        """
        Checks if records have been changed by comparing PySimpleGUI control values with the stored Query values

        :param recursive: True to check related `Query` instances
        :param column_name: Limit the changed records search to just the supplied column name
        :returns: True or False on whether changed records were found
        """
        logger.debug(f'Checking if records have changed in table "{self.table}"...')

        # Virtual rows wills always be considered dirty
        if self.rows:
            if self.get_current_row().virtual: return True

        dirty = False
        # First check the current record to see if it's dirty
        for c in self.frm.element_map:
            # Compare the DB version to the GUI version
            if c['query'].table == self.table:
                ## if passed custom column_name
                if column_name is not None and c != column_name:
                    continue

                element_val = c['element'].get()
                table_val = self[c['column']]

                # For elements where the value is a Row type, we need to compare primary keys
                if type(element_val) is ElementRow:
                    element_val = element_val.get_pk()

                # For checkboxes
                if type(element_val) is bool:
                    if table_val is None: ## if there is no record, it will be '' instead of False
                        table_val = False
                    else:
                        table_val = bool(table_val)

                # Sanitize things a bit due to empty values being slightly different in the two cases
                if table_val is None: table_val = ''

                # Cast to similar types
                if type(element_val) != type(table_val):
                    element_val = str(element_val)
                    table_val = str(table_val)

                # Strip trailing whitespace from strings
                if type(table_val) is str: table_val = table_val.rstrip()
                if type(element_val) is str: element_val = element_val.rstrip()

                if element_val != table_val:
                    dirty = True
                    logger.debug(f'CHANGED RECORD FOUND!')
                    logger.debug(f'\telement type: {type(element_val)} column_type: {type(table_val)}')
                    logger.debug(f'\t{c["element"].Key}:{element_val} != {c["column"]}:{table_val}')
                    return dirty
                else:
                    dirty = False

        # handle recursive checking next
        if recursive:
            for rel in self.frm.relationships:
                if rel.parent_table == self.table and rel.update_cascade:
                    dirty = self.frm[rel.child_table].records_changed()
                    if dirty: break
        return dirty


    def prompt_save(self, autosave:bool=False) -> Union[PROMPT_SAVE_PROCEED, PROMPT_SAVE_DISCARDED, PROMPT_SAVE_NONE]:
        """
        Prompts the user if they want to save when changes are detected and the current record is about to change.

        :param autosave: True to autosave when changes are found without prompting the user
        :returns: A prompt return value of one of the following: `PROMPT_PROCEED`, `PROMPT_DISCARDED`, or `PROMPT_NONE`
        """
        # Return False if there is nothing to check or _prompt_save is False
        # TODO: children too?
        if self.current_index is None or self.rows == [] or self._prompt_save is False:
            return PROMPT_SAVE_NONE

        # Check if any records have changed
        changed = self.records_changed()
        if changed:
            if autosave or self.autosave:
                save_changes = 'Yes'
            else:
                save_changes = sg.popup_yes_no('You have unsaved changes! Would you like to save them first?')
            if save_changes == 'Yes':
                # save this records cascaded relationships, last to first
                if self.frm.save_records(table_name=self.table) & SAVE_FAIL:
                    return PROMPT_SAVE_DISCARDED
                return PROMPT_SAVE_PROCEED
            else:
                self.rows.purge_virtual()
                return PROMPT_SAVE_DISCARDED
        else:
            return PROMPT_SAVE_NONE


    def requery(self, select_first:bool=True, filtered:bool=True, update:bool=True, dependents:bool=True) -> None:
        """
        Requeries the table
        The `Query` object maintains an internal representation of the actual database table.
        The requery method will query the actual database and sync the `Query` objects to it

        :param select_first: (optional) If True, the first record will be selected after the requery
        :param filtered: (optional) If True, the relationships will be considered and an appropriate WHERE clause will
                         be generated. If False all records in the table will be fetched.
        :param update: (optional) Passed to `Query.first()` to update_elements. Note that the select_first parameter
                        must = True to use this parameter.
        :param dependents: (optional) passed to `Query.first()` to requery_dependents. Note that the select_first
                           parameter must = True to use this parameter.
        :returns: None
        """
        join = ''
        where = ''
        
        if self.filtered == False: filtered=False

        if filtered:
            join = self.driver.generate_join_clause(self)
            where = self.driver.generate_where_clause(self)

        query = self.query + ' ' + join + ' ' + where + ' ' + self.order
        # We want to store our sort settings before we wipe out the current ResultSet
        try:
            sort_settings = self.rows.store_sort_settings()
        except AttributeError:
            sort_settings = [None, ResultSet.SORT_NONE] # default for first query

        rows = self.driver.execute(query)
        self.rows = rows
        # now we can restore the sort order
        self.rows.load_sort_settings(sort_settings)
        self.rows.sort()

        for row in self.rows:
            # perform transform one row at a time
            if self.transform is not None:
                self.transform(row, TFORM_DECODE)

            # Strip trailing white space, as this is what sg[element].get() does, so we can have an equal comparison
            # Not the prettiest solution..  Will look into this more on the  PySimpleGUI end and make a ticket to follow up
            for k,v in row.items():
                if type(v) is str: row[k] = v.rstrip()


        if select_first:
            self.first(skip_prompt_save=True, update=update, dependents=dependents) # We don't want to prompt save in this situation, since there was a requery of the data

    def requery_dependents(self,child:bool=False, update:bool=True) -> None:
        """
        Requery parent `Query` instances as defined by the relationships of the table

        :param child: (optional) If True, will requery self. Default False; used to skip requery when called by parent.
        :param update: (optional) passed to `Query.requery()` -> `Query.first()` to update_elements.
        :returns: None
        """
        if child: self.requery(update=update,dependents=False) # dependents=False: we don't another recursive dependent requery
        for rel in self.frm.relationships:
            if rel.parent_table == self.table and rel.update_cascade:
                logger.debug(f"Requerying dependent table {self.frm[rel.child_table].table}")
                self.frm[rel.child_table].requery_dependents(child=True, update=update)

    def first(self, update:bool=True, dependents:bool=True, skip_prompt_save:bool=False) -> None:
        """
        Move to the first record of the table
        Only one entry in the table is ever considered "Selected"  This is one of several functions that influences
        which record is currently selected. See `Query.first()`, `Query.previous()`, `Query.next()`, `Query.last()`,
        `Query.search()`, `Query.set_by_pk()`, `Query.set_by_index()`

        :param update: (optional) Update the GUI elements after switching records
        :param dependents: (optional) Requery dependents after switching records?
        :param skip_prompt_save: (optional) True to skip prompting to save dirty records
        :returns: None
        """
        logger.debug(f'Moving to the first record of table {self.table}')
        if skip_prompt_save is False: self.prompt_save()
        self.current_index = 0
        if dependents: self.requery_dependents(update=update)
        if update: self.frm.update_elements(self.table)
        # callback
        if 'record_changed' in self.callbacks.keys():
            self.callbacks['record_changed'](self.frm, self.frm.window)

    def last(self, update:bool=True, dependents:bool=True, skip_prompt_save:bool=False):
        """
        Move to the last record of the table
        Only one entry in the table is ever considered "Selected"  This is one of several functions that influences
        which record is currently selected. See `Query.first()`, `Query.previous()`, `Query.next()`, `Query.last()`,
        `Query.search()`, `Query.set_by_pk()`, `Query.set_by_index()`

        :param update: (optional) Update the GUI elements after switching records
        :param dependents: (optional) Requery dependents after switching records?
        :param skip_prompt_save: (optional) True to skip prompting to save dirty records
        :returns: None
        """
        logger.debug(f'Moving to the last record of table {self.table}')
        if skip_prompt_save is False: self.prompt_save()
        self.current_index = len(self.rows) - 1
        if dependents: self.requery_dependents()
        if update: self.frm.update_elements(self.table)
        # callback
        if 'record_changed' in self.callbacks.keys():
            self.callbacks['record_changed'](self.frm, self.frm.window)

    def next(self, update:bool=True, dependents:bool=True, skip_prompt_save:bool=False):
        """
        Move to the next record of the table
        Only one entry in the table is ever considered "Selected"  This is one of several functions that influences
        which record is currently selected. See `Query.first()`, `Query.previous()`, `Query.next()`, `Query.last()`,
        `Query.search()`, `Query.set_by_pk()`, `Query.set_by_index()`

        :param update: (optional) Update the GUI elements after switching records
        :param dependents: (optional) Requery dependents after switching records?
        :param skip_prompt_save: (optional) True to skip prompting to save dirty records
        :returns: None
        """
        if self.current_index < len(self.rows) - 1:
            logger.debug(f'Moving to the next record of table {self.table}')
            if skip_prompt_save is False: self.prompt_save()
            self.current_index += 1
            if dependents: self.requery_dependents()
            if update: self.frm.update_elements(self.table)
            # callback
            if 'record_changed' in self.callbacks.keys():
                self.callbacks['record_changed'](self.frm, self.frm.window)

    def previous(self, update:bool=True, dependents:bool=True, skip_prompt_save:bool=False):
        """
        Move to the previous record of the table
        Only one entry in the table is ever considered "Selected"  This is one of several functions that influences
        which record is currently selected. See `Query.first()`, `Query.previous()`, `Query.next()`, `Query.last()`,
        `Query.search()`, `Query.set_by_pk()`, `Query.set_by_index()`

        :param update: (optional) Update the GUI elements after switching records
        :param dependents: (optional) Requery dependents after switching records?
        :param skip_prompt_save: (optional) True to skip prompting to save dirty records
        :returns: None
        """
        if self.current_index > 0:
            logger.debug(f'Moving to the previous record of table {self.table}')
            if skip_prompt_save is False: self.prompt_save()
            self.current_index -= 1
            if dependents: self.requery_dependents()
            if update: self.frm.update_elements(self.table)
            # callback
            if 'record_changed' in self.callbacks.keys():
                self.callbacks['record_changed'](self.frm, self.frm.window)

    def search(self, search_string:str, update:bool=True, dependents:bool=True, skip_prompt_save:bool=False) \
        -> Union[SEARCH_FAILED, SEARCH_RETURNED, SEARCH_ABORTED]:
        """
        Move to the next record in the `Query` that contains `search_string`.
        Successive calls will search from the current position, and wrap around back to the beginning.
        The search order from `Query.set_search_order()` will be used.  If the search order is not set by the user,
        it will default to the description column (see `Query.set_description_column()`.
        Only one entry in the table is ever considered "Selected"  This is one of several functions that influences
        which record is currently selected. See `Query.first()`, `Query.previous()`, `Query.next()`, `Query.last()`,
        `Query.search()`, `Query.set_by_pk()`, `Query.set_by_index()`

        :param search_string: The search string to look for
        :param update: (optional) Update the GUI elements after switching records
        :param dependents: (optional) Requery dependents after switching records?
        :param skip_prompt_save: (optional) True to skip prompting to save dirty records
        :returns: One of the following search values: `SEARCH_FAILED`, `SEARCH_RETURNED`, `SEARCH_ABORTED`
        """
        # See if the string is an element name # TODO this is a bit of an ugly hack, but it works
        if search_string in self.frm.window.key_dict.keys():
            search_string = self.frm.window[search_string].get()
        if search_string == '':
            return SEARCH_ABORTED

        logger.debug(f'Searching for a record of table {self.table} with search string "{search_string}"')
        # callback
        if 'before_search' in self.callbacks.keys():
            if not self.callbacks['before_search'](self.frm, self.frm.window):
                return SEARCH_ABORTED

        if skip_prompt_save is False: self.prompt_save() # TODO: Should this be before the before_search callback?
        # First lets make a search order.. TODO: remove this hard coded garbage
        if len(self.rows): logger.debug(f'DEBUG: {self.search_order} {self.rows[0].keys()}')
        for o in self.search_order:
            # Perform a search for str, from the current position to the end and back by creating a list of all indexes
            for i in list(range(self.current_index + 1, len(self.rows))) + list(range(0, self.current_index)):
                if o in self.rows[i].keys():
                    if self.rows[i][o]:
                        if search_string.lower() in str(self.rows[i][o]).lower():
                            old_index = self.current_index
                            self.current_index = i
                            if dependents: self.requery_dependents()
                            if update: self.frm.update_elements(self.table)

                            # callback
                            if 'after_search' in self.callbacks.keys():
                                if not self.callbacks['after_search'](self.frm, self.frm.window):
                                    self.current_index = old_index
                                    self.requery_dependents()
                                    self.frm.update_elements(self.table)
                                    return SEARCH_ABORTED

                            # callback
                            if 'record_changed' in self.callbacks.keys():
                                self.callbacks['record_changed'](self.frm, self.frm.window)

                            return SEARCH_RETURNED
        return SEARCH_FAILED
        # If we have made it here, then it was not found!
        # sg.Popup('Search term "'+str+'" not found!')
        # TODO: Play sound?

    def set_by_index(self, index:int, update:bool=True, dependents:bool=True, skip_prompt_save:bool=False,
                     omit_elements:List[str]=[]) -> None:
        """
        Move to the record of the table located at the specified index in Query.
         Only one entry in the table is ever considered "Selected"  This is one of several functions that influences
        which record is currently selected. See `Query.first()`, `Query.previous()`, `Query.next()`, `Query.last()`,
        `Query.search()`, `Query.set_by_pk()`, `Query.set_by_index()`

        :param index: The index of the record to move to.
        :param update: (optional) Update the GUI elements after switching records
        :param dependents: (optional) Requery dependents after switching records?
        :param skip_prompt_save: (optional) True to skip prompting to save dirty records
        :param omit_elements: (optional) A list of elements to omit from updating
        :returns: None
        """
        logger.debug(f'Moving to the record at index {index} on {self.table}')
        if skip_prompt_save is False: self.prompt_save()

        self.current_index = index
        if dependents: self.requery_dependents()
        if update: self.frm.update_elements(self.table, omit_elements=omit_elements)

    def set_by_pk(self, pk:int, update:bool=True, dependents:bool=True, skip_prompt_save:bool=False,
                  omit_elements:list=[str]) -> None:
        """
        Move to the record with this primary key
        This is useful when modifying a record (such as renaming).  The primary key can be stored, the record re-named,
        and then the current record selection updated regardless of the new sort order.
        Only one entry in the table is ever considered "Selected"  This is one of several functions that influences
        which record is currently selected. See @Query.first, @Query.previous, @Query.next, @Query.last, @Query.search,
        @Query.set_by_index

        :param pk: The record to move to containing the primary key
        :param update: (optional) Update the GUI elements after switching records
        :param dependents: (optional) Requery dependents after switching records?
        :param skip_prompt_save: (optional) True to skip prompting to save dirty records
        :param omit_elements: (optional) A list of elements to omit from updating
        :returns: None
        """
        logger.debug(f'Setting table {self.table} record by primary key {pk}')
        if skip_prompt_save is False: self.prompt_save()

        i = 0
        for r in self.rows:
            if r[self.pk_column] == pk:
                self.current_index = i
                break
            else:
                i += 1

        if dependents: self.requery_dependents()
        if update: self.frm.update_elements(self.table, omit_elements=omit_elements)

    def get_current(self, column_name:str, default:Union[str,int]="") -> Union[str,int]:
        """
        Get the current value pointed to for `column_name`
        You can also use indexing of the @Form object to get the current value of a column
        I.e. frm["{Query}].[{column'}]

        :param column_name: The column you want to get the value from
        :param default: A value to return if the record is null
        :returns: The value of the column requested
        """
        logger.debug(f'Getting current record for {self.table}.{column_name}')
        if self.rows:
            if self.get_current_row()[column_name] != '':
                return self.get_current_row()[column_name]
            else:
                return default
        else:
            return default

    def set_current(self, column_name:str, value:Union[str,int]) -> None:
        """
       Set the current value pointed to for `column_name`
       You can also use indexing of the `Form` object to set the current value of a column
       I.e. frm[{Query}].[{column}] = 'New value'

       :param column_name: The column you want to set the value for
       :param value: A value to set the current record's column to
       :returns: None
       """
        logger.debug(f'Setting current record for {self.table}.{column_name} = {value}')
        self.get_current_row()[column_name] = value

    def get_keyed_value(self,value_column:str, key_column:str, key_value:Union[str,int]) -> Union[str,int]:
        """
        Return `value_column` where` key_column`=`key_value`.  Useful for datastores with key/value pairs

        :param value_column: The column to fetch the value from
        :param key_column: The column in which to search for the value
        :param key_value: The value to search for
        :returns: Returns the value found in `value_column`
        """
        for r in self.rows:
            if r[key_column] == key_value:
                return r[value_column]

    def get_current_pk(self) -> int:
        """
        Get the primary key of the currently selected record

        :returns: the primary key
        """
        return self.get_current(self.pk_column)

    def get_current_row(self) -> ResultRow:
        """
        Get the row for the currently selected record of this table

        :returns: A `ResultRow` object
        """
        if self.rows:
            self.current_index = self.current_index # force the current_index to be in bounds! For child reparenting
            return self.rows[self.current_index]

    def add_selector(self, element:sg.Element, query_name:str, where_column:str=None, where_value:str=None) -> None:
        """
        Use an element such as a listbox, combobox or a table as a selector item for this table.
        Note: This is not typically used by the end user, as this is called from the`selector()` convenience function

        :param element: the PySinpleGUI element used as a selector element
        :param query_name: the `Query` name this selector will operate on
        :param where_column: (optional)
        :param where_value: (optional)
        :returns: None
        """
        if type(element) not in [sg.PySimpleGUI.Listbox, sg.PySimpleGUI.Slider, sg.Combo, sg.Table]:
            raise RuntimeError(f'add_selector() error: {element} is not a supported element.')

        logger.debug(f'Adding {element.Key} as a selector for the {self.table} table.')
        d={'element': element, 'query': query_name, 'where_column': where_column, 'where_value': where_value}
        self.selector.append(d)

    def insert_record(self, values:Dict[str:Union[str,int]]=None, skip_prompt_save:bool=False) -> None:
        """
        Insert a new record virtually in the `Query` object. If values are passed, it will initially set those columns to
        the values (I.e. {'name': 'New Record', 'note': ''}), otherwise they will be fetched from the database if present.

        :param values: column_name:value pairs
        :param skip_prompt_save: Skip prompting the user to save dirty records before the insert
        :returns: None
        """
        # todo: you don't add a record if there isn't a parent!!!
        # todo: this is currently filtered out by enabling of the element, but it should be filtered here too!
        # todo: bring back the values parameter
        if skip_prompt_save is False:
            if self.prompt_save() == PROMPT_SAVE_DISCARDED:
                return

        # Get a new dict for a new row with default values already filled in
        new_values = self.column_info.default_row_dict(self)

        # If the values parameter was passed in, overwrite any values in the dict
        if values is not None:
            for k,v in values.items():
                if k in new_values:
                    new_values[k]=v

        # Make sure we take into account the foreign key relationships...
        for r in self.frm.relationships:
            if self.table == r.child_table and r.update_cascade:
                new_values[r.fk_column] = self.frm[r.parent_table].get_current_pk()

        # Update the pk to match the expected pk the driver would generate on insert.
        new_values[self.pk_column] = self.driver.next_pk(self.table, self.pk_column)

        # Insert the new values using RecordSet.insert(). This will mark the new row as virtual!
        self.rows.insert(new_values)

        # and move to the new record
        self.set_by_pk(new_values[self.pk_column], update=True, dependents=True, skip_prompt_save=True) # already saved
        self.frm.update_elements(self.table)

    def save_record(self, display_message:bool=True, update_elements:bool=True) -> None:
        """
        Save the currently selected record
        Saves any changes made via the GUI back to the database.  The before_save and after_save `Query.callbacks` will call
        your own functions for error checking if needed!

        :param display_message: Displays a message "Updates saved successfully", otherwise is silent on success
        :param update_elements: Update the GUI elements after saving
        :returns: None
        """
        logger.debug(f'Saving records for table {self.table}...')
        # Ensure that there is actually something to save
        if not len(self.rows):
            if display_message: sg.popup_quick_message('There were no updates to save.',keep_on_top=True)
            return SAVE_NONE + SHOW_MESSAGE

        # callback
        if 'before_save' in self.callbacks.keys():
            if self.callbacks['before_save']() == False:
                logger.debug("We are not saving!")
                if update_elements: self.frm.update_elements(self.table)
                if display_message: sg.popup('Updates not saved.', keep_on_top=True)
                return SAVE_FAIL + SHOW_MESSAGE

        # Work with a copy of the original row and transform it if needed
        # Note that while saving, we are working with just the current row of data
        current_row = self.get_current_row().copy()

        # Propagate GUI data back to the stored current_row
        for v in self.frm.element_map:
            if v['query'] == self:
                if '?' in v['element'].key and '=' in v['element'].key:
                    val = v['element'].get()
                    table_info, where_info = v['element'].Key.split('?')
                    for row in self.rows:
                        if row[v['where_column']] == v['where_value']:
                            row[v['column']] = val
                else:
                    if '.' not in v['element'].key:
                        continue

                    if type(v['element']) == sg.Combo:
                        if type(v['element'].get()) == str:
                            val = v['element'].get()
                        else:
                            val = v['element'].get().get_pk()
                    else:
                        val = v['element'].get()

                    if val =='':
                        val = None
                    
                    # Fix for Checkboxes switching from 0 to False, and from 1 to True
                    if type(val) is bool and type(self[v['column']]) is int:
                        val = int(val)
                        
                    current_row[v['column']] = val

        changed_row = {k:v for k,v in current_row.items()}

        if not self.records_changed(recursive=False):
            if display_message:  sg.popup_quick_message('There were no changes to save!', keep_on_top=True)
            return SAVE_NONE + SHOW_MESSAGE
            
        # check to see if cascading-fk has changed before we update database
        cascade_fk_changed = False
        cascade_fk_column = self.frm.get_cascade_fk_column(self.table)
        if cascade_fk_column:
            # check if fk 
            for v in self.frm.element_map:
                if v['query'] == self and pysimplesql.get_record_info(v['element'].Key)[1] == cascade_fk_column:
                    cascade_fk_changed = self.records_changed(recursive=False, column_name=v)

        # Update the database from the stored rows
        if self.transform is not None: self.transform(self,changed_row, TFORM_ENCODE)

        # Save or Insert the record as needed
        if current_row.virtual==True:
            result = self.driver.insert_record(self.table,self.get_current_pk(),self.pk_column,changed_row)
        else:
            result = self.driver.save_record(self,changed_row)

        if result.exception is not None:
            sg.popup(f"Query Failed! {result.exception}", keep_on_top=True)
            self.driver.rollback()
            return SAVE_FAIL # Do not show the message in this case, since it's handled here

        # callback
        if 'after_save' in self.callbacks.keys():
            if not self.callbacks['after_save'](self.frm, self.frm.window):
                self.driver.rollback()
                return SAVE_FAIL + SHOW_MESSAGE

        # If we made it here, we can commit the changes
        self.driver.commit()

        # Store the pk can we can move to it later - use the value returned in the resultset if possible, just in case
        # the expected pk changed from autoincrement and/or condurrent access
        pk = result.lastrowid if result.lastrowid is not None else self.get_current_pk()
        current_row[self.pk_column] = pk

        # then update the current row data
        self.rows[self.current_index] = current_row

        # If child changes parent, move index back and requery/requery_dependents
        if cascade_fk_changed and not current_row.virtual: # Virtual rows already requery, and don't have any dependents.
            self.frm[self.table].requery(select_first=False) #keep spot in table
            self.frm[self.table].requery_dependents()

        # Lets refresh our data
        if current_row.virtual:
            self.requery(select_first=False, update=False) # Requery so that the new  row honors the order clause
            self.set_by_pk(pk,skip_prompt_save=True)       # Then move to the record

        if update_elements:self.frm.update_elements(self.table)
        logger.debug(f'Record Saved!')
        if display_message:  sg.popup_quick_message('Updates saved successfully!',keep_on_top=True)

        return SAVE_SUCCESS + SHOW_MESSAGE


    def save_record_recursive(self,results:Dict[str,Union[PROMPT_SAVE_PROCEED,PROMPT_SAVE_DISCARDED,PROMPT_SAVE_NONE]],
                             display_message=False, check_prompt_save:bool=False) \
                             -> Dict[str,Union[PROMPT_SAVE_PROCEED,PROMPT_SAVE_DISCARDED,PROMPT_SAVE_NONE]]:
        """
        Recursively save changes, taking into account the relationships of the tables
        :param results: Used in Form.save_records to collect Query.save_record returns. Pass an empty dict to get list
               of {table_name : result}
        :param display_message: Passed to Query.save_record. Displays a message "Updates saved successfully", otherwise
               is silent on success
        :param check_prompt_save: Used when called from Form.prompt_save. Updates elements without saving if individual
               `Query._prompt_save()` is False.
        :returns: dict of {table_name : results}
        """
        for rel in self.frm.relationships:
            if rel.parent_table == self.table and rel.update_cascade:
                self.frm[rel.child_table].save_record_recursive(
                    results=results,
                    display_message=display_message,
                    check_prompt_save=check_prompt_save
                    )
        if check_prompt_save and self._prompt_save is False:
            self.frm.update_elements(self.table)
            results[self.table] = PROMPT_SAVE_NONE
            return results
        else:
            result = self.save_record(display_message=display_message)
            results[self.table] = result
            return results

    def delete_record(self, cascade:bool=True): # TODO: check return type, we return True below
        """
        Delete the currently selected record
        The before_delete and after_delete callbacks are run during this process to give some control over the process

        :param cascade: Delete child records (as defined by `Relationship`s that were set up) before deleting this record
        :returns: None
        """
        # Ensure that there is actually something to delete
        if not len(self.rows):
            return

        # callback
        if 'before_delete' in self.callbacks.keys():
            if not self.callbacks['before_delete'](self.frm, self.frm.window):
                return

        children = []
        if cascade:
            for qry in self.frm.queries:
                for r in self.frm.relationships:
                    if r.parent_table == self.table and r.update_cascade:
                        children.append(r.child_table)
        
        children = list(set(children))
        if len(children):
            msg = f'Are you sure you want to delete this record? Keep in mind that children records in - {children} - will be deleted as well!'
        else:
            msg = 'Are you sure you want to delete this record?'
        answer = sg.popup_yes_no(msg, title='Confirm Delete',  keep_on_top=True)
        if answer == 'No':
            return True

        # Delete child records first!
        self.driver.delete_record(self, True)

        # callback
        if 'after_delete' in self.callbacks.keys():
            if not self.callbacks['after_delete'](self.frm, self.frm.window):
                self.driver.rollback()
            else:
                self.driver.commit()
        else:
            self.driver.commit()


        self.current_index = self.current_index  # force the current_index to be in bounds! todo should this be done in requery?
        self.requery_dependents()

        self.requery(select_first=False)
        self.frm.update_elements()
        
    def duplicate_record(self, cascade:bool=True) -> None: # TODO check return type, returns True within
        """
        Duplicate the currently selected record
        The before_duplicate and after_duplicate callbacks are run during this process to give some control over the process

        :param cascade: Duplicate child records (as defined by `Relationship`s that were set up) before duplicating this record
        :returns: None
        """
        # Ensure that there is actually something to duplicate
        if not len(self.rows):
            return

        # callback
        if 'before_duplicate' in self.callbacks.keys():
            if not self.callbacks['before_duplicate'](self.frm, self.frm.window):
                return
            
        children = []
        if cascade:
            for qry in self.frm.queries:
                for r in self.frm.relationships:
                    if r.parent_table == self.table and r.update_cascade:
                        children.append(r.child_table)
        
        children = list(set(children))
        if len(children):
            msg = f'Are you sure you want to duplicate this record? Keep in mind that children records in - {children} - will be duplicated as well!'
        else:
            msg = 'Are you sure you want to duplicate this record?'
        answer = sg.popup_yes_no(msg, title='Confirm Duplicate', keep_on_top=True)
        if answer == 'No':
            return True
        # Store our current pk so we can move to it if the duplication fails
        pk = self.get_current_pk()

        # Have the driver duplicate the record
        res = self.driver.duplicate_record(self,cascade)
        if res.exception:
            self.driver.rollback()
            sg.popup(res.exception, keep_on_top=True)
        else:
            pk = res.lastrowid
                        
        # callback
        if 'after_duplicate' in self.callbacks.keys():
            if not self.callbacks['after_duplicate'](self.frm, self.frm.window):
                self.driver.rollback()
            else:
                self.driver.commit()
        else:
            self.driver.commit()
        self.driver.commit()
        
        # move to new pk
        self.frm[r.child_table].requery(False)
        self.requery()
        self.set_by_pk(pk)
        self.requery_dependents()

        self.frm.update_elements()
        self.frm.window.refresh()

    def get_description_for_pk(self, pk:int) -> Union[str,int,None]:
        """
        Get the description from `Query.desctiption_column` from the row where the `Query.pk_column` = `pk`

        :param pk: The primary key from which to find the description for
        :returns: The value found in the description column, or None if nothing is found
        """
        for row in self.rows:
            if row[self.pk_column] == pk:
                return row[self.description_column]
        return None

    def table_values(self, column_names:List[str]=None, mark_virtual:bool=False) -> List[TableRow]:
        """
        Create a values list of `TableRows`s for use in a PySimpleGUI Table element. Each

        :param column_names: A list of column names to create table values for.  Defaults to getting them from the
                             `Query.rows` `ResultSet`
        :param mark_virtual: Place a marker next to virtual records
        :returns: A list of `TableRow`s suitable for using with PySimpleGUI Table element values
        """
        values = []
        #column_names=self.column_info.names() if columns == None else columns #<- old version got this from self.column_info
        # Get the column names directly from the row information so that the order is preserved
        try:
            all_columns = self.rows[0].keys()
        except IndexError:
            all_columns = []

        if column_names == None:
            column_names = all_columns
        else:
            column_names = column_names

        pk_column = self.column_info.pk_column()

        for row in self.rows:
            if mark_virtual:
                lst = [icon.marker_virtual] if row.virtual else [' ']
            else:
                lst = []

            rels = self.frm.get_relationships_for_table(self)
            pk = None
            for col in all_columns:
                # Is this the primary key column?
                if col == pk_column: pk = row[col]
                # Skip this column if we aren't supposed to grab it
                if col not in column_names: continue
                # Get this column info, including fk descriptions
                found = False
                for rel in rels:
                    if col == rel.fk_column:
                        lst.append(self.frm[rel.parent_table].get_description_for_pk(row[col]))
                        found = True
                        break
                if not found: lst.append(row[col])
            values.append(TableRow(pk,lst))

        return values

    def get_related_table_for_column(self, column_name:str) -> str:
        """
        Get parent table name as it relates to this column

        :param column_name: The column name to get related table informaion for
        :returns: The name of the related table, or the current table if none are found
        """
        rels = self.frm.get_relationships_for_table(self)
        for rel in rels:
            if column_name == rel.fk_column:
                return rel.parent_table
        return self.name  # None could be found, return ourself

    def quick_editor(self, pk_update_funct:callable=None, funct_param:any=None, skip_prompt_save:bool=False) -> None:
        """
        The quick editor is a dynamic PySimpleGUI Window for quick editing of tables.  This is very useful for putting
        a button next to a combobox or listbox so that the available values can be added/edited/deleted easily.
        Note: This is not typically used by the end user, as it can be configured from the `record()` convenience function

        :param: pk_update_funct: (optional) A function to call to determine the pk to select by default when the quick editor loads
        :param: funct_param: (optional) A parameter to pass to the `pk_update_funct`
        :param skip_prompt_save: (Optional) True to skip prompting to save dirty records
        :returns: None
        """
        global keygen

        if skip_prompt_save is False: self.prompt_save()
        # Reset the keygen to keep consistent naming
        logger.info('Creating Quick Editor window')
        keygen.reset()
        query_name = self.name
        layout = []
        headings = self.column_info.names()
        visible = [1] * len(headings); visible[0] = 0
        col_width=int(55/(len(headings)-1))
        for i in range(0,len(headings)):
            headings[i]=headings[i].ljust(col_width,' ')

        layout.append(
            [pysimplesql.selector('quick_edit2', query_name, sg.Table, num_rows=10, headings=headings, visible_column_map=visible)])
        layout.append([pysimplesql.actions("act_quick_edit2",query_name,edit_protect=False)])
        layout.append([sg.Text('')])
        layout.append([sg.HorizontalSeparator()])
        for col in self.column_info.names():
            column=f'{query_name}.{col}'
            if col!=self.pk_column:
                layout.append([pysimplesql.record(column)])

        quick_win = sg.Window(f'Quick Edit - {query_name}', layout, keep_on_top=True, finalize=True, ttk_theme=pysimplesql.get_ttk_theme()) ## Without specifying same ttk_theme, quick_edit will override user-set theme in main window
        driver=Sqlite(sqlite3_database=self.frm.driver.con)
        quick_frm = Form(driver, bind=quick_win)


        # Select the current entry to start with
        if pk_update_funct is not None:
            if funct_param is None:
                quick_frm[query_name].set_by_pk(pk_update_funct())
            else:
                quick_frm[query_name].set_by_pk(pk_update_funct(funct_param))

        while True:
            event, values = quick_win.read()

            if quick_frm.process_events(event, values):
                logger.debug(f'PySimpleSQL Quick Editor event handler handled the event {event}!')
            if event == sg.WIN_CLOSED or event == 'Exit':
                break
            else:
                logger.debug(f'This event ({event}) is not yet handled.')
        quick_win.close()
        self.requery()

    def add_simple_transform(self, transforms:Dict[str,Dict[str,Callable[[str,str],None]]]) -> None:
        """
        Merge a dictionary of transforms into the `Query._simple_transform` dictionary.

        Example:
        {'entry_date' : {
            'decode' : lambda row,col: datetime.utcfromtimestamp(int(row[col])).strftime('%m/%d/%y'),
            'encode' : lambda row,col: datetime.strptime(row[col], '%m/%d/%y').replace(tzinfo=timezone.utc).timestamp(),
        }}
        :param transofrms: A dict of dicts containing either 'encode' or 'decode' along with a callable to do the transform.
               see example above
        :returns: None
        """
        for k,v in transforms.items():
            if not callable(v): RuntimeError(f'Transofrm for {k} must be callable!')
            self._simple_transform[k] = v

class Form:
    """
    @orm class
    Maintains an internal version of the actual database
    Queries can be accessed by key, I.e. frm['query_name"] to return a `Query` instance
    """
    instances = []  # Track our instances
    relationships = [] # Track our relationships

    def __init__(self, driver:SQLDriver, bind:sg.Window=None, prefix_queries:str='', parent:Form=None, filter:str=None,
                 select_first:bool=True, autosave:bool=False) -> Form:
        """
        Initialize a new `Form` instance

        :param driver: Supported `SQLDriver`. See `Sqlite()`, `Mysql()`, `Postgres()`
        :param bind: Bind this window to the `Form`
        :param prefix_queries: (optional) prefix auto generated query names with this value. Example 'qry_'
        :param parent: (optional)Parent `Form` to base queries off of
        :param filter: (optional) Only import elements with the same filter set. Typically set with `record()`, but can
                       also be set manually as a dict with the key 'filter' set in the element's metadata
        :param select_first: (optional) Default:True. For each top-level parent, selects first row, populating children as well.
        :param autosave: (optional) Default:False. True to autosave when changes are found without prompting the user
        :returns: A `Form` instance

        """
        Form.instances.append(self)

        self.driver:SQLDriver = driver
        self.filter:str = filter
        self.parent:Form = parent  # TODO: This doesn't seem to really be used yet
        self.window:sg.Window = None
        self._edit_protect:bool = False
        self.queries:Dict[str,Query] = {}
        self.element_map:Dict[str,any] = []
        """
        The element map dict is set up as below:
        
        .. literalinclude:: ../doc_examples/element_map.1.py
        :language: python
        :caption: Example code
        """
        self.event_map = [] # Array of dicts, {'event':, 'function':, 'table':}
        self.relationships:List[Relationship] = []
        self.callbacks:Dict[str,Callable[[Form,sg.Window],Union[None,bool]]] = {}
        self.autosave:bool = autosave

        # Add our default queries and relationships
        self.auto_add_queries(prefix_queries)
        self.auto_add_relationships()
        self.requery_all(select_first=select_first, update=False, dependents=True)
        if bind!=None:
            self.window=bind
            self.bind(self.window)

    def __del__(self):
        self.close()


    # Override the [] operator to retrieve queries by key
    def __getitem__(self, key:str) -> Query:
        return self.queries[key]

    def close(self,reset_keygen:bool=True):
        """
        Safely close out the `Form`

        :param reset_keygen: True to reset the keygen for this `Form`
        """
        # First delete the queries associated
        Query.purge_form(self,reset_keygen)
        self.driver.close()

    def bind(self, win:sg.Window) -> None:
        """
        Bind the PySimpleGUI Window to the Form for the purpose of GUI element, event and relationship mapping.
        This can happen automatically on `Form` creation with the bind parameter and is not typically called by the end user.
        This function literally just groups all of the auto_* methods.  See `Form.auto_add_tables()`,
        `Form.auto_add_relationships()`, `Form.auto_map_elements()`, `Form.auto_map_events()`

        :param win: The PySimpleGUI window
        :returns:  None
        """
        logger.info('Binding Window to Form')
        self.window = win
        self.auto_map_elements(win)
        self.auto_map_events(win)
        self.update_elements()
        logger.debug('Binding finished!')


    def execute(self, query_string:str) -> ResultSet:
        """
        Convenience function to pass along to `SQLDriver.execute()`

        :param query_string: The query to execute
        :returns: A `ResultSet` object
        """
        return self.driver.execute(query_string)

    def commit(self) -> None:
        """
        Convenience function to pass along to `SQLDriver.commit()`

        :returns: None
        """
        self.driver.commit()

    def set_callback(self, callback_name:str, fctn:Callable[[Form,sg.Window],Union[None,bool]]) -> None:
        """
       Set `Form` callbacks. A runtime error will be raised if the callback is not supported.
       The following callbacks are supported:
           update_elements Called after elements are updated via `Form.update_elements()`. This allows for other GUI manipulation on each update of the GUI
           edit_enable Called before editing mode is enabled. This can be useful for asking for a password for example
           edit_disable Called after the editing mode is disabled
           {element_name} Called while updating MAPPED element.  This overrides the default element update implementation.
           Note that the {element_name} callback function needs to return a value to pass to Win[element].update()

       :param callback_name: The name of the callback, from the list above
       :param fctn: The function to call.  Note, the function must take in two parameters, a Form instance, and a PySimpleGUI.Window instance
       :returns: None
       """
        logger.info(f'Callback {callback_name} being set on Form')
        supported = ['update_elements', 'edit_enable', 'edit_disable']

        # Add in mapped elements
        for element in self.element_map:
            supported.append(element['element'].Key)

        # Add in other window elements
        for element in self.window.key_dict:
            supported.append(element)

        if callback_name in supported:
            self.callbacks[callback_name] = fctn
        else:
            raise RuntimeError(f'Callback "{callback_name}" not supported. callback: {callback_name} supported: {supported}')

    def add_query(self, name:str, table_name:str, pk_column:str, description_column:str, query_string:str='',
                  order_clause:str='') -> None:
        """
        Manually add a `Query` to the `Form`
        When you attach to a database, PySimpleSQL isn't aware of what it contains until this command is run
        Note that `Form.auto_add_queries()` does this automatically, which is called when a `Form` is created

        :param name: The name to give this `Query`.  Use frm['query_name'] to access it.
        :param table_name: The name of the table in the database
        :param pk_column: The primary key column of the table in the database
        :param description_column: The column to be used to display to users in listboxes, comboboxes, etc.
        :param query_string: The initial query for the table.  Auto generates "SELECT * FROM {table}" if none is passed
        :param order_clause: The initial sort order for the query
        :returns: None
        """
        self.queries.update({name: Query(name,self, table_name, pk_column, description_column, query_string, order_clause)})
        self[name].set_search_order([description_column])  # set a default sort order

    def add_relationship(self, join:str, child_table:str, fk_column:str, parent_table:str, pk_column:str, update_cascade) -> None:
        """
        Add a foreign key relationship between two queries of the database
        When you attach a database, PySimpleSQL isn't aware of the relationships contained until queries are
        added via `Form.add_query`, and the relationship of various tables is set with this function.
        Note that `Form.auto_add_relationships()` will do this automatically from the schema of the database,
        which also happens automatically when a `Form` is created.

        :param join: The join type of the relationship ('LEFT JOIN', 'INNER JOIN', 'RIGHT JOIN')
        :param child_table: The child table containing the foreign key
        :param fk_column: The foreign key column of the child table
        :param parent_table: The parent table containing the primary key
        :param pk_column: The primary key column of the parent table
        :param update_cascade: Automatically requery the child table if the parent table changes (ON UPDATE CASCADE in SQL)
        :returns: None
        """
        self.relationships.append(Relationship(join, child_table, fk_column, parent_table, pk_column, update_cascade, self.driver))

    def get_relationships_for_table(self, table:str) -> List[Relationship]:
        """
        Return the relationships for the passed-in table.

        :param table: The table to get relationships for
        :returns: A list of @Relationship objects
        """
        rel = []
        for r in self.relationships:
            if r.child_table == table.table:
                rel.append(r)
        return rel

    def get_cascaded_relationships(self, table:str) -> List[str]:
        """
        Return a unique list of the relationships for this table that should requery with this table.

        :param table: The table to get cascaded children for
        :returns: A unique list of table names
        """
        rel = []
        for r in self.relationships:
            if r.parent_table == table and r.update_cascade:
                rel.append(r.child_table)
        # make unique
        rel = list(set(rel))
        return rel

    def get_parent(self, table:str) -> Union[str,None]:
        """
        Return the parent table for the passed-in table
        :param table: The table (str) to get relationships for
        :returns: The name of the Parent table, or None if there is none
        """
        for r in self.relationships:
            if r.child_table == table and r.update_cascade:
                return r.parent_table
        return None
    
    def get_cascade_fk_column(self, table:str) -> Union[str,None]:
        """
        Return the cascade fk that filters for the passed-in table

        :param table: The table name of the child
        :returns: The name of the cascade-fk, or None
        """
        for qry in self.queries:
            for r in self.relationships:
                if r.child_table == self[table].table and r.update_cascade:
                    return r.fk_column
        return None
    
    def auto_add_queries(self, prefix_queries:str='') -> None:
        """
        Automatically add `Query` objects from the database by looping through the tables available and creating a
        `Query` object for each.
        When you attach to a sqlite database, PySimpleSQL isn't aware of what it contains until this command is run.
        This is called automatically when a `Form ` is created.
        Note that `Form.add_table()` can do this manually on a per-table basis.

        :param prefix_queries: Adds a prefix to the auto-generated `Query` names
        :returns: None
        """
        logger.info('Automatically generating queries for each table in the sqlite database')
        # Ensure we clear any current queries so that successive calls will not double the entries
        self.queries = {}
        table_names = self.driver.table_names()
        for table_name in table_names:
            column_info = self.driver.column_info(table_name)

            # auto generate description column.  Default it to the 2nd column,
            # but can be overwritten below
            description_column = column_info.col_name(1)
            for col in column_info.names():
                if col in ('name', 'description', 'title'):
                    description_column = col
                    break

            # Get our pk column
            pk_column = self.driver.pk_column(table_name)

            query_name=prefix_queries+table_name
            logger.debug(
                f'Adding query "{query_name}" on table {table_name} to Form with primary key {pk_column} and description of {description_column}')
            self.add_query(query_name,table_name, pk_column, description_column)
            self.queries[query_name].column_info = column_info

    # Make sure to send a list of table names to requery if you want
    # dependent queries to requery automatically
    def auto_add_relationships(self) -> None:
        """
        Automatically add a foreign key relationship between tables of the database. This is done by foregn key constrains
        within the database.  Automatically requery the child table if the parent table changes (ON UPDATE CASCADE in sql is set)
        When you attach a database, PySimpleSQL isn't aware of the relationships contained until tables are
        added and the relationship of various tables is set. This happens automatically during `Form` creation.
        Note that `Form.add_relationship()` can do this manually.

        :returns: None
        """
        logger.info(f'Automatically adding foreign key relationships')
        # Ensure we clear any current queries so that successive calls will not double the entries
        self.relationships = [] # clear any relationships already stored
        relationships = self.driver.relationships()
        for r in relationships:
            logger.debug(f'Adding relationship {r["from_table"]}.{r["from_column"]} = {r["to_table"]}.{r["to_column"]}')
            self.add_relationship('LEFT JOIN', r['from_table'], r['from_column'], r['to_table'], r['to_column'], r['update_cascade'])

    # Map an element to a Query.
    # Optionally a where_column and a where_value.  This is useful for key,value pairs!
    def map_element(self, element:sg.Element, query:Query, column:str, where_column:str=None, where_value:str=None) -> None:
        """
        Map a PySimpleGUI element to a specific `Query` column.  This is what makes the GUI automatically update to
        the contents of the database.  This happens automatically when a PySimpleGUI Window is bound to a `Form` by
        using the bind parameter of `Form` creation, or by executing `Form.auto_map_elements()` as long as the
        Table.column naming convention is used, This method can be used to manually map any element to any `Query` column
        regardless of naming convention.

        :param element: A PySimpleGUI Element
        :param query: A `Query` object
        :param column: The name of the column to bind to the element
        :param where_column: Used for ke, value shorthand TODO: expand on this
        :param where_value: Used for ey, value shorthand TODO: expand on this
        :returns: None
        """
        dic = {
            'element': element,
            'query': query,
            'column': column,
            'where_column': where_column,
            'where_value': where_value,
            # Element-level query clauses
            'where_clause': None,
            'order_clause': None,
            'join_clause': None
        }
        logger.debug(f'Mapping element {element.Key}')
        self.element_map.append(dic)

    def auto_map_elements(self, win:sg.Window, keys:List[str]=None) -> None:
        """
        Automatically map PySimpleGUI Elements to `Query` columns. A special naming convention has to be used for
        automatic mapping to happen.  Note that `Form.map_element()` can be used to manually map an Element to a column.
        Automatic mapping reilies on a special naming convention as well as certain data in the Elemen's metadata.
        The convenience functions `record()`, `selector()`, and `actions()` do this automatically and shoule be used in
        almost all cases to make elements that conform to this standard, but this information will allow you to do this
        manually if needed.
        For individual fields, Element keys must be named 'Table.column'. Additionally the metadata must contain a dict
        with the key of 'type' set to `TYPE_RECORD`.
        For selectors, the key can be named whatever you want, but the metadata must contain a dict with the key of
        'type' set to TPE_SELECTOR

        :param win: A PySimpleGUI Window
        :param keys: (optional) Limit the auto mapping to this list of Element keys
        :returns: None
        """
        logger.info('Automapping elements')
        # clear out any previously mapped elements to ensure successive calls doesn't produce duplicates
        self.element_map = []
        for key in win.key_dict.keys():
            element=win[key]

            # Skip this element if there is no metadata present
            if type(element.metadata) is not dict:
                continue


            # Process the filter to ensure this element should be mapped to this Form
            if element.metadata['filter'] == self.filter:
                element.metadata['Form'] = self

            # Skip this element if it's an event
            if element.metadata['type'] == TYPE_EVENT:
                continue

            if element.metadata['Form'] != self:
                continue
            # If we passed in a custom list of elements
            if keys is not None:
                if key not in keys: continue

            # Map Record Element
            if element.metadata['type']==TYPE_RECORD:
                # Does this record imply a where clause (indicated by ?) If so, we can strip out the information we need
                if '?' in key:
                    table_info, where_info = key.split('?')
                else:
                    table_info = key;
                    where_info = None
                try:
                    table, col = table_info.split('.')
                except ValueError:
                    table, col = table_info, None

                if where_info is None:
                    where_column=where_value=None
                else:
                    where_column,where_value=where_info.split('=')

                if table in self.queries:
                    if col in self[table].column_info:
                        # Map this element to table.column
                        self.map_element(element, self[table], col, where_column, where_value)

            # Map Selector Element
            elif element.metadata['type']==TYPE_SELECTOR:
                k=element.metadata['table']
                if k is None: continue
                if element.metadata['Form'] != self: continue
                if '?' in k:
                    query_info, where_info = k.split('?')
                    where_column,where_value=where_info.split('=')
                else:
                    query_info = k;
                    where_info = where_column = where_value = None
                query= query_info # TODO audit this code, as query is overwritten in the next line!

                if query in self.queries:
                    self[query].add_selector(element,query,where_column,where_value)

                    # Enable sorting if TableHeading  is present
                    if type(element) is sg.Table and 'TableHeading' in element.metadata:
                        table_heading:TableHeadings = element.metadata['TableHeading']
                        # We need a whole chain of things to happen when a heading is clicked on:
                        # 1 we need to run the ResultRow.sort_cycle() with the correct column name
                        # 2 we need to run TableHeading.update_headings() with the Table element, sort_column and sort_reverse
                        # 3 we need to run update_elements() to see the changes
                        def callback_wrapper(column_name, element=element, query=query):
                            # store the pk:
                            pk = self[query].get_current_pk()
                            sort_order = self[query].rows.sort_cycle(column_name)
                            self[query].set_by_pk(pk, update=True, dependents=False, skip_prompt_save=True)
                            table_heading.update_headings(element, column_name, sort_order)

                        table_heading.enable_sorting(element, callback_wrapper)


                else:
                    logger.debug(f'Can not add selector {str(element)}')

    def set_element_clauses(self,element:sg.Element, where_clause:str=None, order_clause:str=None) -> None:
        """
        Set the where and/or order clauses for the specified element in the element map

        :param element: A PySimpleGUI Element
        :param where_clause: (optional) The where clause to set
        :param order_clause: (optional) The order clause to set
        :returns: None
        """
        for e in self.element_map:
            if e['element']==element:
                e['where_clause']=where_clause
                e['order_clause']=order_clause

    def map_event(self, event:str, fctn:Callable[[None],None], table:str=None) -> None:
        """
        Manually map a PySimpleGUI event (returned by Window.read()) to a callable. The callable will execute
        when the event is detected by `Form.process_events()`. Most users will not have to manually map any events,
        as `Form.auto_map_events()` will create most needed events when a PySimpleGUI Window is bound to a `Form`
        by using the bind parameter of `Form` creation, or by executing `Form.auto_map_elements()`.

        :param event: The event to watch for, as returned by PySimpleGUI Window.read() (an element name for example)
        :param fctn: The callable to run when the event is detected. It should take no parameters and have no return value
        :table: (optional) currently not used
        :returns: None
        """
        dic = {
            'event': event,
            'function': fctn,
            'table': table
        }
        logger.debug(f'Mapping event {event} to function {fctn}')
        self.event_map.append(dic)

    def replace_event(self, event:str ,fctn:Callable[[None],None], table:str=None) -> None:
        """
        Replace an event that was manually mapped with `Form.auto_map_events()` or `Form.map_event()`. The callable will execute

        :param event: The event to watch for, as returned by PySimpleGUI Window.read() (an element name for example)
        :param fctn: The callable to run when the event is detected. It should take no parameters and have no return value
        :table: (optional) currently not used
        :returns: None
        """
        for e in self.event_map:
            if e['event'] == event:
                e['function'] = fctn
                e['table'] = table if table is not None else e['table']

    def auto_map_events(self, win:sg.Window) -> None:
        """
        Automatically map events. pysimplesql relies on certain events to function properly. This method maps all of
        the needed events to intelligently have the PySimpleGUI elements interact with the database. This includes things
        like record navigation (previous, next, etc.) and database actions (insert, delete, save, etc.).  Note that the
        event mapper is very general-purpose, and you ca add your own event triggers to the mapper using
        `Form.map_event()`, or even replace one of the auto-generated ones if you have specific needs by using
        `Form.replace_event()`

        :param win: A PySimpleGUI Window
        :returns: None
        """
        logger.info(f'Automapping events')
        # clear out any previously mapped events to ensure successive calls doesn't produce duplicates
        self.event_map = []

        for key in win.key_dict.keys():
            #key = str(key)  # sometimes I end up with an integer element 0? TODO: Research
            element = win[key]
            # Skip this element if there is no metadata present
            if type(element.metadata) is not dict:
                logger.debug(f'Skipping mapping of {key}')
                continue
            if element.metadata['Form'] != self:
                continue
            if element.metadata['type'] == TYPE_EVENT:
                event_type=element.metadata['event_type']
                query=element.metadata['query']
                function=element.metadata['function']

                funct=None

                event_query=query if query in self.queries else None
                if event_type==EVENT_FIRST:
                    if event_query: funct=self[event_query].first
                elif event_type==EVENT_PREVIOUS:
                    if event_query: funct=self[event_query].previous
                elif event_type==EVENT_NEXT:
                    if event_query: funct=self[event_query].next
                elif event_type==EVENT_LAST:
                    if event_query: funct=self[event_query].last
                elif event_type==EVENT_SAVE:
                    if event_query: funct=self[event_query].save_record
                elif event_type==EVENT_INSERT:
                    if event_query: funct=self[event_query].insert_record
                elif event_type==EVENT_DELETE:
                    if event_query: funct=self[event_query].delete_record
                elif event_type==EVENT_DUPLICATE:
                    if event_query: funct=self[event_query].duplicate_record
                elif event_type==EVENT_EDIT_PROTECT_DB:
                    self.edit_protect() # Enable it!
                    funct=self.edit_protect
                elif event_type==EVENT_SAVE_DB:
                    funct=self.save_records
                elif event_type==EVENT_SEARCH:
                    # Build the search box name
                    search_element,command=key.split('.')
                    search_box=f'{search_element}.input_search'
                    if event_query: funct=functools.partial(self[event_query].search, search_box)
                #elif event_type==EVENT_SEARCH_DB:
                elif event_type == EVENT_QUICK_EDIT:
                    t,c,e=key.split('.') #table, column, event
                    referring_table=query
                    query=self[query].get_related_table_for_column(c)
                    funct=functools.partial(self[query].quick_editor,self[referring_table].get_current,c)
                elif event_type == EVENT_FUNCTION:
                    funct=function
                else:
                    logger.debug(f'Unsupported event_type: {event_type}')

                if funct is not None:
                    self.map_event(key, funct, event_query)


    def edit_protect(self) -> None:
        """
        The edit protect system allows records to be protected from accidental editing by disabling the insert, delete,
        duplicate and save buttons on the GUI.  A button to toggle the edit protect mode can easily be added by using
        the `actions()` convenience function.

        :returns: None
        """
        logger.debug('Toggling edit protect mode.')
        # Callbacks
        if self._edit_protect:
            if 'edit_enable' in self.callbacks.keys():
                if not self.callbacks['edit_enable'](self, self.window):
                    return
        else:
            if 'edit_disable' in self.callbacks.keys():
                if not self.callbacks['edit_disable'](self, self.window):
                    return

        self._edit_protect = not self._edit_protect
        self.update_elements(edit_protect_only=True)

    def get_edit_protect(self) -> bool:
        """
        Get the current edit protect state

        :returns: True if edit protect is enabled, False if not enabled
        """
        return self._edit_protect

    def prompt_save(self, autosave:bool=False) -> Union[PROMPT_PROCEED, PROMPT_DISCARDED, PROMPT_NONE]:
        """
        Prompt to save if any GUI changes are found the affect any table on this form. The helps prevent data entry
        loss when performing an action that changes the current record of a `Query`.

        :param autosave: True to autosave when changes are found without prompting the user
        :returns: One of the prompt constant values: PROMPT_PROCEED, PROMPT_DISCARDED, PROMPT_NONE
        """
        user_prompted = False # Has the user been prompted yet?
        for q in self.queries:
            if self[q]._prompt_save is False:
                continue

            if self[q].records_changed(recursive=False): # don't check children
                # we will only show the popup once, regardless of how many queries have changed
                if not user_prompted:
                    user_prompted = True
                    if autosave or self.autosave:
                        save_changes = 'Yes'
                    else:
                        save_changes = sg.popup_yes_no('You have unsaved changes! Would you like to save them first?')

                    if save_changes != 'Yes':
                        # update the elements to erase any GUI changes, since we are choosing not to save
                        for q in self.queries.keys():
                            self[q].rows.purge_virtual()
                        self.update_elements()
                        return PROMPT_SAVE_DISCARDED # We did have a change, regardless if the user chose not to save
                    break
        if user_prompted:
            self.save_records(check_prompt_save=True)
        return PROMPT_SAVE_PROCEED if user_prompted else PROMPT_SAVE_NONE

    def save_records(self, table_name:str=None, cascade_only:bool=False, check_prompt_save:bool=False,) \
                    -> Union[SAVE_SUCCESS,SAVE_FAIL,SAVE_NONE]:
        """
        Save records of all `Query` objects` associated with this `Form`.

        :param table_name: Name of table to save, as well as any cascaded relationships. Used in `Query.prompt_save()`
        :param cascade_only: Save only tables with cascaded relationships. Default False.
        :param check_prompt_save: Passed to `Query.save_record_recursive` to check if individual `Query` has prompt_save enabled.
                                  Used when `Query.save_records()` is called from `Form.prompt_save()`.
        :returns: result - can be used with RETURN BITMASKS
        """
        if check_prompt_save: logger.debug(f'Saving records in all queries that allow prompt_save...')
        else: logger.debug(f'Saving records in all queries...')

        result = 0
        show_message = True
        failed_tables = []
        
        if table_name: tables = [table_name] # if passed single table
        # for cascade_only, build list of top-level queries that have children
        elif cascade_only: tables = [q for q in self.queries
                                     if len(self.get_cascaded_relationships(table=q))
                                     and self.get_parent(q) is None]
        # default behavior, build list of top-level queries (ones without a parent)
        else: tables = [q for q in self.queries.keys() if self.get_parent(q) is None]
        
        # call save_record_recursive on tables, which saves from last to first.
        result_list = []
        for q in tables:
            res = self[q].save_record_recursive(results={},display_message=False,check_prompt_save=check_prompt_save)
            result_list.append(res)
        
        # flatten list of result dicts
        results = {k: v for d in result_list for k, v in d.items()}
        logger.debug(f'Form.save_records - results of tables - {results}')

        # get tables that failed
        for t, res in results.items():
            if not res & SHOW_MESSAGE: show_message = False # Only one instance of not showing the message hides all
            if res & SAVE_FAIL: failed_tables.append(t)
            result |= res

        # Build a descriptive message, since the save spans many tables potentially
        msg = ''
        tables = ', '.join(failed_tables)
        if result & SAVE_FAIL:
            if result & SAVE_SUCCESS:
                msg = f"Some updates saved successfully; "
            msg += f"There was a problem saving updates to the following tables: {tables}"
        elif result & SAVE_SUCCESS:
            msg = 'Updates saved successfully.'
        else:
            msg = 'There was nothing to update.'
        if show_message: sg.popup_quick_message(msg, keep_on_top=True)
        return result

    def set_prompt_save(self, value: bool) -> None:
        """
        Set the prompt to save action when navigating records for all `Query` objects associated with this `Form`

        :param value: a boolean value, True to prompt to save, False for no prompt to save
        :returns: None
        """
        for q in self.queries:
            self[q].set_prompt_save(value)

    def update_elements(self, table_name:str=None, edit_protect_only:bool=False, omit_elements:List[str]=[]) -> None:
        """
        Updated the GUI elements to reflect values from the database for this `Form` instance only
        Not to be confused with the main `update_elements()`, which updates GUI elements for all `Form` instances.

        :param table_name: (optional) name of table to update elements for, otherwise updates elements for all queries
        :param edit_protect_only: (optional) If true, only update items affected by edit_protect
        :param omit_elements: A list of elements to omit updating
        :returns: None
        """
        msg='edit protect' if edit_protect_only else 'PySimpleGUI'
        logger.debug(f'update_elements(): Updating {msg} elements')
        win = self.window
        # Disable/Enable action elements based on edit_protect or other situations
        for t in self.queries:
            if table_name and t != table_name:
                continue
            # disable mapped elements for this table if there are no records in this table or edit protect mode
            disable = len(self[t].rows) == 0 or self._edit_protect
            self.update_element_states(t, disable)
            
            for m in (m for m in self.event_map if m['table'] == t):
                # Disable delete/duplicate and mapped elements for this table if there are no records in this table or edit protect mode
                if ('.table_delete' in m['event']) or ('.table_duplicate' in m['event']):
                    disable = len(self[t].rows) == 0 or self._edit_protect
                    win[m['event']].update(disabled=disable)
                    
                elif '.table_first' in m['event']:
                    disable = len(self[t].rows) < 2 or self[t].current_index == 0
                    win[m['event']].update(disabled=disable)
                
                elif '.table_previous' in m['event']:
                    disable = len(self[t].rows) < 2 or self[t].current_index == 0
                    win[m['event']].update(disabled=disable)
                    
                elif '.table_next' in m['event']:
                    disable = len(self[t].rows) < 2 or (self[t].current_index == len(self[t].rows) - 1)
                    win[m['event']].update(disabled=disable)
                    
                elif '.table_last' in m['event']:
                    disable = len(self[t].rows) < 2 or (self[t].current_index == len(self[t].rows) - 1)
                    win[m['event']].update(disabled=disable)

                # Disable insert on children with no parent records or edit protect mode
                parent = self.get_parent(t)
                if parent is not None:
                    disable = len(self[parent].rows) == 0 or self._edit_protect
                else:
                    disable = self._edit_protect
                if '.table_insert' in m['event']:
                    if m['table'] == t:
                        win[m['event']].update(disabled=disable)

                # Disable db_save when needed
                disable = self._edit_protect
                if '.db_save' in m['event']:
                    win[m['event']].update(disabled=disable)

                # Disable table_save when needed
                disable = self._edit_protect
                if '.table_save' in m['event']:
                    win[m['event']].update(disabled=disable)

                # Enable/Disable quick edit buttons
                if '.quick_edit' in m['event']:
                    win[m['event']].update(disabled=disable)
        if edit_protect_only: return


        # Render GUI Elements
        # d= dictionary (the element map dictionary)
        for d in self.element_map:
            # If the optional query parameter was passed, we will only update elements bound to that table
            if table_name is not None:
                if d['query'].table != table_name:
                    continue
            # skip updating this element if requested
            if d['element'] in omit_elements: continue

            # Show the Required Record marker if the column has notnull set and this is a virtual row
            marker_key = d['element'].key + '.marker'
            try:
                if self[d['query'].table].get_current_row().virtual:
                    # get the column name from the key
                    col = marker_key.split(".")[1]
                    # get notnull from the column info
                    if col in self[d['query'].table].column_info.names():
                        if self[d['query'].table].column_info[col].notnull:
                            self.window[marker_key].update(visible=True)
                else:
                    self.window[marker_key].update(visible=False)
            except AttributeError:
                self.window[marker_key].update(visible=False)


            updated_val = None
            # If there is a callback for this element, use it
            for ekey in self.callbacks:
                if ekey == d['element'].key:
                    self.callbacks[d['element'].Key]()

            elif d['where_column'] is not None:
                # We are looking for a key,value pair or similar.  Lets sift through and see what to put
                updated_val=d['query'].get_keyed_value(d['column'], d['where_column'], d['where_value'])
                if type(d['element']) in [sg.PySimpleGUI.CBox]: # TODO, may need to add more??
                    updated_val=int(updated_val)

            elif type(d['element']) is sg.PySimpleGUI.Combo:
                # Update elements with foreign queries first
                # This will basically only be things like comboboxes
                # TODO: move this to only compute if something else changes?
                # see if we can find the relationship to determine which table to get data from
                target_table=None
                rels = self.get_relationships_for_table(d['query'])
                for rel in rels:
                    if rel.fk_column == d['column']:
                        target_table = self[rel.parent_table]
                        pk_column = target_table.pk_column
                        description = target_table.description_column
                        break

                if target_table==None:
                    logger.info(f"Error! Cound not find a related query for element {d['element'].key} bound to query {d['query'].table}, column: {d['column']}")
                    # we don't want to update the list in this case, as it was most likely supplied and not tied to a query
                    updated_val=d['query'][d['column']]

                # Populate the combobox entries
                else:
                    lst = []
                    for row in target_table.rows:
                        lst.append(ElementRow(row[pk_column], row[description]))
    
                    # Map the value to the combobox, by getting the description_column and using it to set the value
                    for row in target_table.rows:
                        if row[target_table.pk_column] == d['query'][rel.fk_column]:
                            for entry in lst:
                                if entry.get_pk() == d['query'][rel.fk_column]:
                                    updated_val = entry
                                    break
                            break
                    d['element'].update(values=lst)
            elif type(d['element']) is sg.PySimpleGUI.Table:
                # Tables use an array of arrays for values.  Note that the headings can't be changed.
                values = d['query'].table_values()
                # Select the current one
                pk = d['query'].get_current_pk()

                found = False
                if len(values):
                    index = [[v[0] for v in values].index(pk)] # set index to pk
                    pk_position = index[0] / len(values)  # calculate pk percentage position
                    found = True
                else: # if empty
                    index = []
                    pk_position = 0

                # update element
                d['element'].update(values=values, select_rows=index)
                # set vertical scroll bar to follow selected element
                if len(index): d['element'].set_vscroll_position(pk_position)

                eat_events(self.window)
                continue

            elif type(d['element']) is sg.PySimpleGUI.InputText or type(d['element']) is sg.PySimpleGUI.Multiline:
                # Update the element in the GUI
                # For text objects, lets clear it first...
                d['element'].update('')  # HACK for sqlite query not making needed keys! This will blank it out at least
                updated_val = d['query'][d['column']]

            elif type(d['element']) is sg.PySimpleGUI.Checkbox:
                updated_val = d['query'][d['column']]
            elif type(d['element']) is sg.PySimpleGUI.Image:
                val = d['query'][d['column']]

                try:
                    val=eval(val)
                except:
                    # treat it as a filename
                    d['element'].update(val)
                else:
                    # update the bytes data
                    d['element'].update(data=val)
                updated_val=None # Prevent the update from triggering below, since we are doing it here
            else:
                sg.popup(f'Unknown element type {type(d["element"])}')

            # Finally, we will update the actual GUI element!
            if updated_val is not None:
                d['element'].update(updated_val)

        # ---------
        # SELECTORS
        # ---------
        # We can update the selector elements
        # We do it down here because it's not a mapped element...
        # Check for selector events
        for q, table in self.queries.items():
            if table_name is not None:
                if q != table_name:
                    continue
            if len(table.selector):
                for e in table.selector:
                    logger.debug(f'update_elements: SELECTOR FOUND')
                    # skip updating this element if requested
                    if e['element'] in omit_elements: continue

                    element=e['element']
                    logger.debug(f'{type(element)}')
                    pk_column = table.pk_column
                    description_column = table.description_column
                    for ekey in self.callbacks:
                        if ekey == element.Key:
                            self.callbacks[element.Key]()

                    if type(element) == sg.PySimpleGUI.Listbox or type(element) == sg.PySimpleGUI.Combo:
                        logger.debug(f'update_elements: List/Combo selector found...')
                        lst = []
                        for r in table.rows:
                            if e['where_column'] is not None:
                                if str(r[e['where_column']]) == str(e['where_value']): # TODO: This is kind of a hackish way to check for equality...
                                    lst.append(ElementRow(r[pk_column], r[description_column]))
                                else:
                                    pass
                            else:
                                lst.append(ElementRow(r[pk_column], r[description_column]))

                        element.update(values=lst, set_to_index=table.current_index)

                        # set vertical scroll bar to follow selected element (for listboxes only)
                        if type(element) == sg.PySimpleGUI.Listbox:
                            try:
                                element.set_vscroll_position(table.current_index / len(lst))
                            except ZeroDivisionError:
                                element.set_vscroll_position(0)

                    elif type(element) == sg.PySimpleGUI.Slider:
                        # We need to re-range the element depending on the number of records
                        l = len(table.rows)
                        element.update(value=table._current_index + 1, range=(1, l))

                    elif type(element) is sg.PySimpleGUI.Table:
                        logger.debug(f'update_elements: Table selector found...')
                        # Populate entries
                        try:
                            column_names = element.metadata['TableHeading'].column_names()
                        except KeyError:
                            column_names = None # default to all columns

                        values = table.table_values(column_names, mark_virtual=True)

                        # Get the primary key to select.  We have to use the list above instead of getting it directly
                        # from the table, as the data has yet to be updated
                        pk = table.get_current_pk()

                        found = False
                        if len(values):
                            index = [[v.pk for v in values].index(pk)] # set to index by pk
                            pk_position = index[0] / len(values)  # calculate pk percentage position
                            found = True
                        else: # if empty
                            index = []
                            pk_position = 0

                        logger.debug(f'Selector:: index:{index} found:{found}')
                        # update element
                        element.update(values=values,select_rows=index)
                        # set vertical scroll bar to follow selected element
                        element.set_vscroll_position(pk_position)

                        eat_events(self.window)

        # Run callbacks
        if 'update_elements' in self.callbacks.keys():
            # Running user update function
            logger.info('Running the update_elements callback...')
            self.callbacks['update_elements'](self, self.window)


    def requery_all(self, select_first:bool=True, filtered:bool=True, update:bool=True, dependents:bool=True) -> None:
        """
        Requeries all `Query` objects associated with this `Form`
        This effectively re-loads the data from the database into `Query` objects

        :param select_first: passed to `Query.requery()` -> `Query.first()`. If True, the first record will be selected
                             after the requery
        :param filtered: passed to `Query.requery()`. If True, the relationships will be considered and an appropriate
                        WHERE clause will be generated. False will display all records from the table.
        :param update: passed to `Query.requery()` -> `Query.first()` to `Form.update_elements()`. Note that the
                       select_first parameter must = True to use this parameter.
        :param dependents: passed to `Query.requery()` -> `Query.first()` to `Form.requery_dependents()`. Note that the
                           select_first parameter must = True to use this parameter.
        :returns: None
        """
        # TODO: It would make sense to reorder these, and put filtered first, then select_first/update/dependents
        logger.info('Requerying all queries')
        for k in self.queries.keys():
            if self.get_parent(k) is None:
                self[k].requery(select_first=select_first, filtered=filtered, update=update, dependents=dependents)

    def process_events(self, event:str, values:list) -> bool:
        """
        Process mapped events for this specific `Form` instance.

        Not to be confused with the main `process_events()`, which processes events for ALL `Form` instances.
        This should be called once per iteration in your event loop
        Note: Events handled are responsible for requerying and updating elements as needed

        :param event: The event returned by PySimpleGUI.read()
        :param values: the values returned by PySimpleGUI.read()
        :returns: True if an event was handled, False otherwise
        """
        if self.window is None:
            logger.info(f'***** Form appears to be unbound.  Do you have frm.bind(win) in your code? ***')
            return False
        elif event:
            for e in self.event_map:
                if e['event'] == event:
                    logger.debug(f"Executing event {event} via event mapping.")
                    e['function']()
                    logger.debug(f'Done processing event!')
                    return True

            # Check for  selector events
            for k, table in self.queries.items():
                if len(table.selector):
                    for e in table.selector:
                        element=e['element']
                        if element.key == event and len(table.rows) > 0:
                            changed=False # assume that a change will not take place
                            if type(element) == sg.PySimpleGUI.Listbox:
                                row = values[element.Key][0]
                                table.set_by_pk(row.get_pk())
                                changed=True
                            elif type(element) == sg.PySimpleGUI.Slider:
                                table.set_by_index(int(values[event]) - 1)
                                changed=True
                            elif type(element) == sg.PySimpleGUI.Combo:
                                row = values[event]
                                table.set_by_pk(row.get_pk())
                                changed=True
                            elif type(element) is sg.PySimpleGUI.Table:
                                index = values[event][0]
                                pk = self.window[event].Values[index].pk
                                table.set_by_pk(pk, True, omit_elements=[element]) # no need to update the selector!
                                changed=True
                            if changed:
                                if 'record_changed' in table.callbacks.keys():
                                    table.callbacks['record_changed'](self, self.window)
                            return changed
        return False

    def update_element_states(self, table_name:str, disable:bool=None, visible:bool=None) -> None:
        """
        Disable/enable and/or show/hide all elements assocated with a table.

        :param table_name: table name assocated with elements to disable/enable
        :param disable: True/False to disable/enable element(s), None for no change
        :param visible: True/False to make elements visible or not, None for no change
        :returns: None
        """
        for c in self.element_map:
            if c['query'].table != table_name:
                continue
            element=c['element']
            if type(element) is sg.PySimpleGUI.InputText or type(element) is sg.PySimpleGUI.MLine or type(
                    element) is sg.PySimpleGUI.Combo or type(element) is sg.PySimpleGUI.Checkbox:
                #if element.Key in self.window.key_dict.keys():
                logger.debug(f'Updating element {element.Key} to disabled: {disable}, visible: {visible}')
                if disable is not None:
                    element.update(disabled=disable)
                if visible is not None:
                    element.update(visible=visible)

# ======================================================================================================================
# MAIN PYSIMPLESQL UTILITY FUNCTIONS
# ======================================================================================================================
# These functions exist as utilities to the pysimplesql module
# This is a dummy class for documenting utility functions
class Utility():
    """
    Utility functions are a collection of functions and classes that directly improve on aspects of the pysimplesql
    module.

    See the documentation for the following utility functions:
    `sprocess_events()`, `supdate_elements()`, `bind()`, `get_record_info()`, `simple_transform()`, `KeyGen`,

    Note: This is a dummy class that exists purely to enhance documentation and has no use to the end user.
    """
    pass

def process_events(event:str, values:list) -> bool:
    """
        Process mapped events for ALL Form instances.

        Not to be confused with `Form.process_events()`, which processes events for individual `Form` instances.
        This should be called once per iteration in your event loop
        Note: Events handled are responsible for requerying and updating elements as needed

        :param event: The event returned by PySimpleGUI.read()
        :param values: the values returned by PySimpleGUI.read()
        :returns: True if an event was handled, False otherwise
        """
    handled=False
    for i in Form.instances:
        if i.process_events(event, values): handled=True
    return handled

def update_elements(query:str=None, edit_protect_only:bool=False) -> None:
    """
    Updated the GUI elements to reflect values from the database for ALL Form instances
    Not to be confused with `Form.update_elements()`, which updates GUI elements for individual `Form` instances.

    :param query: (optional) name of `Query` to update elements for, otherwise updates elements for all queries
    :param edit_protect_only: (optional) If true, only update items affected by edit_protect
    :returns: None
    """
    for i in Form.instances:
        i.update_elements(query, edit_protect_only)

def bind(win:sg.Window) -> None:
    """
    Bind ALL forms to window
    Not to be confused with `Form.bind()`, which binds specific forms to the window.
    
    :param win: The PySimpleGUI window to bind all forms to
    :returns: None
    """
    for i in Form.instances:
        i.bind(win)

def get_record_info(record:str) -> Tuple[str,str]:
    """
    Take a table.column string and return a tuple of the same

    :param record: A table.column string that needs separated
    :returns: (table,column) Tuple of table and column
    """
    return record.split('.')

def simple_transform(self,row,encode): # TODO: why is self here?
    """
    Convenience transform function that makes it easier to add transforms to your records.
    """
    for col, function in self._simple_transform.items():
        if col in row:
            msg = f'Transforming {col} from {row[col]}'
            if encode == pysimplesql.TFORM_DECODE:
                row[col] = function['decode'](row,col)
            else:
                row[col] = function['encode'](row,col)
            logger.debug(f'{msg} to {row[col]}')

class KeyGen():
    """
    The keygen system provides a mechanism to generate unique keys for use as PySimpleGUI element keys.
    This is needed because many auto-generated items will have the same name.  If for example you had two save buttons on
    the screen at the same time, they must have unique names.  The keygen will append a separator and an incremental number
    to keys that would otherwise be duplicates. A global KeyGen instance is created automatically, see `keygen` for info.
    """
    def __init__(self, separator=':'):
        """
        Create a new KeyGen instance

        :param separator: The default separator that goes between the key and the incremental number
        :returns: None
        """
        self._keygen = {}
        self._separator = separator

    def get(self, key:str, separator:str=None) -> str:
        """
        Get a generated key from the `KeyGen`

        :param key: The key from which to generate the new key.  If the key has not been used before, then it will be
                    returned unmodified.  For each successive call with the same key, it will be appended with a the
                    separator character and an incremental number.  For example, if the key 'button' was passed to
                    `KeyGen.get()` 3 times in a row, then the keys 'button', 'button:1', and 'button:2' would be
                    returned respectively.
        param separator: (optional) override the default separator wth this separator
        :returns: None
        """
        if separator is None: separator = self._separator

        # Generate a unique key by attaching a sequential integer to the end
        if key not in self._keygen:
            self._keygen[key] = 0
        return_key = key
        if self._keygen[key] > 0: return_key += f'{separator}{str(self._keygen[key])}'  # only modify the key if it is a duplicate!
        logger.debug(f'Key generated: {return_key}')
        self._keygen[key] += 1
        return return_key

    def reset_key(self, key: str) -> None:
        """
        Reset the generation sequence for the supplied key

        :param key: The base key to reset te sequence for
        """
        try:
            del self._keygen[key]
        except KeyError:
            pass

    def reset(self) -> None:
        """
        Reset the entire `KeyGen` and remove all keys

        :returns: None
        """
        self._keygen = {}

    def reset_from_form(self, frm:Form) -> None:
        """
        Reset keys from the keygen that were from mapped PySimpleGUI elements of that `Form`

        :param frm: The `Form` from which to get the list of mapped elements
        :returns: None
        """
        # reset keys related to form
        for e in frm.element_map:
            self.reset_key(e['element'].key)

# create a global KeyGen instance
keygen = KeyGen(separator=':')
"""This is a global keygen instance for general purpose use. See `KeyGen` for more info"""

# ----------------------------------------------------------------------------------------------------------------------
# CONVENIENCE FUNCTIONS
# ----------------------------------------------------------------------------------------------------------------------
# Convenience functions aide in building PySimpleGUI interfaces that work well with pysimplesql.
# TODO: How to save Form in metadata?  Perhaps give forms names and reference them that way??
#       For exapmle - give forms names!  and reference them by name string
#       They could even be converted later to a real form during form creation?

# This is a dummy class for documenting convenience functions
class Convenience():
    """
    Convenience functions are a collection of functions and classes that aide in building PySimpleGUI layouts that
    conform to pysimplesql standards so that your database application is up and running quickly, and with all the great
    automatic functionality pysimplesql has to offer.
    See the documentation for the following convenience functions:
    `set_label_size()`, `set_element_size()`, `set_mline_size()`, `record()`, `selector()`, `actions()`, `TableHeadings`

    Note: This is a dummy class that exists purely to enhance documentation and has no use to the end user.
    """
    pass

# Global variables to set default sizes for the record function below
_default_label_size = (15, 1)
_default_element_size = (30, 1)
_default_mline_size = (30, 7)

def set_label_size(w:int, h:int) -> None:
    """
    Sets the default label (text) size when `record()` is used". A label is static text that is displayed near the
    element to describe what it is.

    :param w: the width desired
    :param h: the height desired
    :returns: None
    """
    global _default_label_size
    _default_label_size = (w, h)

def set_element_size(w:int, h:int) -> None:
    """
    Sets the default element size when `record()` is used.  The size parameter of `record()` will override this

    :param w: the width desired
    :param h: the height desired
    :returns: None
    """
    global _default_element_size
    _default_element_size = (w, h)

def set_mline_size(w:int, h:int) -> None:
    """
    Sets the default multi-line text size when `record()` is used.  The size parameter of `record()` will override this

    :param w: the width desired
    :param h: the height desired
    :returns: None
    """
    global _default_mline_size
    _default_mline_size = (w, h)



def record(key:str, element:sg.Element=sg.I, size:Tuple[int,int]=None, label:str='', no_label:bool=False,
           label_above:bool=False, quick_editor:bool=True, filter=None, **kwargs) -> sg.Column:
    """
    Convenience function for adding PySimpleGUI elements to the Window so they are properly configured for pysimplesql
    The automatic functionality of pysimplesql relies on PySimpleGUI elements to have the key {Query}.{name}, as well as
    have some accompanying metadata so that the `Form.auto_add_elements()` can pick them up.
    This convenience function will create a text label, along with a element with the above naming convention and
    metadata set up for you.
    See `set_label_size()`, `set_element_size()` and `set_mline_size()` for setting default sizes of these elements.

    :param key: The key must be named table.column in order to map to the database properly
    :param element: (optional) The element type desired (defaults to PySimpleGUI.Input)
    :param size: Overrides the default element size that was set with `set_element_size()` for this element only
    :param label: The text/label will automatically be generated from the column name. If a different text/label is
                 desired, it can be specified here.
    :param no_label: Do not automatically generate a label for this element
    :param label_above: Place the label above the element instead of to the left of the element
    :param quick_editor: For records that reference another table, place a quick edit button next to the element
    :param filter: Can be used to reference different `Form`s in the same layout.  Use a matching filter when creating
            the `Form` with the filter parameter.
    :param kwargs: Any additional arguments will be passed on to the PySimpleGUI element
    :returns: Element(s) to be used in the creation of PySimpleGUI layouts.  Note that this function actually creates
              multiple Elements wrapped in a PySimpleGUI Column, but can be treated as a single Element.
    """
    # TODO: See what the metadata does after initial setup is complete - is it needed anymore?
    global keygen

    # Does this record imply a where clause (indicated by ?) If so, we can strip out the information we need
    if '?' in key:
        query_info, where_info = key.split('?')
        label_text = where_info.split('=')[1].replace('fk', '').replace('_', ' ').capitalize() + ':'
    else:
        query_info = key
        where_info = None
        label_text = query_info.split('.')[1].replace('fk', '').replace('_', ' ').capitalize() + ':'
    query, column = query_info.split('.')


    key=keygen.get(key)

    if 'values' in kwargs:
        first_param=kwargs['values']
        del kwargs['values']  # make sure we don't put it in twice
    else:
        first_param=''

    if element.__name__ == 'Multiline':
        layout_element = element(first_param, key=key, size=size or _default_mline_size, metadata={'type': TYPE_RECORD, 'Form': None, 'filter': filter}, **kwargs)
    else:
        layout_element = element(first_param, key=key, size=size or _default_element_size, metadata={'type': TYPE_RECORD, 'Form': None, 'filter': filter}, **kwargs)
    layout_label =  sg.T(label_text if label == '' else label, size=_default_label_size)
    layout_marker = sg.Column([[sg.T(icon.marker_required, key=f'{key}.marker', text_color = icon.marker_required_color, visible=True)]], pad=(0,0)) # Marker for required (notnull) records
    if no_label:
        layout = [[layout_marker, layout_element]]
    elif label_above:
        layout = [[layout_label], [layout_marker, layout_element]]
    else:
        layout = [[layout_label , layout_marker, layout_element]]
    # Add the quick editor button where appropriate
    if element == sg.Combo and quick_editor:
        meta = {'type': TYPE_EVENT, 'event_type': EVENT_QUICK_EDIT, 'query': query, 'function': None, 'Form': None, 'filter': filter}
        if type(icon.quick_edit) is bytes:
            layout[-1].append(sg.B('', key=keygen.get(f'{key}.quick_edit'), size=(1, 1), image_data=icon.quick_edit, metadata=meta))
        else:
            layout[-1].append(sg.B(icon.quick_edit, key=keygen.get(f'{key}.quick_edit'), metadata=meta, use_ttk_buttons = True))
    #return layout
    return sg.Col(layout=layout, pad=(0,0)) # TODO: Does this actually need wrapped in a sg.Col???

def actions(key:str, table_name:str, default:bool=True, edit_protect:bool=None, navigation:bool=None, insert:bool=None,
            delete:bool=None, duplicate:bool=None, save:bool=None, search:bool=None, search_size:Tuple[int,int]=(30, 1),
            bind_return_key:bool=True, filter:str=None) -> sg.Column:
    """
    Allows for easily adding record navigation and record action elements to the PySimpleGUI window
    The navigation elements are generated automatically (first, previous, next, last and search).  The action elements
    can be customized by selecting which ones you want generated from the parameters available.  This allows full control
    over what is available to the user of your database application. Check out `ThemePacks` to give any of these auto
    generated controls a custom look!

    :param key: The key to give these controls. Note that this is a root key, and the various elements will build from
                this root key.  For example, if the root key 'action' is used, then the following element keys will be
                generated (depending on parameters set) of:
                action.edit_protect, action.db_save, action.table_first, action.table_previous, action.table_next,
                action.table_last, action.table_duplicate, action.table_insert, action.table_delete, action.input_search,
                action.table_search. Also note that these autogenerated keys also pass through the `KeyGen`, so it's
                possible that these keys could be action.table_last:1, action.table_last:2, etc.
    :param table_name: The table name that this "element" will provide actions for
    :param default: Default edit_protect, navigation, insert, delete, save and search to either true or false (defaults to True)
                    The individual keyword arguments will trump the default parameter.  This allows for starting with
                    all actions defualted False, then individual ones can be enabled with True - or the opposite by
                    defaulting them all to True, and disabling the ones not needed with False.
    :param edit_protect: An edit protection mode to prevent accidental changes in the database. It is a button that toggles
                    the ability on and off to prevent accidental changes in the database by enabling/disabling the insert,
                    edit, dubplicate, delete and save buttons.
    :param navigation: The standard << < > >> (First, previous, next, last) buttons for navigation
    :param insert: Button to insert new records
    :param delete: Button to delete current record
    :param duplicate: Button to duplicate current record
    :param save: Button to save record.  Note that the save button feature saves changes made to any table, therefore
                 only one save button is needed per window.
    :param search: A search Input element. Size can be specified with the `search_size` parameter
    :param search_size: The size of the search input element
    :param bind_return_key: Bind the return key to the search button. Defaults to true
    :returns: An element to be used in the creation of PySimpleGUI layouts.  Note that this is technically multiple
              elements wrapped in a PySimpleGUI.Column, but acts as one element for the purpose of layout building.
    """
    global keygen
    edit_protect = default if edit_protect is None else edit_protect
    navigation = default if navigation is None else navigation
    insert = default if insert is None else insert
    delete = default if delete is None else delete
    duplicate = default if duplicate is None else duplicate
    save = default if save is None else save
    search = default if search is None else search

    layout = []
    meta = {'type': TYPE_EVENT, 'event_type': None, 'query': None, 'function': None, 'Form': None, 'filter': filter}

    # Form-level events
    if edit_protect:
        meta = {'type': TYPE_EVENT, 'event_type': EVENT_EDIT_PROTECT_DB, 'query': None, 'function': None, 'Form': None, 'filter': filter}
        if type(icon.edit_protect) is bytes:
            layout.append(sg.B('', key=keygen.get(f'{key}.edit_protect'), size=(1, 1), button_color=('orange', 'yellow'),
                               image_data=icon.edit_protect, metadata=meta))
        else:
            layout.append(sg.B(icon.edit_protect, key=keygen.get(f'{key}.edit_protect'), metadata=meta, use_ttk_buttons = True))
    if save:
        meta = {'type': TYPE_EVENT, 'event_type': EVENT_SAVE_DB, 'query': table_name, 'function': None, 'Form': None, 'filter': filter}
        if type(icon.save) is bytes:
            layout.append(sg.B('', key=keygen.get(f'{key}.db_save'), size=(1, 1), button_color=('white', 'white'), image_data=icon.save,
                               metadata=meta))
        else:
            layout.append(sg.B(icon.save, key=keygen.get(f'{key}.db_save'), metadata=meta, use_ttk_buttons = True))

    # Query-level events
    if navigation:
        # first
        meta = {'type': TYPE_EVENT, 'event_type': EVENT_FIRST, 'query': table_name, 'function': None, 'Form': None, 'filter': filter}
        if type(icon.first) is bytes:
            layout.append(sg.B('', key=keygen.get(f'{key}.table_first'), size=(1, 1), image_data=icon.first, metadata=meta))
        else:
            layout.append(sg.B(icon.first, key=keygen.get(f'{key}.table_first'), metadata=meta, use_ttk_buttons = True))
        # previous
        meta = {'type': TYPE_EVENT, 'event_type': EVENT_PREVIOUS, 'query': table_name, 'function': None, 'Form': None, 'filter': filter}
        if type(icon.previous) is bytes:
            layout.append(sg.B('', key=keygen.get(f'{key}.table_previous'), size=(1, 1), image_data=icon.previous, metadata=meta))
        else:
            layout.append(sg.B(icon.previous, key=keygen.get(f'{key}.table_previous'), metadata=meta, use_ttk_buttons = True))
        # next
        meta = {'type': TYPE_EVENT, 'event_type': EVENT_NEXT, 'query': table_name, 'function': None, 'Form': None, 'filter': filter}
        if type(icon.next) is bytes:
            layout.append(sg.B('', key=keygen.get(f'{key}.table_next'), size=(1, 1), image_data=icon.next, metadata=meta))
        else:
            layout.append(sg.B(icon.next, key=keygen.get(f'{key}.table_next'), metadata=meta, use_ttk_buttons = True))
        # last
        meta = {'type': TYPE_EVENT, 'event_type': EVENT_LAST, 'query': table_name, 'function': None, 'Form': None, 'filter': filter}
        if type(icon.last) is bytes:
            layout.append(sg.B('', key=keygen.get(f'{key}.table_last'), size=(1, 1), image_data=icon.last, metadata=meta))
        else:
            layout.append(sg.B(icon.last, key=keygen.get(f'{key}.table_last'), metadata=meta, use_ttk_buttons = True))
    if duplicate:
        meta = {'type': TYPE_EVENT, 'event_type': EVENT_DUPLICATE, 'query': table_name, 'function': None, 'Form': None,
                'filter': filter}
        if type(icon.duplicate) is bytes:
            layout.append(sg.B('', key=keygen.get(f'{key}.table_duplicate'), size=(1, 1), button_color=('orange', 'orange'),
                               image_data=icon.duplicate, metadata=meta))
        else:
            layout.append(
                sg.B(icon.duplicate, key=keygen.get(f'{key}.table_duplicate'), metadata=meta, use_ttk_buttons=True))
    if insert:
        meta = {'type': TYPE_EVENT, 'event_type': EVENT_INSERT, 'query': table_name, 'function': None, 'Form': None, 'filter': filter}
        if type(icon.insert) is bytes:
            layout.append(sg.B('', key=keygen.get(f'{key}.table_insert'), size=(1, 1), button_color=('black', 'chartreuse3'),
                               image_data=icon.insert, metadata=meta))
        else:
            layout.append(sg.B(icon.insert, key=keygen.get(f'{key}.table_insert'), metadata=meta, use_ttk_buttons = True))
    if delete:
        meta = {'type': TYPE_EVENT, 'event_type': EVENT_DELETE, 'query': table_name, 'function': None, 'Form': None, 'filter': filter}
        if type(icon.delete) is bytes:
            layout.append(sg.B('', key=keygen.get(f'{key}.table_delete'), size=(1, 1), button_color=('white', 'red'),
                            image_data=icon.delete, metadata=meta))
        else:
            layout.append(sg.B(icon.delete, key=keygen.get(f'{key}.table_delete'), metadata=meta, use_ttk_buttons = True))
    if search:
        meta = {'type': TYPE_EVENT, 'event_type': EVENT_SEARCH, 'query': table_name, 'function': None, 'Form': None, 'filter': filter}
        if type(icon.search) is bytes:
            layout+=[sg.Input('', key=keygen.get(f'{key}.input_search'), size=search_size),sg.B('', key=keygen.get(f'{key}.table_search'), bind_return_key=bind_return_key, size=(1, 1), button_color=('white', 'red'),
                                                                                            image_data=icon.delete, metadata=meta, use_ttk_buttons = True)]
        else:
            layout+=[sg.Input('', key=keygen.get(f'{key}.input_search'), size=search_size),sg.B(icon.search, key=keygen.get(f'{key}.table_search'), bind_return_key=bind_return_key, metadata=meta, use_ttk_buttons = True)]
    return sg.Col(layout=[layout], pad=(0,0))



def selector(key:str, table_name:str, element:sg.Element=sg.LBox, size:Tuple[int,int]=None, filter:str=None,
             **kwargs) -> sg.Element:
    """
    Selectors in pysimplesql are special elements that allow the user to change records in the database application.
    For example, Listboxes, Comboboxes and Tables all provide a convenient way to users to choose which record they
    want to select. This convenience function makes making selectors very quick and as easy as using a normal
    PySimpleGUI element.

    :param key: The key to give to this selector
    :param table_name: The table name in the database that this selector will act on
    :param element: The type of element you would like to use as a selector (defaults to a Listbox)
    :param size: The desired size of this selector element
    :param filter: Can be used to reference different `Form`s in the same layout.  Use a matching filter when creating
                   the `Form` with the filter parameter.
    :param kwargs: Any additional arguments supplied will be passed on to the PySimpleGUI element

    """
    global keygen
    key=keygen.get(key)
    meta = {'type': TYPE_SELECTOR, 'table': table_name, 'Form': None, 'filter': filter}
    if element == sg.Listbox:
        layout = element(values=(), size=size or _default_element_size, key=key,
                    select_mode=sg.LISTBOX_SELECT_MODE_SINGLE,
                    enable_events=True, metadata=meta)
    elif element == sg.Slider:
        layout = element(enable_events=True, size=size or _default_element_size, orientation='h',
                          disable_number_display=True, key=key, metadata=meta)
    elif element == sg.Combo:
        w = _default_element_size[0]
        layout = element(values=(), size=size or (w, 10), readonly=True, enable_events=True, key=key,
                          auto_size_text=False, metadata=meta)
    elif element == sg.Table:
        # Check if the headings arg is a Table heading...
        if kwargs['headings'].__class__.__name__ == 'TableHeadings':
            # Overwrite the kwargs from the TableHeading info
            kwargs['visible_column_map'] = kwargs['headings'].visible_map()
            kwargs['col_widths'] = kwargs['headings'].width_map()
            kwargs['auto_size_columns'] = False  # let the col_windths handle it
            # Store the TableHeadings object in metadata to complete setup on auto_add_elements()
            meta['TableHeading'] = kwargs['headings']
        else:
            required_kwargs = ['headings', 'visible_column_map', 'num_rows']
            for kwarg in required_kwargs:
                if kwarg not in kwargs:
                    raise RuntimeError(f'Query selectors must use the {kwarg} keyword argument.')

        # Create other kwargs that are required
        kwargs['enable_events'] = True
        kwargs['select_mode'] = sg.TABLE_SELECT_MODE_BROWSE
        kwargs['justification'] = 'left'

        # Create a narrow column for displaying a * character for virtual rows. This will have to be the 2nd column right after the pk
        kwargs['headings'].insert(0,'')
        kwargs['visible_column_map'].insert(0,1)
        if 'col_widths' in kwargs:
            kwargs['col_widths'].insert(0,2)

        # Make an empty list of values
        vals = []
        vals.append([''] * len(kwargs['headings']))

        # Change the headings parameter to be a list so the heading doesn't display dicts when it first loads
        # The TableHeadings instance is already stored in metadata
        if kwargs['headings'].__class__.__name__ == 'TableHeadings':
            kwargs['headings'] = kwargs['headings'].heading_names()

        layout = element(values=vals, key=key, metadata=meta, **kwargs)
    else:
        raise RuntimeError(f'Element type "{element}" not supported as a selector.')

    return layout

class TableHeadings(list):
    """
    This is a convenience class used to build table headings for PySimpleGUI.  In addition, `TableHeading` objects
    can sort columns in ascending or descending order by clicking on the column in the heading in the PySimpleGUI Table
    element if the sort_enable parameter is set to True.
    """
    # store our instances
    instances = []
    def __init__(self, sort_enable:bool=True) -> None:
        """
        Create a new TableHeadings object

        :param sort_enable: True to enable sorting by heading column
        :returns: None
        """
        self._sort_enable = sort_enable
        self._width_map = []
        self._visible_map = []

        # Store this instance in the master list of instances
        TableHeadings.instances.append(self)

    def add_column(self, heading_column:str, column_name:str, width:int, visible:bool=True) -> None:
        """
        Add a new heading column to this TableHeading object.  Columns are added in the order that this method is called.
        Note that the primary key column does not need to be included, as primary keys are stored internally in the
        `TableRow` class.

        :param heading_column: The name of this columns heading (title)
        :param column_name: The name of the column in the database the heading column is for
        :param width: The width for this column to display within the Table element
        :param visible: True if the column is visible.  Typically, the only hidden column would be the primary key column
                        if any. This is also useful if the `Query.rows` `ResultSet` has some information that you don't
                        want to display.
        :returns: None
        """
        self.append({'heading': heading_column, 'column_name': column_name})
        self._width_map.append(width)
        self._visible_map.append(visible)

    def heading_names(self) -> List[str]:
        """
        Return a list of heading_names for use with the headings parameter of PySimpleGUI.Table

        :returns: a list of heading names
        """
        return [c['heading'] for c in self]

    def column_names(self):
        """
        Return a list of column names

        :returns: a list of column names
        """
        return [c['column_name'] for c in self if c['column_name'] is not None]


    def visible_map(self) -> List[Union[bool,int]]:
        """
        Convenience method for creating PySimpleGUI tables

        :returns: a list of visible columns for use with th PySimpleGUI Table visible_column_map parameter
        """
        return [x for x in self._visible_map]

    def width_map(self) -> List[int]:
        """
        Convenience method for creating PySimpleGUI tables

        :returns: a list column widths for use with th PySimpleGUI Table col_widths parameter
        """
        return[x for x in self._width_map]

    def update_headings(self, element:sg.Table, sort_column=None, sort_order:int = None) -> None:
        """
        Perform the actual update to the PySimpleGUI Table heading
        Note: Not typically called by the end user

        :param element: The PySimpleGUI Table element
        :param sort_column: The column to show the sort direction indicators on
        :param sort_order: A ResultSet SORT_* constant (ResultSet.SORT_NONE, ResultSet.SORT_ASC, ResultSet.SORT_DESC)
        :returns: None
        """
        global icon

        # Load in our marker characters.  We will use them to both display the sort direction and to detect current direction
        try:
            asc = icon.sort_asc_marker
        except AttributeError:
            asc = '\u25BC'
        try:
            desc = icon.sort_desc_marker
        except AttributeError:
            desc = '\u25B2'

        for i, x in zip(range(len(self)), self):
            # Clear the direction markers
            x['heading'] = x['heading'].replace(asc, '').replace(desc, '')
            if x['column_name'] == sort_column and sort_column is not None:
                if sort_order != ResultSet.SORT_NONE:
                    x['heading'] += asc if sort_order == ResultSet.SORT_ASC else desc
            element.Widget.heading(i, text=x['heading'], anchor='w')


    def enable_sorting(self, element:sg.Table, fn:callable) -> None:
        """
        Enable the sorting callbacks for each column index
        Note: Not typically used by the end user. Called from `Form.auto_map_elements()`

        :param element: The PySimpleGUI Table element associated with this TableHeading
        :param fn: A callback functions to run when a heading is clicked. The callback should take one colun_name parameter.
        :returns: None
        """
        if self._sort_enable:
            for i in range(len(self)):
                if self[i]['column_name'] is not None:
                    element.widget.heading(i, command=functools.partial(fn, self[i]['column_name']))
        self.update_headings(element)

    def insert(self, idx, heading_column:str, column_name:str=None, *args, **kwargs):
        super().insert(idx,{'heading': heading_column, 'column_name': column_name})

# ======================================================================================================================
# THEMEPACKS
# ======================================================================================================================
# Change the look and feel of your database application all in one place.

# This is a dummy class for documenting ThemePacks
class ThemePacks():
    """
    ThemePacks are user-definable dicts that allow for the look and feel of database applications built with
    PySimpleGUI + pysimplesql.  This includes everything from icons, the ttk themes, to sounds. pysimplesql comes with
    3 pre-made ThemePacks: ss_small (default), ss_large and ss_text

    See the documentation for the following ThemePack related functions:
    `load_iconpack()`, `set_iconpack()`, `set_ttk_theme()`, `get_ttk_theme()`

    Note: This is a dummy class that exists purely to enhance documentation and has no use to the end user.
    """
    pass

tp_text = {
    'ttk_theme': 'default',
    'edit_protect': '\U0001F512',
    'quick_edit': '\u270E',
    'save': '\U0001f4be',
    'first': '\u2770',
    'previous': '\u276C',
    'next': '\u276D',
    'last': '\u2771',
    'insert': '\u271A',
    'delete': '\u274E',
    'duplicate': '\u274F',
    'search': 'Search',
    'marker_virtual': '\u2731',
    'marker_required': '\u2731',
    'marker_required_color': 'red2',
    'sort_asc_marker': '\u25BC',
    'sort_desc_marker': '\u25B2'
}

tp_large = {
    'ttk_theme': 'default',
    'edit_protect': b'iVBORw0KGgoAAAANSUhEUgAAABgAAAAYCAYAAADgdz34AAADqUlEQVR42qWUW2gUVxjHvzO7O7ubzDYWUZIGY7IumqiNTdHYSB9UlJS+tIog+OAFfKqJVqqg1Ni8iW0JVKxCHrRiElvSFsGHCM2lERWjsKKBjbrgBY2ablxwL9ndc/U7k1WISepuPHCYmd2Z/++c3/fNEJjBeLxuXa3DMC4QwxgmANuLL168Pd29JN/wO/X1VgFjQQwPGIaBByONIU0JzlsC3d3yvQD3hkKGeW3gL9XW9rUhpdIAJAAeFZ79i7fswN08mjEgGTq3k5Z80ZoMhYCfOAEwPKzD7ZkFvcTABoS05w1ItC+dTUDcTs36rMS5vIlQZira0UF4V5cOUVldGiRjjC2o7O19mBdgrGNJJ6OZTZRmVAp8xLWiWbnmrSVycBBSx48rFY3aAFT1IiaEf3FfXyxnAIZvFZz+lslQoJSClAIoEwDlG6Fw5UEwlQmp1lagly4BcTg2z+/p6cxZUbJ98Xwl+S0MLtIApaTiXBAhxHiRfRWgPj2sfGWrCAkGuz5cv/7LnIv84OQiY46P9KCa1TpcSokApRhj+jnldruJ/o1ypXhgR8Rauu3zkvKqcM6ARFvlfs7oUa2FMQ5OpwMVMcDVg2m6AHsUOOf6Wklw1vv3jnS/nTEtIH520TIpxDUsqhsBxOVyYZDUNbDVuN2mrUoDcBe/lO998e1UOVMCnrYucFtu4zqGfYwAu88djvHV68CCAq8N0+c4Q6hoxcL90VTOgNiZwM+o5Ltsxyivt4AwRm0AqrF3gP/jDjjF1a/C1QenMzEJ8PJMYA2q+QeL6sBigmUVKikkySCM4N2mqdVwVCMUuv++bE/kyP/VcQIgPPC3Z+6TX++kI3fLtHev14OFdSl9rnV4PB67oOMAfjk2JlcvOTAqcgYwlqlTLHUlduUHoOFO+MBn2S9WVg22KGS7hsexBjXzdv93H94xJgDw4c3Y5r+jVyWe9BB+oxlo/DnGEqJbNFtUVCN3ljY8P/Wu8KkA+xDwkwbgJHIsApmBQ8oZuaqdv179+ZJvnm3IJXwqwDEENOi3c8K8/yfwmz8CS8dHsAGqP9r1LDIjwOjo6PmioqKv3uxgHKC/DiQ5MpRhN5o3lG3B73MeYwKgtrY2WFdXV9PY2KhKS0ttQDqdFtFo9I9kItH8SU1NOJ/wSYCqqiq99dmWZUFLS4uGXEgkEk3V1dWD+QZPAvj9/kLs8zjq0Fq6i4uLm/r7+wdmGjwJUFFRsRDf0tMYfigcDve9b/Dr8QptdEU3XH9lbwAAAABJRU5ErkJggg==',
    'quick_edit': b'iVBORw0KGgoAAAANSUhEUgAAABgAAAAYCAYAAADgdz34AAADqUlEQVR42qWUW2gUVxjHvzO7O7ubzDYWUZIGY7IumqiNTdHYSB9UlJS+tIog+OAFfKqJVqqg1Ni8iW0JVKxCHrRiElvSFsGHCM2lERWjsKKBjbrgBY2ablxwL9ndc/U7k1WISepuPHCYmd2Z/++c3/fNEJjBeLxuXa3DMC4QwxgmANuLL168Pd29JN/wO/X1VgFjQQwPGIaBByONIU0JzlsC3d3yvQD3hkKGeW3gL9XW9rUhpdIAJAAeFZ79i7fswN08mjEgGTq3k5Z80ZoMhYCfOAEwPKzD7ZkFvcTABoS05w1ItC+dTUDcTs36rMS5vIlQZira0UF4V5cOUVldGiRjjC2o7O19mBdgrGNJJ6OZTZRmVAp8xLWiWbnmrSVycBBSx48rFY3aAFT1IiaEf3FfXyxnAIZvFZz+lslQoJSClAIoEwDlG6Fw5UEwlQmp1lagly4BcTg2z+/p6cxZUbJ98Xwl+S0MLtIApaTiXBAhxHiRfRWgPj2sfGWrCAkGuz5cv/7LnIv84OQiY46P9KCa1TpcSokApRhj+jnldruJ/o1ypXhgR8Rauu3zkvKqcM6ARFvlfs7oUa2FMQ5OpwMVMcDVg2m6AHsUOOf6Wklw1vv3jnS/nTEtIH520TIpxDUsqhsBxOVyYZDUNbDVuN2mrUoDcBe/lO998e1UOVMCnrYucFtu4zqGfYwAu88djvHV68CCAq8N0+c4Q6hoxcL90VTOgNiZwM+o5Ltsxyivt4AwRm0AqrF3gP/jDjjF1a/C1QenMzEJ8PJMYA2q+QeL6sBigmUVKikkySCM4N2mqdVwVCMUuv++bE/kyP/VcQIgPPC3Z+6TX++kI3fLtHev14OFdSl9rnV4PB67oOMAfjk2JlcvOTAqcgYwlqlTLHUlduUHoOFO+MBn2S9WVg22KGS7hsexBjXzdv93H94xJgDw4c3Y5r+jVyWe9BB+oxlo/DnGEqJbNFtUVCN3ljY8P/Wu8KkA+xDwkwbgJHIsApmBQ8oZuaqdv179+ZJvnm3IJXwqwDEENOi3c8K8/yfwmz8CS8dHsAGqP9r1LDIjwOjo6PmioqKv3uxgHKC/DiQ5MpRhN5o3lG3B73MeYwKgtrY2WFdXV9PY2KhKS0ttQDqdFtFo9I9kItH8SU1NOJ/wSYCqqiq99dmWZUFLS4uGXEgkEk3V1dWD+QZPAvj9/kLs8zjq0Fq6i4uLm/r7+wdmGjwJUFFRsRDf0tMYfigcDve9b/Dr8QptdEU3XH9lbwAAAABJRU5ErkJggg==',
    'save': b'iVBORw0KGgoAAAANSUhEUgAAABgAAAAYCAYAAADgdz34AAAEp0lEQVR42qWWf0zUZRzH35+7+95PDksKmagXjCTAUNB+2FbN1XZXNJrhlo7MLF1WGksry7GiVm6pqS1tmStnxrIRFVaKrGmuqWvNIA1EYR5gkK418Hvc7/ve0+f5fr8I+ef53T483+fZ7v269/t5ns9BMJ5crhe5yrgsyOzZxHX82kXiyoPN9ivur52OKbMIpOuLe6dZqSrPjiyPW3jcTnI7HXA6HFAUm0in0xRPJEQ0lqBwNIbm7kHRtuPdEMJqNX/22LWALbhv+ToULhTmXAcsutNNK0qzMMnrEd4sN3lcLricdhCRGFIjdPofVSTjcfJZNHzSqYqmX7oILfWjGL3yKH/+yETAQTyyKYCcYp6RsWK1YMndWXiu/AZke9zsQoo7odisSCSTaDl/CS8f78UkxYJd5TnY0xPFdx1JIDEAfLshitDIQlZpGwMcQtXmAHKLBWwW4mIAiWV3eWnN7Bx4OSK3y0kOu4KUpiEai4sfugep/li3yFastLniZjT2p8SPPVaClgZifwk0r49BHa6R2gageksAU0sYYDUANhIr5nnppcpccDTC6bTr0cViCYSjUXGo8yJtPNopsuxWqq/Mw9eXINqG3IQUp5xKC8QGCU2vxnHl30UGoGabH9NKoYsrFn1cVenFK3PzOBoHc62IJ5KI8IaGwhG0911GS0cQlNawIN+DA8N2/KxOluJGJbmGfgeaXj9sABZ/EMCMMgFlzIFFrJ6TRa/Ny4edT00ypVE0FsNoOAo1HBGqGqYRNSSG1RANj4TQGnGLE1o+mQCBpEYY6AT217UagKU7AvAxwG4CFKuY7NDoJoe8FRYhICgtj5ZIc8z8V0uTpmkizWAtpWEUDhElF7HwOKCPAftWm4CnP/KjYBYL26T41Zh4LyRAbvr4CdMPsU4DWAua+H80EiIreAb47Hkzomc/DqCwXHdwz/RszJ/qFSxKsOjCgu826YBxeWKAQFofJUgwiE4OhXDioiqQYAcXTgO7VpkOXtjtR1E5GIDztWUoynZk1Ct61ThmNnI0CXbQy4CdK00HdZ8GMHO27iC4uBQ+jyL4xupfmb/o1feJ84nrY+99owkU7O8yHPT8AWx/xnSwbk8AxXMEHAx4rPj6AN+cE4gz4FwH8P5yE7B+bwC3mYDqW+FzZwgIM+BAjwHoZsB7y0zAhs/9KKkAAxB8uIgBtoz2oD+SQsHBXjAAONsObHzS3IP6fQGUVgg4bRT0F8LnsmXmIJJEweEL3CrYQRff5HeWmg7e+CKAskoD8OAt1wf4qY8BKUInA95+wgQ0NPoZAAYg+IAPPmeGEcU4oiP9QDQFHdBQa0b0VqPhwKVQcMEMCcjMQZQdHB0wHPx5CnizttX4wWlofAi3z9Uj2lt2I6qmeMVYY+B7KiY0iavzietj799fDuGpzmEDcOaUdKD/HmzDkrV1qFmpRyRPEmRCcnSYc7tZivn/gOw58rbKkicmnjJGHvQ1GVHzbuDLrdslIB+K/Tc8viYPFfMJLocU1e+EKW60cSlutRhdjvsOQ4yuaUCMsy/fI3GB9pOErz78G8nEHWPW87nWcpVgQhwZPrIZnuXayjX4H7Qeh+TT7afMAAAAAElFTkSuQmCC',
    'first': b'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',
    'previous': b'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',
    'next': b'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',
    'last': b'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',
    'insert': b'iVBORw0KGgoAAAANSUhEUgAAABgAAAAYCAYAAADgdz34AAAFJElEQVR42qWWa1CUZRTHz3n3wrLLAnKNi7dEYCW5Vo4gaJI2pgx8yIb64ocosssoVqbN9KmZGMsBHafM5Itfisk+wKA5XlMR7AaIhgsIiYTI6rLALqwv7767p/O+LMiOaUXPzH9299lnz+85/+e851mExw89ax2rkJXGivLP21kdrLOs0yzpUQHwEfMG1jbQYAUui4xhISaYQRumTAPJYyLSbRfR9WFk2cBL1Ty/nyX+G0AGq1abF5caUpQMuZYcejbWgknhiRCqN6kApzSBPaMD9IvNis3WFhhv6Ca56U4Xf1fKan8cYC0atXXGMkvIyjV5ULykgIMapxZh4GIiFr86JTfU916Ey+ebwF1jHSe3XMLT5/4OkMHBGyM+yDBvyC2k7JhUFDgEIpDocaPD7ZiJrfwuwhhBBp0RFZAPkFrvduKJ5rPg+LzdxZD86UymAQZ+1xZVkZaav3YVpEctJQEJWSAwYFlEKpY8WeTfORHyqPujga47OtGnAAiJIXj1Xjc0nmsie3VHF28jSzmTacCH5tWxlZat2bAqPpvPlkAjAEwBiIHp8NKS0gAvv++thav2q0pwVV4f8FkjXBpsBevBFnBduLubl+1RAHrUYH9SVWZMTvJyjDRwtXDiGoF4WoVQRvTT+EryawEZfNtdQ+33WlANTkAcHGUfgkN00W/d17BnxxUbTy5QABtDc8KPWXZaKC0iCXUCgVYgYgj6s6Cs6JX4asq7AYBvug5Q273L6N89yX6Ax4fU4ehB62dWcLaMblIAVYvLFm5P2jgfEkxRoOegC4OfUrwH/yGDJWo5bFzycoBFx3u/A6v9GvgPWX3tE38HyQswOGGHGz/8CTcP39qnAE5mV6asT0ibR2wPmnRaOLD6uLrL2Tt+UJ5Tn2fPT79/5/yLMOHxkEMcx4GOEWjd3XVKWdBScMiSFZ0YDGF6A5h0Othf8CPMZWy7+By4PR4YlUSwD9yHC+XWNhWwviYlOzJBR2a9HkM4g72rfppTBu81roBxzsAleXD4tgdOlXW1qhatq17MFhnIpAMG6KEyt21OgF1NmQyQyO0BtkiE0xU3VYuqcrc9UZFeHEbBGi8adQI8E7uJuJKQpTwTFGfMwrTILQGAjuEjNORuQ64e4OohFv5qO8YW+Uj0arC9fgya9w9Vq2W6KC+koeTTOAjWelk+MLCCNFPSCT5ICi+G/LiDAX433tkKPaP1XJYCTHqRpQFRFuC+X3UfDUFf03iR+qAJWuh/8+jCmJh45HakALxk0PjQD6FFoSW4IvbrgAx+tr1Bfc46lLwCiF6Bdy2gKGuU4GQbJPxq8y2bT4YFM60iu9hcufnjeSrAqCXiLNDgBywwF2NG1OEAQLv9dep31c8AODC6ZQQ3A45+MoKt9a5d061iptmVfxGdkpmvAzOXqlEHEOy3Kd5UBMnhXwZY1D36Fj9QDWwNW8LigwUXl+iVRgkOvW1/qNmp7doYipd2HokMsaQFUXiQkg0BZ8HZACo+cn9Sk/DygUo+mUQZUFQAMtLI5Ah2dkzCni3DLreTHmrXMxeOKQzrd+wLNeUXhmJkUCLbpSfOAvWcidJlVQCbxNYQ755tkWB4coAazzqxarvTNTFGj7xwHlw8CLUbSvUp5e8bYOmiaDDro7m6wrgagtQFkm+Sdz0GLuku3Oizw6G9Ipyolbq4H/3jlTk91Etfq4OKguc1MYUvIOZkEsyPV9oaUP+ggK1XkM6cJLx4xmuTPfCfLv3Z43//bfkLo1muAZZ9QHcAAAAASUVORK5CYII=',
    'delete': b'iVBORw0KGgoAAAANSUhEUgAAABgAAAAYCAYAAADgdz34AAAEe0lEQVR42rWV21MTVxzHf5sLWQJjEyBAIgkhQHBEHNAXL0/MtC9KbRWofUz+AP8gn3bfnKojrZfptF4Yp30oF2VRp6ZAS7jkTshuuAUDpN9zyIbUALUPzczOZnd2P5/fOb/vOSvQ//wTyi9+aGqyWez2UdHh6NVmZoJfJRLyp0BGnM6A49w5KRsOK9urq/3XYzG1QsDgYmPjaM+tW71GUaQ/79+n5Ph48Ot4XP43uHdgQHJeukRr8/P0x507yof19f4bRYnwMVwQBIo+fUqmEydIC4dp9d27IyUPAAdYart6lZIvXtCHbJbIYqGYoij5jY3+G9GoygU/9fRM6fClx49pBw8aqqpIdLn2JaFQEMOWP4Y3X7wo+YrwtVCI37c4nUSYgdj0tPLl7GwfF4wNDRW8167R4sgI5VWMrFCgwt4eGcxmEk+eJG1hgTLoiS554HIFmi9ckHxXrlAK8GwRzt5j71g7Oig1M0OfT04K+hQFGlGNaLNRbnGR9nZ2iHZ38fz+C9UtLaQuLVFmbi7Ini/Bnz+ntffvDxJjMJDY2kobmkYJjHowGpVLTf6+uTng6OuTrA0NtIWKuQSjYAebLite1FIpMtfUEJuW1LNnfFoEFMHhRiOJHg+tMzhGOxiJyBUxZZKGs2cla309lxQg4QAmQfNq2tvJgbSkX76k7Nu3VMjnOYDBq71e2tjcpDhGqcMrBKVMnzkjWe12LiE2Ekh2WUJwNppMlItEiAXCwA5cWzs7aQOyVCIRHCqDHyrQJQ2nT0vW2lrSXr+mnXR6v4GYYwYVimfWnxo0lMET8XgF/EiBnpTP6uslC4a/NTfHp4pDGZwdDI7K1xk8FgsOLS8fulaOFdT5/ZLn8mUK375NlMsdwHGwZrOpiSeTpKpqcPi/CHR4O6KYffWK4k+ecKixCDdiVOy/CZJqTFE0FqPVTOZQiXAsfHKSYoDrYBPiygV4zgCJSZcgXQvRKK2k08FvlpaObjJb/jpcQ+UxbBt65Qxe4/fz/3lsH0zCR8JEkIg+H/2FxZhMpf4hKQlYcmyAdwCussqLcF45GloL+CZWN7u2W620gwgziQkx5RLcq2pro1nsqHEmWVw8WGgMbgecLX91YoKijx6VKjeicgbfAhxRlNm6dbvdgQZEeA8VG5Esc1FihMSMFf87UhfFmrgJCRf8fP584dTwMGVQeeThw4NmFivPAZ5MJmVEke9F99xuqa21NeDAlk7Ly7wXJUl1NQluN41PT9MXb97sb3Y/dndPdQwM9M7LMu1mMgfwri4OX2HwSCRY3q+7kHT6fAEnVryAlW0GnEtwna+ro1/GxpSBUKhPnyKbyWIZteFTuY2K9rAtMPg29qB0KlUBL5ec8vsDLQAaEdUqnKmpiX6dmFAQ2/6bCwuqUJYgm1kUR+2QCKh6G3tQZmVFHjwCXpJ4PFJ3V1fAAzBh1L9NTSlpwL8FvDKmLpcNiRnF9PTmNjdl7OfHwvXfd5B40XhtbU1Z1bQS/KiFZsPJi++p8inwMkkvTmEkRy2//zcpYDQ3Hbr/xQAAAABJRU5ErkJggg==',
    'duplicate': b'iVBORw0KGgoAAAANSUhEUgAAABgAAAAYCAYAAADgdz34AAABhGlDQ1BJQ0MgcHJvZmlsZQAAKJF9kT1Iw1AUhU9TRZGKQztIcchQnSyIFnHUKhShQqgVWnUweekfNGlIUlwcBdeCgz+LVQcXZ10dXAVB8AfE1cVJ0UVKvC8ptIjxwuN9nHfP4b37AKFZZZrVMwFoum1mUkkxl18V+14hIIAwokjIzDLmJCkN3/q6p16quzjP8u/7swbVgsWAgEg8ywzTJt4gnt60Dc77xBFWllXic+Jxky5I/Mh1xeM3ziWXBZ4ZMbOZeeIIsVjqYqWLWdnUiBPEMVXTKV/Ieaxy3uKsVeusfU/+wlBBX1nmOq0RpLCIJUgQoaCOCqqwEaddJ8VChs6TPv6o65fIpZCrAkaOBdSgQXb94H/we7ZWcWrSSwolgd4Xx/kYBfp2gVbDcb6PHad1AgSfgSu94681gZlP0hsdLXYEDG0DF9cdTdkDLneA4SdDNmVXCtISikXg/Yy+KQ+Eb4GBNW9u7XOcPgBZmlX6Bjg4BMZKlL3u8+7+7rn929Oe3w9rHnKk7x4JKQAAAAZiS0dEAAAAAAAA+UO7fwAAAAlwSFlzAAAuIwAALiMBeKU/dgAAAAd0SU1FB+cCARMnDMj6VvgAAAAZdEVYdENvbW1lbnQAQ3JlYXRlZCB3aXRoIEdJTVBXgQ4XAAACVUlEQVRIx7WWQUsbURSFv5nMZDJOFwHb7VuELFxk0y6EgK3QVXHjDxC6aKH9C4IFQZGCq5KVgl1oQRBB/AdCbKLEhRuhC10EMRCVQqAZZJJ5ud3E0CapZmI9MIt53Lnn3nPe3PcAMAxjBJhNp9NXgER5MpnML2CxnaMHlmEYIyLyHXg+MzPD6OgoUVCr1Z6cnp5+CoJgMhaLvdZah90xs4AcHx/LsCiVSrcdve+pIJ1OX83Pz8tD0Gq1xHEcAVZ7JDo7O3vWT5ZKpUKpVKLZbA4kldYa4FWbpOB53jff98XqF1woFJiYmMCyLGzbHojAtm1s2x7TWo81Go0Pvu+/M03zDYDkcrlOuxcXFwLI2tqa3NzcRJZLay3FYvFWssUegp2dHbEsa6jkf2JhYUGUUtdmd6vNZhPbtkkkEjwEyWSS8/Pzp+YwH+fzeZaXlweKHYqgXC6zu7v7eARR8OgE1qCal8vlzvv+/j7VapWNjY3Omuu6TE9PE4/HoxMcHh7+pXm1WqVSqbCystJZS6VSTE1N9RD0/AdbW1viuu6de3x9fV2y2eydMblcTgAxM5lMvVarPZ7JJycnX5aWljg6OkJE/r/JhmF8DoJgcnx8/KXjOGit7x1wruuSSqUGZ4nFYlb7sFgFftznQRAEUq/XB/OgPctD4CvwEchrrWm1Wv8sKB6P43nenUWHYYhSqu9h8haQYrE49CS9vLyUbDYrwKbRnd3zPMP3/T3HcSbn5uZIJpORTA3DkO3tbQ4ODn4CL/pvLdNMAItKqeuo1xilVAPYBBTAb9rfs0kjJGFsAAAAAElFTkSuQmCC',
    'search': 'Search',
    'marker_virtual': '\u2731',
    'marker_required': '\u2731',
    'marker_required_color': 'red2',
    'sort_asc_marker': '\u25BC',
    'sort_desc_marker': '\u25B2'
}

class ThemePack():
    """
    ThemePacks are user-definable objects that allow for the look and feel of database applications built with
    PySimpleGUI + pysimplesql.  This includes everything from icons, the ttk themes, to sounds. Pysimplesql comes with
    3 pre-made ThemePacks: default (aka ss_small), ss_large and ss_text. Creating your own is easy as well! In fact, a
    ThemePack can be as simple as one line if you just want to change one aspect of the default ThemePack. Example:
        my_tp = {'search': 'Click here to search'} # I want a different search button

    Once a ThemePack is created, it's very easy to use.  Here is a very simple example of using a ThemePack:
        themepack = ThemePack(my_tp_dict_variable)
        # make a search button, using the 'search' key from the ThemePack
        sg.Button(themepack.search, key='search_button')

    """
    default = {
        'ttk_theme': 'default',
        'edit_protect': b'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',
        'quick_edit': b'iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAGJ3pUWHRSYXcgcHJvZmlsZSB0eXBlIGV4aWYAAHjarVdZsuQmEPznFD4CVSwFx2GN8A18fCeiUG/zZtoRfnrdQoCKpDJJaDP++Xuav/DH7L3xQVLMMVr8+ewzFxSS3X/5+ibrr299sKfwUm/uBkaVw93tRynav6A+PF44Y1B9rTdJWzhpILoDX39ujbzK/Rkk6nnXk9dAeexCzEmeoVYN1LTjBUU//oa1b+vZvFQIstQDBnLMw5Gz13faCNz+FHwSvlGPftZllJ0jc92iBkNCXqZ3J9A+J+glyadk3rN/l96Sz0Xr3Vsuo+YIhV82UHird/cw/DywuxHxa0MaVj6mo585e5pz7NkVH5HRqIq6kk0nDDpWpNxdr0Vcgk9AWa4r40q22AbKu2224mqUicHKNOSpU6FJ47o3aoDoebDgztzYXXXJCWduYImcXxdNFjDWwSC7xsOAM+/4xkLXuPkar1HCyJ3QlQnBCK/8eJnfNf6Xy8zZVorIpjtXwMVL14CxmFvf6AVCaCpv4UrwuZR++6SfJVWPbivNCRMstu4QNdBDW+7i2aFfwH0vITLSNQBShLEDwJADAzaSCxTJCrMQIY8JBBUgZ+e5ggEKgTtAssfSYCOMJYOx8Y7Q1ZcDR17V8CYQEVx0Am6wpkCW9wH6EZ+goRJc8CGEGCQkE3Io0UUfQ4xR4jK5Ik68BIkikiRLSS75FFJMklLKqWTODh4YcsySU865FDYFAxXEKuhfUFO5uuprqLFKTTXX0iCf5ltosUlLLbfSubsOm+ixS0899zLIDDjF8COMOGSkkUeZ0Np0088w45SZZp7lZk1Z/bj+A2ukrPHF1OonN2uoNSInBC07CYszMMaewLgsBiBoXpzZRN7zYm5xZjNjUQQGyLC4MZ0WY6DQD+Iw6ebuwdxXvJmQvuKN/8ScWdT9H8wZUPfJ2y9Y62ufaxdjexWunFqH1Yf2kYrhVNamVr66TynlKlOengN5/LcEGP4KxHWInT2n0cr1xiiwKpqr29qb9N20X8QeqQ3otEeYEQ7Zhv8Wzwe+GvfAM1dnenTIwYWrtgGOx36Irqbh40boXZ/c+kIE7qMbO5TnvkHCis3bIDg8XHF6chNb7J6V/eJuroIbTVENSTP6svMDvy+0XHshmR5tTeD9qwlyrVEs7X5E0/jiNv4MvwpXtAz1F4VY69XV55qzhkiIP1hDlCaIj5JZ+dfAn3fpUV9AbzzYncCMhbdhYrPaWRmmYguAmve8cpu2VdHBGCsm00U61EoTqyfs9zP14vf0cU5C6rcg13kE60uVNti9of4BbOgHbANYYzUJt84cKNukAodmqmTNMBLk9wvSoRSXe1bEZubhaYjSBE35JHSTNtBx5x2ScjsdEf1fUJcVyvwAex7YEbB1cTTvdw+mEx6nIIVviHQJ0ZZpSHCJoUsI0lEhYL7DteDKESzAt+ULu6dtZnabpu1Pes7vunUgfbfDXfDQqtO8IsuKgszGA2KVNktdJxhEa1Snj8jMR05JjkhNsSKauQ6XcXDArCKssNX4G60e+mGIXczhuFvvd3icEarivBezf8WCwg2XdgGn2q0RbEJasLQXHza31s6oiYH0trbDzzxSb9ZIoDMVGM4YpMRikr2pC1xHeS2cmjunis2g5N5QYkJnSR43KwREPRx4/hOeeeAcVTsi2zNAMAp7Yl363YQDk8p7DLa6uvlCYF4pP5z4Uwib+pK8Tgp7+4hBZYUj1vBtJ/u35j530Vs15+bF6eLBjymhtucH0MVI9aq82poT5TAm/Lx8T522rV9Km1ZWnYRiE1Z/3WxjfDfCF3vQfK+6RjQQeir12E0Rqg8tgBp1y1axTSVtkpyJuko2azhjb61AfnL4TaDOvsnvpztN6X350aqrGoxP4zEXbQkZvzwUUIIyovDRCk4dDe6x9/413X6sYeak4u7rwX23S5on2+n9eHQ+/jdDP63l1n05sPPJSvTdbOsW6nCMWxTw4kCqieHKAqnnDpwUZ+Yft+wPTyz3+rv97qRR3MOS0m2C1by7oDu7dcR2FV6PSH8+RHwiuhNST0LKAXLOMtTqw5eiOWV3V9LZYb4V0nU3v1QYzoHmX+RGJBpl98L8AAABhGlDQ1BJQ0MgcHJvZmlsZQAAeJx9kT1Iw0AcxV9TpUVaBO0gopChOlkQFXHUKhShQqgVWnUwufQLmjQkLS6OgmvBwY/FqoOLs64OroIg+AHi5Oik6CIl/i8ptIjx4Lgf7+497t4BQqPMNKtrHND0qplKxMVMdlUMvCKIPoQxDFFmljEnSUl4jq97+Ph6F+NZ3uf+HGE1ZzHAJxLPMsOsEm8QT29WDc77xBFWlFXic+Ixky5I/Mh1xeU3zgWHBZ4ZMdOpeeIIsVjoYKWDWdHUiKeIo6qmU76QcVnlvMVZK9dY6578haGcvrLMdZpDSGARS5AgQkENJZRRRYxWnRQLKdqPe/gHHb9ELoVcJTByLKACDbLjB/+D391a+ckJNykUB7pfbPtjBAjsAs26bX8f23bzBPA/A1d6219pADOfpNfbWvQI6N0GLq7bmrIHXO4AA0+GbMqO5Kcp5PPA+xl9UxbovwV61tzeWvs4fQDS1FXyBjg4BEYLlL3u8e5gZ2//nmn19wNkDXKhWfC+CAAAAAZiS0dEAAAAAAAA+UO7fwAAAAlwSFlzAAALEwAACxMBAJqcGAAAAAd0SU1FB+QIEg0fJQXnbmsAAAKVSURBVDjLhZJPSFRRFMa/c++b55tGTZpSMZRStCyJFlEoLkSyWtQiyI1FUWRtIooWFS2yKHcG0aICN1IWCNWmQhfixqQokDAHpY3lFJiTZo7ju/e9e0+LwP6o9W3O6vvxfeccwjK6dPEirrS2IkmUE2loeCGkTBFwjIAxw4yinh4AAC0HMIlbSL0zmHs72SV7extldjaElDOS6CoDNwCgsLsbYjmA+q6Rk//xaN6p5kbRfIJDIjZK5YbWtjHQWRCNYqS+fukEmQebIYQTD3R6eJ7z883W83C8LZRpucRIJkl6HtZWVNBIIgH5t3n2fhUIBmxNu1K6WmdSUIl2aJLIab4MGEFhcvz41OfPgyGwuIIkA0Cc01o1KaXBzIC7Clnjd2j2yWFS1WsSBR2POiURNvX1/arw6W4ZYlEHjqD1YaAH5+f9XCEIvq8QiTgAiIIgNGZ4stDZ1ZIqaWwBfk9QFJdwBcOEpsv31UoiwFoGEUFKB8YYWLb7Ubk6FSZvLyQWAPD+1WPM2HKExlxXyt9mrWE34pIxhqJRD9ZastZ2Z2a/Pg2NRenZiQUAAUDHbmBvEzayj0FfF3qx2ArWWpMQPwMqpWbSGbXGy3KCdWdSf+xMAMDBZxorD5kGt67b8/KqGDwHImIpBRsTGiLsiXpuMOcvPrlYGMzlXulOxPbdI17biCwxTsYwMXOn6zovBQGbL6SWBjAzAGwgMNjNY7fuJnj7QxhZ8EFk5RxRyqL49JclP1YCgNYa/f3910pKSvLi8Tjp+TR9Q36XjhYf4NmxtFQTaHueXhJAZWVlcF0X1loeHR0NBgYG3sRisZORSGTo29QUampr8S8Jay2mp6dzieh1ZWXljpqamtogCIbCMPyvGQB+AKK0L000MH1KAAAAAElFTkSuQmCC',
        'save': b'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',
        'first': b'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',
        'previous': b'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',
        'next': b'iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAGz3pUWHRSYXcgcHJvZmlsZSB0eXBlIGV4aWYAAHjarVdZssQmDPznFDkCEovgOCCgKjfI8dMY2fPW5L1UxmWzGAuhbi3j5l9/LvcHfhwyu5ik5Jqzxy/WWLmhU/z51etJPl5PG/i7827ePS8YUwFtOENptr5hPr0+uPeg/n7eFXvDxQTdkk1g2DszOuOtkpjnM0/RBNV5OrkWeatq59OqLbxUsTvIJfoRssfu7UQUWGkkrArMM1Dw17McDcK5G+6CJ+axzoeKfgjs0HC4jwSDvDveY0D/1kDvjHz33EfrP70Pxudm8+GDLbPZCJ0vX1D62viXid9sHB6N+P0LvCmfjmP3WqOsNc/pWsywaDZGeXdbZ3+DhR0mD9dnGZfgTujLdVVcxTevAGd49R2XUiUGKstRpEGNFs2rVVKoGHmyoGVWDtdcCcKVFShRiPuixQLEBhDkoDwdoIuBH13o2rde+ykV7DwIS5kgjPDJt5f7p5e/udxauk1Evjy2gl68mQs1NnL7iVUAhJbhli4D35fB79/wZ1M1Ytk2c8EBm+9HRE/04la4cA5Yl9AeryAnwwTARNg7QRkKQMBnCokyeWEWItixAKAGzTlE7kCAUuIBJTmGHY+E4TLYG98IXWs5ceY9jdgEIFLIQYANfApgxZjAH4kFHGoppJhSyklScammlkOOOeWcJe8g1yRIlCRZRIpUaSWUWFLJRUoptbTKNSAGppqr1FJrbY1dw0YNshrWN8x07qHHnnru0kuvvSnoo1GTZhUtWrUNHmEgTIw8ZJRRR5vkJiLFjDPNPGWWWWdb4NoKK6608pJVVl3tQc1Q/XT9AjUy1PhCaq+TBzXMOpFbBO1wkjZmQIwjAXHZCIDQvDHzhWLkjdzGzFeEsZAYSqaNjRu0EQOEcRKnRQ92L+R+hJtL5Ue48b8h5zZ0/wdyDtB9xu0L1MbOc3ohdrxw29QHeB/WNC4Ot/d4/KbFvvnq9jn8qiHMXp1NsK6mvxX4tn2nUdA6d6etHBdruWabluFnbFd/jqCT26CYCODlPNPVLeRG5NP3qdYRd1/aFF2Quc6wRoQIJOIzCnUgS15iMxNbJ7iR81EilLnYjg7+pW/tI2rm6H7p8uOsdF07bBWnyZsdfNFylrYI8SuGM8LCsZiuQQXRz/ly3EEsJkepUS3reo1Ulcc5qE6JpPUMxpSqYOb5dMa6Ik677KweoWwLimlXEeldm81ucKoiSDPXBxGBZ3I9g95EB1zpGoHJ4iA9nK9WALNbjmfUqpc6TIdKM9VmX+2axSQgaY4G8mOZwzrMSs3n+9kq7LKD9AFMsduQe4R+LtdCBI/3LaqRelTPcGcVM0q7jHIrhBAfZk6mKo0soPR5RYStJzzTPScGGbvxqGQZyNS3VM7+2CxqpQNu53iOEGkKKYzjLrkIDQv+bITS1b93Mz6SwFBY4PACBNXhgjZjZNRFqvZSqM5pCJW2ue6N5w0glBtexKwzS45mqVNsUa7qYaCLUx7nPEI51PI4G8rETWDjKGyn/tLVNX86b1qtZ1nkOL15cdxevIK3wxAOE8xeo6gucWSySxgpVBvtrbQewWh02nkDurcpuSzxM5lnVYeK4Oi52eSTnbhuP0jNuCV15U/sf7wgXkxw4AVj4U1hSKCZXyaLt7cM+I30m7apYqlaMAKvyLujNUo0ixtUDlb4h5PNvhl8e2ldy+PWRcF0gxZ/IZAE/Ne0B+vPWVOF1rb/7ATXnWJWSFAso/y8CNkxeKmdERvpjoeJtFk8jDdM+GfzBOGCDHT1HfKBsAWKjIozWfxTxFT9Md3bFfy358DljSIlaMJnZp+yK72z58AZAtLgeUGhq9qmGdnOfdQ2jl0EnL7OCqlGSdKVys3ZFfvjZ3NvO9xPVf+kOfbgR/NRHHRvt+YpjG5MZUDeqgXSHM3eUPt2moISRc0Bl9fl5HGxdecZbDazzvDQqPzA6u573ftOYXDv24OLpXS4XMWufAbwPtRQFthQ6VWLnaUOltLNY0A8/RijCf5jrydCsDf/Ql7TLIH+xUNFX066jsSS88mRUaP0XfpdqQilJf6ipSd7IuMeS++69HQjbeeQJ6z3V5xsciXInYR24ppKj//gn8MySQB5GpY+7Fpo3dYB9o+53VMbvFgTjbwoEkvJxk1UVJFfwX7xXWWEevXcBoHCriT3GrhXQglhMRBfj2H1hE5UtIcCI+rtHa3EXC2w7cL5rhZgtkyoCcd3UeVQFOUjODgsqsGgiyxBMmWpB3OgIRQ+gJbKzSAOCJWH2mD5uJ2yk/uYQkp+iD7MCjxuDfs3cfvbsuY/tD8TJKizKyD+G3PleeQObj5bAAABhGlDQ1BJQ0MgcHJvZmlsZQAAeJx9kT1Iw0AcxV9TpUVaBO0gopChOlkQFXHUKhShQqgVWnUwufQLmjQkLS6OgmvBwY/FqoOLs64OroIg+AHi5Oik6CIl/i8ptIjx4Lgf7+497t4BQqPMNKtrHND0qplKxMVMdlUMvCKIPoQxDFFmljEnSUl4jq97+Ph6F+NZ3uf+HGE1ZzHAJxLPMsOsEm8QT29WDc77xBFWlFXic+Ixky5I/Mh1xeU3zgWHBZ4ZMdOpeeIIsVjoYKWDWdHUiKeIo6qmU76QcVnlvMVZK9dY6578haGcvrLMdZpDSGARS5AgQkENJZRRRYxWnRQLKdqPe/gHHb9ELoVcJTByLKACDbLjB/+D391a+ckJNykUB7pfbPtjBAjsAs26bX8f23bzBPA/A1d6219pADOfpNfbWvQI6N0GLq7bmrIHXO4AA0+GbMqO5Kcp5PPA+xl9UxbovwV61tzeWvs4fQDS1FXyBjg4BEYLlL3u8e5gZ2//nmn19wNkDXKhWfC+CAAAAAZiS0dEAAAAAAAA+UO7fwAAAAlwSFlzAAALEwAACxMBAJqcGAAAAAd0SU1FB+QIEg0gGAVRCEYAAAJuSURBVDjLnZNLSJRRFMd/95vvMc5YOr6mEYXUoIdp9LBcFFQQVItqEUEPWkRRUC0iCCOElkKhZPs2RS6K2hRpmg+CHlNK6RAKUQRGjxltmmZ05ptv5rQoH1G66A9ncTmc3z3/e89BRJgr2Heb+fIighIRAJrujiCTUTrejvEtmaLGn48rk+QR5VyoKyf6IQSaQRY4s3c9OYaglELjty7HHD4nbOKpNIMJZ3cgL0fycnMPbrei9PQPEfoGjq5z/30Cr1WFUgpgBtC7s5z66lL6YzaM/AjUrQiwOOC78WQ02hqLJwiHetmwqoKJYhOO7pgqmwEUipBIZzEADGQiLZx9PMqZ7StOL1poHiqp3si1zmG8BmDxNwAFk3aWAhdgKZIObCnz0fb6K0srA9dDX35cHf8eIxONMFva7EMyA24FuISUgNttku+1aHsX5/CmqlOFXnP/Mj1vPoBgKgGXYGc1PG4T07RY6fPwLCyU+fNulvg8fwD0GQeCLRo6AmRxlAvLstAVKKVRqGxevXzT1DUchrJ/AADsDGgigODgwmtaKAULtDSDvX0NXS0nrgBw8uS/LTjKhYaAZMhqOm6PxYIcg4Gnzy91tpxoBpJbW+7M/QaOcv3qIJMFw8BSMPDwXkNP04GLQBrA6yv6G6CUon5dLa27KjA0KPNoqUQ8afd3d13uaT7WDEzU7jtHQ/cYpGyIjs/8vsivmTb8S5Qk47J8xxEMQy8aGP5YyYvgGxiK51asIaeglPBYjECBh08D7UztkA4QjoxTHFgtjeeP09H+gGAwGAEiePxs27yH+rU10wW2bdPYd4upi6e38X/1E3nDHDifVZPbAAAAAElFTkSuQmCC',
        'last': b'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',
        'insert': b'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',
        'delete': b'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',
        'duplicate': b'iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAABhGlDQ1BJQ0MgcHJvZmlsZQAAKJF9kT1Iw1AUhU9TRZGKQztIcchQnSyIFnHUKhShQqgVWnUweekfNGlIUlwcBdeCgz+LVQcXZ10dXAVB8AfE1cVJ0UVKvC8ptIjxwuN9nHfP4b37AKFZZZrVMwFoum1mUkkxl18V+14hIIAwokjIzDLmJCkN3/q6p16quzjP8u/7swbVgsWAgEg8ywzTJt4gnt60Dc77xBFWllXic+Jxky5I/Mh1xeM3ziWXBZ4ZMbOZeeIIsVjqYqWLWdnUiBPEMVXTKV/Ieaxy3uKsVeusfU/+wlBBX1nmOq0RpLCIJUgQoaCOCqqwEaddJ8VChs6TPv6o65fIpZCrAkaOBdSgQXb94H/we7ZWcWrSSwolgd4Xx/kYBfp2gVbDcb6PHad1AgSfgSu94681gZlP0hsdLXYEDG0DF9cdTdkDLneA4SdDNmVXCtISikXg/Yy+KQ+Eb4GBNW9u7XOcPgBZmlX6Bjg4BMZKlL3u8+7+7rn929Oe3w9rHnKk7x4JKQAAAAZiS0dEAAAAAAAA+UO7fwAAAAlwSFlzAAAuIwAALiMBeKU/dgAAAAd0SU1FB+cCARMnD1HzB0IAAAAZdEVYdENvbW1lbnQAQ3JlYXRlZCB3aXRoIEdJTVBXgQ4XAAABJUlEQVQ4y6WTT2qDQBTGvxnLwFTETZfZZCu9hPdwJei2B3GThZcovUJAkx6hdXqBisxOycI/YF43VWxiTEo+eAy8gW9+35sZMMYeAWxM0zwAoEvFOSfbtvcA1piIAdhEUfTieR4451iSUgqu634BcMamaZqHoihoqqZpLtYv0WpqTFprIiLK85x836elKJP6GOKMBr7vU5ZldIuSJCEhxHY0GPBuldaaDMOg5akBqOsaYRjO7vV9j6sEZVnO9rXWBIAelk7uug5VVQHAuEopIYTA2S2cEgRBMDv9OI7/EIBzflcEblnWu1IK92gNQA2Ip2rbdsSeI5garf77DqSUx+ktfAP4TNP02XGcq9i73Q51Xb+dxRFCbA3DWPwHUsojgFfG2NMPCKbWh17KiKEAAAAASUVORK5CYII=',
        'search': 'Search',
        'marker_virtual': '\u2731',
        'marker_required': '\u2731',
        'marker_required_color': 'red2',
        'sort_asc_marker': '\u25BC',
        'sort_desc_marker': '\u25B2'
    }
    """Default Themepack"""

    def __init__(self, tp_dict:Dict[str,str] = None) -> None:
        """
        Create a new ThemePack object from tp_dict

        Example minimal ThemePack: NOTE: You can add additional keys if desired
            tp_example = {
                'ttk_theme : the name of a ttk theme
                'edit_protect' : either base64 image (eg b''), or string eg '', f''
                'quick_edit' : either base64 image (eg b''), or string eg '', f''
                'save' : either base64 image (eg b''), or string eg '', f''
                'first' : either base64 image (eg b''), or string eg '', f''
                'previous' : either base64 image (eg b''), or string eg '', f''
                'next' : either base64 image (eg b''), or string eg '', f''
                'last' : either base64 image (eg b'') or a string eg '', f''
                'insert' : either base64 image (eg b''), or string eg '', f''
                'delete' : either base64 image (eg b''), or string eg '', f''
                'duplicate' : either base64 image (eg b''), or string eg '', f''
                'search' : either base64 image (eg b''), or string eg '', f''
                'marker_virtual' : string eg '', f'',  unicode
                'marker_required' : string eg '', f'',  unicode
                'marker_required_color': string eg 'red', Tuple eg (255,0,0)
                'sort_asc_marker': string eg '', f'',  unicode
                'sort_desc_marker': string eg '', f'',  unicode
            }
        For Base64, you can convert a whole folder using https://github.com/PySimpleGUI/PySimpleGUI-Base64-Encoder
      	Remember to us b'' around the string.

      	For Text buttons, yan can even add Emoji's.
      	https://carpedm20.github.io/emoji/ and copy-paste the 'Python Unicode name:' (less the variable)
      	Format like f'\N{WASTEBASKET} Delete',

        :param tp_dict: (optional) A dict formatted as above to create the ThemePack from. If one is not supplied, a
                        default ThemePack will be generated.  Any keys not present in the supplied tp_dict will be
                        generated from the default values.  Additionally, tp_dict may contain additional keys not
                        specified in the minimal default ThemePack
        :returns: None
        """
        if tp_dict is not None:
            # The user passed in a dict.  Make sure that it has all of the minimum required keys.
            # if it doesn't have a key, use the default for that key
            for k,v in ThemePack.default.items():
                if k not in tp_dict:
                    tp_dict[k] = v
        else:
            tp_dict = ThemePack.default

        self.tp_dict = tp_dict

    def __getattr__(self, key):
        try:
            return self.tp_dict[key]
        except KeyError:
            raise AttributeError(f"ThemePack object has no attribute '{key}'")

    def __setattr__(self, key, value):
        if key == 'tp_dict':
            super().__setattr__(key, value)
        else:
            self.tp_dict[key] = value

# set a default themepack
themepack = ThemePack()


_iconpack = {
    'ss_text': {
        'ttk_theme': 'default',
        'edit_protect': '\U0001F512',
        'quick_edit': '\u270E',
        'save': '\U0001f4be',
        'first': '\u2770',
        'previous': '\u276C',
        'next': '\u276D',
        'last': '\u2771',
        'insert': '\u271A',
        'delete': '\u274E',
        'duplicate': '\u274F',
        'search': 'Search',
        'marker_virtual': '\u2731',
        'marker_required': '\u2731',
        'marker_required_color': 'red2',
        'sort_asc_marker': '\u25BC',
        'sort_desc_marker': '\u25B2'

    },
    'ss_small': {
        'ttk_theme': 'default',
        'edit_protect': b'iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAGJ3pUWHRSYXcgcHJvZmlsZSB0eXBlIGV4aWYAAHjarVdZsuQmEPznFD4CVSwFx2GN8A18fCeiUG/zZtoRfnrdQoCKpDJJaDP++Xuav/DH7L3xQVLMMVr8+ewzFxSS3X/5+ibrr299sKfwUm/uBkaVw93tRynav6A+PF44Y1B9rTdJWzhpILoDX39ujbzK/Rkk6nnXk9dAeexCzEmeoVYN1LTjBUU//oa1b+vZvFQIstQDBnLMw5Gz13faCNz+FHwSvlGPftZllJ0jc92iBkNCXqZ3J9A+J+glyadk3rN/l96Sz0Xr3Vsuo+YIhV82UHird/cw/DywuxHxa0MaVj6mo585e5pz7NkVH5HRqIq6kk0nDDpWpNxdr0Vcgk9AWa4r40q22AbKu2224mqUicHKNOSpU6FJ47o3aoDoebDgztzYXXXJCWduYImcXxdNFjDWwSC7xsOAM+/4xkLXuPkar1HCyJ3QlQnBCK/8eJnfNf6Xy8zZVorIpjtXwMVL14CxmFvf6AVCaCpv4UrwuZR++6SfJVWPbivNCRMstu4QNdBDW+7i2aFfwH0vITLSNQBShLEDwJADAzaSCxTJCrMQIY8JBBUgZ+e5ggEKgTtAssfSYCOMJYOx8Y7Q1ZcDR17V8CYQEVx0Am6wpkCW9wH6EZ+goRJc8CGEGCQkE3Io0UUfQ4xR4jK5Ik68BIkikiRLSS75FFJMklLKqWTODh4YcsySU865FDYFAxXEKuhfUFO5uuprqLFKTTXX0iCf5ltosUlLLbfSubsOm+ixS0899zLIDDjF8COMOGSkkUeZ0Np0088w45SZZp7lZk1Z/bj+A2ukrPHF1OonN2uoNSInBC07CYszMMaewLgsBiBoXpzZRN7zYm5xZjNjUQQGyLC4MZ0WY6DQD+Iw6ebuwdxXvJmQvuKN/8ScWdT9H8wZUPfJ2y9Y62ufaxdjexWunFqH1Yf2kYrhVNamVr66TynlKlOengN5/LcEGP4KxHWInT2n0cr1xiiwKpqr29qb9N20X8QeqQ3otEeYEQ7Zhv8Wzwe+GvfAM1dnenTIwYWrtgGOx36Irqbh40boXZ/c+kIE7qMbO5TnvkHCis3bIDg8XHF6chNb7J6V/eJuroIbTVENSTP6svMDvy+0XHshmR5tTeD9qwlyrVEs7X5E0/jiNv4MvwpXtAz1F4VY69XV55qzhkiIP1hDlCaIj5JZ+dfAn3fpUV9AbzzYncCMhbdhYrPaWRmmYguAmve8cpu2VdHBGCsm00U61EoTqyfs9zP14vf0cU5C6rcg13kE60uVNti9of4BbOgHbANYYzUJt84cKNukAodmqmTNMBLk9wvSoRSXe1bEZubhaYjSBE35JHSTNtBx5x2ScjsdEf1fUJcVyvwAex7YEbB1cTTvdw+mEx6nIIVviHQJ0ZZpSHCJoUsI0lEhYL7DteDKESzAt+ULu6dtZnabpu1Pes7vunUgfbfDXfDQqtO8IsuKgszGA2KVNktdJxhEa1Snj8jMR05JjkhNsSKauQ6XcXDArCKssNX4G60e+mGIXczhuFvvd3icEarivBezf8WCwg2XdgGn2q0RbEJasLQXHza31s6oiYH0trbDzzxSb9ZIoDMVGM4YpMRikr2pC1xHeS2cmjunis2g5N5QYkJnSR43KwREPRx4/hOeeeAcVTsi2zNAMAp7Yl363YQDk8p7DLa6uvlCYF4pP5z4Uwib+pK8Tgp7+4hBZYUj1vBtJ/u35j530Vs15+bF6eLBjymhtucH0MVI9aq82poT5TAm/Lx8T522rV9Km1ZWnYRiE1Z/3WxjfDfCF3vQfK+6RjQQeir12E0Rqg8tgBp1y1axTSVtkpyJuko2azhjb61AfnL4TaDOvsnvpztN6X350aqrGoxP4zEXbQkZvzwUUIIyovDRCk4dDe6x9/413X6sYeak4u7rwX23S5on2+n9eHQ+/jdDP63l1n05sPPJSvTdbOsW6nCMWxTw4kCqieHKAqnnDpwUZ+Yft+wPTyz3+rv97qRR3MOS0m2C1by7oDu7dcR2FV6PSH8+RHwiuhNST0LKAXLOMtTqw5eiOWV3V9LZYb4V0nU3v1QYzoHmX+RGJBpl98L8AAABhGlDQ1BJQ0MgcHJvZmlsZQAAeJx9kT1Iw0AcxV9TpUVaBO0gopChOlkQFXHUKhShQqgVWnUwufQLmjQkLS6OgmvBwY/FqoOLs64OroIg+AHi5Oik6CIl/i8ptIjx4Lgf7+497t4BQqPMNKtrHND0qplKxMVMdlUMvCKIPoQxDFFmljEnSUl4jq97+Ph6F+NZ3uf+HGE1ZzHAJxLPMsOsEm8QT29WDc77xBFWlFXic+Ixky5I/Mh1xeU3zgWHBZ4ZMdOpeeIIsVjoYKWDWdHUiKeIo6qmU76QcVnlvMVZK9dY6578haGcvrLMdZpDSGARS5AgQkENJZRRRYxWnRQLKdqPe/gHHb9ELoVcJTByLKACDbLjB/+D391a+ckJNykUB7pfbPtjBAjsAs26bX8f23bzBPA/A1d6219pADOfpNfbWvQI6N0GLq7bmrIHXO4AA0+GbMqO5Kcp5PPA+xl9UxbovwV61tzeWvs4fQDS1FXyBjg4BEYLlL3u8e5gZ2//nmn19wNkDXKhWfC+CAAAAAZiS0dEAAAAAAAA+UO7fwAAAAlwSFlzAAALEwAACxMBAJqcGAAAAAd0SU1FB+QIEg0fJQXnbmsAAAKVSURBVDjLhZJPSFRRFMa/c++b55tGTZpSMZRStCyJFlEoLkSyWtQiyI1FUWRtIooWFS2yKHcG0aICN1IWCNWmQhfixqQokDAHpY3lFJiTZo7ju/e9e0+LwP6o9W3O6vvxfeccwjK6dPEirrS2IkmUE2loeCGkTBFwjIAxw4yinh4AAC0HMIlbSL0zmHs72SV7extldjaElDOS6CoDNwCgsLsbYjmA+q6Rk//xaN6p5kbRfIJDIjZK5YbWtjHQWRCNYqS+fukEmQebIYQTD3R6eJ7z883W83C8LZRpucRIJkl6HtZWVNBIIgH5t3n2fhUIBmxNu1K6WmdSUIl2aJLIab4MGEFhcvz41OfPgyGwuIIkA0Cc01o1KaXBzIC7Clnjd2j2yWFS1WsSBR2POiURNvX1/arw6W4ZYlEHjqD1YaAH5+f9XCEIvq8QiTgAiIIgNGZ4stDZ1ZIqaWwBfk9QFJdwBcOEpsv31UoiwFoGEUFKB8YYWLb7Ubk6FSZvLyQWAPD+1WPM2HKExlxXyt9mrWE34pIxhqJRD9ZastZ2Z2a/Pg2NRenZiQUAAUDHbmBvEzayj0FfF3qx2ArWWpMQPwMqpWbSGbXGy3KCdWdSf+xMAMDBZxorD5kGt67b8/KqGDwHImIpBRsTGiLsiXpuMOcvPrlYGMzlXulOxPbdI17biCwxTsYwMXOn6zovBQGbL6SWBjAzAGwgMNjNY7fuJnj7QxhZ8EFk5RxRyqL49JclP1YCgNYa/f3910pKSvLi8Tjp+TR9Q36XjhYf4NmxtFQTaHueXhJAZWVlcF0X1loeHR0NBgYG3sRisZORSGTo29QUampr8S8Jay2mp6dzieh1ZWXljpqamtogCIbCMPyvGQB+AKK0L000MH1KAAAAAElFTkSuQmCC',
        'quick_edit': b'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',
        'save': b'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',
        'first': b'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',
        'previous': b'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',
        'next': b'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',
        'last': b'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',
        'insert': b'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',
        'delete': b'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',
        'duplicate': b'iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAABhGlDQ1BJQ0MgcHJvZmlsZQAAKJF9kT1Iw1AUhU9TRZGKQztIcchQnSyIFnHUKhShQqgVWnUweekfNGlIUlwcBdeCgz+LVQcXZ10dXAVB8AfE1cVJ0UVKvC8ptIjxwuN9nHfP4b37AKFZZZrVMwFoum1mUkkxl18V+14hIIAwokjIzDLmJCkN3/q6p16quzjP8u/7swbVgsWAgEg8ywzTJt4gnt60Dc77xBFWllXic+Jxky5I/Mh1xeM3ziWXBZ4ZMbOZeeIIsVjqYqWLWdnUiBPEMVXTKV/Ieaxy3uKsVeusfU/+wlBBX1nmOq0RpLCIJUgQoaCOCqqwEaddJ8VChs6TPv6o65fIpZCrAkaOBdSgQXb94H/we7ZWcWrSSwolgd4Xx/kYBfp2gVbDcb6PHad1AgSfgSu94681gZlP0hsdLXYEDG0DF9cdTdkDLneA4SdDNmVXCtISikXg/Yy+KQ+Eb4GBNW9u7XOcPgBZmlX6Bjg4BMZKlL3u8+7+7rn929Oe3w9rHnKk7x4JKQAAAAZiS0dEAAAAAAAA+UO7fwAAAAlwSFlzAAAuIwAALiMBeKU/dgAAAAd0SU1FB+cCARMnD1HzB0IAAAAZdEVYdENvbW1lbnQAQ3JlYXRlZCB3aXRoIEdJTVBXgQ4XAAABJUlEQVQ4y6WTT2qDQBTGvxnLwFTETZfZZCu9hPdwJei2B3GThZcovUJAkx6hdXqBisxOycI/YF43VWxiTEo+eAy8gW9+35sZMMYeAWxM0zwAoEvFOSfbtvcA1piIAdhEUfTieR4451iSUgqu634BcMamaZqHoihoqqZpLtYv0WpqTFprIiLK85x836elKJP6GOKMBr7vU5ZldIuSJCEhxHY0GPBuldaaDMOg5akBqOsaYRjO7vV9j6sEZVnO9rXWBIAelk7uug5VVQHAuEopIYTA2S2cEgRBMDv9OI7/EIBzflcEblnWu1IK92gNQA2Ip2rbdsSeI5garf77DqSUx+ktfAP4TNP02XGcq9i73Q51Xb+dxRFCbA3DWPwHUsojgFfG2NMPCKbWh17KiKEAAAAASUVORK5CYII=',
        'search': 'Search',
        'marker_virtual': '\u2731',
        'marker_required': '\u2731',
        'marker_required_color': 'red2',
        'sort_asc_marker': '\u25BC',
        'sort_desc_marker': '\u25B2'
    },
    'ss_large': {
        'ttk_theme': 'default',
        'edit_protect': b'iVBORw0KGgoAAAANSUhEUgAAABgAAAAYCAYAAADgdz34AAADqUlEQVR42qWUW2gUVxjHvzO7O7ubzDYWUZIGY7IumqiNTdHYSB9UlJS+tIog+OAFfKqJVqqg1Ni8iW0JVKxCHrRiElvSFsGHCM2lERWjsKKBjbrgBY2ablxwL9ndc/U7k1WISepuPHCYmd2Z/++c3/fNEJjBeLxuXa3DMC4QwxgmANuLL168Pd29JN/wO/X1VgFjQQwPGIaBByONIU0JzlsC3d3yvQD3hkKGeW3gL9XW9rUhpdIAJAAeFZ79i7fswN08mjEgGTq3k5Z80ZoMhYCfOAEwPKzD7ZkFvcTABoS05w1ItC+dTUDcTs36rMS5vIlQZira0UF4V5cOUVldGiRjjC2o7O19mBdgrGNJJ6OZTZRmVAp8xLWiWbnmrSVycBBSx48rFY3aAFT1IiaEf3FfXyxnAIZvFZz+lslQoJSClAIoEwDlG6Fw5UEwlQmp1lagly4BcTg2z+/p6cxZUbJ98Xwl+S0MLtIApaTiXBAhxHiRfRWgPj2sfGWrCAkGuz5cv/7LnIv84OQiY46P9KCa1TpcSokApRhj+jnldruJ/o1ypXhgR8Rauu3zkvKqcM6ARFvlfs7oUa2FMQ5OpwMVMcDVg2m6AHsUOOf6Wklw1vv3jnS/nTEtIH520TIpxDUsqhsBxOVyYZDUNbDVuN2mrUoDcBe/lO998e1UOVMCnrYucFtu4zqGfYwAu88djvHV68CCAq8N0+c4Q6hoxcL90VTOgNiZwM+o5Ltsxyivt4AwRm0AqrF3gP/jDjjF1a/C1QenMzEJ8PJMYA2q+QeL6sBigmUVKikkySCM4N2mqdVwVCMUuv++bE/kyP/VcQIgPPC3Z+6TX++kI3fLtHev14OFdSl9rnV4PB67oOMAfjk2JlcvOTAqcgYwlqlTLHUlduUHoOFO+MBn2S9WVg22KGS7hsexBjXzdv93H94xJgDw4c3Y5r+jVyWe9BB+oxlo/DnGEqJbNFtUVCN3ljY8P/Wu8KkA+xDwkwbgJHIsApmBQ8oZuaqdv179+ZJvnm3IJXwqwDEENOi3c8K8/yfwmz8CS8dHsAGqP9r1LDIjwOjo6PmioqKv3uxgHKC/DiQ5MpRhN5o3lG3B73MeYwKgtrY2WFdXV9PY2KhKS0ttQDqdFtFo9I9kItH8SU1NOJ/wSYCqqiq99dmWZUFLS4uGXEgkEk3V1dWD+QZPAvj9/kLs8zjq0Fq6i4uLm/r7+wdmGjwJUFFRsRDf0tMYfigcDve9b/Dr8QptdEU3XH9lbwAAAABJRU5ErkJggg==',
        'quick_edit': b'iVBORw0KGgoAAAANSUhEUgAAABgAAAAYCAYAAADgdz34AAADqUlEQVR42qWUW2gUVxjHvzO7O7ubzDYWUZIGY7IumqiNTdHYSB9UlJS+tIog+OAFfKqJVqqg1Ni8iW0JVKxCHrRiElvSFsGHCM2lERWjsKKBjbrgBY2ablxwL9ndc/U7k1WISepuPHCYmd2Z/++c3/fNEJjBeLxuXa3DMC4QwxgmANuLL168Pd29JN/wO/X1VgFjQQwPGIaBByONIU0JzlsC3d3yvQD3hkKGeW3gL9XW9rUhpdIAJAAeFZ79i7fswN08mjEgGTq3k5Z80ZoMhYCfOAEwPKzD7ZkFvcTABoS05w1ItC+dTUDcTs36rMS5vIlQZira0UF4V5cOUVldGiRjjC2o7O19mBdgrGNJJ6OZTZRmVAp8xLWiWbnmrSVycBBSx48rFY3aAFT1IiaEf3FfXyxnAIZvFZz+lslQoJSClAIoEwDlG6Fw5UEwlQmp1lagly4BcTg2z+/p6cxZUbJ98Xwl+S0MLtIApaTiXBAhxHiRfRWgPj2sfGWrCAkGuz5cv/7LnIv84OQiY46P9KCa1TpcSokApRhj+jnldruJ/o1ypXhgR8Rauu3zkvKqcM6ARFvlfs7oUa2FMQ5OpwMVMcDVg2m6AHsUOOf6Wklw1vv3jnS/nTEtIH520TIpxDUsqhsBxOVyYZDUNbDVuN2mrUoDcBe/lO998e1UOVMCnrYucFtu4zqGfYwAu88djvHV68CCAq8N0+c4Q6hoxcL90VTOgNiZwM+o5Ltsxyivt4AwRm0AqrF3gP/jDjjF1a/C1QenMzEJ8PJMYA2q+QeL6sBigmUVKikkySCM4N2mqdVwVCMUuv++bE/kyP/VcQIgPPC3Z+6TX++kI3fLtHev14OFdSl9rnV4PB67oOMAfjk2JlcvOTAqcgYwlqlTLHUlduUHoOFO+MBn2S9WVg22KGS7hsexBjXzdv93H94xJgDw4c3Y5r+jVyWe9BB+oxlo/DnGEqJbNFtUVCN3ljY8P/Wu8KkA+xDwkwbgJHIsApmBQ8oZuaqdv179+ZJvnm3IJXwqwDEENOi3c8K8/yfwmz8CS8dHsAGqP9r1LDIjwOjo6PmioqKv3uxgHKC/DiQ5MpRhN5o3lG3B73MeYwKgtrY2WFdXV9PY2KhKS0ttQDqdFtFo9I9kItH8SU1NOJ/wSYCqqiq99dmWZUFLS4uGXEgkEk3V1dWD+QZPAvj9/kLs8zjq0Fq6i4uLm/r7+wdmGjwJUFFRsRDf0tMYfigcDve9b/Dr8QptdEU3XH9lbwAAAABJRU5ErkJggg==',
        'save': b'iVBORw0KGgoAAAANSUhEUgAAABgAAAAYCAYAAADgdz34AAAEp0lEQVR42qWWf0zUZRzH35+7+95PDksKmagXjCTAUNB+2FbN1XZXNJrhlo7MLF1WGksry7GiVm6pqS1tmStnxrIRFVaKrGmuqWvNIA1EYR5gkK418Hvc7/ve0+f5fr8I+ef53T483+fZ7v269/t5ns9BMJ5crhe5yrgsyOzZxHX82kXiyoPN9ivur52OKbMIpOuLe6dZqSrPjiyPW3jcTnI7HXA6HFAUm0in0xRPJEQ0lqBwNIbm7kHRtuPdEMJqNX/22LWALbhv+ToULhTmXAcsutNNK0qzMMnrEd4sN3lcLricdhCRGFIjdPofVSTjcfJZNHzSqYqmX7oILfWjGL3yKH/+yETAQTyyKYCcYp6RsWK1YMndWXiu/AZke9zsQoo7odisSCSTaDl/CS8f78UkxYJd5TnY0xPFdx1JIDEAfLshitDIQlZpGwMcQtXmAHKLBWwW4mIAiWV3eWnN7Bx4OSK3y0kOu4KUpiEai4sfugep/li3yFastLniZjT2p8SPPVaClgZifwk0r49BHa6R2gageksAU0sYYDUANhIr5nnppcpccDTC6bTr0cViCYSjUXGo8yJtPNopsuxWqq/Mw9eXINqG3IQUp5xKC8QGCU2vxnHl30UGoGabH9NKoYsrFn1cVenFK3PzOBoHc62IJ5KI8IaGwhG0911GS0cQlNawIN+DA8N2/KxOluJGJbmGfgeaXj9sABZ/EMCMMgFlzIFFrJ6TRa/Ny4edT00ypVE0FsNoOAo1HBGqGqYRNSSG1RANj4TQGnGLE1o+mQCBpEYY6AT217UagKU7AvAxwG4CFKuY7NDoJoe8FRYhICgtj5ZIc8z8V0uTpmkizWAtpWEUDhElF7HwOKCPAftWm4CnP/KjYBYL26T41Zh4LyRAbvr4CdMPsU4DWAua+H80EiIreAb47Hkzomc/DqCwXHdwz/RszJ/qFSxKsOjCgu826YBxeWKAQFofJUgwiE4OhXDioiqQYAcXTgO7VpkOXtjtR1E5GIDztWUoynZk1Ct61ThmNnI0CXbQy4CdK00HdZ8GMHO27iC4uBQ+jyL4xupfmb/o1feJ84nrY+99owkU7O8yHPT8AWx/xnSwbk8AxXMEHAx4rPj6AN+cE4gz4FwH8P5yE7B+bwC3mYDqW+FzZwgIM+BAjwHoZsB7y0zAhs/9KKkAAxB8uIgBtoz2oD+SQsHBXjAAONsObHzS3IP6fQGUVgg4bRT0F8LnsmXmIJJEweEL3CrYQRff5HeWmg7e+CKAskoD8OAt1wf4qY8BKUInA95+wgQ0NPoZAAYg+IAPPmeGEcU4oiP9QDQFHdBQa0b0VqPhwKVQcMEMCcjMQZQdHB0wHPx5CnizttX4wWlofAi3z9Uj2lt2I6qmeMVYY+B7KiY0iavzietj799fDuGpzmEDcOaUdKD/HmzDkrV1qFmpRyRPEmRCcnSYc7tZivn/gOw58rbKkicmnjJGHvQ1GVHzbuDLrdslIB+K/Tc8viYPFfMJLocU1e+EKW60cSlutRhdjvsOQ4yuaUCMsy/fI3GB9pOErz78G8nEHWPW87nWcpVgQhwZPrIZnuXayjX4H7Qeh+TT7afMAAAAAElFTkSuQmCC',
        'first': b'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',
        'previous': b'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',
        'next': b'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',
        'last': b'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',
        'insert': b'iVBORw0KGgoAAAANSUhEUgAAABgAAAAYCAYAAADgdz34AAAFJElEQVR42qWWa1CUZRTHz3n3wrLLAnKNi7dEYCW5Vo4gaJI2pgx8yIb64ocosssoVqbN9KmZGMsBHafM5Itfisk+wKA5XlMR7AaIhgsIiYTI6rLALqwv7767p/O+LMiOaUXPzH9299lnz+85/+e851mExw89ax2rkJXGivLP21kdrLOs0yzpUQHwEfMG1jbQYAUui4xhISaYQRumTAPJYyLSbRfR9WFk2cBL1Ty/nyX+G0AGq1abF5caUpQMuZYcejbWgknhiRCqN6kApzSBPaMD9IvNis3WFhhv6Ca56U4Xf1fKan8cYC0atXXGMkvIyjV5ULykgIMapxZh4GIiFr86JTfU916Ey+ebwF1jHSe3XMLT5/4OkMHBGyM+yDBvyC2k7JhUFDgEIpDocaPD7ZiJrfwuwhhBBp0RFZAPkFrvduKJ5rPg+LzdxZD86UymAQZ+1xZVkZaav3YVpEctJQEJWSAwYFlEKpY8WeTfORHyqPujga47OtGnAAiJIXj1Xjc0nmsie3VHF28jSzmTacCH5tWxlZat2bAqPpvPlkAjAEwBiIHp8NKS0gAvv++thav2q0pwVV4f8FkjXBpsBevBFnBduLubl+1RAHrUYH9SVWZMTvJyjDRwtXDiGoF4WoVQRvTT+EryawEZfNtdQ+33WlANTkAcHGUfgkN00W/d17BnxxUbTy5QABtDc8KPWXZaKC0iCXUCgVYgYgj6s6Cs6JX4asq7AYBvug5Q273L6N89yX6Ax4fU4ehB62dWcLaMblIAVYvLFm5P2jgfEkxRoOegC4OfUrwH/yGDJWo5bFzycoBFx3u/A6v9GvgPWX3tE38HyQswOGGHGz/8CTcP39qnAE5mV6asT0ibR2wPmnRaOLD6uLrL2Tt+UJ5Tn2fPT79/5/yLMOHxkEMcx4GOEWjd3XVKWdBScMiSFZ0YDGF6A5h0Othf8CPMZWy7+By4PR4YlUSwD9yHC+XWNhWwviYlOzJBR2a9HkM4g72rfppTBu81roBxzsAleXD4tgdOlXW1qhatq17MFhnIpAMG6KEyt21OgF1NmQyQyO0BtkiE0xU3VYuqcrc9UZFeHEbBGi8adQI8E7uJuJKQpTwTFGfMwrTILQGAjuEjNORuQ64e4OohFv5qO8YW+Uj0arC9fgya9w9Vq2W6KC+koeTTOAjWelk+MLCCNFPSCT5ICi+G/LiDAX433tkKPaP1XJYCTHqRpQFRFuC+X3UfDUFf03iR+qAJWuh/8+jCmJh45HakALxk0PjQD6FFoSW4IvbrgAx+tr1Bfc46lLwCiF6Bdy2gKGuU4GQbJPxq8y2bT4YFM60iu9hcufnjeSrAqCXiLNDgBywwF2NG1OEAQLv9dep31c8AODC6ZQQ3A45+MoKt9a5d061iptmVfxGdkpmvAzOXqlEHEOy3Kd5UBMnhXwZY1D36Fj9QDWwNW8LigwUXl+iVRgkOvW1/qNmp7doYipd2HokMsaQFUXiQkg0BZ8HZACo+cn9Sk/DygUo+mUQZUFQAMtLI5Ah2dkzCni3DLreTHmrXMxeOKQzrd+wLNeUXhmJkUCLbpSfOAvWcidJlVQCbxNYQ755tkWB4coAazzqxarvTNTFGj7xwHlw8CLUbSvUp5e8bYOmiaDDro7m6wrgagtQFkm+Sdz0GLuku3Oizw6G9Ipyolbq4H/3jlTk91Etfq4OKguc1MYUvIOZkEsyPV9oaUP+ggK1XkM6cJLx4xmuTPfCfLv3Z43//bfkLo1muAZZ9QHcAAAAASUVORK5CYII=',
        'delete': b'iVBORw0KGgoAAAANSUhEUgAAABgAAAAYCAYAAADgdz34AAAEe0lEQVR42rWV21MTVxzHf5sLWQJjEyBAIgkhQHBEHNAXL0/MtC9KbRWofUz+AP8gn3bfnKojrZfptF4Yp30oF2VRp6ZAS7jkTshuuAUDpN9zyIbUALUPzczOZnd2P5/fOb/vOSvQ//wTyi9+aGqyWez2UdHh6NVmZoJfJRLyp0BGnM6A49w5KRsOK9urq/3XYzG1QsDgYmPjaM+tW71GUaQ/79+n5Ph48Ot4XP43uHdgQHJeukRr8/P0x507yof19f4bRYnwMVwQBIo+fUqmEydIC4dp9d27IyUPAAdYart6lZIvXtCHbJbIYqGYoij5jY3+G9GoygU/9fRM6fClx49pBw8aqqpIdLn2JaFQEMOWP4Y3X7wo+YrwtVCI37c4nUSYgdj0tPLl7GwfF4wNDRW8167R4sgI5VWMrFCgwt4eGcxmEk+eJG1hgTLoiS554HIFmi9ckHxXrlAK8GwRzt5j71g7Oig1M0OfT04K+hQFGlGNaLNRbnGR9nZ2iHZ38fz+C9UtLaQuLVFmbi7Ini/Bnz+ntffvDxJjMJDY2kobmkYJjHowGpVLTf6+uTng6OuTrA0NtIWKuQSjYAebLite1FIpMtfUEJuW1LNnfFoEFMHhRiOJHg+tMzhGOxiJyBUxZZKGs2cla309lxQg4QAmQfNq2tvJgbSkX76k7Nu3VMjnOYDBq71e2tjcpDhGqcMrBKVMnzkjWe12LiE2Ekh2WUJwNppMlItEiAXCwA5cWzs7aQOyVCIRHCqDHyrQJQ2nT0vW2lrSXr+mnXR6v4GYYwYVimfWnxo0lMET8XgF/EiBnpTP6uslC4a/NTfHp4pDGZwdDI7K1xk8FgsOLS8fulaOFdT5/ZLn8mUK375NlMsdwHGwZrOpiSeTpKpqcPi/CHR4O6KYffWK4k+ecKixCDdiVOy/CZJqTFE0FqPVTOZQiXAsfHKSYoDrYBPiygV4zgCJSZcgXQvRKK2k08FvlpaObjJb/jpcQ+UxbBt65Qxe4/fz/3lsH0zCR8JEkIg+H/2FxZhMpf4hKQlYcmyAdwCussqLcF45GloL+CZWN7u2W620gwgziQkx5RLcq2pro1nsqHEmWVw8WGgMbgecLX91YoKijx6VKjeicgbfAhxRlNm6dbvdgQZEeA8VG5Esc1FihMSMFf87UhfFmrgJCRf8fP584dTwMGVQeeThw4NmFivPAZ5MJmVEke9F99xuqa21NeDAlk7Ly7wXJUl1NQluN41PT9MXb97sb3Y/dndPdQwM9M7LMu1mMgfwri4OX2HwSCRY3q+7kHT6fAEnVryAlW0GnEtwna+ro1/GxpSBUKhPnyKbyWIZteFTuY2K9rAtMPg29qB0KlUBL5ec8vsDLQAaEdUqnKmpiX6dmFAQ2/6bCwuqUJYgm1kUR+2QCKh6G3tQZmVFHjwCXpJ4PFJ3V1fAAzBh1L9NTSlpwL8FvDKmLpcNiRnF9PTmNjdl7OfHwvXfd5B40XhtbU1Z1bQS/KiFZsPJi++p8inwMkkvTmEkRy2//zcpYDQ3Hbr/xQAAAABJRU5ErkJggg==',
        'duplicate': b'iVBORw0KGgoAAAANSUhEUgAAABgAAAAYCAYAAADgdz34AAABhGlDQ1BJQ0MgcHJvZmlsZQAAKJF9kT1Iw1AUhU9TRZGKQztIcchQnSyIFnHUKhShQqgVWnUweekfNGlIUlwcBdeCgz+LVQcXZ10dXAVB8AfE1cVJ0UVKvC8ptIjxwuN9nHfP4b37AKFZZZrVMwFoum1mUkkxl18V+14hIIAwokjIzDLmJCkN3/q6p16quzjP8u/7swbVgsWAgEg8ywzTJt4gnt60Dc77xBFWllXic+Jxky5I/Mh1xeM3ziWXBZ4ZMbOZeeIIsVjqYqWLWdnUiBPEMVXTKV/Ieaxy3uKsVeusfU/+wlBBX1nmOq0RpLCIJUgQoaCOCqqwEaddJ8VChs6TPv6o65fIpZCrAkaOBdSgQXb94H/we7ZWcWrSSwolgd4Xx/kYBfp2gVbDcb6PHad1AgSfgSu94681gZlP0hsdLXYEDG0DF9cdTdkDLneA4SdDNmVXCtISikXg/Yy+KQ+Eb4GBNW9u7XOcPgBZmlX6Bjg4BMZKlL3u8+7+7rn929Oe3w9rHnKk7x4JKQAAAAZiS0dEAAAAAAAA+UO7fwAAAAlwSFlzAAAuIwAALiMBeKU/dgAAAAd0SU1FB+cCARMnDMj6VvgAAAAZdEVYdENvbW1lbnQAQ3JlYXRlZCB3aXRoIEdJTVBXgQ4XAAACVUlEQVRIx7WWQUsbURSFv5nMZDJOFwHb7VuELFxk0y6EgK3QVXHjDxC6aKH9C4IFQZGCq5KVgl1oQRBB/AdCbKLEhRuhC10EMRCVQqAZZJJ5ud3E0CapZmI9MIt53Lnn3nPe3PcAMAxjBJhNp9NXgER5MpnML2CxnaMHlmEYIyLyHXg+MzPD6OgoUVCr1Z6cnp5+CoJgMhaLvdZah90xs4AcHx/LsCiVSrcdve+pIJ1OX83Pz8tD0Gq1xHEcAVZ7JDo7O3vWT5ZKpUKpVKLZbA4kldYa4FWbpOB53jff98XqF1woFJiYmMCyLGzbHojAtm1s2x7TWo81Go0Pvu+/M03zDYDkcrlOuxcXFwLI2tqa3NzcRJZLay3FYvFWssUegp2dHbEsa6jkf2JhYUGUUtdmd6vNZhPbtkkkEjwEyWSS8/Pzp+YwH+fzeZaXlweKHYqgXC6zu7v7eARR8OgE1qCal8vlzvv+/j7VapWNjY3Omuu6TE9PE4/HoxMcHh7+pXm1WqVSqbCystJZS6VSTE1N9RD0/AdbW1viuu6de3x9fV2y2eydMblcTgAxM5lMvVarPZ7JJycnX5aWljg6OkJE/r/JhmF8DoJgcnx8/KXjOGit7x1wruuSSqUGZ4nFYlb7sFgFftznQRAEUq/XB/OgPctD4CvwEchrrWm1Wv8sKB6P43nenUWHYYhSqu9h8haQYrE49CS9vLyUbDYrwKbRnd3zPMP3/T3HcSbn5uZIJpORTA3DkO3tbQ4ODn4CL/pvLdNMAItKqeuo1xilVAPYBBTAb9rfs0kjJGFsAAAAAElFTkSuQmCC',
        'search': 'Search',
        'marker_virtual': '\u2731',
        'marker_required': '\u2731',
        'marker_required_color': 'red2',
        'sort_asc_marker': '\u25BC',
        'sort_desc_marker': '\u25B2'
    },
}

## Use SimpleNamespace instead of passing dict['key'] via f-string. Can't pass b' (bytes) via f-string.
icon = SimpleNamespace(**_iconpack['ss_small'])


def load_iconpack(pack):
    """
    Appends user-defined iconpack to internal _iconpack dict.
    PySimpleSql comes with 'ss_small' and 'ss_large'

  	For Base64, you can convert a whole folder using https://github.com/PySimpleGUI/PySimpleGUI-Base64-Encoder
  	Remember to us b'' around the string.

  	For Text buttons, yan can even add Emoji's.
  	https://carpedm20.github.io/emoji/ and copy-paste the 'Python Unicode name:' (less the variable)
  	Format like f'\N{WASTEBASKET} Delete',

    Example structure:
        'example' : {
            'edit_protect' : either base64 image (eg b''), or string eg '', f''
            'quick_edit' : either base64 image (eg b''), or string eg '', f''
            'save' : either base64 image (eg b''), or string eg '', f''
            'first' : either base64 image (eg b''), or string eg '', f''
            'previous' : either base64 image (eg b''), or string eg '', f''
            'next' : either base64 image (eg b''), or string eg '', f''
            'insert' : either base64 image (eg b''), or string eg '', f''
            'search' : either base64 image (eg b''), or string eg '', f''
            'duplicate' : either base64 image (eg b''), or string eg '', f''
        }
    :param pack: iconpack. Key name of iconpack
    :returns: None
    """
    global _iconpack
    for k in pack.keys():
        if k not in _iconpack.keys():
            _iconpack |= pack


def set_iconpack(name):
    """
    Sets which iconpack to use in gui
    PySimpleSql comes with 'ss.small' (default) 'ss.large' and 'ss_text'
    :param name: name of iconpack to set as active
    :returns: None
    """
    global icon
    icon = SimpleNamespace(**_iconpack[name])


_default_ttk_theme = 'default'
def set_ttk_theme(name):
    """
    Advise users to set their ttk theme here, so we can use in quick_edit popup. Otherwise it changes all the buttons.
    Available: 'winnative' 'clam' 'alt' 'default' 'classic' 'vista' 'xpnative'
    :param name: name of ttk_theme.
    :returns: None
    """
    global _default_ttk_theme
    _default_ttk_theme = name


def get_ttk_theme():
    """
    Advise users to query this to fix window changing theme when you go to use quick_edit.
    :returns: _default_ttk_theme
    """
    return _default_ttk_theme


# ======================================================================================================================
# ABSTRACTION LAYERS
# ======================================================================================================================
# Database abstraction layers for a uniform API
# ----------------------------------------------------------------------------------------------------------------------

# This is a dummy class for documenting convenience functions
class Abstractions():
    """
    Supporting multiple databases in your application can quickly become very complicated and unmanagealbe.
    pysimplesql abstracts all of this complexity and presents a unified API via abstracting the main concepts of
    database programming. See the following documentation for a better understanding of how this is accomplished.
    `Column`, `ColumnInfo`, `ResultRow `, `ResultSet`, `SQLDriver`, `Sqlite`, `Mysql`, `Postgres`

    Note: This is a dummy class that exists purely to enhance documentation and has no use to the end user.
    """
    pass

# ======================================================================================================================
# COLUMN ABSTRACTION
# ======================================================================================================================
# The column abstraction hides the complexity of dealing with SQL columns, getting their names, default values, data
# types, primary key status and notnull status
# ----------------------------------------------------------------------------------------------------------------------
class Column:
    """
    The `Column` class is a generic column class.  It holds a dict containing the column name, type  whether the
    column is notnull, whether the column is a primary key and the default value, if any. `Column`s are typically
    stored in a `ColumnInfo` collection. There are multiple ways to get information from a `Column`, including subscript
    notation, and via properties. The available column info via these methods are name, sql_type, notnull, default and pk
    See example:
    .. literalinclude:: ../doc_examples/Column.1.py
        :language: python
        :caption: Example code
    """
    def __init__(self, name:str, sql_type:str, notnull:bool, default:None, pk:bool, virtual:bool = False):
        self._column={'name': name, 'sql_type': sql_type, 'notnull': notnull, 'default': default, 'pk': pk, 'virtual': virtual}

    def __str__(self):
        return f"Column: {self._column}"

    def __repr__(self):
        return f"Column: {self._column}"

    def __getitem__(self,item):
        return self._column[item]

    def __setitem__(self, key, value):
        self._column[key] = value

    def __lt__(self, other, key):
        return self._column[key] < other._column[key]

    def __contains__(self, item):
        return item in self._column

    # Make some properties for easy access
    @property
    def name(self):
        return self._column['name']
    @name.setter
    def name(self, value):
        self._column['name'] = value
    @property
    def sql_type(self):
        return self._column['sql_type']
    @sql_type.setter
    def sql_type(self, value):
        self._column['sql_type'] = value
    @property
    def notnull(self):
        return self._column['notnull']
    @notnull.setter
    def notnull(self, value:bool):
        self._column['notnull'] = value
    @property
    def default(self):
        return self._column['default']
    @default.setter
    def default(self, value):
        self._column['default'] = value
    @property
    def pk(self):
        return(self._column['pk'])
    @pk.setter
    def pk(self, value):
        self._column['pk'] = value
    @property
    def virtual(self):
        return self._column['virtual']
    @virtual.setter
    def virtual(self, value):
        self._column['virtual'] = value

class ColumnInfo(List):
    """
    Column Information Class

    The `ColumnInfo` class is a custom container that behaves like a List containing a collection of `Columns`. This
    class is responsible for maintaining information about all the columns (`Column`) in a table. While the
    individual `Column` elements of this collection contain information such as default values, primary key status,
    SQL data type, column name, and the notnull status - this class ties them all together into a collection and adds
    functionality to set default values for null columns and retrieve a dict representing a table row with all defaults
    already assigned. See example below:
    .. literalinclude:: ../doc_examples/ColumnInfo.1.py
        :language: python
        :caption: Example code
    """
    def __init__(self, driver:SQLDriver, table_name:str):
        self.driver = driver
        self.table_name = table_name

        # List of required SQL types to check against when user sets custom values
        self._sql_types = [
            'TEXT','VARCHAR', 'CHAR', 'INTEGER', 'REAL', 'DOUBLE', 'FLOAT', 'DECIMAL', 'BOOLEAN', 'TIME', 'DATE',
            'DATETIME', 'TIMESTAMP'
        ]

        # Defaults to use for Null values returned from the database. These can be overwritten by the user and support
        # function calls as well by using ColumnInfo.set_null_default() and ColumnInfo.set_null_defaults()
        self.null_defaults = {
            'TEXT': 'New Record',
            'VARCHAR': 'New Record',
            'CHAR' : 'New Record',
            'INT': 1,
            'INTEGER': 1,
            'REAL': 0.0,
            'DOUBLE': 0.0,
            'FLOAT': 0.0,
            'DECIMAL': 0.0,
            'BOOLEAN': 0,
            'TIME': lambda x: datetime.now().strftime("%H:%M:%S"),
            'DATE': lambda x: date.today().strftime("%Y-%m-%d"),
            'TIMESTAMP': lambda x: datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'DATETIME': lambda x: datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        super().__init__()

    def __contains__(self, item):
        if isinstance(item, str):
            return self._contains_key_value_pair('name', item)
        else:
            return super().__contains__(item)
    def __getitem__(self,item):
        if isinstance(item, str):
            return next((i for i in self if i.name == item), None)
        else:
            return super().__getitem__(item)
    def pk_column(self) -> str:
        """
        Get the pk_column for this colection of column_info

        :returns: A string containing the column name of the PK column, or None if one was not found
        """
        for c in self:
            if c.pk: return c.name
        return None

    def names(self) -> List:
        """
        Return a List of column names from the `Column`s in this collection

        :returns: List
        """
        return self._get_list('name')

    def col_name(self,idx:int) -> str:
        """
        Get the column name located at the specified index in this collection of `Column`s

        :param idx: The index of the column to get the name from
        :returns: The name of the column at the specified index
        """
        return self[idx].name

    def default_row_dict(self, q_obj:Query) -> dict:
        """
        Return a dictionary of a table row with all defaults assigned. This is useful for inserting new records to
        prefill the GUI elements

        :param q_obj: a pysimplesql Query object
        :returns: dict
        """
        d = {}
        for c in self:
            default = c.default
            sql_type = c.sql_type

            # First, check to see if the default might be a database function
            if self._looks_like_function(default):
                table_name = self.driver.quote_table(self.table_name)
                q = f'SELECT {default} FROM {table_name};' # TODO: may need AS column_name to support all databases?
                rows = self.driver.execute(q)
                if rows.exception is None:
                    default = rows.fetchone()[default]
                    logger.debug(f'Default fetched from database function. Default value is: {default}')
                    d[c.name] = default
                    continue

            # The stored default is a literal value, lets try to use it:
            if default is None:
                try:
                    null_default = self.null_defaults[sql_type]
                except KeyError:
                    # Perhaps our default dict does not yet support this datatype
                    null_default = None

                # If our default is callable, call it.  Otherwise, assign it
                # Make sure to skip primary keys, and onlu consider text that is in the description column
                if (sql_type not in ['TEXT','VARCHAR','CHAR'] and c.name != q_obj.description_column) and c.pk==False:
                    default = null_default() if callable(null_default) else null_default
            else:
                # Load the default from the database
                if sql_type in ['TEXT', 'VARCHAR', 'CHAR']:
                    # strip quotes from default strings as they seem to get passed with some database-stored defaults
                    default = c.default.strip('"\'')  # strip leading and trailing quotes

            d[c.name]= default
        if q_obj.transform is not None: q_obj.transform(d, TFORM_DECODE)
        return d

    def set_null_default(self, sql_type:str, value:object) -> None:
        """
        Set a Null default for a single SQL type

        :param sql_type: The SQL type to set the default for ('INTEGER', 'TEXT', 'BOOLEAN', etc.)
        :param value: The new value to set the SQL type to. This can be a literal or even a callable
        :returns: None
        """
        if sql_type not in self._sql_types:
            RuntimeError(f'Unsupported SQL Type: {sql_type}. Supported types are: {self._sql_types}')

        self.null_defaults[sql_type] = value

    def set_null_defaults(self, null_defaults:dict) -> None:
        """
        Set Null defaults for all SQL types

        supported types:  'TEXT','VARCHAR', 'CHAR', 'INTEGER', 'REAL', 'DOUBLE', 'FLOAT', 'DECIMAL', 'BOOLEAN', 'TIME',
        'DATE', 'DATETIME', 'TIMESTAMP'
        :param null_defaults: A dict of SQL types and default values. This can be a literal or even a callable
        :returns: None
        """
        # Check if the null_defaults dict has all of the required keys:
        if not all(key in null_defaults for key in self._sql_types):
            RuntimeError(f'The supplied null_defaults dictionary does not havle all required SQL types. Required: {self._sql_types}')

        self.null_defaults = null_defaults
    def get_virtual_names(self) -> List:
        """
        Get a list of virtual column names

        :returns: A List of column names that are virtual, or [] if none are present in this collections
        """
        return [c for c in self if not c.virtual]

    def _contains_key_value_pair(self, key, value): #used by __contains__
        for d in self:
            if key in d and d[key] == value:
                return True
        return False

    def _looks_like_function(self, s:str): # TODO: check if something looks like a statement for complex defaults?  Regex?
        # check if the string is empty
        if not s:
            return False

        # If the entire string is in all caps, it looks like a function (like in MySQL CURRENT_TIMESTAMP)
        if s.isupper(): return True

        # find the index of the first opening parenthesis
        open_paren_index = s.find("(")

        # if there is no opening parenthesis, the string is not a function
        if open_paren_index == -1:
            return False

        # check if there is a name before the opening parenthesis
        name = s[:open_paren_index].strip()
        if not name.isidentifier():
            return False

        # find the index of the last closing parenthesis
        last_char_index = len(s) - 1
        close_paren_index = s.rfind(")")

        # if there is no closing parenthesis, the string is not a function
        if close_paren_index == -1 or close_paren_index <= open_paren_index:
            return False

        # if all checks pass, the string looks like a function
        return True

    def _get_list(self, key: str) -> List:
        # returns a list of any key in the underlying Column instances. For example, column names, types, defaults, etc.
        return [d[key] for d in self]


# ======================================================================================================================
# DATABASE ABSTRACTION
# ======================================================================================================================
# The database abstraction hides the complexity of dealing with multiple databases.  The concept relies on individual
# "drivers" that derive from the SQLDriver class, and return a generic ResultSet instance, which contains a collection
# of generic ResultRow instances.
# ----------------------------------------------------------------------------------------------------------------------
class ResultRow():
    """
    The ResulRow class is a generic row class.  It holds a dict containing the column names and values of the row, along
    with a "virtual" flag.  A "virtual" row is one which exists in PySimpleSQL, but not in the underlying database.
    This is useful for inserting records or other temporary storage of records.  Note that when querying a database,
    the virtual flag will never be set for a row- it is only set by the end user by calling <ResultSet>.insert() to insert
    a new virtual row.

    ResultRows are not typcially used by the end user directly, they are typically used as a collection of ResultRows in
    a ResultSet.
    """

    def __init__(self, row:dict, original_index=None, virtual=False):
        self.row = row
        self.original_index = original_index
        self.virtual=virtual

    def __str__(self):
        return f"ResultRow: {self.row}"

    def __contains__(self, item):
        return item in self.row

    def __getitem__(self, item):
        return self.row[item]

    def __setitem__(self, key, value):
        self.row[key] = value

    def __lt__(self, other, key):
        return self.row[key] < other.row[key]
    def __iter__(self):
        return iter(self.row)
    def keys(self):
        return self.row.keys()
    def items(self):
        return self.row.items()
    def values(self):
        return self.row.values()

    def __next__(self):
        if self._iter_index == len(self.rows):
            raise StopIteration
        else:
            self._iter_index += 1
            return self.rows[self._iter_index - 1]


    def items(self):
        # forward calls to .items() to the underlying row dict
        return self.row.items()

    def copy(self):
        # return a copy of this row
        return ResultRow(self.row.copy(), virtual=self.virtual)

class ResultSet:
    """
    The ResultSet class is a generic result class so that working with the resultset of the different supported
    databases behave in a consistent manner. A ResultSet is a collection of ResultRows, along with the lastrowid
    and any exception returned by the underlying SQLDriver when an query is executed.

    Note: The lastrowid is set by the caller, but by pysimplesql convention, the lastrowid should only be set after
    and INSERT statement is executed.
    """
    # Store class-related constants
    SORT_NONE = 0
    SORT_ASC = 1
    SORT_DESC = 2

    def __init__(self, rows:list=[], lastrowid=None, exception=None, column_info=None):
        """
        Create a new ResultSet instance

        :returns: ResultSet
        """
        self.rows = [ResultRow(r,i) for r,i in zip(rows,range(len(rows)))]
        self.lastrowid = lastrowid
        self._iter_index = 0
        self.exception = exception
        self.column_info = column_info
        self.sort_column = None
        self.sort_reverse = False # ASC or DESC

    def __iter__(self):
        return (row for row in self.rows)

    def __next__(self):
        if self._iter_index == len(self.rows):
            raise StopIteration
        else:
            self._iter_index += 1
            return self.rows[self._iter_index - 1]

    def __str__(self):
        return str([row.row for row in self.rows])

    def __contains__(self, item):
        return item in self.rows

    def __getitem__(self,item):
        return self.rows[item]

    def __setitem__(self, idx:int, new_row:ResultRow):
        self.rows[idx]=new_row

    def __len__(self):
        return len(self.rows)

    def fetchone(self):
        return self.rows[0] if len(self.rows) else []

    def insert(self, row:dict, idx:int = None):
        # Insert a new row manually.  This will mark the row as virtual, as it did not come from the database.
        self.rows.insert(idx if idx else len(self.rows), ResultRow(row, virtual=True))

    def purge_virtual(self):
        # Purge virtual rows from the list
        self.rows = [row for row in self.rows if not row.virtual]

    def sort_by_column(self,column:str,reverse=False):
        try:
            self.rows = sorted(self.rows, key=lambda x: x[column], reverse=reverse)
        except KeyError:
            logger.debug(f'ResultSet could not sort by column {column}. KeyError.')

    def sort_by_index(self,index:int,reverse=False):
        try:
            column = list(self[0].keys())[index]
        except IndexError:
            logger.debug(f'ResultSet could not sort by column index {index}. IndexError.')
            return
        self.sort_by_column(column, reverse)


    def store_sort_settings(self) -> list:
        return [self.sort_column, self.sort_reverse]
    def load_sort_settings(self, sort_settings:list):
        self.sort_column = sort_settings[0]
        self.sort_reverse = sort_settings[1]


    def sort_reset(self) -> None:
        """
        Reset the sort order to the original when this ResultSet was created.  Each ResultRow has the original order
        stored
        :returns: None
        """
        self.rows = sorted(self.rows, key=lambda x: x.original_index)
    def sort(self) -> None:
        """
        Sort according to the internal sort_column and sort_reverse variables
        This is a good way to re-sort without changing the sort_cycle

        :returns: None
        """
        if self.sort_column is None:
            self.sort_reset()
        else:
            self.sort_by_column(self.sort_column, self.sort_reverse)

    def sort_cycle(self, column:str, advance_cycle=True) -> int:
        """
        Cycle between original sort order of the ResultSet, ASC by column, and DESC by column with each call
        :param column: The column name to cycle the sort on
        :param cb: A callable function callback to run after this sort runs.
        :returns: A ResultSet sort constant; ResultSet.SORT_NONE, ResultSet.SORT_ASC, or ResultSet.SORT_DESC
        """
        if column != self.sort_column:
            # We are going to sort by a new column.  Default to ASC
            self.sort_column = column
            self.sort_reverse = False
            self.sort()
            ret =  ResultSet.SORT_ASC
        else:
            if self.sort_reverse == False:
                self.sort_reverse = True
                self.sort()
                ret = ResultSet.SORT_DESC
            else:
                self.sort_reverse=False
                self.sort_column = None
                self.sort()
                ret = ResultSet.SORT_NONE
        return ret
# TODO min_pk, max_pk
class SQLDriver:
    """"
    Abstract SQLDriver class.  Derive from this class to create drivers that conform to PySimpleSQL.  This ensures
    that the same code will work the same way regardless of which database is used.  There are a few important things
    to note:
    The commented code below is broken into methods that MUST be implemented in the derived class, methods that SHOULD
    be implemented in the derived class, and methods that MAY need to be implemented in the derived class for it to
    work as expected.  Most derived drivers will at least partially work by implementing the MUST have methods.

    NOTE: SQLDriver.execute should return a ResultSet instance.  Additionally, py pysimplesql convention, the
    ResultSet.lastrowid should always be None unless and INSERT query is executed with SQLDriver.execute() or a record
    is inserted with SQLDriver.insert_record()
    """
    # ---------------------------------------------------------------------
    # MUST implement
    # in order to function
    # ---------------------------------------------------------------------
    def __init__(self, name:str, placeholder='%s', table_quote='', column_quote='', value_quote="'"):
        # Be sure to call super().__init__() in derived class!
        self.con = None
        self.name = name

        # Each database type expects their SQL prepared in a certain way.  Below are defaults for how various elements
        # in the SQL string should be quoted and represented as placeholders. Override these in the derived class as
        # needed to satisfy SQL requirements
        self.placeholder = placeholder                     # override this in derived __init__()
        self.quote_table_char = table_quote                # override this in derived __init__() (defaults to no quotes)
        self.quote_column_char = column_quote              # override this in derived __init__() (defaults to no quotes)
        self.quote_value_char = value_quote                # override this in derived __init__() (defaults to single quotes)

    def connect(self, database):
        raise NotImplementedError

    def execute(self, query, values=None, column_info:ColumnInfo=None):
        raise NotImplementedError

    def execute_script(self, script:str, silent:bool=False):
        raise NotImplementedError

    def table_names(self):
        raise NotImplementedError

    def column_info(self, table):
        raise NotImplementedError

    def pk_column(self,table):
        raise NotImplementedError

    def relationships(self):
        raise NotImplementedError

    def save_record(self, q_obj:Query, row:dict):
        raise NotImplementedError

    def insert_record(self, table:str, pk:int, pk_column:str, row:dict):
        raise NotImplementedError

    # ---------------------------------------------------------------------
    # SHOULD implement
    # based on specifics of the database
    # ---------------------------------------------------------------------
    # This is a generic way to estimate the next primary key to be generated.
    # Note that this is not always a reliable way, as manual inserts which assign a primary key value don't always
    # update the sequencer for the given database.  This is just a default way to "get things working", but the best
    # bet is to override this in the derived class and get the value right from the sequencer.
    def next_pk(self, table_name: str, pk_column_name: str) -> int:
        max_pk = self.max_pk(table_name, pk_column_name)
        if max_pk is not None:
            return max_pk + 1
        else: return 1
        

    # ---------------------------------------------------------------------
    # MAY need to be implemented
    # These default implementations will likely work for most SQL databases.
    # Override any of the following methods as needed.
    # ---------------------------------------------------------------------
    def quote_table(self, table: str):
        return f'{self.quote_table_char}{table}{self.quote_table_char}'

    def quote_column(self, column: str):
        return f'{self.quote_column_char}{column}{self.quote_column_char}'

    def quote_value(self, value: str):
        return f'{self.quote_value_char}{value}{self.quote_value_char}'

    def commit(self):
        self.con.commit()

    def rollback(self):
        self.con.rollback()

    def close(self):
        self.con.close()

    def default_query(self, table):
        table=self.quote_table(table)
        return f'SELECT {table}.* FROM {table}'

    def default_order(self, description_column):
        description_column = self.quote_column(description_column)
        return f' ORDER BY {description_column} ASC'

    def relationship_to_join_clause(self, r_obj:Relationship):
        parent = self.quote_table(r_obj.parent_table)
        child = self.quote_table(r_obj.child_table)
        fk = self.quote_column(r_obj.fk_column)
        pk = self.quote_column(r_obj.pk_column)

        return f'{r_obj.join} {parent} ON {child}.{fk}={parent}.{pk}'

    def min_pk(self, table_name: str, pk_column_name: str) -> int:
        rows = self.execute(f"SELECT MIN({pk_column_name}) FROM {table_name}")
        return rows.fetchone()[f'MAX({pk_column_name})']

    def max_pk(self, table_name: str, pk_column_name: str) -> int:
        rows = self.execute(f"SELECT MAX({pk_column_name}) FROM {table_name}")
        return rows.fetchone()[f'MAX({pk_column_name})']

    def generate_join_clause(self, q_obj:Query) -> str:
        """
        Automatically generates a join clause from the Relationships that have been set

        This typically isn't used by end users

        :returns: A join string to be used in a sqlite3 query
        :rtype: str
        """
        join = ''
        for r in q_obj.frm.relationships:
            if q_obj.table == r.child_table:
                join += f' {self.relationship_to_join_clause(r)}'
        return join if q_obj.join == '' else q_obj.join


    def generate_where_clause(self, q_obj:Query) -> str:
        """
        Generates a where clause from the Relationships that have been set, as well as the Query's where clause

        This is not typically used by end users

        :returns: A where clause string to be used in a sqlite3 query
        :rtype: str
        """
        where = ''
        for r in q_obj.frm.relationships:
            if q_obj.table == r.child_table:
                if r.update_cascade:
                    table = q_obj.table
                    parent_pk = q_obj.frm[r.parent_table].get_current(r.pk_column)
                    if parent_pk == '': parent_pk = 'NULL' # passed so that children without a cascade-filtering parent arn't displayed
                    clause=f' WHERE {table}.{r.fk_column}={str(parent_pk)}'
                    if where!='': clause=clause.replace('WHERE','AND')
                    where += clause

        if where == '':
            # There was no where clause from Relationships..
            where = q_obj.where
        else:
            # There was an auto-generated portion of the where clause.  We will add the table's where clause to it
            where = where + ' ' + q_obj.where.replace('WHERE', 'AND')

        return where

    def generate_query(self, q_obj:Query, join:bool=True, where:bool=True, order:bool=True) -> str:
        """
        Generate a query string using the relationships that have been set

        :param join: True if you want the join clause auto-generated, False if not
        :type join: bool
        :param where: True if you want the where clause auto-generated, False if not
        :type where: bool
        :param order: True if you want the order by clause auto-generated, False if not
        :type order: bool
        :returns: a query string for use with sqlite3
        :rtype: str
        """
        q = q_obj.query
        q += f' {q_obj.join if join else ""}'
        q += f' {q_obj.where if where else ""}'
        q += f' {q_obj.order if order else ""}'
        return q

    def delete_record(self, q_obj:Query, cascade=True): # TODO: get ON DELETE CASCADE from db
        # Delete child records first!
        if cascade:
            for qry in q_obj.frm.queries:
                for r in q_obj.frm.relationships:
                    if r.parent_table == q_obj.table:
                        child = self.quote_table(r.child_table)
                        fk_column = self.quote_column(r.fk_column)
                        q = f'DELETE FROM {child} WHERE {fk_column}={q_obj.get_current(q_obj.pk_column)}'
                        self.execute(q)
                        logger.debug(f'Delete query executed: {q}')
                        q_obj.frm[r.child_table].requery(False)

        table = self.quote_table(q_obj.table)
        pk_column = self.quote_column(q_obj.pk_column)
        q = f'DELETE FROM {table} WHERE {pk_column}={q_obj.get_current(q_obj.pk_column)};'
        self.execute(q)

    def duplicate_record(self, q_obj:Query, cascade:bool) -> ResultSet:
        ## https://stackoverflow.com/questions/1716320/how-to-insert-duplicate-rows-in-sqlite-with-a-unique-id
        ## This can be done using * syntax without having to know the schema of the table
        ## (other than the name of the primary key). The trick is to create a temporary table
        ## using the "CREATE TABLE AS" syntax.
        description = self.quote_value(f"Copy of {q_obj.get_description_for_pk(q_obj.get_current_pk())}")
        table = self.quote_table(q_obj.table)
        pk_column = self.quote_column(q_obj.pk_column)
        description_column = self.quote_column(q_obj.description_column)

        query= []
        query.append('DROP TABLE IF EXISTS tmp;')
        query.append(f'CREATE TEMPORARY TABLE tmp AS SELECT * FROM {table} WHERE {pk_column}={q_obj.get_current(q_obj.pk_column)}')
        query.append(f'UPDATE tmp SET {pk_column} = {self.next_pk(q_obj.table, q_obj.pk_column)}')
        query.append(f'UPDATE tmp SET {description_column} = {description}')
        query.append(f'INSERT INTO {table} SELECT * FROM tmp')
        for q in query:
            res = self.execute(q)
            if res.exception: return res
            
        # Now we save the new pk
        pk = res.lastrowid

        # create list of which children we have duplicated
        child_duplicated = []
        # Next, duplicate the child records!
        if cascade:
            for qry in q_obj.frm.queries:
                for r in q_obj.frm.relationships:
                    if r.parent_table == q_obj.table and r.update_cascade and (r.child_table not in child_duplicated):
                        child = self.quote_table(r.child_table)
                        fk = self.quote_column(r.fk_column)
                        pk_column = self.quote_column(q_obj.frm[r.child_table].pk_column)
                        fk_column = self.quote_column(r.fk_column)

                        query = []
                        query.append('DROP TABLE IF EXISTS tmp;')
                        query.append(f'CREATE TEMPORARY TABLE tmp AS SELECT * FROM {child} WHERE {fk}={q_obj.get_current(q_obj.pk_column)}')
                        query.append(f'UPDATE tmp SET {pk_column} = {self.next_pk(r.child_table, r.pk_column)}')
                        query.append(f'UPDATE tmp SET {fk_column} = {pk}')
                        query.append(f'INSERT INTO {child} SELECT * FROM tmp')
                        query.append('DROP TABLE IF EXISTS tmp;')
                        for q in query:
                            res = self.execute(q)
                            if res.exception: return res
                            
                        child_duplicated.append(r.child_table)
        # If we made it here, we can return the pk.  Since the pk was stored earlier, we will just send and empty ResultSet
        return ResultSet(lastrowid=pk)

    def save_record(self, q_obj:Query, changed_row:dict) -> ResultSet:
        pk = q_obj.get_current_pk()
        pk_column = q_obj.pk_column

        # Remove the pk column and any virtual columns
        changed_row = {k: v for k,v in changed_row.items() if k!= pk_column and k not in q_obj.column_info.get_virtual_names()}

        # quote appropriately
        table = self.quote_table(q_obj.table)
        pk_column = self.quote_column(pk_column)

        # Create the WHERE clause
        where = f"WHERE {pk_column} = {pk}"

        # Generate an UPDATE query
        query = f"UPDATE {table} SET {', '.join(f'{k}={self.placeholder}' for k in changed_row.keys())} {where};"
        values = [v for v in changed_row.values()]

        result = self.execute(query, tuple(values))
        result.lastrowid = None # manually clear th rowid since it is not needed for updated records (we already know the key)
        return result


    def insert_record(self, table:str, pk:int, pk_column:str, row:dict):
        # Remove the pk column
        row = {k: v for k, v in row.items() if k != pk_column}

        # quote appropriately
        table = self.quote_table(table)
        pk_column = self.quote_column(pk_column)

        # Remove the primary key column to ensure autoincrement is used!
        query = f"INSERT INTO {table} ({', '.join(key for key in row.keys())}) VALUES ({','.join(self.placeholder for _ in range(len(row)))}); "
        values = [value for key, value in row.items()]
        return self.execute(query, tuple(values))

# ----------------------------------------------------------------------------------------------------------------------
# SQLITE3 DRIVER
# ----------------------------------------------------------------------------------------------------------------------
class Sqlite(SQLDriver):
    def __init__(self, db_path=None, sql_script=None, sqlite3_database=None, sql_commands=None):
        super().__init__(name='SQLite3', placeholder='?')

        new_database = False
        if db_path is not None:
            logger.info(f'Opening database: {db_path}')
            new_database = not os.path.isfile(db_path)
            self.connect(db_path)  # Open our database

        self.imported_database = False
        if sqlite3_database is not None:
            self.con = sqlite3_database
            new_database = False
            self.imported_database = True

        self.con.row_factory = sqlite3.Row
        if sql_commands is not None and new_database:
            # run SQL script if the database does not yet exist
            logger.info(f'Executing sql commands passed in')
            logger.debug(sql_commands)
            self.con.executescript(sql_commands)
            self.con.commit()
        if sql_script is not None and new_database:
            # run SQL script from the file if the database does not yet exist
            logger.info('Executing sql script from file passed in')
            self.execute_script(sql_script)

        self.db_path = db_path


    def connect(self, database):
        self.con = sqlite3.connect(database)

    def execute(self, query, values=None, silent=False, column_info = None):
        if not silent:logger.info(f'Executing query: {query} {values}')

        cursor = self.con.cursor()
        exception = None
        try:
            cur = cursor.execute(query, values) if values else cursor.execute(query)
        except sqlite3.Error as e:
            exception = e

        try:
            rows = cur.fetchall()
        except:
            rows = []


        lastrowid = cursor.lastrowid if cursor.lastrowid is not None else None
        return ResultSet([dict(row) for row in rows], lastrowid, exception, column_info)


    def close(self):
        # Only do cleanup if this is not an imported database
        if not self.imported_database:
            # optimize the database for long-term benefits
            if self.db_path != ':memory:':
                q = 'PRAGMA optimize;'
                self.con.execute(q)
            # Close the connection
            self.con.close()

    def table_names(self):
        q = 'SELECT name FROM sqlite_master WHERE type="table" AND name NOT like "sqlite%";'
        cur = self.execute(q, silent=True)
        return [row['name'] for row in cur]

    def column_info(self, table):
        # Return a list of column names
        q = f'PRAGMA table_info({table})'
        rows = self.execute(q, silent=True)
        names=[]
        col_info = ColumnInfo(self, table)

        for row in rows:
            name = row['name']
            names.append(name)
            sql_type = row['type']
            notnull = row['notnull']
            default = row['dflt_value']
            pk = row['pk']
            col_info.append(Column(name = name, sql_type = sql_type, notnull=notnull, default=default, pk=pk))

        return col_info

    def pk_column(self,table):
        q = f'PRAGMA table_info({table})'
        row = self.execute(q, silent=True).fetchone()

        return row['name'] if 'name' in row else None


    def relationships(self):
        # Return a list of dicts {from_table,to_table,from_column,to_column,requery}
        relationships = []
        tables = self.table_names()
        for from_table in tables:
            rows = self.execute(f"PRAGMA foreign_key_list({from_table})", silent=True)

            for row in rows:
                dic={}
                # Add the relationship if it's in the requery list
                if row['on_update'] == 'CASCADE':
                    dic['update_cascade'] = True
                else:
                    dic['update_cascade'] = False
                dic['from_table'] = from_table
                dic['to_table'] = row['table']
                dic['from_column'] = row['from']
                dic['to_column'] = row ['to']
                relationships.append(dic)
        return relationships

    def execute_script(self,script):
        with open(script, 'r') as file:
            logger.info(f'Loading script {script} into database.')
            self.con.executescript(file.read())

# ----------------------------------------------------------------------------------------------------------------------
# MYSQL DRIVER
# ----------------------------------------------------------------------------------------------------------------------
class Mysql(SQLDriver):
    def __init__(self, host, user, password, database, sql_script=None, sql_commands=None):
        super().__init__(name='MySQL')

        self.name = "MySQL"
        self.host = host
        self.user = user
        self.password = password
        self.database = database
        self.con = self.connect()

        if sql_commands is not None:
            # run SQL script if the database does not yet exist
            logger.info(f'Executing sql commands passed in')
            logger.debug(sql_commands)
            self.con.executescript(sql_commands)
            self.con.commit()
        if sql_script is not None:
            # run SQL script from the file if the database does not yet exist
            logger.info('Executing sql script from file passed in')
            self.execute_script(sql_script)


    def connect(self):
        con = mysql.connector.connect(
            host = self.host,
            user = self.user,
            password = self.password,
            database = self.database
        )
        return con

    def execute(self, query, values=None, silent=False, column_info=None):
        if not silent: logger.info(f'Executing query: {query} {values}')
        cursor = self.con.cursor(dictionary=True)
        exception = None
        try:
            cursor.execute(query, values) if values else cursor.execute(query)
        except mysql.connector.Error as e:
            exception = e.msg

        try:
            rows = cursor.fetchall()
        except:
            rows = []

        lastrowid=cursor.lastrowid if cursor.lastrowid else None

        return ResultSet([dict(row) for row in rows], lastrowid, exception, column_info)


    def table_names(self):
        query = "SELECT table_name FROM information_schema.tables WHERE table_schema = %s"
        rows = self.execute(query, [self.database], silent=True)
        return [row['table_name'] for row in rows]


    def column_info(self, table):
        # Return a list of column names
        query = "DESCRIBE {}".format(table)
        rows = self.execute(query, silent=True)
        col_info = ColumnInfo(self, table)

        for row in rows:
            name = row['Field']
            # Capitolize and get rid of the extra information of the row type I.e. varchar(255) becomes VARCHAR
            sql_type = row['Type'].split('(')[0].upper()
            notnull = True if row['Null'] == 'NO' else False
            default = row['Default']
            pk = True if row['Key'] == 'PRI' else False
            col_info.append(Column(name=name, sql_type=sql_type, notnull=notnull, default=default, pk=pk))

        return col_info


    def pk_column(self,table):
        query = "SHOW KEYS FROM {} WHERE Key_name = 'PRIMARY'".format(table)
        cur = self.execute(query, silent=True)
        row = cur.fetchone()
        return row['Column_name'] if row else None

    def relationships(self):
        # Return a list of dicts {from_table,to_table,from_column,to_column,requery}
        tables=self.table_names()
        relationships = []
        for from_table in tables:
            query = "SELECT * FROM information_schema.key_column_usage WHERE referenced_table_name IS NOT NULL AND table_name = %s"
            rows=self.execute(query, (from_table,), silent=True)

            for row in rows:
                dic = {}
                # Get the constraint information
                constraint = self.constraint(row['CONSTRAINT_NAME'])
                if constraint == 'CASCADE':
                    dic['update_cascade'] = True
                else:
                    dic['update_cascade'] = False
                dic['from_table'] = row['TABLE_NAME']
                dic['to_table'] = row['REFERENCED_TABLE_NAME']
                dic['from_column'] = row['COLUMN_NAME']
                dic['to_column'] = row['REFERENCED_COLUMN_NAME']
                relationships.append(dic)
        return relationships

    def execute_script(self,script):
        with open(script, 'r') as file:
            logger.info(f'Loading script {script} into database.')
            # TODO

    # Not required for SQLDriver
    def constraint(self,constraint_name):
        query = f"SELECT UPDATE_RULE FROM INFORMATION_SCHEMA.REFERENTIAL_CONSTRAINTS WHERE CONSTRAINT_NAME = '{constraint_name}'"
        rows = self.execute(query, silent=True)
        return rows[0]['UPDATE_RULE']

# ----------------------------------------------------------------------------------------------------------------------
# POSTGRES DRIVER
# ----------------------------------------------------------------------------------------------------------------------
class Postgres(SQLDriver):
    def __init__(self,host,user,password,database,sql_script=None, sql_commands=None, sync_sequences=True):
        super().__init__(name='PostgreSQL', table_quote='"')

        self.host = host
        self.user = user
        self.password = password
        self.database = database
        self.con = self.connect()

        # experiment to see if I can make a nocase collation
        query = "CREATE COLLATION NOCASE (provider = icu, locale = 'und-u-ks-level2');"
        #self.execute(query)

        if sync_sequences:
            # synchronize the sequences with the max pk for each table. This is useful if manual records were inserted
            # without calling nextval() to update the sequencer
            q = "SELECT sequence_name FROM information_schema.sequences;"
            sequences = self.execute(q, silent=True)
            for s in sequences:
                seq = s['sequence_name']

                # get the max pk for this table
                q = f"SELECT column_name, table_name FROM information_schema.columns WHERE column_default LIKE 'nextval(%{seq}%)'"
                rows = self.execute(q, silent=True)
                row=rows.fetchone()
                table_name = row['table_name']
                pk_column_name = row['column_name']
                max_pk = self.max_pk(table_name, pk_column_name)

                # update the sequence
                seq = self.quote_table(seq)
                if max_pk > 0:
                    q = f"SELECT setval('{seq}', {max_pk});"
                else:
                    q = f"SELECT setval('{seq}', 1, false);"
                self.execute(q, silent=True)


        if sql_commands is not None:
            # run SQL script if the database does not yet exist
            logger.info(f'Executing sql commands passed in')
            logger.debug(sql_commands)
            self.con.executescript(sql_commands)
            self.con.commit()
        if sql_script is not None:
            # run SQL script from the file if the database does not yet exist
            logger.info('Executing sql script from file passed in')
            self.execute_script(sql_script)

    def connect(self):
        con = psycopg2.connect(
            host = self.host,
            user = self.user,
            password = self.password,
            database = self.database
        )
        return con

    def execute(self, query:str, values=None, silent=False, column_info=None):
        if not silent: logger.info(f'Executing query: {query} {values}')
        cursor = self.con.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        exception = None
        try:
            cursor.execute(query, values) if values else cursor.execute(query)
        except psycopg2.Error as e:
            exception = e

        try:
            rows = cursor.fetchall()
        except:
            rows = []

        # In Postgres, the cursor does not return a lastrowid.  We will not set it here, we will instead set it in
        # save_records() due to the RETURNING stement of the query
        return ResultSet([dict(row) for row in rows], exception=exception, column_info=column_info)

    def table_names(self):
        query = "SELECT table_name FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE';"
        #query = "SELECT tablename FROM pg_tables WHERE table_schema='public'"
        rows = self.execute(query, silent=True)
        return [row['table_name'] for row in rows]

    def column_info(self, table):
        # Return a list of column names
        query = f"SELECT column_name FROM information_schema.columns WHERE table_name = '{table}'"
        rows = self.execute(query, silent=True)
        return [row['column_name'] for row in rows]

    def pk_column(self,table):
        query = f"SELECT column_name FROM information_schema.table_constraints tc JOIN information_schema.key_column_usage kcu ON tc.constraint_name = kcu.constraint_name WHERE tc.constraint_type = 'PRIMARY KEY' AND tc.table_name = '{table}' "
        cur = self.execute(query, silent=True)
        row = cur.fetchone()
        return row['column_name'] if row else None

    def relationships(self):
        # Return a list of dicts {from_table,to_table,from_column,to_column,requery}
        tables=self.table_names()
        relationships = []
        for from_table in tables:
            query = f"SELECT conname, conrelid::regclass, confrelid::regclass, confupdtype, "
            query += f"a1.attname AS column_name, a2.attname AS referenced_column_name "
            query += f"FROM pg_constraint "
            query += f"JOIN pg_attribute AS a1 ON conrelid = a1.attrelid AND a1.attnum = ANY(conkey) "
            query += f"JOIN pg_attribute AS a2 ON confrelid = a2.attrelid AND a2.attnum = ANY(confkey) "
            query += f"WHERE confrelid = '\"{from_table}\"'::regclass AND contype = 'f'"


            rows=self.execute(query, (from_table,), silent=True)

            for row in rows:
                dic = {}
                # Get the constraint information
                #constraint = self.constraint(row['conname'])
                if row['conname'] == 'c':
                    dic['update_cascade'] = True
                else:
                    dic['update_cascade'] = False
                dic['from_table'] = row['conrelid'].strip('"')
                dic['to_table'] = row['confrelid'].strip('"')
                dic['from_column'] = row['column_name']
                dic['to_column'] = row['referenced_column_name']
                relationships.append(dic)
        return relationships

    def min_pk(self, table_name: str, pk_column_name: str) -> int:
        table_name = self.quote_table(table_name)
        pk_column_name = self.quote_column(pk_column_name)
        rows = self.execute(f'SELECT COALESCE(MIN({pk_column_name}), 0) AS min_pk FROM {table_name};', silent=True)
        return rows.fetchone()[f'min_pk']

    def max_pk(self, table_name: str, pk_column_name: str) -> int:
        table_name = self.quote_table(table_name)
        pk_column_name = self.quote_column(pk_column_name)
        rows = self.execute(f'SELECT COALESCE(MAX({pk_column_name}), 0) AS max_pk FROM {table_name};', silent=True)
        return rows.fetchone()[f'max_pk']

    def next_pk(self, table_name: str, pk_column_name: str) -> int:
        # Working with case-sensitive tables is painful in Postgres.  First, the sequence must be quoted in a manner
        # similar to tables, then the quoted sequence name has to be also surrounded in single quotes to be treated
        # literally and prevent folding of the casing.
        seq = f'{table_name}_{pk_column_name}_seq' # build the default sequence name
        seq = self.quote_table(seq) # quote it like a table

        q=f"SELECT nextval('{seq}');" # wrap the quoted string in singe quotes.  Phew!
        rows = self.execute(q, silent=True)
        return rows.fetchone()['nextval']

    def insert_record(self, table:str, pk:int, pk_column:str, row:dict):
        # insert_record() for Postgres is a little different than the rest. Instead of relying on an autoincrement, we
        # first already "reserved" a primary key earlier, so we will use it directly
        # quote appropriately
        table = self.quote_table(table)
        pk_column = self.quote_column(pk_column)

        # Remove the primary key column to ensure autoincrement is used!
        query = f"INSERT INTO {table} ({', '.join(key for key in row.keys())}) VALUES ({','.join('%s' for _ in range(len(row)))}); "
        values = [value for key, value in row.items()]
        result = self.execute(query, tuple(values))

        result.lastid = pk
        return result

    def execute_script(self, script):
        pass


# ======================================================================================================================
# ALIASES
# ======================================================================================================================
Database=Form
Table=Query
