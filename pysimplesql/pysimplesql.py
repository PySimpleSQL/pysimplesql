"""
# **pysimplesql** User's Manual

## DISCLAIMER:
While **pysimplesql** works with and was inspired by the excellent PySimpleGUI™ project, it has no affiliation.

## Rapidly build and deploy database applications in Python
**pysimplesql** binds PySimpleGUI to various databases for rapid, effortless database application development. Makes a
great replacement for MS Access or LibreOffice Base! Have the full power and language features of Python while having
the power and control of managing your own codebase. **pysimplesql** not only allows for super simple automatic control
(not one single line of SQL needs written to use **pysimplesql**), but also allows for very low level control for
situations that warrant it.

------------------------------------------------------------------------------------------------------------------------
NAMING CONVENTIONS USED THROUGHOUT THE SOURCE CODE
------------------------------------------------------------------------------------------------------------------------
There is a lot of ambiguity with database terminology, as many terms are used interchangeably in some circumstances, but
not in others.  The Internet has post after post debating this topic.  See one example here:
https://dba.stackexchange.com/questions/65609/column-vs-field-have-i-been-using-these-terms-incorrectly
To avoid confusion in the source code, specific naming conventions will be used whenever possible

Naming conventions can fall under 4 categories:
- referencing the actual database (variables, functions, etc. that relate to the database)
- referencing the `DataSet` (variables, functions, etc. that relate to the `DataSet`)
- referencing pysimplesql
- referencing PySimpleGUI

- Database related:
    driver - a `SQLDriver` derived class
    t, table, tables - the database table name(s)
    r, row, rows - A group of related data in a table
    c, col, cols, column, columns -  A set of values of a particular type
    q, query - An SQL query string
    domain - the data type of the data (INTEGER, TEXT, etc.)

 - `DataSet` related:
    r, row, rows, resultset - A row, or collection of rows from  querying the database
    c, col, cols, column, columns -  A set of values of a particular type
    Record - A collection of fields that make up a row
    field - the value found where a row intersects a column

- pysimplesql related
    frm - a `Form` object
    dataset, datasets - a `DataSet` object, or collection of `DataSet` objects
    data_key - the key (name) of a dataset object

- PySimpleGUI related
    win, window - A PySimpleGUI Window object
    element - a Window element
    element_key -  a window element key
------------------------------------------------------------------------------------------------------------------------
"""

# The first two imports are for docstrings
from __future__ import annotations
from typing import List, Union, Optional, Tuple, Callable, Dict, Type, TypedDict
from datetime import date, datetime
import PySimpleGUI as sg
import functools
import os.path
import logging

# For threaded info popup
from time import sleep
import threading

# Wrap optional imports so that pysimplesql can be imported as a single file if desired:
try:
    from .language_pack import *
except (ModuleNotFoundError, ImportError): # ImportError for 'attempted relative import with no known parent package'
    pass

try:
    from .theme_pack import *
except (ModuleNotFoundError, ImportError): # ImportError for 'attempted relative import with no known parent package'
    pass

try:
    from .reserved_sql_keywords import ADAPTERS as RESERVED
except (ModuleNotFoundError, ImportError):
    # Use common as minium default
    RESERVED = {'common': ["SELECT", "INSERT", "DELETE", "UPDATE", "DROP", "CREATE", "ALTER",
                               "WHERE", "FROM", "INNER", "JOIN", "AND", "OR", "LIKE", "ON", "IN",
                               "SET", "BY", "GROUP", "ORDER", "LEFT", "OUTER", "IF", "END", "THEN",
                               "LOOP", "AS", "ELSE", "FOR", "CASE", "WHEN", "MIN", "MAX", "DISTINCT",]}

# Load database backends if present
supported_databases = ['SQLite3', 'MySQL', 'PostgreSQL', 'Flatfile']
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
try:
    import csv
except ModuleNotFoundError:
    failed_modules += 1

if failed_modules == len(supported_databases):
    RuntimeError(f"You muse have at least one of the following databases installed to use PySimpleSQL:"
                 f"\n{', '.join(supported_databases)} ")


logger = logging.getLogger(__name__)

# ---------------------------
# Types for automatic mapping
# ---------------------------
TYPE_RECORD: int = 1
TYPE_SELECTOR: int = 2
TYPE_EVENT: int = 3

# -----------------
# Transform actions
# -----------------
TFORM_ENCODE: int = 1
TFORM_DECODE: int = 0

# -----------
# Event types
# -----------
# Custom events (requires 'function' dictionary key)
EVENT_FUNCTION: int = 0
# DataSet-level events (requires 'table' dictionary key)
EVENT_FIRST: int = 1
EVENT_PREVIOUS: int = 2
EVENT_NEXT: int = 3
EVENT_LAST: int = 4
EVENT_SEARCH: int = 5
EVENT_INSERT: int = 6
EVENT_DELETE: int = 7
EVENT_DUPLICATE: int = 13
EVENT_SAVE: int = 8
EVENT_QUICK_EDIT: int = 9
# Form-level events
EVENT_SEARCH_DB: int = 10
EVENT_SAVE_DB: int = 11
EVENT_EDIT_PROTECT_DB: int = 12

# ----------------
# GENERIC BITMASKS
# ----------------
# Can be used with other bitmask values
SHOW_MESSAGE: int = 4096

# ---------------------------
# PROMPT_SAVE RETURN BITMASKS
# ---------------------------
PROMPT_SAVE_DISCARDED: int = 1
PROMPT_SAVE_PROCEED: int = 2
PROMPT_SAVE_NONE: int = 4

# ---------------------------
# RECORD SAVE RETURN BITMASKS
# ---------------------------
SAVE_FAIL: int = 1     # Save failed due to callback
SAVE_SUCCESS: int = 2  # Save was successful
SAVE_NONE: int = 4     # There was nothing to save

# ----------------------
# SEARCH RETURN BITMASKS
# ----------------------
SEARCH_FAILED: int = 1    # No result was found
SEARCH_RETURNED: int = 2  # A result was found
SEARCH_ABORTED: int = 4   # The search was aborted, likely during a callback
SEARCH_ENDED: int = 8     # We have reached the end of the search

# ----------------------------
# DELETE RETURNS BITMASKS
# ----------------------------
DELETE_FAILED: int = 1    # No result was found
DELETE_RETURNED: int = 2  # A result was found
DELETE_ABORTED: int = 4   # The search was aborted, likely during a callback
DELETE_RECURSION_LIMIT_ERROR: int = 8     # We hit max nested levels
DELETE_CASCADE_RECURSION_LIMIT = 15 # Mysql sets this as 15 when using foreign key CASCADE DELETE

# -------
# CLASSES
# -------
# TODO: Combine TableRow and ElementRow into one class for simplicity
class TableRow(list):
    """
    This is a convenience class used by Tables to associate a primary key with a row of information
    Note: This is typically not used by the end user.
    """
    def __init__(self, pk: int, *args, **kwargs):
        self.pk = pk
        super().__init__(*args, **kwargs)

    def __str__(self):
        return str(self[:])

    def __int__(self):
        return self.pk

    def __repr__(self):
        # Add some extra information that could be useful for debugging
        return f'TableRow(pk={self.pk}): {super().__repr__()}'


class ElementRow:
    """
    This is a convenience class used by listboxes and comboboxes to associate a primary key with a row of information
    Note: This is typically not used by the end user.
    """
    def __init__(self, pk: int, val: Union[str, int]) -> None:
        self.pk = pk
        self.val = val

    def __repr__(self):
        return str(self.val)

    def __str__(self):
        return str(self.val)

    def __int__(self):
        return self.pk

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
    # TODO: Relationships are table-based only.  Audit code to ensure that we aren't dealing with data_keys
    # store our own instances
    instances = []

    @classmethod
    def get_relationships_for_table(cls, table: str) -> List[Relationship]:
        """
        Return the relationships for the passed-in table.

        :param table: The table to get relationships for
        :returns: A list of @Relationship objects
        """
        rel = [r for r in cls.instances if r.child_table == table]
        return rel

    @classmethod
    def get_update_cascade_relationships(cls, table: str) -> List[str]:
        """
        Return a unique list of the relationships for this table that should requery with this table.

        :param table: The table to get cascaded children for
        :returns: A unique list of table names
        """
        rel = [r.child_table for r in cls.instances
               if r.parent_table == table and r._update_cascade]
        # make unique
        rel = list(set(rel))
        return rel
    
    @classmethod
    def get_delete_cascade_relationships(cls, table: str) -> List[str]:
        """
        Return a unique list of the relationships for this table that should be deleted with this table.

        :param table: The table to get cascaded children for
        :returns: A unique list of table names
        """
        rel = [r.child_table for r in cls.instances
               if r.parent_table == table and r._delete_cascade]
        # make unique
        rel = list(set(rel))
        return rel

    @classmethod
    def get_parent(cls, table: str) -> Union[str, None]:
        """
        Return the parent table for the passed-in table
        :param table: The table (str) to get relationships for
        :returns: The name of the Parent table, or None if there is none
        """
        for r in cls.instances:
            if r.child_table == table and r._update_cascade:
                return r.parent_table
        return None

    @classmethod
    def get_update_cascade_fk_column(cls, table: str) -> Union[str, None]:
        """
        Return the cascade fk that filters for the passed-in table

        :param table: The table name of the child
        :returns: The name of the cascade-fk, or None
        """
        for r in cls.instances:
            if r.child_table == table and r._update_cascade:
                return r.fk_column
        return None
    
    @classmethod
    def get_delete_cascade_fk_column(cls, table: str) -> Union[str, None]:
        """
        Return the cascade fk that filters for the passed-in table

        :param table: The table name of the child
        :returns: The name of the cascade-fk, or None
        """
        for r in cls.instances:
            if r.child_table == table and r._delete_cascade:
                return r.fk_column
        return None

    def __init__(self, join_type: str, child_table: str, fk_column: Union[str, int], parent_table: str,
                 pk_column: Union[str, int], update_cascade: bool, delete_cascade: bool,
                 driver: SQLDriver, frm: Form) -> None:
        """
        Initialize a new Relationship instance

        :param join_type: The join type. I.e. "LEFT JOIN", "INNER JOIN", etc.
        :param child_table: The table name of the child table
        :param fk_column: The child table's foreign key column
        :param parent_table: The table name of the parent table
        :param pk_column: The parent table's primary key column
        :param update_cascade: True if the child's fk_column ON UPDATE rule is 'CASCADE'
        :param delete_cascade: True if the child's fk_column ON DELETE rule is 'CASCADE'
        :param driver: A `SQLDriver` instance
        :param frm: A Form instance
        :returns: None
        """
        self.join_type = join_type
        self.child_table = child_table
        self.fk_column = fk_column
        self.parent_table = parent_table
        self.pk_column = pk_column
        self.update_cascade = update_cascade
        self.delete_cascade = delete_cascade
        self.driver = driver
        self.frm = frm
        Relationship.instances.append(self)
        
    @property
    def _update_cascade(self):
        if self.update_cascade and self.frm.update_cascade:
            return True
        else:
            return False

    @property
    def _delete_cascade(self):
        if self.delete_cascade and self.frm.delete_cascade:
            return True
        else:
            return False

    def __str__(self):
        """
        Return a join clause when cast to a string
        """
        return self.driver.relationship_to_join_clause(self)

    def __repr__(self):
        """
        Return a more descriptive string for debugging
        """
        ret = f'Relationship (' \
              f'\n\tjoin={self.join_type},' \
              f'\n\tchild_table={self.child_table},' \
              f'\n\tfk_column={self.fk_column},' \
              f'\n\tparent_table={self.parent_table},' \
              f'\n\tpk_column={self.pk_column}' \
              f'\n)'

        return ret


class ElementMap(dict):
    """
    Map a PySimpleGUI element to a specific `DataSet` column.  This is what makes the GUI automatically update to
    the contents of the database.  This happens automatically when a PySimpleGUI Window is bound to a `Form` by
    using the bind parameter of `Form` creation, or by executing `Form.auto_map_elements()` as long as the
    Table.column naming convention is used, This method can be used to manually map any element to any `DataSet` column
    regardless of naming convention.

    """
    def __init__(self, element: sg.Element, dataset: DataSet, column: str, where_column: str = None,
                 where_value: str = None) -> None:
        """
        Create a new ElementMap instance
        :param element: A PySimpleGUI Element
        :param dataset: A `DataSet` object
        :param column: The name of the column to bind to the element
        :param where_column: Used for key, value shorthand
        :param where_value: Used for key, value shorthand
        :returns: None
        """
        super().__init__()
        self['element'] = element
        self['dataset'] = dataset
        self['table'] = dataset.table
        self['column'] = column
        self['where_column'] = where_column
        self['where_value'] = where_value

    def __getattr__(self, key: str):
        try:
            return self[key]
        except KeyError:
            raise KeyError(f'ElementMap has no key {key}.')

    def __setattr__(self, key, value):
        self[key] = value


class DataSet:
    """
    This class is used for an internal representation of database tables. `DataSet` instances are added by the
    `Form` methods: `Form.add_table` `Form.auto_add_tables` # TODO refactor:rename these
    A `DataSet` is synonymous for a SQL Table (though you can technically have multiple `DataSet` objects referencing
    the same table, with each `DataSet` object having its own sorting, where clause, etc.)
    Note: While users will interact with DataSet objects often in pysimplesql, they typically aren't created manually by
    the user.
    """
    instances = []  # Track our own instances

    def __init__(self, data_key: str, frm_reference: Form, table: str, pk_column: str, description_column: str,
                 query: Optional[str] = '', order_clause: Optional[str] = '', filtered: bool = True,
                 prompt_save: bool = True, autosave=False) -> None:
        """
        Initialize a new `DataSet` instance

        :param data_key: The name you are assigning to this `DataSet` object (I.e. 'people')
        :param frm_reference: This is a reference to the @ Form object, for convenience
        :param table: Name of the table
        :param pk_column: The name of the column containing the primary key for this table
        :param description_column: The name of the column used for display to users (normally in a combobox or listbox)
        :param query: You can optionally set an initial query here. If none is provided, it will default to
               "SELECT * FROM {query}"
        :param order_clause: The sort order of the returned query. If none is provided it will default to
               "ORDER BY {description_column} ASC"
        :param filtered: (optional) If True, the relationships will be considered and an appropriate WHERE clause will
               be generated. False will display all records in query.
        :param prompt_save: (optional) Prompt to save changes when dirty records are present
        :param autosave: (optional) Default:False. True to autosave when changes are found without prompting the user
        :returns: None
        """
        DataSet.instances.append(self)
        self.driver = frm_reference.driver
        # No query was passed in, so we will generate a generic one
        if query == '':
            query = self.driver.default_query(table)
        # No order was passed in, so we will generate generic one
        if order_clause == '':
            order_clause = self.driver.default_order(description_column)

        self.key: str = data_key
        self.frm: Form = frm_reference
        self._current_index: int = 0
        self.table: str = table
        self.pk_column: str = pk_column
        self.description_column: str = description_column
        self.query: str = query
        self.order_clause: str = order_clause
        self.join_clause: str = ''
        self.where_clause: str = ''  # In addition to the generated where clause!
        self.dependents: list = []
        self.column_info: ColumnInfo  # ColumnInfo collection
        self.rows: Union[ResultSet, None] = None
        self.search_order: List[str] = []
        self.selector: List[str] = []
        self.callbacks: CallbacksDict = {}
        self.transform: Optional[Callable[[ResultRow, Union[TFORM_ENCODE, TFORM_DECODE]], None]] = None
        self.filtered: bool = filtered
        self._prompt_save: bool = prompt_save
        self._simple_transform: SimpleTransformsDict = {}
        self.autosave: bool = autosave

    # Override the [] operator to retrieve columns by key
    def __getitem__(self, key: str):
        return self.get_current(key)

    # Make current_index a property so that bounds can be respected
    @property
    def current_index(self):
        return self._current_index

    @current_index.setter
    # Keeps the current_index in bounds
    def current_index(self, val: int):
        if val > len(self.rows) - 1:
            self._current_index = len(self.rows) - 1
        elif val < 0:
            self._current_index = 0
        else:
            self._current_index = val

    @classmethod
    def purge_form(cls, frm: Form, reset_keygen: bool) -> None:
        """
        Purge the tracked instances related to frm

        :param frm: the `Form` to purge `DataSet`` instances from
        :param reset_keygen: Reset the keygen after purging?
        :returns: None
        """
        global keygen
        new_instances = []
        selector_keys = []

        for dataset in DataSet.instances:
            if dataset.frm != frm:
                new_instances.append(dataset)
            else:
                logger.debug(f'Removing DataSet {dataset.key} related to {frm.driver.__class__.__name__}')
                # we need to get a list of elements to purge from the keygen
                for s in dataset.selector:
                    selector_keys.append(s['element'].key)

        # Reset the keygen for selectors and elements from this Form
        # This is probably a little hack-ish, perhaps I should relocate the keygen?
        if reset_keygen:
            for k in selector_keys:
                keygen.reset_key(k)
            keygen.reset_from_form(frm)
        # Update the internally tracked instances
        DataSet.instances = new_instances

    def set_prompt_save(self, value: bool) -> None:
        """
        Set the prompt to save action when navigating records

        :param value: a boolean value, True to prompt to save, False for no prompt to save
        :returns: None
        """
        self._prompt_save = value

    def set_search_order(self, order: List[str]) -> None:
        """
        Set the search order when using the search box.

        This is a list of column names to be searched, in order

        :param order: A list of column names to search
        :returns: None
        """
        self.search_order = order

    def set_callback(self, callback: str, fctn: Callable[[Form, sg.Window], bool]) -> None:
        """
        Set DataSet callbacks. A runtime error will be thrown if the callback is not supported.

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

    def set_transform(self, fn: callable) -> None:
        """
        Set a transform on the data for this `DataSet`.

        Here you can set custom a custom transform to both decode data from the
        database and encode data written to the database. This allows you to have dates stored as timestamps in the
        database yet work with a human-readable format in the GUI and within PySimpleSQL. This transform happens only
        while PySimpleSQL actually reads from or writes to the database.

        :param fn: A callable function to preform encode/decode. This function should take three arguments: query, row
        (which will be populated by a dictionary of the row data), and an encode parameter (1 to encode, 0 to decode -
        see constants `TFORM_ENCODE` and `TFORM_DECODE`). Note that this transform works on one row at a time.
        See the example `journal_with_data_manipulation.py` for a usage example.
        :returns: None
        """
        self.transform = fn

    def set_query(self, query: str) -> None:
        """
        Set the query string for the `DataSet`.

        This is more for advanced users.  It defaults to "SELECT * FROM {table};" This can override the default

        :param query: The query string you would like to associate with the table
        :returns: None
        """
        logger.debug(f'Setting {self.table} query to {query}')
        self.query = query

    def set_join_clause(self, clause: str) -> None:
        """
        Set the `DataSet` object's join string.

        This is more for advanced users, as it will automatically generate from the database Relationships otherwise.

        :param clause: The join clause, such as "LEFT JOIN That on This.pk=That.fk"
        :returns: None
        """
        logger.debug(f'Setting {self.table} join clause to {clause}')
        self.join_clause = clause

    def set_where_clause(self, clause: str) -> None:
        """
        Set the `DataSet` object's where clause.

        This is ADDED TO the auto-generated where clause from Relationship data

        :param clause: The where clause, such as "WHERE pkThis=100"
        :returns: None
        """
        logger.debug(f'Setting {self.table} where clause to {clause} for DataSet {self.key}')
        self.where_clause = clause

    def set_order_clause(self, clause: str) -> None:
        """
        Set the `DataSet` object's order clause.

        This is more for advanced users, as it will automatically generate from the database Relationships otherwise.

        :param clause: The order clause, such as "Order by name ASC"
        :returns: None
        """
        logger.debug(f'Setting {self.table} order clause to {clause}')
        self.order_clause = clause

    def update_column_info(self, column_info: ColumnInfo = None) -> None:
        """
        Generate column information for the `DataSet` object.  This may need done, for example, when a manual query
        using joins is used.

        This is more for advanced users.
        :param column_info: (optional) A `ColumnInfo` instance. Defaults to being generated by the `SQLDriver`
        :returns: None
        """
        # Now we need to set  new column names, as the query could have changed
        if column_info is not None:
            self.column_info = column_info
        else:
            self.column_info = self.driver.column_info(self.table)

    def set_description_column(self, column: str) -> None:
        """
        Set the `DataSet` object's description column.

        This is the column that will display in Listboxes, Comboboxes, Tables, etc.
        By default,this is initialized to either the 'description','name' or 'title' column, or the 2nd column of the
        table if none of those columns exist.
        This method allows you to specify a different column to use as the description for the record.

        :param column: The name of the column to use
        :returns: None
        """
        self.description_column = column

    def records_changed(self, column: str = None, cascade=True) -> bool:
        """
        Checks if records have been changed by comparing PySimpleGUI control values with the stored DataSet values

        :param column: Limit the changed records search to just the supplied column name
        :param cascade: True to check related `DataSet` instances
        :returns: True or False on whether changed records were found
        """
        logger.debug(f'Checking if records have changed in table "{self.table}"...')

        # Virtual rows wills always be considered dirty
        if self.rows:
            if self.get_current_row().virtual:
                return True

        dirty = False
        # First check the current record to see if it's dirty
        for mapped in self.frm.element_map:
            # Compare the DB version to the GUI version
            if mapped.table == self.table:
                # if passed custom column name
                if column is not None and mapped.column != column:
                    continue
                
                # don't check if there aren't any rows. Fixes checkbox = '' when no rows.
                if not len(self.frm[mapped.table].rows):
                    continue

                # Get the element value and cast it, so we can compare it to the database version
                element_val = self.column_info[mapped.column].cast(mapped.element.get())

                # Get the table value.  If this is a keyed element, we need figure out the appropriate table column
                if mapped.where_column is not None:
                    for row in self.rows:
                        if row[mapped.where_column] == mapped.where_value:
                            table_val = row[mapped.column]
                else:
                    table_val = self[mapped.column]
                    
                if type(mapped.element) is sg.PySimpleGUI.Checkbox:
                    table_val = checkbox_to_bool(table_val)
                    element_val = checkbox_to_bool(element_val)

                # Sanitize things a bit due to empty values being slightly different in the two cases
                if table_val is None:
                    table_val = ''

                # Strip trailing whitespace from strings
                if type(table_val) is str:
                    table_val = table_val.rstrip()
                if type(element_val) is str:
                    element_val = element_val.rstrip()

                # Make the comparison
                if element_val != table_val:
                    dirty = True
                    logger.debug(f'CHANGED RECORD FOUND!')
                    logger.debug(f'\telement type: {type(element_val)} column_type: {type(table_val)}')
                    logger.debug(f'\t{mapped.element.Key}:{element_val} != {mapped.column}:{table_val}')
                    return dirty
                else:
                    dirty = False

        # handle cascade checking next
        if cascade:
            for rel in self.frm.relationships:
                if rel.parent_table == self.table and rel._update_cascade:
                    dirty = self.frm[rel.child_table].records_changed()
                    if dirty:
                        break
        return dirty

    def prompt_save(self, autosave: bool = False, update_elements: bool = True)  \
            -> Union[PROMPT_SAVE_PROCEED, PROMPT_SAVE_DISCARDED, PROMPT_SAVE_NONE]:
        """
        Prompts the user if they want to save when changes are detected and the current record is about to change.

        :param autosave: True to autosave when changes are found without prompting the user
        :param update_elements: (optional) Passed to `Form.save_records()` -> `Form.save_cascade()` to
                        update_elements. Additionally used to discard changes if user reply's 'No' to prompt.
        :returns: A prompt return value of one of the following: `PROMPT_PROCEED`, `PROMPT_DISCARDED`, or `PROMPT_NONE`
        """
        # Return False if there is nothing to check or _prompt_save is False
        # TODO: children too?
        if self.current_index is None or self.rows == [] or self._prompt_save is False:
            return PROMPT_SAVE_NONE

        # See if any rows are virtual
        vrows = len([row for row in self.rows if row.virtual])
        # Check if any records have changed
        changed = self.records_changed() or vrows
        if changed:
            if autosave or self.autosave:
                save_changes = 'yes'
            else:
                save_changes = self.frm.popup.yes_no(lang.dataset_prompt_save_title, lang.dataset_prompt_save)
            if save_changes == 'yes':
                # save this record's cascaded relationships, last to first
                if self.frm.save_records(table=self.table, update_elements=update_elements) & SAVE_FAIL:
                    return PROMPT_SAVE_DISCARDED
                return PROMPT_SAVE_PROCEED
            else:
                self.rows.purge_virtual()
                if vrows and update_elements:
                    self.frm.update_elements(self.table)
                return PROMPT_SAVE_DISCARDED
        else:
            return PROMPT_SAVE_NONE

    def requery(self, select_first: bool = True, filtered: bool = True, update_elements: bool = True,
                requery_cascade: bool = True) -> None:
        """
        Requeries the table
        The `DataSet` object maintains an internal representation of the actual database table.
        The requery method will query the actual database and sync the `DataSet` object to it

        :param select_first: (optional) If True, the first record will be selected after the requery
        :param filtered: (optional) If True, the relationships will be considered and an appropriate WHERE clause will
                         be generated. If False all records in the table will be fetched.
        :param update_elements: (optional) Passed to `DataSet.first()` to update_elements. Note that the select_first
                        parameter must equal True to use this parameter.
        :param requery_cascade: (optional) passed to `DataSet.first()` to requery_cascade. Note that the
                           select_first parameter must = True to use this parameter.
        :returns: None
        """
        join = ''
        where = ''
        
        if not self.filtered:
            filtered = False

        if filtered:
            join = self.driver.generate_join_clause(self)
            where = self.driver.generate_where_clause(self)

        query = self.query + ' ' + join + ' ' + where + ' ' + self.order_clause
        # We want to store our sort settings before we wipe out the current ResultSet
        try:
            sort_settings = self.rows.store_sort_settings()
        except AttributeError:
            sort_settings = [None, ResultSet.SORT_NONE]  # default for first query

        rows = self.driver.execute(query)
        self.rows = rows
        # now we can restore the sort order
        self.rows.load_sort_settings(sort_settings)
        self.rows.sort(self.table)

        for row in self.rows:
            # perform transform one row at a time
            if self.transform is not None:
                self.transform(self, row, TFORM_DECODE)

            # Strip trailing white space, as this is what sg[element].get() does, so we can have an equal comparison
            # Not the prettiest solution.  Will look into this more on the PySimpleGUI end and make a follow-up ticket
            for k, v in row.items():
                if type(v) is str:
                    row[k] = v.rstrip()

        if select_first:
            self.first(update_elements=update_elements, requery_cascade=requery_cascade,
                       skip_prompt_save=True)  # We don't want to prompt save in this situation, requery already done

    def requery_cascade(self, child: bool = False, update_elements: bool = True) -> None:
        """
        Requery parent `DataSet` instances as defined by the relationships of the table

        :param child: (optional) If True, will requery self. Default False; used to skip requery when called by parent.
        :param update_elements: (optional) passed to `DataSet.requery()` -> `DataSet.first()` to update_elements.
        :returns: None
        """
        if child:
            self.requery(update_elements=update_elements,
                         requery_cascade=False)  # dependents=False: no cascade requery

        for rel in self.frm.relationships:
            if rel.parent_table == self.table and rel._update_cascade:
                logger.debug(f"Requerying dependent table {self.frm[rel.child_table].table}")
                self.frm[rel.child_table].requery_cascade(child=True, update_elements=update_elements)

    def first(self, update_elements: bool = True, requery_cascade: bool = True, skip_prompt_save: bool = False) \
            -> None:
        """
        Move to the first record of the table
        Only one entry in the table is ever considered "Selected"  This is one of several functions that influences
        which record is currently selected. See `DataSet.first()`, `DataSet.previous()`, `DataSet.next()`,
        `DataSet.last()`, `DataSet.search()`, `DataSet.set_by_pk()`, `DataSet.set_by_index()`

        :param update_elements: (optional) Update the GUI elements after switching records
        :param requery_cascade: (optional) Requery cascade after switching records?
        :param skip_prompt_save: (optional) True to skip prompting to save dirty records
        :returns: None
        """
        logger.debug(f'Moving to the first record of table {self.table}')
        if skip_prompt_save is False:
            self.prompt_save(update_elements=False) # don't update self/dependents if we are going to below anyway

        self.current_index = 0
        if requery_cascade:
            self.requery_cascade(update_elements=update_elements)
        if update_elements:
            self.frm.update_elements(self.table)
        # callback
        if 'record_changed' in self.callbacks.keys():
            self.callbacks['record_changed'](self.frm, self.frm.window)

    def last(self, update_elements: bool = True, requery_cascade: bool = True, skip_prompt_save: bool = False):
        """
        Move to the last record of the table
        Only one entry in the table is ever considered "Selected"  This is one of several functions that influences
        which record is currently selected. See `DataSet.first()`, `DataSet.previous()`, `DataSet.next()`,
        `DataSet.last()`, `DataSet.search()`, `DataSet.set_by_pk()`, `DataSet.set_by_index()`

        :param update_elements: (optional) Update the GUI elements after switching records
        :param requery_cascade: (optional) Requery cascade after switching records?
        :param skip_prompt_save: (optional) True to skip prompting to save dirty records
        :returns: None
        """
        logger.debug(f'Moving to the last record of table {self.table}')
        if skip_prompt_save is False:
            self.prompt_save(update_elements=False) # don't update self/dependents if we are going to below anyway
            
        self.current_index = len(self.rows) - 1
        if requery_cascade:
            self.requery_cascade()
        if update_elements:
            self.frm.update_elements(self.table)
        # callback
        if 'record_changed' in self.callbacks.keys():
            self.callbacks['record_changed'](self.frm, self.frm.window)

    def next(self, update_elements: bool = True, requery_cascade: bool = True, skip_prompt_save: bool = False):
        """
        Move to the next record of the table
        Only one entry in the table is ever considered "Selected"  This is one of several functions that influences
        which record is currently selected. See `DataSet.first()`, `DataSet.previous()`, `DataSet.next()`,
        `DataSet.last()`, `DataSet.search()`, `DataSet.set_by_pk()`, `DataSet.set_by_index()`

        :param update_elements: (optional) Update the GUI elements after switching records
        :param requery_cascade: (optional) Requery cascade after switching records?
        :param skip_prompt_save: (optional) True to skip prompting to save dirty records
        :returns: None
        """
        if self.current_index < len(self.rows) - 1:
            logger.debug(f'Moving to the next record of table {self.table}')
            if skip_prompt_save is False:
                self.prompt_save(update_elements=False) # don't update self/dependents if we are going to below anyway

            self.current_index += 1
            if requery_cascade:
                self.requery_cascade()
            if update_elements:
                self.frm.update_elements(self.table)
            # callback
            if 'record_changed' in self.callbacks.keys():
                self.callbacks['record_changed'](self.frm, self.frm.window)

    def previous(self, update_elements: bool = True, requery_cascade: bool = True, skip_prompt_save: bool = False):
        """
        Move to the previous record of the table
        Only one entry in the table is ever considered "Selected"  This is one of several functions that influences
        which record is currently selected. See `DataSet.first()`, `DataSet.previous()`, `DataSet.next()`,
        `DataSet.last()`, `DataSet.search()`, `DataSet.set_by_pk()`, `DataSet.set_by_index()`

        :param update_elements: (optional) Update the GUI elements after switching records
        :param requery_cascade: (optional) Requery cascade after switching records?
        :param skip_prompt_save: (optional) True to skip prompting to save dirty records
        :returns: None
        """
        if self.current_index > 0:
            logger.debug(f'Moving to the previous record of table {self.table}')
            if skip_prompt_save is False:
                self.prompt_save(update_elements=False) # don't update self/dependents if we are going to below anyway

            self.current_index -= 1
            if requery_cascade:
                self.requery_cascade()
            if update_elements:
                self.frm.update_elements(self.table)
            # callback
            if 'record_changed' in self.callbacks.keys():
                self.callbacks['record_changed'](self.frm, self.frm.window)

    def search(self, search_string: str, update_elements: bool = True, dependents: bool = True,
               skip_prompt_save: bool = False) \
            -> Union[SEARCH_FAILED, SEARCH_RETURNED, SEARCH_ABORTED]:
        """
        Move to the next record in the `DataSet` that contains `search_string`.
        Successive calls will search from the current position, and wrap around back to the beginning.
        The search order from `DataSet.set_search_order()` will be used.  If the search order is not set by the user,
        it will default to the description column (see `DataSet.set_description_column()`).
        Only one entry in the table is ever considered "Selected"  This is one of several functions that influences
        which record is currently selected. See `DataSet.first()`, `DataSet.previous()`, `DataSet.next()`,
        `DataSet.last()`, `DataSet.search()`, `DataSet.set_by_pk()`, `DataSet.set_by_index()`

        :param search_string: The search string to look for
        :param update_elements: (optional) Update the GUI elements after switching records
        :param dependents: (optional) Requery cascade after switching records?
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

        if skip_prompt_save is False:  # TODO: Should this be before the before_search callback?
            self.prompt_save(update_elements=False) # don't update self/dependents if we are going to below anyway

        # First lets make a search order.. TODO: remove this hard coded garbage
        if len(self.rows):
            logger.debug(f'DEBUG: {self.search_order} {self.rows[0].keys()}')
        for o in self.search_order:
            # Perform a search for str, from the current position to the end and back by creating a list of all indexes
            for i in list(range(self.current_index + 1, len(self.rows))) + list(range(0, self.current_index)):
                if o in self.rows[i].keys():
                    if self.rows[i][o]:
                        if search_string.lower() in str(self.rows[i][o]).lower():
                            old_index = self.current_index
                            self.current_index = i
                            if dependents:
                                self.requery_cascade()
                            if update_elements:
                                self.frm.update_elements(self.table)

                            # callback
                            if 'after_search' in self.callbacks.keys():
                                if not self.callbacks['after_search'](self.frm, self.frm.window):
                                    self.current_index = old_index
                                    self.requery_cascade()
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

    def set_by_index(self, index: int, update_elements: bool = True, dependents: bool = True,
                     skip_prompt_save: bool = False, omit_elements: List[str] = None) -> None:
        """
        Move to the record of the table located at the specified index in DataSet.
         Only one entry in the table is ever considered "Selected"  This is one of several functions that influences
        which record is currently selected. See `DataSet.first()`, `DataSet.previous()`, `DataSet.next()`,
        `DataSet.last()`, `DataSet.search()`, `DataSet.set_by_pk()`, `DataSet.set_by_index()`

        :param index: The index of the record to move to.
        :param update_elements: (optional) Update the GUI elements after switching records
        :param dependents: (optional) Requery cascade after switching records?
        :param skip_prompt_save: (optional) True to skip prompting to save dirty records
        :param omit_elements: (optional) A list of elements to omit from updating
        :returns: None
        """
        logger.debug(f'Moving to the record at index {index} on {self.table}')
        if omit_elements is None:
            omit_elements = []

        if skip_prompt_save is False:
            # see if sg.Table has potential changes
            if len(omit_elements) and self.records_changed(cascade=False):
                omit_elements = [] # most likely will need to update, either to discard virtual or update after save
            self.prompt_save(update_elements=False) # don't update self/dependents if we are going to below anyway

        self.current_index = index
        if dependents:
            self.requery_cascade()
        if update_elements:
            self.frm.update_elements(self.table, omit_elements=omit_elements)

    def set_by_pk(self, pk: int, update_elements: bool = True, requery_cascade: bool = True,
                  skip_prompt_save: bool = False, omit_elements: list[str] = None) -> None:
        """
        Move to the record with this primary key
        This is useful when modifying a record (such as renaming).  The primary key can be stored, the record re-named,
        and then the current record selection updated regardless of the new sort order.
        Only one entry in the table is ever considered "Selected"  This is one of several functions that influences
        which record is currently selected. See `DataSet.first`, `DataSet.previous`, `DataSet.next`, `DataSet.last`,
         `DataSet.search`, `DataSet.set_by_index`

        :param pk: The record to move to containing the primary key
        :param update_elements: (optional) Update the GUI elements after switching records
        :param requery_cascade: (optional) Requery cascade after switching records?
        :param skip_prompt_save: (optional) True to skip prompting to save dirty records
        :param omit_elements: (optional) A list of elements to omit from updating
        :returns: None
        """
        logger.debug(f'Setting table {self.table} record by primary key {pk}')
        if omit_elements is None:
            omit_elements = []

        if skip_prompt_save is False:
            # see if sg.Table has potential changes
            if len(omit_elements) and self.records_changed(cascade=False):
                omit_elements = [] # most likely will need to update, either to discard virtual or update after save
            self.prompt_save(update_elements=False) # don't update self/dependents if we are going to below anyway

        i = 0
        for r in self.rows:
            if r[self.pk_column] == pk:
                self.current_index = i
                break
            else:
                i += 1

        if requery_cascade:
            self.requery_cascade()
        if update_elements:
            self.frm.update_elements(self.table, omit_elements=omit_elements)

    def get_current(self, column: str, default: Union[str, int] = "") -> Union[str, int]:
        """
        Get the current value for the supplied column
        You can also use indexing of the @Form object to get the current value of a column
        I.e. frm[{DataSet}].[{column}]

        :param column: The column you want to get the value from
        :param default: A value to return if the record is null
        :returns: The value of the column requested
        """
        logger.debug(f'Getting current record for {self.table}.{column}')
        if self.rows:
            if self.get_current_row()[column] != '':
                return self.get_current_row()[column]
            else:
                return default
        else:
            return default

    def set_current(self, column: str, value: Union[str, int]) -> None:
        """
       Set the current value for the supplied column
       You can also use indexing of the `Form` object to set the current value of a column
       I.e. frm[{DataSet}].[{column}] = 'New value'

       :param column: The column you want to set the value for
       :param value: A value to set the current record's column to
       :returns: None
       """
        logger.debug(f'Setting current record for {self.table}.{column} = {value}')
        self.get_current_row()[column] = value

    def get_keyed_value(self, value_column: str, key_column: str, key_value: Union[str, int]) -> Union[str, int]:
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
            self.current_index = self.current_index  # force the current_index to be in bounds! For child reparenting
            return self.rows[self.current_index]

    def add_selector(self, element: sg.Element, data_key: str, where_column: str = None, where_value: str = None) \
            -> None:
        """
        Use an element such as a listbox, combobox or a table as a selector item for this table.
        Note: This is not typically used by the end user, as this is called from the`selector()` convenience function

        :param element: the PySimpleGUI element used as a selector element
        :param data_key: the `DataSet` item this selector will operate on
        :param where_column: (optional)
        :param where_value: (optional)
        :returns: None
        """
        if type(element) not in [sg.PySimpleGUI.Listbox, sg.PySimpleGUI.Slider, sg.Combo, sg.Table]:
            raise RuntimeError(f'add_selector() error: {element} is not a supported element.')

        logger.debug(f'Adding {element.Key} as a selector for the {self.table} table.')
        d = {'element': element, 'data_key': data_key, 'where_column': where_column, 'where_value': where_value}
        self.selector.append(d)

    def insert_record(self, values: Dict[str: Union[str, int]] = None, skip_prompt_save: bool = False) -> None:
        """
        Insert a new record virtually in the `DataSet` object. If values are passed, it will initially set those columns
        to the values (I.e. {'name': 'New Record', 'note': ''}), otherwise they will be fetched from the database if
        present.

        :param values: column:value pairs
        :param skip_prompt_save: Skip prompting the user to save dirty records before the insert
        :returns: None
        """
        # todo: you don't add a record if there isn't a parent!!!
        # todo: this is currently filtered out by enabling of the element, but it should be filtered here too!
        # todo: bring back the values parameter
        if skip_prompt_save is False:
            self.prompt_save(update_elements=False) # don't update self/dependents if we are going to below anyway

        # Get a new dict for a new row with default values already filled in
        new_values = self.column_info.default_row_dict(self)

        # If the values parameter was passed in, overwrite any values in the dict
        if values is not None:
            for k, v in values.items():
                if k in new_values:
                    new_values[k] = v

        # Make sure we take into account the foreign key relationships...
        for r in self.frm.relationships:
            if self.table == r.child_table and r._update_cascade:
                new_values[r.fk_column] = self.frm[r.parent_table].get_current_pk()

        # Update the pk to match the expected pk the driver would generate on insert.
        new_values[self.pk_column] = self.driver.next_pk(self.table, self.pk_column)

        # Insert the new values using RecordSet.insert(). This will mark the new row as virtual!
        self.rows.insert(new_values)

        # and move to the new record
        self.set_by_pk(new_values[self.pk_column], update_elements=True, requery_cascade=True,
                       skip_prompt_save=True)  # already saved
        self.frm.update_elements(self.table)

    def save_record(self, display_message: bool = True, update_elements: bool = True) -> int:
        """
        Save the currently selected record
        Saves any changes made via the GUI back to the database.  The before_save and after_save `DataSet.callbacks`
        will call your own functions for error checking if needed!

        :param display_message: Displays a message "Updates saved successfully", otherwise is silent on success
        :param update_elements: Update the GUI elements after saving
        :returns: SAVE_NONE, SAVE_FAIL or SAVE_SUCCESS masked with SHOW_MESSAGE
        """
        logger.debug(f'Saving records for table {self.table}...')
        # Ensure that there is actually something to save
        if not len(self.rows):
            if display_message:
                self.frm.popup.info(lang.dataset_save_empty)
            return SAVE_NONE + SHOW_MESSAGE

        # callback
        if 'before_save' in self.callbacks.keys():
            if self.callbacks['before_save']() is False:
                logger.debug("We are not saving!")
                if update_elements:
                    self.frm.update_elements(self.table)
                if display_message:
                    self.frm.popup.ok(lang.dataset_save_callback_false_title, lang.dataset_save_callback_false)
                return SAVE_FAIL + SHOW_MESSAGE

        # Check right away to see if any records have changed, no need to proceed any further than we have to
        if not self.records_changed(cascade=False) and self.frm.force_save is False:
            self.frm.popup.info(lang.dataset_save_none, display_message=display_message)
            return SAVE_NONE + SHOW_MESSAGE

        # Work with a copy of the original row and transform it if needed
        # Note that while saving, we are working with just the current row of data, unless it's 'keyed' via ?/= 
        current_row = self.get_current_row().copy()

        # Track the keyed queries we have to run.  Set to None, so we can tell later if there were keyed elements
        keyed_queries: Optional[List] = None  # {'column':column, 'changed_row': row, 'where_clause': where_clause}

        # Propagate GUI data back to the stored current_row
        for mapped in self.frm.element_map:
            if mapped.dataset == self:

                # convert the data into the correct data type using the domain in ColumnInfo
                element_val = self.column_info[mapped.column].cast(mapped.element.get())

                # Looked for keyed elements first
                if mapped.where_column is not None:
                    if keyed_queries is None:
                        keyed_queries = []  # Make the list here so != None if keyed elements
                    for row in self.rows:
                        if row[mapped.where_column] == mapped.where_value:
                            if row[mapped.column] != element_val:
                                # This record has changed.  We will save it
                                row[mapped.column] = element_val  # propagate the value
                                changed = {mapped.column: element_val}
                                where_clause = f'WHERE {self.driver.quote_column(mapped.where_column)} = \
                                                {self.driver.quote_value(mapped.where_value)}'
                                keyed_queries.append({'column': mapped.column, 'changed_row': changed,
                                                      'where_clause': where_clause})
                else:
                    current_row[mapped.column] = element_val

        changed_row = {k: v for k, v in current_row.items()}
        cascade_fk_changed = False
        # check to see if cascading-fk has changed before we update database
        cascade_fk_column = Relationship.get_update_cascade_fk_column(self.table)
        if cascade_fk_column:
            # check if fk
            for mapped in self.frm.element_map:
                if mapped.dataset == self and mapped.column == cascade_fk_column:
                    cascade_fk_changed = self.records_changed(column=cascade_fk_column, cascade=False)

        # Update the database from the stored rows
        if self.transform is not None:
            self.transform(self, changed_row, TFORM_ENCODE)

        # Save or Insert the record as needed
        if keyed_queries is not None:
            # Now execute all the saved queries from earlier
            for q in keyed_queries:
                # Update the database from the stored rows
                if self.transform is not None:
                    self.transform(self, q['changed_row'], TFORM_ENCODE)
                result = self.driver.save_record(self, q['changed_row'], q['where_clause'])
                if result.exception is not None:
                    self.frm.popup.ok(lang.dataset_save_keyed_fail_title,
                                      lang.dataset_save_keyed_fail.format_map(LangFormat(exception=result.exception)))
                    self.driver.rollback()
                    return SAVE_FAIL  # Do not show the message in this case, since it's handled here
        else:
            if current_row.virtual:
                result = self.driver.insert_record(self.table, self.get_current_pk(), self.pk_column, changed_row)
            else:
                result = self.driver.save_record(self, changed_row)

            if result.exception is not None:
                self.frm.popup.ok(lang.dataset_save_fail_title, 
                                  lang.dataset_save_fail.format_map(LangFormat(exception=result.exception)))
                self.driver.rollback()
                return SAVE_FAIL  # Do not show the message in this case, since it's handled here

            # Store the pk can we can move to it later - use the value returned in the resultset if possible
            # the expected pk changed from autoincrement and/or concurrent access
            pk = result.lastrowid if result.lastrowid is not None else self.get_current_pk()
            current_row[self.pk_column] = pk

            # then update the current row data
            self.rows[self.current_index] = current_row

            # If child changes parent, move index back and requery/requery_cascade
            if cascade_fk_changed and not current_row.virtual:  # Virtual rows already requery, and have no dependents.
                self.frm[self.table].requery(select_first=False)  # keep spot in table
                self.frm[self.table].requery_cascade()

            # Lets refresh our data
            if current_row.virtual:
                self.requery(select_first=False,
                             update_elements=False)  # Requery so that the new  row honors the order clause
                if update_elements:
                    self.set_by_pk(pk, skip_prompt_save=True)  # Then move to the record

        # callback
        if 'after_save' in self.callbacks.keys():
            if not self.callbacks['after_save'](self.frm, self.frm.window):
                self.driver.rollback()
                return SAVE_FAIL + SHOW_MESSAGE

        # If we made it here, we can commit the changes, since the save and insert above do not commit or rollback
        self.driver.commit()

        if update_elements:
            self.frm.update_elements(self.table)
        logger.debug(f'Record Saved!')
        if display_message:
            self.frm.popup.info(lang.dataset_save_success)

        return SAVE_SUCCESS + SHOW_MESSAGE

    def save_cascade(self, results: SaveResultsDict, display_message = False, check_prompt_save: bool = False,
                              update_elements: bool = True) -> SaveResultsDict:
        """
        Save changes, taking into account the relationships of the tables.
        :param results: Used in Form.save_records to collect DataSet.save_record returns. Pass an empty dict to get list
               of {table : result}
        :param display_message: Passed to DataSet.save_record. Displays a message "Updates saved successfully", otherwise
               is silent on success
        :param check_prompt_save: Used when called from Form.prompt_save. Updates elements without saving if individual
               `DataSet._prompt_save()` is False.
        :returns: dict of {table : results}
        """
        for rel in self.frm.relationships:
            if rel.parent_table == self.table and rel._update_cascade:
                self.frm[rel.child_table].save_cascade(
                    results=results,
                    display_message=display_message,
                    check_prompt_save=check_prompt_save,
                    update_elements=update_elements
                    )
        if check_prompt_save and self._prompt_save is False:
            if update_elements:
                self.frm.update_elements(self.table)
            results[self.table] = PROMPT_SAVE_NONE
            return results
        else:
            result = self.save_record(display_message=display_message,update_elements=update_elements)
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
            children = Relationship.get_delete_cascade_relationships(self.table)

        msg_children = ', '.join(children)
        if len(children):
            msg = lang.delete_cascade.format_map(LangFormat(children=msg_children))
        else:
            msg = lang.delete_single
        answer = self.frm.popup.yes_no(lang.delete_title, msg)
        if answer == 'no':
            return True
        
        if self.get_current_row().virtual:
            self.rows.purge_virtual()
            self.frm.update_elements(self.table)
            self.requery_cascade()
            return

        # Delete child records first!
        result = self.driver.delete_record(self, True)
        if result == DELETE_RECURSION_LIMIT_ERROR:
            self.frm.popup.ok(lang.delete_failed_title, 
                              lang.delete_failed.format_map(LangFormat(exception=lang.delete_recursion_limit_error)))
        elif result.exception is not None:
            self.frm.popup.ok(lang.delete_failed_title, 
                              lang.delete_failed.format_map(LangFormat(exception=result.exception)))

        # callback
        if 'after_delete' in self.callbacks.keys():
            if not self.callbacks['after_delete'](self.frm, self.frm.window):
                self.driver.rollback()
            else:
                self.driver.commit()
        else:
            self.driver.commit()

        self.requery(select_first=False)
        self.requery_cascade()
        self.frm.update_elements(self.table)
        
    def duplicate_record(self, cascade:bool=True) -> None: # TODO check return type, returns True within
        """
        Duplicate the currently selected record
        The before_duplicate and after_duplicate callbacks are run during this process to give some control over the process

        :param cascade: Duplicate child records (as defined by `Relationship`s that were set up) before duplicating this record
        :returns: None
        """
        # Ensure that there is actually something to duplicate
        if not len(self.rows) or self.get_current_row().virtual:
            return

        # callback
        if 'before_duplicate' in self.callbacks.keys():
            if not self.callbacks['before_duplicate'](self.frm, self.frm.window):
                return
            
        children = []
        if cascade:
            children = Relationship.get_update_cascade_relationships(self.table)

        msg_children = ', '.join(children)
        msg = lang.duplicate_child.format_map(LangFormat(children=msg_children)).splitlines()
        layout = [[sg.T(line, font='bold')] for line in msg]
        if len(children):
            answer = sg.Window(lang.duplicate_child_title, [
                layout,
                [sg.Button(button_text=lang.duplicate_child_button_dupparent, key='parent',
                                use_ttk_buttons = themepack.use_ttk_buttons,
                                pad = themepack.popup_button_pad)],
                [sg.Button(button_text=lang.duplicate_child_button_dupboth, key='cascade',
                                use_ttk_buttons = themepack.use_ttk_buttons,
                                pad = themepack.popup_button_pad)],
                [sg.Button(button_text=lang.button_cancel, key='cancel',
                                use_ttk_buttons = themepack.use_ttk_buttons,
                                pad = themepack.popup_button_pad)],
                ], keep_on_top=True, modal=True, ttk_theme = themepack.ttk_theme).read(close=True)
            if answer[0] == 'parent':
                cascade = False
            elif answer[0] in ['cancel', None]:
                return True
        else:
            msg = lang.duplicate_single
            answer = self.frm.popup.yes_no(lang.duplicate_single_title, msg)
            if answer == 'no':
                return True
        # Store our current pk, so we can move to it if the duplication fails
        pk = self.get_current_pk()

        # Have the driver duplicate the record
        result = self.driver.duplicate_record(self, cascade)
        if result.exception:
            self.driver.rollback()
            self.frm.popup.ok(lang.duplicate_failed_title, 
                              lang.duplicate_failed.format_map(LangFormat(exception=result.exception)))
        else:
            pk = result.lastrowid
                        
        # callback
        if 'after_duplicate' in self.callbacks.keys():
            if not self.callbacks['after_duplicate'](self.frm, self.frm.window):
                self.driver.rollback()
            else:
                self.driver.commit()
        else:
            self.driver.commit()
        self.driver.commit()
        
        # requery and move to new pk
        self.requery(select_first=False)
        self.set_by_pk(pk, skip_prompt_save=True)

    def get_description_for_pk(self, pk:int) -> Union[str,int,None]:
        """
        Get the description from `DataSet.description_column` from the row where the `DataSet.pk_column` = `pk`

        :param pk: The primary key from which to find the description for
        :returns: The value found in the description column, or None if nothing is found
        """
        for row in self.rows:
            if row[self.pk_column] == pk:
                return row[self.description_column]
        return None

    def table_values(self, columns: List[str] = None, mark_virtual: bool = False) -> List[TableRow]:
        """
        Create a values list of `TableRows`s for use in a PySimpleGUI Table element. Each

        :param columns: A list of column names to create table values for.  Defaults to getting them from the
                             `DataSet.rows` `ResultSet`
        :param mark_virtual: Place a marker next to virtual records
        :returns: A list of `TableRow`s suitable for using with PySimpleGUI Table element values
        """
        global themepack

        values = []
        try:
            all_columns = self.rows[0].keys()
        except IndexError:
            all_columns = []

        if columns is None:
            columns = all_columns
        else:
            columns = columns

        pk_column = self.column_info.pk_column()

        for row in self.rows:
            if mark_virtual:
                lst = [themepack.marker_virtual] if row.virtual else [' ']
            else:
                lst = []

            rels = Relationship.get_relationships_for_table(self.table)
            pk = None
            for col in all_columns:
                # Is this the primary key column?
                if col == pk_column: pk = row[col]
                # Skip this column if we aren't supposed to grab it
                if col not in columns: continue
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

    def get_related_table_for_column(self, column: str) -> str:
        """
        Get parent table name as it relates to this column

        :param column: The column name to get related table information for
        :returns: The name of the related table, or the current table if none are found
        """
        rels = Relationship.get_relationships_for_table(self.table)
        for rel in rels:
            if column == rel.fk_column:
                return rel.parent_table
        return self.table  # None could be found, return our own table instead

    def quick_editor(self, pk_update_funct: callable = None, funct_param: any = None,
                     skip_prompt_save: bool = False) -> None:
        """
        The quick editor is a dynamic PySimpleGUI Window for quick editing of tables.  This is very useful for putting
        a button next to a combobox or listbox so that the available values can be added/edited/deleted easily.
        Note: This is not typically used by the end user, as it can be configured from the `field()` convenience function

        :param pk_update_funct: (optional) A function to call to determine the pk to select by default when the quick editor loads
        :param funct_param: (optional) A parameter to pass to the `pk_update_funct`
        :param skip_prompt_save: (Optional) True to skip prompting to save dirty records
        :returns: None
        """
        global keygen
        global themepack

        if skip_prompt_save is False: self.frm.prompt_save()
        # Reset the keygen to keep consistent naming
        logger.info('Creating Quick Editor window')
        keygen.reset()
        data_key = self.key
        layout = []
        headings = self.column_info.names()
        visible = [1] * len(headings); visible[0] = 0
        col_width=int(55/(len(headings)-1))
        for i in range(0,len(headings)):
            headings[i]=headings[i].ljust(col_width,' ')

        layout.append(
            [selector(data_key, sg.Table, key=f'{data_key}:quick_editor', num_rows=10, headings=headings, visible_column_map=visible)])
        layout.append([actions(data_key, edit_protect=False)])
        layout.append([sg.Text('')])
        layout.append([sg.HorizontalSeparator()])
        for col in self.column_info.names():
            column=f'{data_key}.{col}'
            if col!=self.pk_column:
                layout.append([field(column)])

        quick_win = sg.Window(lang.quick_edit_title.format_map(LangFormat(data_key=data_key)),
                              layout, keep_on_top = True, modal = True, finalize = True,
                              ttk_theme=themepack.ttk_theme) # Without specifying same ttk_theme,
                                                             # quick_edit will override user-set theme
                                                             # in main window
        quick_frm = Form(self.frm.driver, bind_window=quick_win)

        # Select the current entry to start with
        if pk_update_funct is not None:
            if funct_param is None:
                quick_frm[data_key].set_by_pk(pk_update_funct())
            else:
                quick_frm[data_key].set_by_pk(pk_update_funct(funct_param))

        while True:
            event, values = quick_win.read()

            if quick_frm.process_events(event, values):
                logger.debug(f'PySimpleSQL Quick Editor event handler handled the event {event}!')
            if event in [sg.WIN_CLOSED,'Exit']:
                break
            else:
                logger.debug(f'This event ({event}) is not yet handled.')
        quick_win.close()
        self.requery()
        self.frm.update_elements()

    def add_simple_transform(self, transforms: SimpleTransformsDict) -> None:
        """
        Merge a dictionary of transforms into the `DataSet._simple_transform` dictionary.

        Example:
        {'entry_date' : {
            'decode' : lambda row,col: datetime.utcfromtimestamp(int(row[col])).strftime('%m/%d/%y'),
            'encode' : lambda row,col: datetime.strptime(row[col], '%m/%d/%y').replace(tzinfo=timezone.utc).timestamp(),
        }}
        :param transforms: A dict of dicts containing either 'encode' or 'decode' along with a callable to do the transform.
               see example above
        :returns: None
        """
        for k,v in transforms.items():
            if not callable(v): RuntimeError(f'Transform for {k} must be callable!')
            self._simple_transform[k] = v

class Form:
    """
    @orm class
    Maintains an internal version of the actual database
    `DataSet` objects can be accessed by key, I.e. frm['data_key']
    """
    instances = []  # Track our instances
    relationships = [] # Track our relationships

    def __init__(self, driver: SQLDriver, bind_window: sg.Window = None, prefix_data_keys: str = '',
                 parent: Form = None, filter: str = None, select_first: bool = True, autosave: bool = False,
                 update_cascade: bool = True, delete_cascade: bool = True) -> None:
        """
        Initialize a new `Form` instance

        :param driver: Supported `SQLDriver`. See `Sqlite()`, `Mysql()`, `Postgres()`
        :param bind_window: Bind this window to the `Form`
        :param prefix_data_keys: (optional) prefix auto generated data_key names with this value. Example 'data_'
        :param parent: (optional)Parent `Form` to base dataset off of
        :param filter: (optional) Only import elements with the same filter set. Typically set with `field()`, but can
                       also be set manually as a dict with the key 'filter' set in the element's metadata
        :param select_first: (optional) Default:True. For each top-level parent, selects first row, populating children
                             as well.
        :param autosave: (optional) Default:False. True to autosave when changes are found without prompting the user
        :returns: None

        """
        win_pb = ProgressBar(lang.startup_form)
        win_pb.update(lang.startup_init, 0)
        Form.instances.append(self)

        self.driver: SQLDriver = driver
        self.filter: str = filter
        self.parent: Form = parent  # TODO: This doesn't seem to really be used yet
        self.window: Optional[sg.Window] = None
        self._edit_protect: bool = False
        self.datasets: Dict[str, DataSet] = {}
        self.element_map: List[ElementMap] = []
        self.popup = None
        """
        The element map dict is set up as below:
        
        .. literalinclude:: ../doc_examples/element_map.1.py
        :language: python
        :caption: Example code
        """
        self.event_map = []  # Array of dicts, {'event':, 'function':, 'table':}
        self.relationships: List[Relationship] = []
        self.callbacks: CallbacksDict = {}
        self.autosave: bool = autosave
        self.force_save: bool = False
        self.update_cascade: bool = update_cascade
        self.delete_cascade: bool = delete_cascade

        # Add our default datasets and relationships
        win_pb.update(lang.startup_datasets, 25)
        self.auto_add_datasets(prefix_data_keys)
        win_pb.update(lang.startup_relationships, 50)
        self.auto_add_relationships()
        self.requery_all(select_first=select_first, update_elements=False, requery_cascade=True)
        if bind_window is not None:
            win_pb.update(lang.startup_binding, 75)
            self.window=bind_window
            self.popup = Popup()
            self.bind(self.window)
        win_pb.close()

    def __del__(self):
        self.close()

    # Override the [] operator to retrieve dataset by key
    def __getitem__(self, key: str) -> DataSet:
        try:
            return self.datasets[key]
        except KeyError:
            raise RuntimeError(f'The DataSet for `{key}` does not exist.  This can be caused because the database does'
                    f'not exist, the database user does not have the proper permissions set, or any number of '
                    f'database configuration issues.')

    def close(self, reset_keygen: bool = True):
        """
        Safely close out the `Form`

        :param reset_keygen: True to reset the keygen for this `Form`
        """
        # First delete the dataset associated
        DataSet.purge_form(self, reset_keygen)
        self.driver.close()

    def bind(self, win:sg.Window) -> None:
        """
        Bind the PySimpleGUI Window to the Form for the purpose of GUI element, event and relationship mapping.
        This can happen automatically on `Form` creation with the bind parameter and is not typically called by the end
        user. This function literally just groups all the auto_* methods.  See `Form.auto_add_tables()`,
        `Form.auto_add_relationships()`, `Form.auto_map_elements()`, `Form.auto_map_events()`

        :param win: The PySimpleGUI window
        :returns:  None
        """
        logger.info('Binding Window to Form')
        self.window = win
        self.popup = Popup()
        self.auto_map_elements(win)
        self.auto_map_events(win)
        self.update_elements()
        logger.debug('Binding finished!')


    def execute(self, query: str) -> ResultSet:
        """
        Convenience function to pass along to `SQLDriver.execute()`

        :param query: The query to execute
        :returns: A `ResultSet` object
        """
        return self.driver.execute(query)

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
        for mapped in self.element_map:
            supported.append(mapped.element.key)

        # Add in other window elements
        for element in self.window.key_dict:
            supported.append(element)

        if callback_name in supported:
            self.callbacks[callback_name] = fctn
        else:
            raise RuntimeError(f'Callback "{callback_name}" not supported. callback: {callback_name} supported: {supported}')

    def add_dataset(self, data_key: str, table: str, pk_column: str, description_column: str, query: str = '',
                    order_clause: str = '') -> None:
        """
        Manually add a `DataSet` object to the `Form`
        When you attach to a database, PySimpleSQL isn't aware of what it contains until this command is run
        Note that `Form.auto_add_datasets()` does this automatically, which is called when a `Form` is created

        :param data_key: The key to give this `DataSet`.  Use frm['data_key'] to access it.
        :param table: The name of the table in the database
        :param pk_column: The primary key column of the table in the database
        :param description_column: The column to be used to display to users in listboxes, comboboxes, etc.
        :param query: The initial query for the table.  Auto generates "SELECT * FROM {table}" if none is passed
        :param order_clause: The initial sort order for the query
        :returns: None
        """
        self.datasets.update({data_key: DataSet(data_key, self, table, pk_column, description_column, query, order_clause)})
        self[data_key].set_search_order([description_column])  # set a default sort order

    def add_relationship(self, join:str, child_table:str, fk_column:str, parent_table:str, pk_column:str,
                         update_cascade:bool, delete_cascade:bool) -> None:
        """
        Add a foreign key relationship between two dataset of the database
        When you attach a database, PySimpleSQL isn't aware of the relationships contained until dataset are
        added via `Form.add_data`, and the relationship of various tables is set with this function.
        Note that `Form.auto_add_relationships()` will do this automatically from the schema of the database,
        which also happens automatically when a `Form` is created.

        :param join: The join type of the relationship ('LEFT JOIN', 'INNER JOIN', 'RIGHT JOIN')
        :param child_table: The child table containing the foreign key
        :param fk_column: The foreign key column of the child table
        :param parent_table: The parent table containing the primary key
        :param pk_column: The primary key column of the parent table
        :param update_cascade: Requery and filter child table results on selected parent primary key (ON UPDATE CASCADE in SQL)
        :param delete_cascade: Delete the dependent child records if the parent table record is deleted (ON UPDATE DELETE in SQL)
        :returns: None
        """
        self.relationships.append(
            Relationship(join, child_table, fk_column, parent_table, pk_column,
                         update_cascade, delete_cascade, self.driver, self))
        
    def update_fk_relationship(self, child_table:str, fk_column:str, update_cascade:bool = None, delete_cascade:bool = None) -> None:
        """
        Update a foreign key's update_cascade and delete_cascade behavior.
        `Form.auto_add_relationships()` automatically sets update_cascade and delete_cascade
        from the schema of the database.
        :param child_table: The child table containing the foreign key
        :param fk_column: The foreign key column of the child table
        :param update_cascade: True requeries and filters child table results on selected parent primary key (ON UPDATE CASCADE in SQL)
        :param delete_cascade: Delete the dependent child records if the parent table record is deleted (ON UPDATE DELETE in SQL)
        :returns: None
        """
        for rel in self.relationships:
            if rel.child_table == child_table and rel.fk_column == fk_column:
                logger.info(f'Updating {fk_column=} relationship.')
                if update_cascade is not None:
                    rel.update_cascade = update_cascade
                if delete_cascade is not None:
                    rel.delete_cascade = update_cascade
    
    def auto_add_datasets(self, prefix_data_keys: str = '') -> None:
        """
        Automatically add `DataSet` objects from the database by looping through the tables available and creating a
        `DataSet` object for each. Each dataset key is an optional prefix plus the name of the table.
        When you attach to a sqlite database, PySimpleSQL isn't aware of what it contains until this command is run.
        This is called automatically when a `Form ` is created.
        Note that `Form.add_table()` can do this manually on a per-table basis.

        :param prefix_data_keys: Adds a prefix to the auto-generated `DataSet` keys
        :returns: None
        """
        logger.info('Automatically generating dataset for each table in the sqlite database')
        # Ensure we clear any current dataset so that successive calls will not double the entries
        self.datasets = {}
        tables = self.driver.get_tables()
        for table in tables:
            column_info = self.driver.column_info(table)

            # auto generate description column.  Default it to the 2nd column,
            # but can be overwritten below
            description_column = column_info.col_name(1)
            for col in column_info.names():
                if col in ('name', 'description', 'title'):
                    description_column = col
                    break

            # Get our pk column
            pk_column = self.driver.pk_column(table)

            data_key= prefix_data_keys + table
            logger.debug(
                f'Adding DataSet "{data_key}" on table {table} to Form with primary key {pk_column} and description of {description_column}')
            self.add_dataset(data_key, table, pk_column, description_column)
            self.datasets[data_key].column_info = column_info

    # Make sure to send a list of table names to requery if you want
    # dependent dataset to requery automatically
    def auto_add_relationships(self) -> None:
        """
        Automatically add a foreign key relationship between tables of the database. This is done by foreign key
        constraints within the database.  Automatically requery the child table if the parent table changes (ON UPDATE
        CASCADE in sql is set) When you attach a database, PySimpleSQL isn't aware of the relationships contained until
        tables are added and the relationship of various tables is set. This happens automatically during `Form`
        creation. Note that `Form.add_relationship()` can do this manually.

        :returns: None
        """
        logger.info(f'Automatically adding foreign key relationships')
        # Ensure we clear any current dataset so that successive calls will not double the entries
        self.relationships = [] # clear any relationships already stored
        relationships = self.driver.relationships()
        for r in relationships:
            logger.debug(f'Adding relationship {r["from_table"]}.{r["from_column"]} = {r["to_table"]}.{r["to_column"]}')
            self.add_relationship('LEFT JOIN', r['from_table'], r['from_column'], r['to_table'], r['to_column'],
                                  r['update_cascade'], r['delete_cascade'])

    # Map an element to a DataSet.
    # Optionally a where_column and a where_value.  This is useful for key,value pairs!
    def map_element(self, element: sg.Element, dataset: DataSet, column: str, where_column: str = None,
                    where_value: str = None) -> None:
        """
        Map a PySimpleGUI element to a specific `DataSet` column.  This is what makes the GUI automatically update to
        the contents of the database.  This happens automatically when a PySimpleGUI Window is bound to a `Form` by
        using the bind parameter of `Form` creation, or by executing `Form.auto_map_elements()` as long as the element
        metadata is configured properly. This method can be used to manually map any element to any `DataSet` column
        regardless of metadata configuration.

        :param element: A PySimpleGUI Element
        :param dataset: A `DataSet` object
        :param column: The name of the column to bind to the element
        :param where_column: Used for ke, value shorthand TODO: expand on this
        :param where_value: Used for ey, value shorthand TODO: expand on this
        :returns: None
        """
        logger.debug(f'Mapping element {element.key}')
        self.element_map.append(ElementMap(element, dataset, column, where_column, where_value))

    def auto_map_elements(self, win:sg.Window, keys:List[str]=None) -> None:
        """
        Automatically map PySimpleGUI Elements to `DataSet` columns. A special naming convention has to be used for
        automatic mapping to happen.  Note that `Form.map_element()` can be used to manually map an Element to a column.
        Automatic mapping relies on a special naming convention as well as certain data in the Element's metadata.
        The convenience functions `field()`, `selector()`, and `actions()` do this automatically and should be used in
        almost all cases to make elements that conform to this standard, but this information will allow you to do this
        manually if needed.
        For individual fields, Element keys must be named 'Table.column'. Additionally, the metadata must contain a dict
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
                data_key = element.metadata['data_key']
                field = element.metadata['field']
                if '?' in field:
                    table_info, where_info = field.split('?')
                else:
                    table_info = field
                    where_info = None
                try:
                    table, col = table_info.split('.')
                except ValueError:
                    table, col = table_info, None

                if where_info is None:
                    where_column=where_value=None
                else:
                    where_column,where_value=where_info.split('=')

                # make sure we don't use reserved keywords that could end up in a query
                for keyword in [table, col, where_column, where_value]:
                    if keyword is not None and keyword != '':
                        self.driver.check_keyword(keyword)

                # DataSet objects are named after the tables they represent (with an optional prefix)
                # TODO: How to handle the prefix?
                if table in self.datasets: # TODO: check in DataSet.table
                    if col in self[table].column_info:
                        # Map this element to DataSet.column
                        self.map_element(element, self[table], col, where_column, where_value)

            # Map Selector Element
            elif element.metadata['type']==TYPE_SELECTOR:
                k=element.metadata['table']
                if k is None: continue
                if element.metadata['Form'] != self: continue
                if '?' in k:
                    table_info, where_info = k.split('?')
                    where_column, where_value=where_info.split('=')
                else:
                    table_info = k
                    where_column = where_value = None
                data_key = table_info

                if data_key in self.datasets:
                    self[data_key].add_selector(element, data_key, where_column, where_value)

                    # Enable sorting if TableHeading  is present
                    if type(element) is sg.Table and 'TableHeading' in element.metadata:
                        table_heading:TableHeadings = element.metadata['TableHeading']
                        # We need a whole chain of things to happen when a heading is clicked on:
                        # 1 we need to run the ResultRow.sort_cycle() with the correct column name
                        # 2 and run TableHeading.update_headings() with the Table element, sort_column, sort_reverse
                        # 3 and run update_elements() to see the changes
                        table_heading.enable_sorting(element, _SortCallbackWrapper(self, data_key, element, table_heading))


                else:
                    logger.debug(f'Can not add selector {str(element)}')

    def set_element_clauses(self, element: sg.Element, where_clause: str = None, order_clause: str = None) -> None:
        """
        Set the where and/or order clauses for the specified element in the element map

        :param element: A PySimpleGUI Element
        :param where_clause: (optional) The where clause to set
        :param order_clause: (optional) The order clause to set
        :returns: None
        """
        for mapped in self.element_map:
            if mapped.element == element:
                mapped.where_clause = where_clause
                mapped.order_clause =order_clause

    def map_event(self, event:str, fctn:Callable[[None],None], table:str=None) -> None:
        """
        Manually map a PySimpleGUI event (returned by Window.read()) to a callable. The callable will execute
        when the event is detected by `Form.process_events()`. Most users will not have to manually map any events,
        as `Form.auto_map_events()` will create most needed events when a PySimpleGUI Window is bound to a `Form`
        by using the bind parameter of `Form` creation, or by executing `Form.auto_map_elements()`.

        :param event: The event to watch for, as returned by PySimpleGUI Window.read() (an element name for example)
        :param fctn: The callable to run when the event is detected. It should take no parameters and have no return value
        :param table: (optional) currently not used
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
        :param table: (optional) currently not used
        :returns: None
        """
        for e in self.event_map:
            if e['event'] == event:
                e['function'] = fctn
                e['table'] = table if table is not None else e['table']

    def auto_map_events(self, win:sg.Window) -> None:
        """
        Automatically map events. pysimplesql relies on certain events to function properly. This method maps all the
        record navigation (previous, next, etc.) and database actions (insert, delete, save, etc.).  Note that the event
        mapper is very general-purpose, and you can add your own event triggers to the mapper using
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
                event_type = element.metadata['event_type']
                table = element.metadata['table']
                column = element.metadata['column']
                function = element.metadata['function']
                funct = None

                data_key = table
                data_key = data_key if data_key in self.datasets else None
                if event_type==EVENT_FIRST:
                    if data_key: funct=self[data_key].first
                elif event_type==EVENT_PREVIOUS:
                    if data_key: funct=self[data_key].previous
                elif event_type==EVENT_NEXT:
                    if data_key: funct=self[data_key].next
                elif event_type==EVENT_LAST:
                    if data_key: funct=self[data_key].last
                elif event_type==EVENT_SAVE:
                    if data_key: funct=self[data_key].save_record
                elif event_type==EVENT_INSERT:
                    if data_key: funct=self[data_key].insert_record
                elif event_type==EVENT_DELETE:
                    if data_key: funct=self[data_key].delete_record
                elif event_type==EVENT_DUPLICATE:
                    if data_key: funct=self[data_key].duplicate_record
                elif event_type==EVENT_EDIT_PROTECT_DB:
                    self.edit_protect() # Enable it!
                    funct=self.edit_protect
                elif event_type==EVENT_SAVE_DB:
                    funct=self.save_records
                elif event_type==EVENT_SEARCH:
                    # Build the search box name
                    search_element,command=key.split(':')
                    search_box=f'{search_element}:search_input'
                    if data_key: funct=functools.partial(self[data_key].search, search_box)
                #elif event_type==EVENT_SEARCH_DB:
                elif event_type == EVENT_QUICK_EDIT:
                    referring_table = table
                    table = self[table].get_related_table_for_column(column)
                    funct = functools.partial(self[table].quick_editor, self[referring_table].get_current, column)
                elif event_type == EVENT_FUNCTION:
                    funct=function
                else:
                    logger.debug(f'Unsupported event_type: {event_type}')

                if funct is not None:
                    self.map_event(key, funct, data_key)


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

    def prompt_save(self, autosave:bool=False) -> PromptSaveValue:
        """
        Prompt to save if any GUI changes are found the affect any table on this form. The helps prevent data entry
        loss when performing an action that changes the current record of a `DataSet`.

        :param autosave: True to autosave when changes are found without prompting the user
        :returns: One of the prompt constant values: PROMPT_SAVE_PROCEED, PROMPT_SAVE_DISCARDED, PROMPT_SAVE_NONE
        """
        user_prompted = False # Has the user been prompted yet?
        for data_key in self.datasets:
            if self[data_key]._prompt_save is False:
                continue

            if self[data_key].records_changed(cascade=False): # don't check children
                # we will only show the popup once, regardless of how many dataset have changed
                if not user_prompted:
                    user_prompted = True
                    if autosave or self.autosave:
                        save_changes = 'yes'
                    else:
                        save_changes = self.popup.yes_no(lang.form_prompt_save_title, 
                                                         lang.form_prompt_save)
                    if save_changes != 'yes':
                        # update the elements to erase any GUI changes, since we are choosing not to save
                        for data_key in self.datasets:
                            self[data_key].rows.purge_virtual()
                        self.update_elements()
                        return PROMPT_SAVE_DISCARDED # We did have a change, regardless if the user chose not to save
                    break
        if user_prompted:
            self.save_records(check_prompt_save=True)
        return PROMPT_SAVE_PROCEED if user_prompted else PROMPT_SAVE_NONE

    def set_force_save(self, force:bool=False) -> None:
        """
        Force save without checking for changes first, so even an unchanged record will be written back to the database.

        :param force: True to force unchanged records to save.
        :returns: None
        """
        self.force_save = force

    def save_records(self, table: str = None, cascade_only: bool = False, check_prompt_save: bool = False, \
            update_elements: bool = True) -> Union[SAVE_SUCCESS,SAVE_FAIL,SAVE_NONE]:
        """
        Save records of all `DataSet` objects` associated with this `Form`.

        :param table: Name of table to save, as well as any cascaded relationships. Used in `DataSet.prompt_save()`
        :param cascade_only: Save only tables with cascaded relationships. Default False.
        :param check_prompt_save: Passed to `DataSet.save_cascade` to check if individual `DataSet` has prompt_save enabled.
                                  Used when `DataSet.save_records()` is called from `Form.prompt_save()`.
        :param update_elements: (optional) Passed to `Form.save_cascade()` to update_elements.
        :returns: result - can be used with RETURN BITMASKS
        """
        if check_prompt_save: logger.debug(f'Saving records in all datasets that allow prompt_save...')
        else: logger.debug(f'Saving records in all datasets...')

        result = 0
        show_message = True
        failed_tables = []
        
        if table: tables = [table] # if passed single table
        # for cascade_only, build list of top-level dataset that have children
        elif cascade_only: tables = [dataset.table for dataset in self.datasets.values()
                                     if len(Relationship.get_update_cascade_relationships(dataset.table))
                                     and Relationship.get_parent(dataset.table) is None]
        # default behavior, build list of top-level dataset (ones without a parent)
        else: tables = [dataset.table for dataset in self.datasets.values() if Relationship.get_parent(dataset.table) is None]
        
        # call save_cascade on tables, which saves from last to first.
        result_list = []
        for q in tables:
            res = self[q].save_cascade(results={},display_message=False,check_prompt_save=check_prompt_save, \
                                                update_elements=update_elements)
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
        msg_tables = ', '.join(failed_tables)
        if result & SAVE_FAIL:
            if result & SAVE_SUCCESS:
                msg = lang.form_save_partial
            msg += lang.form_save_problem.format_map(LangFormat(tables=msg_tables))
        elif result & SAVE_SUCCESS:
            msg = lang.form_save_success
        else:
            msg = lang.form_save_none
        if show_message: self.popup.info(msg)
        return result

    def set_prompt_save(self, value: bool) -> None:
        """
        Set the prompt to save action when navigating records for all `DataSet` objects associated with this `Form`

        :param value: a boolean value, True to prompt to save, False for no prompt to save
        :returns: None
        """
        for data_key in self.datasets:
            self[data_key].set_prompt_save(value)

    def update_elements(self, target_data_key: str = None, edit_protect_only: bool = False, omit_elements: List[str] = []) -> None:
        """
        Updated the GUI elements to reflect values from the database for this `Form` instance only
        Not to be confused with the main `update_elements()`, which updates GUI elements for all `Form` instances. This
        method also executes `update_selectors()`, which updates selector elements.

        :param target_data_key: (optional) dataset key to update elements for, otherwise updates elements for all datasets
        :param edit_protect_only: (optional) If true, only update items affected by edit_protect
        :param omit_elements: A list of elements to omit updating
        :returns: None
        """

        msg='edit protect' if edit_protect_only else 'PySimpleGUI'
        logger.debug(f'update_elements(): Updating {msg} elements')
        win = self.window
        # Disable/Enable action elements based on edit_protect or other situations

        for data_key in self.datasets:
            if target_data_key is not None and data_key != target_data_key:
                continue
            # disable mapped elements for this table if there are no records in this table or edit protect mode
            disable = len(self[data_key].rows) == 0 or self._edit_protect
            self.update_element_states(data_key, disable)
            
            for m in (m for m in self.event_map if m['table'] == self[data_key].table):
                # Disable delete and mapped elements for this table if there are no records in this table or edit protect mode
                if ':table_delete' in m['event']:
                    disable = len(self[data_key].rows) == 0 or self._edit_protect
                    win[m['event']].update(disabled=disable)

                # Disable duplicate if no rows, edit protect, or current row virtual
                if ':table_duplicate' in m['event']:
                    disable = len(self[data_key].rows) == 0 or self._edit_protect or self[data_key].get_current_row().virtual
                    win[m['event']].update(disabled=disable)
                    
                elif ':table_first' in m['event']:
                    disable = len(self[data_key].rows) < 2 or self[data_key].current_index == 0
                    win[m['event']].update(disabled=disable)
                
                elif ':table_previous' in m['event']:
                    disable = len(self[data_key].rows) < 2 or self[data_key].current_index == 0
                    win[m['event']].update(disabled=disable)
                    
                elif ':table_next' in m['event']:
                    disable = len(self[data_key].rows) < 2 or (self[data_key].current_index == len(self[data_key].rows) - 1)
                    win[m['event']].update(disabled=disable)
                    
                elif ':table_last' in m['event']:
                    disable = len(self[data_key].rows) < 2 or (self[data_key].current_index == len(self[data_key].rows) - 1)
                    win[m['event']].update(disabled=disable)

                # Disable insert on children with no parent records or edit protect mode
                parent = Relationship.get_parent(data_key)
                if parent is not None:
                    disable = len(self[parent].rows) == 0 or self._edit_protect
                else:
                    disable = self._edit_protect
                if ':table_insert' in m['event']:
                    if m['table'] == self[data_key].table:
                        win[m['event']].update(disabled=disable)

                # Disable db_save when needed
                disable = self._edit_protect
                if ':db_save' in m['event']:
                    win[m['event']].update(disabled=disable)

                # Disable table_save when needed
                disable = self._edit_protect
                if ':table_save' in m['event']:
                    win[m['event']].update(disabled=disable)

                # Enable/Disable quick edit buttons
                if ':quick_edit' in m['event']:
                    win[m['event']].update(disabled=disable)
        if edit_protect_only: return


        # Render GUI Elements
        # d= dictionary (the element map dictionary)
        for mapped in self.element_map:
            # If the optional target_data_key parameter was passed, we will only update elements bound to that table
            if target_data_key is not None:
                if mapped.table != self[target_data_key].table:
                    continue

            # skip updating this element if requested
            if mapped.element in omit_elements: continue

            if type(mapped.element) is not sg.Text: # don't show markers for sg.Text
                # Show the Required Record marker if the column has notnull set and this is a virtual row
                marker_key = mapped.element.key + ':marker'
                try:
                    if mapped.dataset.get_current_row().virtual:
                        # get the column name from the key
                        col = mapped.column
                        # get notnull from the column info
                        if col in mapped.dataset.column_info.names():
                            if mapped.dataset.column_info[col].notnull:
                                self.window[marker_key].update(visible=True, text_color = themepack.marker_required_color)
                    else:
                        self.window[marker_key].update(visible=False)
                        if self.window is not None:
                            self.window[marker_key].update(visible=False)
                except AttributeError:
                    self.window[marker_key].update(visible=False)


            updated_val = None
            # If there is a callback for this element, use it
            if mapped.element.key in self.callbacks:
                self.callbacks[mapped.element.key]()

            elif mapped.where_column is not None:
                # We are looking for a key,value pair or similar.  Sift through and see what to put
                updated_val=mapped.dataset.get_keyed_value(mapped.column, mapped.where_column, mapped.where_value)
                if type(mapped.element) in [sg.PySimpleGUI.CBox]: # TODO, may need to add more??
                    updated_val = checkbox_to_bool(updated_val)

            elif type(mapped.element) is sg.PySimpleGUI.Combo:
                # Update elements with foreign dataset first
                # This will basically only be things like comboboxes
                # TODO: move this to only compute if something else changes?
                # see if we can find the relationship to determine which table to get data from
                target_table=None
                rels = Relationship.get_relationships_for_table(mapped.dataset.table) # TODO this should be get_relationships_for_data?
                for rel in rels:
                    if rel.fk_column == mapped.column:
                        target_table = self[rel.parent_table]
                        pk_column = target_table.pk_column
                        description = target_table.description_column
                        break

                if target_table is None:
                    logger.info(f"Error! Could not find related data for element {mapped.element.key} bound to DataSet "
                                f"key {mapped.table}, column: {mapped.column}")

                    # we don't want to update the list in this case, as it was most likely supplied and not tied to data
                    updated_val=mapped.dataset[mapped.column]

                # Populate the combobox entries
                else:
                    lst = []
                    for row in target_table.rows:
                        lst.append(ElementRow(row[pk_column], row[description]))
    
                    # Map the value to the combobox, by getting the description_column and using it to set the value
                    for row in target_table.rows:
                        if row[target_table.pk_column] == mapped.dataset[rel.fk_column]:
                            for entry in lst:
                                if entry.get_pk() == mapped.dataset[rel.fk_column]:
                                    updated_val = entry
                                    break
                            break
                    mapped.element.update(values=lst)
            elif type(mapped.element) is sg.PySimpleGUI.Table:
                # Tables use an array of arrays for values.  Note that the headings can't be changed.
                values = mapped.dataset.table_values()
                # Select the current one
                pk = mapped.dataset.get_current_pk()

                found = False
                if len(values):
                    index = [[v[0] for v in values].index(pk)] # set index to pk
                    pk_position = index[0] / len(values)  # calculate pk percentage position
                    found = True
                else: # if empty
                    index = []
                    pk_position = 0

                # update element
                mapped.element.update(values=values, select_rows=index)
                # set vertical scroll bar to follow selected element
                if len(index): mapped.element.set_vscroll_position(pk_position)

                eat_events(self.window)
                continue

            elif type(mapped.element) in [sg.PySimpleGUI.InputText, sg.PySimpleGUI.Multiline, sg.PySimpleGUI.Text]:
                # Update the element in the GUI
                # For text objects, lets clear it first...
                mapped.element.update('')  # HACK for sqlite query not making needed keys! This will blank it out
                updated_val = mapped.dataset[mapped.column]

            elif type(mapped.element) is sg.PySimpleGUI.Checkbox:
                updated_val = checkbox_to_bool(mapped.dataset[mapped.column])
            elif type(mapped.element) is sg.PySimpleGUI.Image:
                val = mapped.dataset[mapped.column]

                try:
                    val = eval(val)
                except:
                    # treat it as a filename
                    mapped.element.update(val)
                else:
                    # update the bytes data
                    mapped.element.update(data=val)
                updated_val=None # Prevent the update from triggering below, since we are doing it here
            else:
                sg.popup(f'Unknown element type {type(mapped.element)}')

            # Finally, we will update the actual GUI element!
            if updated_val is not None:
                mapped.element.update(updated_val)

        self.update_selectors(target_data_key, omit_elements)

        # Run callbacks
        if 'update_elements' in self.callbacks.keys():
            # Running user update function
            logger.info('Running the update_elements callback...')
            self.callbacks['update_elements'](self, self.window)

    def update_selectors(self, target_data_key: str = None, omit_elements: List[str] = []) -> None:
        """
        Updated the GUI elements to reflect values from the database for this `Form` instance only
        Not to be confused with the main `update_elements()`, which updates GUI elements for all `Form` instances.

        :param target_data_key: (optional) dataset key to update elements for, otherwise updates elements for all datasets
        :param omit_elements: A list of elements to omit updating
        :returns: None
        """
        # ---------
        # SELECTORS
        # ---------
        # We can update the selector elements
        # We do it down here because it's not a mapped element...
        # Check for selector events
        for data_key, dataset in self.datasets.items():
            if target_data_key is not None:
                if target_data_key != data_key:
                    continue

            if len(dataset.selector):
                for e in dataset.selector:
                    logger.debug(f'update_elements: SELECTOR FOUND')
                    # skip updating this element if requested
                    if e['element'] in omit_elements: continue

                    element: sg.Element = e['element']
                    logger.debug(f'{type(element)}')
                    pk_column = dataset.pk_column
                    description_column = dataset.description_column
                    if element.key in self.callbacks:
                        self.callbacks[element.key]()

                    if type(element) == sg.PySimpleGUI.Listbox or type(element) == sg.PySimpleGUI.Combo:
                        logger.debug(f'update_elements: List/Combo selector found...')
                        lst = []
                        for r in dataset.rows:
                            if e['where_column'] is not None:
                                if str(r[e['where_column']]) == str(e[
                                                                        'where_value']):  # TODO: This is kind of a hackish way to check for equality...
                                    lst.append(ElementRow(r[pk_column], r[description_column]))
                                else:
                                    pass
                            else:
                                lst.append(ElementRow(r[pk_column], r[description_column]))

                        element.update(values=lst, set_to_index=dataset.current_index)

                        # set vertical scroll bar to follow selected element (for listboxes only)
                        if type(element) == sg.PySimpleGUI.Listbox:
                            try:
                                element.set_vscroll_position(dataset.current_index / len(lst))
                            except ZeroDivisionError:
                                element.set_vscroll_position(0)

                    elif type(element) == sg.PySimpleGUI.Slider:
                        # We need to re-range the element depending on the number of records
                        l = len(dataset.rows)
                        element.update(value=dataset._current_index + 1, range=(1, l))

                    elif type(element) is sg.PySimpleGUI.Table:
                        logger.debug(f'update_elements: Table selector found...')
                        # Populate entries
                        try:
                            columns = element.metadata['TableHeading'].columns()
                        except KeyError:
                            columns = None  # default to all columns

                        values = dataset.table_values(columns, mark_virtual=True)

                        # Get the primary key to select.  We have to use the list above instead of getting it directly
                        # from the table, as the data has yet to be updated
                        pk = dataset.get_current_pk()

                        found = False
                        if len(values):
                            index = [[v.pk for v in values].index(pk)]  # set to index by pk
                            pk_position = index[0] / len(values)  # calculate pk percentage position
                            found = True
                        else:  # if empty
                            index = []
                            pk_position = 0

                        logger.debug(f'Selector:: index:{index} found:{found}')
                        # update element
                        element.update(values=values, select_rows=index)
                        # set vertical scroll bar to follow selected element
                        element.set_vscroll_position(pk_position)

                        eat_events(self.window)

    def requery_all(self, select_first: bool = True, filtered: bool = True, update_elements: bool = True,
                    requery_cascade: bool = True) -> None:
        """
        Requeries all `DataSet` objects associated with this `Form`
        This effectively re-loads the data from the database into `DataSet` objects

        :param select_first: passed to `DataSet.requery()` -> `DataSet.first()`. If True, the first record will be
                             selected after the requery
        :param filtered: passed to `DataSet.requery()`. If True, the relationships will be considered and an appropriate
                        WHERE clause will be generated. False will display all records from the table.
        :param update_elements: passed to `DataSet.requery()` -> `DataSet.first()` to `Form.update_elements()`. Note
                       that the select_first parameter must = True to use this parameter.
        :param requery_cascade: passed to `DataSet.requery()` -> `DataSet.first()` to `Form.requery_cascade()`.
                                   Note that the select_first parameter must = True to use this parameter.
        :returns: None
        """
        # TODO: It would make sense to reorder these, and put filtered first, then select_first/update/dependents
        logger.info('Requerying all datasets')
        for data_key in self.datasets:
            if Relationship.get_parent(data_key) is None:
                self[data_key].requery(select_first=select_first, filtered=filtered, update_elements=update_elements,
                                       requery_cascade=requery_cascade)

    def process_events(self, event: str, values: list) -> bool:
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
            for data_key, dataset in self.datasets.items():
                if len(dataset.selector):
                    for e in dataset.selector:
                        element:sg.Element = e['element']
                        if element.key == event and len(dataset.rows) > 0:
                            changed = False  # assume that a change will not take place
                            if type(element) == sg.PySimpleGUI.Listbox:
                                row = values[element.Key][0]
                                dataset.set_by_pk(row.get_pk())
                                changed = True
                            elif type(element) == sg.PySimpleGUI.Slider:
                                dataset.set_by_index(int(values[event]) - 1)
                                changed = True
                            elif type(element) == sg.PySimpleGUI.Combo:
                                row = values[event]
                                dataset.set_by_pk(row.get_pk())
                                changed = True
                            elif type(element) is sg.PySimpleGUI.Table:
                                index = values[event][0]
                                pk = self.window[event].Values[index].pk
                                dataset.set_by_pk(pk, True, omit_elements=[element])  # no need to update the selector!
                                changed = True
                            if changed:
                                if 'record_changed' in dataset.callbacks.keys():
                                    dataset.callbacks['record_changed'](self, self.window)
                            return changed
        return False

    def update_element_states(self, table: str, disable: bool = None, visible: bool = None) -> None:
        """
        Disable/enable and/or show/hide all elements associated with a table.

        :param table: table name associated with elements to disable/enable
        :param disable: True/False to disable/enable element(s), None for no change
        :param visible: True/False to make elements visible or not, None for no change
        :returns: None
        """
        for mapped in self.element_map:
            if mapped.table != table:
                continue
            element = mapped.element
            if type(element) in [sg.PySimpleGUI.InputText, sg.PySimpleGUI.MLine, sg.PySimpleGUI.Combo,
                                 sg.PySimpleGUI.Checkbox]:
                # if element.Key in self.window.key_dict.keys():
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
class Utility:
    """
    Utility functions are a collection of functions and classes that directly improve on aspects of the pysimplesql
    module.

    See the documentation for the following utility functions:
    `process_events()`, `update_elements()`, `bind()`, `simple_transform()`, `KeyGen()`,

    Note: This is a dummy class that exists purely to enhance documentation and has no use to the end user.
    """
    pass


def process_events(event: str, values: list) -> bool:
    """
        Process mapped events for ALL Form instances.

        Not to be confused with `Form.process_events()`, which processes events for individual `Form` instances.
        This should be called once per iteration in your event loop
        Note: Events handled are responsible for requerying and updating elements as needed

        :param event: The event returned by PySimpleGUI.read()
        :param values: the values returned by PySimpleGUI.read()
        :returns: True if an event was handled, False otherwise
        """
    handled = False
    for i in Form.instances:
        if i.process_events(event, values): handled=True
    return handled


def update_elements(data_key: str = None, edit_protect_only: bool = False) -> None:
    """
    Updated the GUI elements to reflect values from the database for ALL Form instances
    Not to be confused with `Form.update_elements()`, which updates GUI elements for individual `Form` instances.

    :param data_key: (optional) key of `DataSet` to update elements for, otherwise updates elements for all datasets
    :param edit_protect_only: (optional) If true, only update items affected by edit_protect
    :returns: None
    """
    for i in Form.instances:
        i.update_elements(data_key, edit_protect_only)

def bind(win: sg.Window) -> None:
    """
    Bind ALL forms to window
    Not to be confused with `Form.bind()`, which binds specific forms to the window.
    
    :param win: The PySimpleGUI window to bind all forms to
    :returns: None
    """
    for i in Form.instances:
        i.bind(win)

def simple_transform(dataset:DataSet, row, encode):
    """
    Convenience transform function that makes it easier to add transforms to your records.
    """
    for col, function in dataset._simple_transform.items():
        if col in row:
            msg = f'Transforming {col} from {row[col]}'
            if encode == TFORM_DECODE:
                row[col] = function['decode'](row, col)
            else:
                row[col] = function['encode'](row, col)
            logger.debug(f'{msg} to {row[col]}')

def eat_events(win:sg.Window) -> None:
    """
    Eat extra events emitted by PySimpleGUI.DataSet.update().

    Call this function directly after update() is run on a DataSet element. The reason is that updating the selection or values
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

def checkbox_to_bool(value):
    """
    Allows a variety of checkbox values to still return True or False.
    :param value: Value to convert into True or False
    :returns: bool
    """
    return str(value).lower() in ['y','yes','t','true','1']

class Popup:
    """
    Popup helper class. Has popup functions for internal use. Stores last info popup as last_info
    """
    def __init__(self):
        """
        Create a new Popup instance
        :returns: None
        """
        self.last_info = None
        self.popup_info = None

    def ok(self, title, msg):
        """
        Internal use only. Creates sg.Window with LanguagePack OK button
        """
        msg = msg.splitlines()
        layout = [[sg.T(line, font='bold')] for line in msg]
        layout.append(sg.Button(button_text = lang.button_ok, key = 'ok',
                                use_ttk_buttons = themepack.use_ttk_buttons,
                                pad = themepack.popup_button_pad))
        popup_win = sg.Window(title, layout= [layout], keep_on_top = True, modal = True, finalize = True,
                              ttk_theme = themepack.ttk_theme, element_justification = "center")

        while True:
            event, values = popup_win.read()
            if event in [sg.WIN_CLOSED,'Exit','ok']:
                break
        popup_win.close()

    def yes_no(self, title, msg):
        """
        Internal use only. Creates sg.Window with LanguagePack Yes/No button
        """
        msg = msg.splitlines()
        layout = [[sg.T(line, font='bold')] for line in msg]
        layout.append(sg.Button(button_text = lang.button_yes, key = 'yes',
                                use_ttk_buttons = themepack.use_ttk_buttons,
                                pad = themepack.popup_button_pad))
        layout.append(sg.Button(button_text = lang.button_no, key = 'no',
                                use_ttk_buttons = themepack.use_ttk_buttons,
                                pad = themepack.popup_button_pad))
        popup_win = sg.Window(title, layout= [layout], keep_on_top = True, modal = True, finalize = True,
                              ttk_theme = themepack.ttk_theme, element_justification = "center")
        
        while True:
            event, values = popup_win.read()
            if event in [sg.WIN_CLOSED,'Exit','no','yes']:
                result = event
                break
        popup_win.close()
        return result

    def info(self, msg: str, display_message: bool = True, auto_close_seconds: int = None):
        """
        Creates sg.Window with no buttons to display passed in message string, and writes message to
        to self.last_info.
        Uses title as defined in lang.info_popup_title.
        By default auto-closes in seconds as defined in themepack.popup_info_auto_close_seconds
        :param msg: String to display as message
        :param display_message: (optional) By default True. False only writes [title,msg] to self.last_info
        :param auto_close_seconds: (optional) Gets value from themepack.info_popup_auto_close_seconds by default.
        :returns: None
        """
        """
        Internal use only. Creates sg.Window with no buttons, auto-closing after seconds as defined in themepack
        """
        title = lang.info_popup_title
        if auto_close_seconds is None:
            auto_close_seconds = themepack.popup_info_auto_close_seconds
        self.last_info = [title,msg]
        if display_message:
            msg = msg.splitlines()
            layout = [sg.T(line, font='bold') for line in msg]
            self.popup_info = sg.Window(title = title, layout = [layout], no_titlebar = False,
                                  keep_on_top = True, finalize = True, 
                                  alpha_channel = themepack.popup_info_alpha_channel,
                                  element_justification = "center", ttk_theme = themepack.ttk_theme)
            threading.Thread(target=self.auto_close,
                             args=(self.popup_info, auto_close_seconds),
                             daemon=True).start()
        
    def get_last_info(self) -> List[str]:
        """
        Get last info popup. Useful for integrating into a status bar.
        :returns: a single list of [type,title, msg]
        """
        return self.last_info
    
    def auto_close(self, window: sg.Window, seconds: int):
        """
        Use in a thread to automatically close the passed in sg.Window.
        :param window: sg.Window object to close
        :param seconds: Seconds to keep window open
        :returns: None
        """
        step = 1
        while step <= seconds:
            sleep(1)
            step += 1
        self.close(window)
    
    def close(self, window):
        window.close()

class ProgressBar:
    def __init__(self, title: str, max_value: int = 100):
        layout = [
            [sg.Text('', key='message', size=(31, 1))],
            [sg.ProgressBar(max_value, orientation='h', size=(30, 20), key='bar', style=themepack.ttk_theme)]
        ]

        self.title = title
        self.max = max
        self.win = sg.Window(title, layout=layout, keep_on_top=True, finalize=True, ttk_theme=themepack.ttk_theme)

    def update(self, message: str, current_count: int):
        self.win['message'].update(message)
        self.win['bar'].update(current_count=current_count)

    def close(self):
        self.win.close()

class LangFormat(dict):
    def __missing__(self, key):
        return None

class KeyGen:
    """
    The keygen system provides a mechanism to generate unique keys for use as PySimpleGUI element keys.
    This is needed because many auto-generated items will have the same name.  If for example you had two save buttons on
    the screen at the same time, they must have unique names.  The keygen will append a separator and an incremental number
    to keys that would otherwise be duplicates. A global KeyGen instance is created automatically, see `keygen` for info.
    """
    def __init__(self, separator='!'):
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
                    returned unmodified.  For each successive call with the same key, it will be appended with the
                    separator character and an incremental number.  For example, if the key 'button' was passed to
                    `KeyGen.get()` 3 times in a row, then the keys 'button', 'button:1', and 'button:2' would be
                    returned respectively.
        :param separator: (optional) override the default separator wth this separator
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
        for mapped in frm.element_map:
            self.reset_key(mapped.element.key)

# create a global KeyGen instance
keygen = KeyGen(separator=':')
"""This is a global keygen instance for general purpose use. See `KeyGen` for more info"""

# Convenience dicts for example database connection
postgres_examples = {
    'host': 'tommy2.heliohost.org',
    'user': 'pysimplesql_user',
    'password': 'pysimplesql',
    'database': 'pysimplesql_examples'
}

mysql_examples = {
    'host': 'tommy2.heliohost.org',
    'user': 'pysimplesql_user',
    'password': 'pysimplesql',
    'database': 'pysimplesql_examples'
}


# ----------------------------------------------------------------------------------------------------------------------
# CONVENIENCE FUNCTIONS
# ----------------------------------------------------------------------------------------------------------------------
# Convenience functions aide in building PySimpleGUI interfaces that work well with pysimplesql.
# TODO: How to save Form in metadata?  Perhaps give forms names and reference them that way??
#       For example - give forms names!  and reference them by name string
#       They could even be converted later to a real form during form creation?

# This is a dummy class for documenting convenience functions
class Convenience:
    """
    Convenience functions are a collection of functions and classes that aide in building PySimpleGUI layouts that
    conform to pysimplesql standards so that your database application is up and running quickly, and with all the great
    automatic functionality pysimplesql has to offer.
    See the documentation for the following convenience functions:
    `field()`, `selector()`, `actions()`, `TableHeadings`

    Note: This is a dummy class that exists purely to enhance documentation and has no use to the end user.
    """
    pass




def field(field: str, element: Type[sg.Element] = sg.I, size: Tuple[int, int] = None, label: str = '',
          no_label: bool = False, label_above: bool = False, quick_editor: bool = True, filter=None, key=None,
          use_ttk_buttons = None, pad = None, **kwargs) -> sg.Column:
    """
    Convenience function for adding PySimpleGUI elements to the Window, so they are properly configured for pysimplesql
    The automatic functionality of pysimplesql relies on accompanying metadata so that the `Form.auto_add_elements()`
    can pick them up. This convenience function will create a text label, along with an element with the above metadata
    already set up for you.
    Note: The element key will default to the record name if none is supplied.
    See `set_label_size()`, `set_element_size()` and `set_mline_size()` for setting default sizes of these elements.

    :param field: The database record in the form of table.column I.e. 'Journal.entry'
    :param element: (optional) The element type desired (defaults to PySimpleGUI.Input)
    :param size: Overrides the default element size that was set with `set_element_size()` for this element only
    :param label: The text/label will automatically be generated from the column name. If a different text/label is
                 desired, it can be specified here.
    :param no_label: Do not automatically generate a label for this element
    :param label_above: Place the label above the element instead of to the left of the element
    :param quick_editor: For records that reference another table, place a quick edit button next to the element
    :param filter: Can be used to reference different `Form`s in the same layout.  Use a matching filter when creating
            the `Form` with the filter parameter.
    :param key: (optional) The key to give this element. See note above about the default auto generated key
    :param kwargs: Any additional arguments will be passed on to the PySimpleGUI element.
    :returns: Element(s) to be used in the creation of PySimpleGUI layouts.  Note that this function actually creates
              multiple Elements wrapped in a PySimpleGUI Column, but can be treated as a single Element.
    """
    # TODO: See what the metadata does after initial setup is complete - is it needed anymore?
    global keygen
    
    if use_ttk_buttons is None:
        use_ttk_buttons = themepack.use_ttk_buttons
    if pad is None:
        pad = themepack.quick_editor_button_pad

    # Does this record imply a where clause (indicated by ?) If so, we can strip out the information we need
    if '?' in field:
        table_info, where_info = field.split('?')
        label_text = where_info.split('=')[1].replace('fk', '').replace('_', ' ').capitalize() + ':'
    else:
        table_info = field
        label_text = table_info.split('.')[1].replace('fk', '').replace('_', ' ').capitalize() + ':'
    table, column = table_info.split('.')

    key = field if key is None else key
    key = keygen.get(key)


    if 'values' in kwargs:
        first_param=kwargs['values']
        del kwargs['values']  # make sure we don't put it in twice
    else:
        first_param=''

    if element.__name__ == 'Multiline':
        layout_element = element(first_param, key=key, size=size or themepack.default_mline_size, metadata={'type': TYPE_RECORD, 'Form': None, 'filter': filter, 'field': field, 'data_key': key}, **kwargs)
    else:
        layout_element = element(first_param, key=key, size=size or themepack.default_element_size, metadata={'type': TYPE_RECORD, 'Form': None, 'filter': filter, 'field': field, 'data_key': key}, **kwargs)
    layout_label =  sg.T(label_text if label == '' else label, size=themepack.default_label_size, key=f'{key}:label')
    layout_marker = sg.Column([[sg.T(themepack.marker_required, key=f'{key}:marker', text_color=sg.theme_background_color(), visible=True)]], pad=(0, 0)) # Marker for required (notnull) records
    if element.__name__ == 'Text': # don't show markers for sg.Text
        if no_label:
            layout = [[layout_element]]
        elif label_above:
            layout = [[layout_label], [layout_element]]
        else:
            layout = [[layout_label , layout_element]]
    else:        
        if no_label:
            layout = [[layout_marker, layout_element]]
        elif label_above:
            layout = [[layout_label], [layout_marker, layout_element]]
        else:
            layout = [[layout_label , layout_marker, layout_element]]
    # Add the quick editor button where appropriate
    if element == sg.Combo and quick_editor:
        meta = {'type': TYPE_EVENT, 'event_type': EVENT_QUICK_EDIT, 'table': table, 'column': column, 'function': None, 'Form': None, 'filter': filter}
        if type(themepack.quick_edit) is bytes:
            layout[-1].append(sg.B('', key=keygen.get(f'{key}.quick_edit'), size=(1, 1), image_data=themepack.quick_edit, metadata=meta,
                                   use_ttk_buttons = use_ttk_buttons, pad = pad))
        else:
            layout[-1].append(sg.B(themepack.quick_edit, key=keygen.get(f'{key}.quick_edit'), metadata=meta, use_ttk_buttons = use_ttk_buttons, pad = pad))
    #return layout
    return sg.Col(layout=layout, pad=(0,0)) # TODO: Does this actually need wrapped in a sg.Col???

def actions(table: str, key=None, default: bool = True, edit_protect: bool = None, navigation: bool = None,
            insert: bool = None, delete: bool = None, duplicate: bool = None, save: bool = None, search: bool = None,
            search_size: Tuple[int, int] = (30, 1), bind_return_key: bool = True, filter: str = None,
            use_ttk_buttons: bool = None, pad = None, **kwargs) -> sg.Column:
    """
    Allows for easily adding record navigation and record action elements to the PySimpleGUI window
    The navigation elements are generated automatically (first, previous, next, last and search).  The action elements
    can be customized by selecting which ones you want generated from the parameters available.  This allows full
    control over what is available to the user of your database application. Check out `ThemePacks` to give any of these
    autogenerated controls a custom look!

    Note: By default, the base element keys generated for PySimpleGUI will be table!action using the name of the table
    passed in the table parameter plus the action strings below separated by a colon: (I.e. Journal:table_insert)
    edit_protect, db_save, table_first, table_previous, table_next, table_last, table_duplicate, table_insert,
    table_delete, search_input, search_button.
    If you supply a key with the key parameter, then these additional strings will be appended to that key. Also note
    that these autogenerated keys also pass through the `KeyGen`, so it's possible that these keys could be
    selector:table_last!1, selector:table_last!2, etc.

    :param table: The table name that this "element" will provide actions for
    :param key: (optional) The base key to give the generated elements
    :param default: Default edit_protect, navigation, insert, delete, save and search to either true or false (defaults
                    to True) The individual keyword arguments will trump the default parameter.  This allows for
                    starting with all actions defualting to False, then individual ones can be enabled with True - or
                    the opposite by defaulting them all to True, and disabling the ones not needed with False.
    :param edit_protect: An edit protection mode to prevent accidental changes in the database. It is a button that
                    toggles the ability on and off to prevent accidental changes in the database by enabling/disabling
                    the insert, edit, duplicate, delete and save buttons.
    :param navigation: The standard << < > >> (First, previous, next, last) buttons for navigation
    :param insert: Button to insert new records
    :param delete: Button to delete current record
    :param duplicate: Button to duplicate current record
    :param save: Button to save record.  Note that the save button feature saves changes made to any table, therefore
                 only one save button is needed per window.
    :param search: A search Input element. Size can be specified with the `search_size` parameter
    :param search_size: The size of the search input element
    :param bind_return_key: Bind the return key to the search button. Defaults to true
    :param filter: Can be used to reference different `Form`s in the same layout.  Use a matching filter when creating
            the `Form` with the filter parameter.
    :returns: An element to be used in the creation of PySimpleGUI layouts.  Note that this is technically multiple
              elements wrapped in a PySimpleGUI.Column, but acts as one element for the purpose of layout building.
    """
    global keygen
    global themepack
    
    if use_ttk_buttons is None:
        use_ttk_buttons = themepack.use_ttk_buttons
    if pad is None:
        pad = themepack.action_button_pad

    edit_protect = default if edit_protect is None else edit_protect
    navigation = default if navigation is None else navigation
    insert = default if insert is None else insert
    delete = default if delete is None else delete
    duplicate = default if duplicate is None else duplicate
    save = default if save is None else save
    search = default if search is None else search
    key = f'{table}:' if key is None else f'{key}:'

    layout = []

    # Form-level events
    if edit_protect:
        meta = {'type': TYPE_EVENT, 'event_type': EVENT_EDIT_PROTECT_DB, 'table': None, 'column': None, 'function': None, 'Form': None, 'filter': filter}
        if type(themepack.edit_protect) is bytes:
            layout.append(sg.B('', key=keygen.get(f'{key}edit_protect'), size=(1, 1), image_data=themepack.edit_protect, metadata=meta, use_ttk_buttons = use_ttk_buttons, pad = pad, **kwargs))
        else:
            layout.append(sg.B(themepack.edit_protect, key=keygen.get(f'{key}edit_protect'), metadata=meta, use_ttk_buttons = use_ttk_buttons, pad = pad, **kwargs))
    if save:
        meta = {'type': TYPE_EVENT, 'event_type': EVENT_SAVE_DB, 'table': None, 'column': None, 'function': None, 'Form': None, 'filter': filter}
        if type(themepack.save) is bytes:
            layout.append(sg.B('', key=keygen.get(f'{key}db_save'), image_data=themepack.save, metadata=meta, use_ttk_buttons = use_ttk_buttons, pad = pad, **kwargs))
        else:
            layout.append(sg.B(themepack.save, key=keygen.get(f'{key}db_save'), metadata=meta))

    # DataSet-level events
    if navigation:
        # first
        meta = {'type': TYPE_EVENT, 'event_type': EVENT_FIRST, 'table': table, 'column': None, 'function': None, 'Form': None, 'filter': filter}
        if type(themepack.first) is bytes:
            layout.append(sg.B('', key=keygen.get(f'{key}table_first'), size=(1, 1), image_data=themepack.first, metadata=meta, use_ttk_buttons = use_ttk_buttons, pad = pad, **kwargs))
        else:
            layout.append(sg.B(themepack.first, key=keygen.get(f'{key}table_first'), metadata=meta, use_ttk_buttons = use_ttk_buttons, pad = pad, **kwargs))
        # previous
        meta = {'type': TYPE_EVENT, 'event_type': EVENT_PREVIOUS, 'table': table, 'column': None, 'function': None, 'Form': None, 'filter': filter}
        if type(themepack.previous) is bytes:
            layout.append(sg.B('', key=keygen.get(f'{key}table_previous'), size=(1, 1), image_data=themepack.previous, metadata=meta, use_ttk_buttons = use_ttk_buttons, pad = pad, **kwargs))
        else:
            layout.append(sg.B(themepack.previous, key=keygen.get(f'{key}table_previous'), metadata=meta, use_ttk_buttons = use_ttk_buttons, pad = pad, **kwargs))
        # next
        meta = {'type': TYPE_EVENT, 'event_type': EVENT_NEXT, 'table': table, 'column': None, 'function': None, 'Form': None, 'filter': filter}
        if type(themepack.next) is bytes:
            layout.append(sg.B('', key=keygen.get(f'{key}table_next'), size=(1, 1), image_data=themepack.next, metadata=meta, use_ttk_buttons = use_ttk_buttons, pad = pad, **kwargs))
        else:
            layout.append(sg.B(themepack.next, key=keygen.get(f'{key}table_next'), metadata=meta, use_ttk_buttons = use_ttk_buttons, pad = pad, **kwargs))
        # last
        meta = {'type': TYPE_EVENT, 'event_type': EVENT_LAST, 'table': table, 'column': None, 'function': None, 'Form': None, 'filter': filter}
        if type(themepack.last) is bytes:
            layout.append(sg.B('', key=keygen.get(f'{key}table_last'), size=(1, 1), image_data=themepack.last, metadata=meta, use_ttk_buttons = use_ttk_buttons, pad = pad, **kwargs))
        else:
            layout.append(sg.B(themepack.last, key=keygen.get(f'{key}table_last'), metadata=meta, use_ttk_buttons = use_ttk_buttons, pad = pad, **kwargs))
    if duplicate:
        meta = {'type': TYPE_EVENT, 'event_type': EVENT_DUPLICATE, 'table': table, 'column': None, 'function': None, 'Form': None, 'filter': filter}
        if type(themepack.duplicate) is bytes:
            layout.append(sg.B('', key=keygen.get(f'{key}table_duplicate'), size=(1, 1), image_data=themepack.duplicate, metadata=meta, use_ttk_buttons = use_ttk_buttons, pad = pad, **kwargs))
        else:
            layout.append(
                sg.B(themepack.duplicate, key=keygen.get(f'{key}table_duplicate'), metadata=meta, use_ttk_buttons = use_ttk_buttons, pad = pad, **kwargs))
    if insert:
        meta = {'type': TYPE_EVENT, 'event_type': EVENT_INSERT, 'table': table, 'column': None, 'function': None, 'Form': None, 'filter': filter}
        if type(themepack.insert) is bytes:
            layout.append(sg.B('', key=keygen.get(f'{key}table_insert'), size=(1, 1), image_data=themepack.insert, metadata=meta, use_ttk_buttons = use_ttk_buttons, pad = pad, **kwargs))
        else:
            layout.append(sg.B(themepack.insert, key=keygen.get(f'{key}table_insert'), metadata=meta, use_ttk_buttons = use_ttk_buttons, pad = pad, **kwargs))
    if delete:
        meta = {'type': TYPE_EVENT, 'event_type': EVENT_DELETE, 'table': table, 'column': None, 'function': None, 'Form': None, 'filter': filter}
        if type(themepack.delete) is bytes:
            layout.append(sg.B('', key=keygen.get(f'{key}table_delete'), size=(1, 1), image_data=themepack.delete, metadata=meta, use_ttk_buttons = use_ttk_buttons, pad = pad, **kwargs))
        else:
            layout.append(sg.B(themepack.delete, key=keygen.get(f'{key}table_delete'), metadata=meta, use_ttk_buttons = use_ttk_buttons, pad = pad, **kwargs))
    if search:
        meta = {'type': TYPE_EVENT, 'event_type': EVENT_SEARCH, 'table': table, 'column': None, 'function': None, 'Form': None, 'filter': filter}
        if type(themepack.search) is bytes:
            layout+=[sg.Input('', key=keygen.get(f'{key}search_input'), size=search_size),sg.B('', key=keygen.get(f'{key}search_button'),
                                                                                               bind_return_key=bind_return_key, size=(1, 1),
                                                                                               image_data=themepack.delete, metadata=meta, use_ttk_buttons = use_ttk_buttons, pad = pad, **kwargs)]
        else:
            layout+=[sg.Input('', key=keygen.get(f'{key}search_input'), size=search_size),sg.B(themepack.search, key=keygen.get(f'{key}search_button'),
                                                                                               bind_return_key=bind_return_key, metadata=meta, use_ttk_buttons = use_ttk_buttons, pad = pad, **kwargs)]
    return sg.Col(layout=[layout], pad=(0,0))



def selector(table: str, element: Type[sg.Element] = sg.LBox, size: Tuple[int, int] = None, filter: str = None,
             key: str = None, **kwargs) -> sg.Element:
    """
    Selectors in pysimplesql are special elements that allow the user to change records in the database application.
    For example, Listboxes, Comboboxes and Tables all provide a convenient way to users to choose which record they
    want to select. This convenience function makes creating selectors very quick and as easy as using a normal
    PySimpleGUI element.

    :param table: The table name in the database that this selector will act on
    :param element: The type of element you would like to use as a selector (defaults to a Listbox)
    :param size: The desired size of this selector element
    :param filter: Can be used to reference different `Form`s in the same layout.  Use a matching filter when creating
                   the `Form` with the filter parameter.
    :param key: (optional) The key to give to this selector. If no key is provided, it will default to table:selector
                using the table specified in the table parameter. This is also passed through the keygen, so if
                selectors all use the default name, they will be made unique. I.e. Journal:selector!1, Journal:selector!2, etc.
    :param kwargs: Any additional arguments supplied will be passed on to the PySimpleGUI element

    """
    global keygen

    key = f'{table}:selector' if key is None else key
    key=keygen.get(key)

    meta = {'type': TYPE_SELECTOR, 'table': table, 'Form': None, 'filter': filter}
    if element == sg.Listbox:
        layout = element(values=(), size=size or themepack.default_element_size, key=key,
                    select_mode=sg.LISTBOX_SELECT_MODE_SINGLE,
                    enable_events=True, metadata=meta)
    elif element == sg.Slider:
        layout = element(enable_events=True, size=size or themepack.default_element_size, orientation='h',
                          disable_number_display=True, key=key, metadata=meta)
    elif element == sg.Combo:
        w = themepack.default_element_size[0]
        layout = element(values=(), size=size or (w, 10), readonly=True, enable_events=True, key=key,
                          auto_size_text=False, metadata=meta)
    elif element == sg.Table:
        # Check if the headings arg is a Table heading...
        if kwargs['headings'].__class__.__name__ == 'TableHeadings':
            # Overwrite the kwargs from the TableHeading info
            kwargs['visible_column_map'] = kwargs['headings'].visible_map()
            kwargs['col_widths'] = kwargs['headings'].width_map()
            kwargs['auto_size_columns'] = False  # let the col_widths handle it
            # Store the TableHeadings object in metadata to complete setup on auto_add_elements()
            meta['TableHeading'] = kwargs['headings']
        else:
            required_kwargs = ['headings', 'visible_column_map', 'num_rows']
            for kwarg in required_kwargs:
                if kwarg not in kwargs:
                    raise RuntimeError(f'DataSet selectors must use the {kwarg} keyword argument.')

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
        vals = [[''] * len(kwargs['headings'])]

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

    def add_column(self, column: str, heading_column: str, width: int, visible: bool = True) -> None:
        """
        Add a new heading column to this TableHeading object.  Columns are added in the order that this method is called.
        Note that the primary key column does not need to be included, as primary keys are stored internally in the
        `TableRow` class.

        :param heading_column: The name of this columns heading (title)
        :param column: The name of the column in the database the heading column is for
        :param width: The width for this column to display within the Table element
        :param visible: True if the column is visible.  Typically, the only hidden column would be the primary key column
                        if any. This is also useful if the `DataSet.rows` `ResultSet` has some information that you don't
                        want to display.
        :returns: None
        """
        self.append({'heading': heading_column, 'column': column})
        self._width_map.append(width)
        self._visible_map.append(visible)

    def heading_names(self) -> List[str]:
        """
        Return a list of heading_names for use with the headings parameter of PySimpleGUI.Table

        :returns: a list of heading names
        """
        return [c['heading'] for c in self]

    def columns(self):
        """
        Return a list of column names

        :returns: a list of column names
        """
        return [c['column'] for c in self if c['column'] is not None]


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
        global themepack

        # Load in our marker characters.  We will use them to both display the sort direction and to detect current direction
        try:
            asc = themepack.sort_asc_marker
        except AttributeError:
            asc = '\u25BC'
        try:
            desc = themepack.sort_desc_marker
        except AttributeError:
            desc = '\u25B2'

        for i, x in zip(range(len(self)), self):
            # Clear the direction markers
            x['heading'] = x['heading'].replace(asc, '').replace(desc, '')
            if x['column'] == sort_column and sort_column is not None:
                if sort_order != ResultSet.SORT_NONE:
                    x['heading'] += asc if sort_order == ResultSet.SORT_ASC else desc
            element.Widget.heading(i, text=x['heading'], anchor='w')


    def enable_sorting(self, element:sg.Table, fn:callable) -> None:
        """
        Enable the sorting callbacks for each column index
        Note: Not typically used by the end user. Called from `Form.auto_map_elements()`

        :param element: The PySimpleGUI Table element associated with this TableHeading
        :param fn: A callback functions to run when a heading is clicked. The callback should take one column parameter.
        :returns: None
        """
        if self._sort_enable:
            for i in range(len(self)):
                if self[i]['column'] is not None:
                    element.widget.heading(i, command=functools.partial(fn, self[i]['column']))
        self.update_headings(element)

    def insert(self, idx, heading_column:str, column:str=None, *args, **kwargs):
        super().insert(idx,{'heading': heading_column, 'column': column})

class _SortCallbackWrapper:
    """
    Internal class used when sg.Table column headers are clicked.
    """
    
    def __init__(self,frm_reference: Form, data_key: str, element: sg.Element, table_heading):
        """
        Create a new _SortCallbackWrapper object

        :param frm_reference: `Form` object
        :param data_key: `DataSet` key
        :param element: PySimpleGUI sg.Table element
        :param table_heading: `TableHeading` object
        :returns: None
        """
        self.frm: Form = frm_reference
        self.data_key = data_key
        self.element = element
        self.table_heading:TableHeadings = table_heading
    
    def __call__(self, column):
        # store the pk:
        pk = self.frm[self.data_key].get_current_pk()
        sort_order = self.frm[self.data_key].rows.sort_cycle(column, self.data_key)
        # We only need to update the selectors not all elements, so first set by the primary key,
        # then update_selectors()
        self.frm[self.data_key].set_by_pk(pk, update_elements=False, requery_cascade=False,
                                 skip_prompt_save=True)
        self.frm.update_selectors(self.data_key)
        self.table_heading.update_headings(self.element, column, sort_order)

# ======================================================================================================================
# THEMEPACKS
# ======================================================================================================================
# Change the look and feel of your database application all in one place.
class ThemePack:
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
        # Theme to use with ttk widgets.
        #-------------------------------
        # Choices (on Windows) include:
        # 'default', 'winnative', 'clam', 'alt', 'classic', 'vista', 'xpnative'
        'ttk_theme': 'default',
        
        # Defaults for actions() buttons & popups
        #----------------------------------------
        'use_ttk_buttons' : True,
        'quick_editor_button_pad' : (3,0),
        'action_button_pad' : (3,0),
        'popup_button_pad' : (5,5),
        
        # Action buttons
        #----------------------------------------
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
        
        # Markers
        #----------------------------------------
        'marker_virtual': '\u2731',
        'marker_required': '\u2731',
        'marker_required_color': 'red2',
        
        # Sorting icons
        #----------------------------------------
        'sort_asc_marker': '\u25BC',
        'sort_desc_marker': '\u25B2',
        
        # Info Popup defaults
        #----------------------------------------
        'popup_info_auto_close_seconds' : 1,
        'popup_info_alpha_channel' : .85,

        # Default sizes for elements
        #---------------------------
        # Label Size
        # Sets the default label (text) size when `field()` is used.
        # A label is static text that is displayed near the element to describe what it is.
        'default_label_size' : (20, 1), # (width, height)

        # Element Size
        # Sets the default element size when `field()` is used.
        # The size= parameter of `field()` will override this.
        'default_element_size' : (30, 1), # (width, height)

        # Mline size
        # Sets the default multi-line text size when `field()` is used.
        # The size= parameter of `field()` will override this.
        'default_mline_size' : (30, 7), # (width, height)
    }
    """Default Themepack"""

    def __init__(self, tp_dict:Dict[str,str] = {}) -> None:
        self.tp_dict = ThemePack.default

    def __getattr__(self, key):
        # Try to get the key from the internal tp_dict first.  If it fails, then check the default dict.
        try:
            return self.tp_dict[key]
        except KeyError:
            try:
                return ThemePack.default[key]
            except KeyError:
                raise AttributeError(f"ThemePack object has no attribute '{key}'")
            
    def __call__(self, tp_dict:Dict[str,str] = {}) -> None:
        """
        Update the ThemePack object from tp_dict

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
        # For default use cases, load the default directly to avoid the overhead
        # of __getattr__() going through 2 key reads
        if tp_dict == {}: tp_dict = ThemePack.default

        self.tp_dict = tp_dict

# set a default themepack
themepack = ThemePack()


# ======================================================================================================================
# LANGUAGEPACKS
# ======================================================================================================================
# Change the language text used throughout the program.
class LanguagePack:
    """
    LanguagePacks are user-definable collections of strings that allow for localization of strings and messages presented
    to the end user. Creating your own is easy as well! In fact, a LanguagePack can be as simple as one line if you just
    want to change one aspect of the default LanguagePack. Example:
        lp_en = {'save_success': 'SAVED!'} # I want the save popup to display this text in English in all caps
    """
    default = {
        
    # ------------------------
    # Buttons
    # ------------------------
    'button_cancel' : ' Cancel ',
    'button_ok' : '  OK  ',
    'button_yes' : ' Yes ',
    'button_no' : '  No  ',
    
    # ------------------------
    # Startup progress bar
    # ------------------------
    'startup_form' : 'Creating Form',
    'startup_init' : 'Initializing',
    'startup_datasets' : 'Adding datasets',
    'startup_relationships' : 'Adding relationships',
    'startup_binding' : 'Binding window to Form',

    # ------------------------
    # Progress bar displayed during sqldriver operations
    # ------------------------
    'sqldriver_init' : '{name} connection',
    'sqldriver_connecting' : 'Connecting to database',
    'sqldriver_execute' : 'executing SQL commands',

    # ------------------------
    # Info Popup Title - universal
    # ------------------------
    'info_popup_title': 'Info',

    # ------------------------
    # Info Popups - no buttons
    # ------------------------
    # Form save_records
    # ------------------------
    'form_save_partial': 'Some updates were saved successfully;',
    'form_save_problem': 'There was a problem saving updates to the following tables:\n{tables}.',
    'form_save_success': 'Updates saved successfully.',
    'form_save_none': 'There were no updates to save.',
    # DataSet save_record
    # ------------------------
    'dataset_save_empty': 'There were no updates to save.',
    'dataset_save_none': 'There were no changes to save!',
    'dataset_save_success': 'Updates saved successfully.',

    # ------------------------
    # Yes No Popups
    # ------------------------
    # Form prompt_save
    # ------------------------
    'form_prompt_save_title': 'Unsaved Changes',
    'form_prompt_save': 'You have unsaved changes!\nWould you like to save them first?',
    # DataSet prompt_save
    # ------------------------
    'dataset_prompt_save_title': 'Unsaved Changes',
    'dataset_prompt_save': 'You have unsaved changes!\nWould you like to save them first?',

    # ------------------------
    # Ok Popups
    # ------------------------
    # DataSet save_record
    'dataset_save_callback_false_title': 'Callback Prevented Save',
    'dataset_save_callback_false': 'Updates not saved.',
    
    'dataset_save_keyed_fail_title': 'Problem Saving',
    'dataset_save_keyed_fail': 'Query failed: {exception}.',

    'dataset_save_fail_title': 'Problem Saving',
    'dataset_save_fail': 'Query failed: {exception}.',

    # ------------------------
    # Custom Popups
    # ------------------------
    # DataSet delete_record
    # ------------------------
    'delete_title': 'Confirm Deletion',
    'delete_cascade': 'Are you sure you want to delete this record?\nKeep in mind that child records:\n({children})\nwill also be deleted!',
    'delete_single': 'Are you sure you want to delete this record?',
    # Failed Ok Popup
    'delete_failed_title': 'Problem Deleting',
    'delete_failed': 'Query failed: {exception}.',
    'delete_recursion_limit_error' : 'Delete Cascade reached max recursion limit.\nDELETE_CASCADE_RECURSION_LIMIT',

    # Dataset duplicate_record
    # ------------------------
    # Msg prepend to front of parent duplicate
    'duplicate_prepend' : 'Copy of ',
    # Popup when record has children
    'duplicate_child_title': 'Confirm Duplication',
    'duplicate_child': 'This record has child records:\n(in {children})\nWhich records would you like to duplicate?',
    'duplicate_child_button_dupparent': 'Only duplicate this record.',
    'duplicate_child_button_dupboth': 'Duplicate this record and its children.',
    # Popup when record is single
    'duplicate_single_title': 'Confirm Duplication',
    'duplicate_single': 'Are you sure you want to duplicate this record?',
    # Failed Ok Popup
    'duplicate_failed_title': 'Problem Duplicating',
    'duplicate_failed': 'Query failed: {exception}.',

    # ------------------------
    # Quick Editor
    # ------------------------
    'quick_edit_title': 'Quick Edit - {data_key}'
    }
    """Default LanguagePack"""

    def __init__(self, lp_dict={}):
        self.lp_dict = type(self).default

    def __getattr__(self, key):
        # Try to get the key from the internal lp_dict first.  If it fails, then check the default dict.
        try:
            return self.lp_dict[key]
        except KeyError:
            try:
                return type(self).default[key]
            except KeyError:
                raise AttributeError(f"LanguagePack object has no attribute '{key}'")
            
    def __call__(self, lp_dict={}):
        """
        Update the LanguagePack instance

        """
        # For default use cases, load the default directly to avoid the overhead
        # of __getattr__() going through 2 key reads
        if lp_dict == {}: lp_dict = type(self).default

        self.lp_dict = lp_dict

# set a default languagepack
lang = LanguagePack()


# ======================================================================================================================
# ABSTRACTION LAYERS
# ======================================================================================================================
# Database abstraction layers for a uniform API
# ----------------------------------------------------------------------------------------------------------------------

# This is a dummy class for documenting convenience functions
class Abstractions:
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
    notation, and via properties. The available column info via these methods are name, domain, notnull, default and pk
    See example:
    .. literalinclude:: ../doc_examples/Column.1.py
        :language: python
        :caption: Example code
    """
    def __init__(self, name: str, domain: str, notnull: bool, default: None, pk: bool, virtual: bool = False):
        self._column={'name': name, 'domain': domain, 'notnull': notnull, 'default': default, 'pk': pk, 'virtual': virtual}

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

    def __getattr__(self, key):
        return self._column[key]

    def __setattr__(self, key, value):
        if key == '_column':
            super().__setattr__(key, value)
        else:
            self._column[key] = value

    def cast(self, value: any) -> any:
        """
        Cast a value to the appropriate data type as defined by the column info for the column.
        This can be useful for comparing values between the database and the GUI.

        :param value: The value you would like to cast
        :returns: The value, cast to a type as defined by the domain
        """
        # convert the data into the correct data type using the domain in ColumnInfo
        domain = self.domain

        # String type casting
        if domain in ['TEXT', 'VARCHAR', 'CHAR']:
            if type(value) is int:
                value = str(value)
            elif type(value) is bool:
                value = str(value)
            else:
                value = str(value)

        # Integer type casting
        elif domain in ['INT', 'INTEGER', 'BOOLEAN']:
            try:
                value = int(value)
            except ValueError:
                value = str(value)

        # float type casting
        elif domain in ['REAL', 'DOUBLE', 'DECIMAL', 'FLOAT']:
            try:
                value = float(value)
            except ValueError:
                value = str(value)

        # Date casting
        elif domain == 'DATE':
            try:
                value = datetime.strptime(value, '%Y-%m-%d').date()
            except TypeError:
                logger.debug(f'Unable to cast {value} to a datetime.date object.  Casting to string instead.')
                value = str(value)

        # other date/time casting
        elif domain in ['TIME', 'DATETIME', 'TIMESTAMP']: # TODO: i'm sure there is a lot of work to do here
            try:
                value = datetime.date(value)
            except TypeError:
                logger.debug(f'Unable to case datetime/time/timestamp.  Casting to string instead.')
                value = str(value)
        return value

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
    def __init__(self, driver: SQLDriver, table: str):
        self.driver = driver
        self.table = table

        # List of required SQL types to check against when user sets custom values
        self._domains = [
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
    def pk_column(self) -> Union[str,None]:
        """
        Get the pk_column for this colection of column_info

        :returns: A string containing the column name of the PK column, or None if one was not found
        """
        for c in self:
            if c.pk: return c.name
        return None

    def names(self) -> List[str]:
        """
        Return a List of column names from the `Column`s in this collection

        :returns: List of column names
        """
        return self._get_list('name')

    def col_name(self, idx:int) -> str:
        """
        Get the column name located at the specified index in this collection of `Column`s

        :param idx: The index of the column to get the name from
        :returns: The name of the column at the specified index
        """
        return self[idx].name

    def default_row_dict(self, dataset: DataSet) -> dict:
        """
        Return a dictionary of a table row with all defaults assigned. This is useful for inserting new records to
        prefill the GUI elements

        :param dataset: a pysimplesql DataSet object
        :returns: dict
        """
        d = {}
        for c in self:
            default = c.default
            domain = c.domain

            # First, check to see if the default might be a database function
            if self._looks_like_function(default):
                table = self.driver.quote_table(self.table)
                q = f'SELECT {default} AS val FROM {table};' # TODO: may need AS column to support all databases?
                rows = self.driver.execute(q)
                if rows.exception is None:
                    default = rows.fetchone()['val']
                    d[c.name] = default
                    continue
                else:
                    logger.warning(f'There was an exception getting the default: {e}')

            # The stored default is a literal value, lets try to use it:
            if default is None:
                try:
                    null_default = self.null_defaults[domain]
                except KeyError:
                    # Perhaps our default dict does not yet support this datatype
                    null_default = None

                # If our default is callable, call it.  Otherwise, assign it
                # Make sure to skip primary keys, and only consider text that is in the description column
                if (domain not in ['TEXT', 'VARCHAR', 'CHAR'] and
                c.name != dataset.description_column) and c.pk == False:
                    default = null_default() if callable(null_default) else null_default
            else:
                # Load the default that was fetched from the database during ColumnInfo creation
                if domain in ['TEXT', 'VARCHAR', 'CHAR']:
                    # strip quotes from default strings as they seem to get passed with some database-stored defaults
                    default = c.default.strip('"\'')  # strip leading and trailing quotes

            d[c.name] = default
            logger.debug(f'Default fetched from database function. Default value is: {default}')
        if dataset.transform is not None: dataset.transform(dataset, d, TFORM_DECODE)
        return d

    def set_null_default(self, domain: str, value: object) -> None:
        """
        Set a Null default for a single SQL type

        :param domain: The SQL type to set the default for ('INTEGER', 'TEXT', 'BOOLEAN', etc.)
        :param value: The new value to set the SQL type to. This can be a literal or even a callable
        :returns: None
        """
        if domain not in self._domains:
            RuntimeError(f'Unsupported SQL Type: {domain}. Supported types are: {self._domains}')

        self.null_defaults[domain] = value

    def set_null_defaults(self, null_defaults:dict) -> None:
        """
        Set Null defaults for all SQL types

        supported types:  'TEXT','VARCHAR', 'CHAR', 'INTEGER', 'REAL', 'DOUBLE', 'FLOAT', 'DECIMAL', 'BOOLEAN', 'TIME',
        'DATE', 'DATETIME', 'TIMESTAMP'
        :param null_defaults: A dict of SQL types and default values. This can be a literal or even a callable
        :returns: None
        """
        # Check if the null_defaults dict has all the required keys:
        if not all(key in null_defaults for key in self._domains):
            RuntimeError(f'The supplied null_defaults dictionary does not havle all required SQL types. Required: {self._domains}')

        self.null_defaults = null_defaults
    def get_virtual_names(self) -> List[str]:
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
class ResultRow:
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

    def copy(self):
        # return a copy of this row
        return ResultRow(self.row.copy(), virtual=self.virtual)

class ResultSet:
    """
    The ResultSet class is a generic result class so that working with the resultset of the different supported
    databases behave in a consistent manner. A `ResultSet` is a collection of `ResultRow`s, along with the lastrowid
    and any exception returned by the underlying `SQLDriver` when a query is executed.

    ResultSets can be thought up as rows of information.  Iterating through a ResultSet is very simple:
        rows:ResultSet = driver.execute('SELECT * FROM Journal;')
        for row in rows:
            print(row['title'])

    Note: The lastrowid is set by the caller, but by pysimplesql convention, the lastrowid should only be set after
    and INSERT statement is executed.
    """
    # Store class-related constants
    SORT_NONE = 0
    SORT_ASC = 1
    SORT_DESC = 2

    def __init__(self, rows: List[Dict[str, any]] = [], lastrowid: int = None, exception: str = None,
                 column_info: ColumnInfo = None) -> None:
        """
        Create a new ResultSet instance

        :param rows: a list of dicts representing a row of data, with each key being a column name
        :param lastrowid: The primary key of an inserted item
        :exception: If an exception was encountered during the query, it will be passed along here
        :column_info: a `ColumnInfo` object can be supplied so that column information can be accessed
        """
        self.rows = [ResultRow(r, i) for r, i in zip(rows, range(len(rows)))]
        self.lastrowid = lastrowid
        self._iter_index = 0
        self.exception = exception
        self.column_info = column_info
        self.sort_column = None
        self.sort_reverse = False  # ASC or DESC

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
        # carry over the original_index
        try:
            new_row.original_index = self.rows[idx].original_index
        except AttributeError:
            pass
        self.rows[idx]=new_row


    def __len__(self):
        return len(self.rows)

    def get(self, key, default=None):
        return self.rows.get(key, default)

    def fetchone(self) -> ResultRow:
        """
        Fetch the first record in the ResulSet.

        :returns: A `ResultRow` object
        """
        return self.rows[0] if len(self.rows) else []
    def fetchall(self) -> ResultSet:
        """
        ResultSets don't actually support a fetchall(), since the rows are already returned. This is more of a
        comfort method that does nothing, for those that are used to calling fetchall()

        :returns: The same ResultSet that called fetchall()
        """
        return self

    def insert(self, row: dict, idx: int = None) -> None:
        """
        Insert a new virtual row into the `ResultSet`. Virtual rows are ones that exist in memory, but not in the
        database. When a save action is performed, virtua rows will be added into the database.

        :param row: A dict representation of a row of data
        :param idx: The index where the row should be inserted (default to last index)
        :returns: None
        """
        # Insert a new row manually.  This will mark the row as virtual, as it did not come from the database.
        self.rows.insert(idx if idx else len(self.rows), ResultRow(row, virtual=True))

    def purge_virtual(self) -> None:
        """
        Purge virtual rows from the `ResultSet`

        :returns: None
        """
        # Purge virtual rows from the list
        self.rows = [row for row in self.rows if not row.virtual]

    def sort_by_column(self, column: str, table: str, reverse = False) -> None:
        """
        Sort the `ResultSet` by column.
        Using the mapped relationships of the database, foreign keys will automatically sort based on the
        parent table's description column, rather than the foreign key number.

        :param column: The name of the column to sort the `ResultSet` by
        :param table: The name of the table the column belongs to
        :param reverse: Reverse the sort; False = ASC, True = DESC
        :returns: None
        """
        # Target sorting by this ResultSet
        rows = self         # search criteria is based on rows
        target_col = column # Looking in rows for this column
        target_val = column # to be equal to the same column in self.rows

        # We don't want to sort by foreign keys directly - we want to sort by the description column of the foreign
        # table that the foreign key references
        rels = Relationship.get_relationships_for_table(table)
        for rel in rels:
            if column == rel.fk_column:
                rows = rel.frm[rel.parent_table].rows # change the rows used for sort criteria
                target_col = rel.pk_column  # change our target column to look in
                target_val = rel.frm[rel.parent_table].description_column # and return the value in this column
                break
        try:
            self.rows = sorted(self.rows, key=lambda x: next(r[target_val] for r in rows if r[target_col] == x[column]),
                               reverse=reverse)
        except KeyError:
            logger.debug(f'ResultSet could not sort by column {column}. KeyError.')

    def sort_by_index(self,index:int, table:str, reverse=False):
        """
        Sort the `ResultSet` by column index
        Using the mapped relationships of the database, foreign keys will automatically sort based on the
        parent table's description column, rather than the foreign key number.

        :param index: The index of the column to sort the `ResultSet` by
        :param table: The name of the table the column belongs to
        :param reverse: Reverse the sort; False = ASC, True = DESC
        :returns: None
        """
        try:
            column = list(self[0].keys())[index]
        except IndexError:
            logger.debug(f'ResultSet could not sort by column index {index}. IndexError.')
            return
        self.sort_by_column(column, table, reverse)


    def store_sort_settings(self) -> list:
        """
        Store the current sort settingg. Sort settings are just the sort column and reverse setting.
        Sort order can be restored with `ResultSet.load_sort_settings()`

        :returns: A list containing the sort_column and the sort_reverse
        """
        return [self.sort_column, self.sort_reverse]

    def load_sort_settings(self, sort_settings:list) -> None:
        """
        Load a previously stored sort setting. Sort settings are just the sort columm and reverse setting

        :param sort_settings: A list as returned by `ResultSet.store_sort_settings()`
        """
        self.sort_column = sort_settings[0]
        self.sort_reverse = sort_settings[1]


    def sort_reset(self) -> None:
        """
        Reset the sort order to the original when this ResultSet was created.  Each ResultRow has the original order
        stored

        :returns: None
        """
        self.rows = sorted(self.rows, key=lambda x: x.original_index if x.original_index is not None else float('inf'))


    def sort(self, table:str) -> None:
        """
        Sort according to the internal sort_column and sort_reverse variables
        This is a good way to re-sort without changing the sort_cycle

        :param table: The table associated with this ResultSet.  Passed along to `ResultSet.sort_by_column()`
        :returns: None
        """
        if self.sort_column is None:
            self.sort_reset()
        else:
            self.sort_by_column(self.sort_column, table, self.sort_reverse)

    def sort_cycle(self, column:str, table:str) -> int:
        """
        Cycle between original sort order of the ResultSet, ASC by column, and DESC by column with each call

        :param column: The column name to cycle the sort on
        :param table: The table that the column belongs to
        :returns: A ResultSet sort constant; ResultSet.SORT_NONE, ResultSet.SORT_ASC, or ResultSet.SORT_DESC
        """
        if column != self.sort_column:
            # We are going to sort by a new column.  Default to ASC
            self.sort_column = column
            self.sort_reverse = False
            self.sort(table)
            ret =  ResultSet.SORT_ASC
        else:
            if not self.sort_reverse:
                self.sort_reverse = True
                self.sort(table)
                ret = ResultSet.SORT_DESC
            else:
                self.sort_reverse=False
                self.sort_column = None
                self.sort(table)
                ret = ResultSet.SORT_NONE
        return ret

class ReservedKeywordError(Exception):
    pass

class SQLDriver:
    """
    Abstract SQLDriver class.  Derive from this class to create drivers that conform to PySimpleSQL.  This ensures
    that the same code will work the same way regardless of which database is used.  There are a few important things
    to note:
    The commented code below is broken into methods that **MUST** be implemented in the derived class, methods that
    **SHOULD** be implemented in the derived class, and methods that **MAY** need to be implemented in the derived class
    for it to work as expected. Most derived drivers will at least partially work by implementing the **MUST** have
    methods.

    See the source code for `Sqlite`, `Mysql` and `Postgres` for examples of how to construct your own driver.

    NOTE: SQLDriver.execute() should return a ResultSet instance.  Additionally, py pysimplesql convention, the
    ResultSet.lastrowid should always be None unless and INSERT query is executed with SQLDriver.execute() or a record
    is inserted with SQLDriver.insert_record()
    """
    # ---------------------------------------------------------------------
    # MUST implement
    # in order to function
    # ---------------------------------------------------------------------
    def __init__(self, name:str, placeholder='%s', table_quote='', column_quote='', value_quote="'"):
        """
        Create a new SQLDriver instance
        This must be overridden in the derived class, which must call super().__init__(), and when finished call
        self.win_pb.close() to close the database.

        """
        # Be sure to call super().__init__() in derived class!
        self.con = None
        self.name = name
        self._check_reserved_keywords = True
        self.win_pb = ProgressBar(lang.sqldriver_init.format_map(LangFormat(name=name)), 100)
        self.win_pb.update(lang.sqldriver_connecting, 0)

        # Each database type expects their SQL prepared in a certain way.  Below are defaults for how various elements
        # in the SQL string should be quoted and represented as placeholders. Override these in the derived class as
        # needed to satisfy SQL requirements

        # The placeholder for values in the query string.  This is typically '?' or'%s'
        self.placeholder = placeholder                     # override this in derived __init__()

        # These se the quote characters for tables, columns and values.  It varies between different databases
        self.quote_table_char = table_quote                # override this in derived __init__() (defaults to no quotes)
        self.quote_column_char = column_quote              # override this in derived __init__() (defaults to no quotes)
        self.quote_value_char = value_quote                # override this in derived __init__() (defaults to single quotes)

    def check_reserved_keywords(self, value: bool) -> None:
        """
        SQLDrivers can check to make sure that field names respect their own reserved keywords.  By default, all
        SQLDrivers will check for their respective keywords.  You can choose to disable this feature with this method.

        :param value: True to check for reserved keywords in field names, false to skip this check
        :return: None
        """
        self._check_reserved_keywords = value

    def connect(self, *args, **kwargs):
        """
        Connect to a database
        Connect to a database in the connect() method, assigning the connection to self.con
        Implementation varies by database, you may need only one parameter, or several depending on how a connection
        is established with the target database.
        """
        raise NotImplementedError

    def execute(self, query, values=None, column_info: ColumnInfo = None, auto_commit_rollback: bool = False):
        """
        Implements the native SQL implementation's execute() command.

        :param query: The query string to execute
        :param values: Values to pass into the query to replace the placeholders
        :param column_info: An optional ColumnInfo object
        :param auto_commit_rollback: Automatically commit or rollback depending on whether an exception was handled. Set
            to False by default.  Set to True to have exceptions and commit/rollbacks happen automatically
        :return:
        """
        raise NotImplementedError

    def execute_script(self, script: str, silent: bool=False):
        raise NotImplementedError

    def get_tables(self):
        raise NotImplementedError

    def column_info(self, table):
        raise NotImplementedError

    def pk_column(self,table):
        raise NotImplementedError

    def relationships(self):
        raise NotImplementedError

    # ---------------------------------------------------------------------
    # SHOULD implement
    # based on specifics of the database
    # ---------------------------------------------------------------------
    # This is a generic way to estimate the next primary key to be generated.
    # Note that this is not always a reliable way, as manual inserts which assign a primary key value don't always
    # update the sequencer for the given database.  This is just a default way to "get things working", but the best
    # bet is to override this in the derived class and get the value right from the sequencer.
    def next_pk(self, table: str, pk_column: str) -> int:
        max_pk = self.max_pk(table, pk_column)
        if max_pk is not None:
            return max_pk + 1
        else: return 1

    def check_keyword(self, keyword: str, key: str = None) -> None:
        """
        Check keyword to see if it is a reserved word.  If it is raise a ReservedKeywordError. Checks to see if the
        database name is in keys and uses the database name for the key if it exists, otherwise defaults to 'common' in the
        RESERVED set. Override this with the specific key for the database if needed for best results.

        :param keyword: the value to check against reserved words
        :param key: The key in the RESERVED set to check in
        :returns: None
        """
        if not self.check_reserved_keywords: return

        if key is None:
            # First try using the name of the driver
            key = self.name.lower() if self.name.lower() in RESERVED else 'common'

        if keyword.upper() in RESERVED[key] or keyword.upper in RESERVED['common']:
            raise ReservedKeywordError(
                f"`{keyword}` is a reserved keyword and cannot be used for table or column names.")

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

        return f'{r_obj.join_type} {parent} ON {child}.{fk}={parent}.{pk}'

    def min_pk(self, table: str, pk_column: str) -> int:
        rows = self.execute(f"SELECT MIN({pk_column}) FROM {table}")
        return rows.fetchone()[f'MAX({pk_column})']

    def max_pk(self, table: str, pk_column: str) -> int:
        rows = self.execute(f"SELECT MAX({pk_column}) FROM {table}")
        return rows.fetchone()[f'MAX({pk_column})']

    def generate_join_clause(self, dataset: DataSet) -> str:
        """
        Automatically generates a join clause from the Relationships that have been set

        This typically isn't used by end users

        :returns: A join string to be used in a sqlite3 query
        :rtype: str
        """
        join = ''
        for r in dataset.frm.relationships:
            if dataset.table == r.child_table:
                join += f' {self.relationship_to_join_clause(r)}'
        return join if dataset.join_clause == '' else dataset.join_clause


    def generate_where_clause(self, dataset: DataSet) -> str:
        """
        Generates a where clause from the Relationships that have been set, as well as the DataSet's where clause

        This is not typically used by end users

        :returns: A where clause string to be used in a sqlite3 query
        :rtype: str
        """
        where = ''
        for r in dataset.frm.relationships:
            if dataset.table == r.child_table:
                if r._update_cascade:
                    table = dataset.table
                    parent_pk = dataset.frm[r.parent_table].get_current(r.pk_column)
                    if parent_pk == '':
                        parent_pk = 'NULL' # passed so that children without cascade-filtering parent aren't displayed
                    clause=f' WHERE {table}.{r.fk_column}={str(parent_pk)}'
                    if where != '':
                        clause = clause.replace('WHERE', 'AND')
                    where += clause

        if where == '':
            # There was no where clause from Relationships..
            where = dataset.where_clause
        else:
            # There was an auto-generated portion of the where clause.  We will add the table's where clause to it
            where = where + ' ' + dataset.where_clause.replace('WHERE', 'AND')

        return where

    def generate_query(self, dataset: DataSet, join_clause: bool = True, where_clause: bool = True,
                       order_clause: bool = True) -> str:
        """
        Generate a query string using the relationships that have been set

        :param dataset: A `DataSet` object
        :param join_clause: True if you want the join clause auto-generated, False if not
        :type join_clause: bool
        :param where_clause: True if you want the where clause auto-generated, False if not
        :type where_clause: bool
        :param order_clause: True if you want the order by clause auto-generated, False if not
        :type order_clause: bool
        :returns: a query string for use with sqlite3
        :rtype: str
        """
        q = dataset.query
        q += f' {dataset.join_clause if join_clause else ""}'
        q += f' {dataset.where_clause if where_clause else ""}'
        q += f' {dataset.order_clause if order_clause else ""}'
        return q

    def delete_record(self, dataset: DataSet, cascade=True): # TODO: get ON DELETE CASCADE from db
        # Get data for query
        table = self.quote_table(dataset.table)
        pk_column = self.quote_column(dataset.pk_column)
        pk = dataset.get_current(dataset.pk_column)
        
        # Create clauses
        delete_clause = f'DELETE FROM {table} ' # leave a space at end for joining
        where_clause = f'WHERE {table}.{pk_column} = {pk}'

        # Delete child records first!
        if cascade:
            recursion = 0
            result = self.delete_cascade(dataset, '', where_clause, table, pk_column, recursion)
        
        # Then delete self
        if result == DELETE_RECURSION_LIMIT_ERROR:
            return DELETE_RECURSION_LIMIT_ERROR
        q = delete_clause + where_clause + ";"
        return self.execute(q)
    
    def delete_cascade(self, dataset: DataSet, inner_join, where_clause, parent, pk_column, recursion):
        for child in Relationship.get_delete_cascade_relationships(dataset.key):
            # Check to make sure we arn't at recursion limit
            recursion += 1 # Increment, since this is a child
            if recursion >= DELETE_CASCADE_RECURSION_LIMIT:
                return DELETE_RECURSION_LIMIT_ERROR

            # Get data for query
            fk_column = self.quote_column(Relationship.get_delete_cascade_fk_column(child))
            pk_column = self.quote_column(dataset.frm[child].pk_column)
            child_table = self.quote_table(child)
            select_clause = f'SELECT {child_table}.{pk_column} FROM {child} '
            delete_clause = f'DELETE FROM {child} WHERE {pk_column} IN '

            # Create new inner join and add it to beginning of passed in inner_join
            inner_join_clause = f'INNER JOIN {parent} ON {parent}.{pk_column} = {child}.{fk_column} {inner_join}'

            # Call function again to create recursion
            result = self.delete_cascade(dataset.frm[child], inner_join_clause,
                                                  where_clause, child, self.quote_column(dataset.frm[child].pk_column), recursion)

            # Break out of cascade call if at recursion limit
            if result == DELETE_RECURSION_LIMIT_ERROR:
                return DELETE_RECURSION_LIMIT_ERROR
            
            # Create query and execute
            q = delete_clause + "(" + select_clause + inner_join_clause + where_clause + ");"
            self.execute(q)
            logger.debug(f'Delete query executed: {q}')

            # Reset limit for next Child stack
            recursion = 0

    def duplicate_record(self, dataset: DataSet, cascade: bool) -> ResultSet:
        ## https://stackoverflow.com/questions/1716320/how-to-insert-duplicate-rows-in-sqlite-with-a-unique-id
        ## This can be done using * syntax without having to know the schema of the table
        ## (other than the name of the primary key). The trick is to create a temporary table
        ## using the "CREATE TABLE AS" syntax.
        description = self.quote_value(f"{lang.duplicate_prepend}{dataset.get_description_for_pk(dataset.get_current_pk())}")
        table = self.quote_table(dataset.table)
        tmp_table = self.quote_table(f"temp_{dataset.table}")
        pk_column = self.quote_column(dataset.pk_column)
        description_column = self.quote_column(dataset.description_column)
        
        # Create tmp table, update pk column in temp and insert into table
        query= [f'DROP TABLE IF EXISTS {tmp_table};',
                f'CREATE TEMPORARY TABLE {tmp_table} AS SELECT * FROM {table} WHERE {pk_column}=\
                    {dataset.get_current(dataset.pk_column)};',
                f'UPDATE {tmp_table} SET {pk_column} = {self.next_pk(dataset.table, dataset.pk_column)};',
                f'UPDATE {tmp_table} SET {description_column} = {description}',
                f'INSERT INTO {table} SELECT * FROM {tmp_table};',
                f'DROP TABLE IF EXISTS {tmp_table};',
               ]
        for q in query:
            res = self.execute(q)
            if res.exception: return res
            
        # Now we save the new pk
        pk = res.lastrowid

        # create list of which children we have duplicated
        child_duplicated = []
        # Next, duplicate the child records!
        if cascade:
            for _ in dataset.frm.datasets:
                for r in dataset.frm.relationships:
                    if r.parent_table == dataset.table and r._update_cascade and (r.child_table not in child_duplicated):
                        child = self.quote_table(r.child_table)
                        tmp_child = self.quote_table(f"temp_{r.child_table}")
                        pk_column = self.quote_column(dataset.frm[r.child_table].pk_column)
                        fk_column = self.quote_column(r.fk_column)
                        # Update children's pk_columns to NULL and set correct parent PK value.
                        queries = [f'DROP TABLE IF EXISTS {tmp_child};',
                                   f'CREATE TEMPORARY TABLE {tmp_child} AS SELECT * FROM {child} WHERE {fk_column}=\
                                       {dataset.get_current(dataset.pk_column)};',
                                   f'UPDATE {tmp_child} SET {pk_column} = NULL;', # don't next_pk(), because child can be plural.
                                   f'UPDATE {tmp_child} SET {fk_column} = {pk}',
                                   f'INSERT INTO {child} SELECT * FROM {tmp_child};',
                                   f'DROP TABLE IF EXISTS {tmp_child};',
                                  ]
                        for q in queries:
                            res = self.execute(q)
                            if res.exception: return res
                            
                        child_duplicated.append(r.child_table)
        # If we made it here, we can return the pk.  Since the pk was stored earlier, we will just send and empty ResultSet
        return ResultSet(lastrowid=pk)

    def save_record(self, dataset: DataSet, changed_row: dict, where_clause: str = None) -> ResultSet:
        pk = dataset.get_current_pk()
        pk_column = dataset.pk_column

        # Remove the pk column and any virtual columns
        changed_row = {k: v for k,v in changed_row.items() if k != pk_column and k not in dataset.column_info.get_virtual_names()}

        # quote appropriately
        table = self.quote_table(dataset.table)
        pk_column = self.quote_column(pk_column)

        # Create the WHERE clause
        if where_clause is None:
            where_clause = f"WHERE {pk_column} = {pk}"

        # Generate an UPDATE query
        query = f"UPDATE {table} SET {', '.join(f'{k}={self.placeholder}' for k in changed_row.keys())} {where_clause};"
        values = [v for v in changed_row.values()]

        result = self.execute(query, tuple(values))
        result.lastrowid = None # manually clear th rowid since it is not needed for updated records (we already know the key)
        return result


    def insert_record(self, table:str, pk:int, pk_column:str, row:dict):
        # Remove the pk column
        row = {k: v for k, v in row.items() if k != pk_column}

        # quote appropriately
        table = self.quote_table(table)

        # Remove the primary key column to ensure autoincrement is used!
        query = f"INSERT INTO {table} ({', '.join(key for key in row.keys())}) VALUES ({','.join(self.placeholder for _ in range(len(row)))}); "
        values = [value for key, value in row.items()]
        return self.execute(query, tuple(values))

# ----------------------------------------------------------------------------------------------------------------------
# SQLITE3 DRIVER
# ----------------------------------------------------------------------------------------------------------------------
class Sqlite(SQLDriver):
    def __init__(self, db_path=None, sql_script=None, sqlite3_database=None, sql_commands=None):
        super().__init__(name='SQLite', placeholder='?')

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

        self.win_pb.update(lang.sqldriver_execute,50)
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
        self.win_pb.close()

    def connect(self, database):
        self.con = sqlite3.connect(database)

    def execute(self, query, values=None, silent=False, column_info = None, auto_commit_rollback: bool = False):
        if not silent:logger.info(f'Executing query: {query} {values}')

        cursor = self.con.cursor()
        exception = None
        try:
            cur = cursor.execute(query, values) if values else cursor.execute(query)
        except sqlite3.Error as e:
            exception = e
            logger.warning(f'Execute exception: {type(e).__name__}: {e}, using query: {query}')
            if auto_commit_rollback:
                self.rollback()
        else:
            if auto_commit_rollback:
                self.commit()

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

    def get_tables(self):
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
            domain = row['type']
            notnull = row['notnull']
            default = row['dflt_value']
            pk = row['pk']
            col_info.append(Column(name=name, domain=domain, notnull=notnull, default=default, pk=pk))

        return col_info

    def pk_column(self,table):
        q = f'PRAGMA table_info({table})'
        row = self.execute(q, silent=True).fetchone()

        return row['name'] if 'name' in row else None


    def relationships(self):
        # Return a list of dicts {from_table,to_table,from_column,to_column,requery}
        relationships = []
        tables = self.get_tables()
        for from_table in tables:
            rows = self.execute(f"PRAGMA foreign_key_list({from_table})", silent=True)

            for row in rows:
                dic={}
                # Add the relationship if it's in the requery list
                if row['on_update'] == 'CASCADE':
                    dic['update_cascade'] = True
                else:
                    dic['update_cascade'] = False
                if row['on_delete'] == 'CASCADE':
                    dic['delete_cascade'] = True
                else:
                    dic['delete_cascade'] = False
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
# FLATFILE DRIVER
# ----------------------------------------------------------------------------------------------------------------------
# The CSV driver uses SQlite3 in the background to use pysimplesql directly with CSV files
class Flatfile(Sqlite):
    """
    The Flatfile driver adds support for flatfile databases such as CSV files to pysimplesql.
    The flatfile data is loaded into an internal SQlite database, where it can be used and manipulated like any other
    database file.  Each timem records are saved, the contents of the internal SQlite database are written back out
    to the file. This makes working with flatfile data as easy and consistent as any other database.
    """
    def __init__(self, file_path: str, delimiter: str = ',', quotechar: str = '"', header_row_num: int = 0,
                 table: str = None, pk_col: str = None) -> None:
        """
        Create a new Flatfile driver instance

        :param file_path: The path to the flatfile
        :param delimiter: The delimiter for the flatfile. Defaults to ','.  Tabs ('\t') are another popular option
        :param quotechar: The quoting character specified by the flatfile. Defaults to '"'
        :param header_row_num: The row containing the header column names.  Defaults to 0
        :param table: The name to give this table in pysimplesql. Default is 'Flatfile'
        :param pk_col: The column name that acts as a primary key for the dataset. See below how to use this parameter:
                       - If no pk_col parameter is supplied, then a generic primary key column named 'pk' will be generated
                         with AUTO INCREMENT and PRIMARY KEY set.  This is a virtual column and will not be written back
                         out to the flatfile.
                       - If the pk_col parameter is supplied, and it exists in the header row, then it will be used
                         as the primary key for the dataset.  If this column does not exist in the header row, then a
                         virtual primary key column with this name will be created with AUTO INCREMENT and PRIMARY KEY set.
                         As above, the virtual primary key column that was created will not be written to the flatfile.

        """

        # First up the SQLite driver that we derived from
        super().__init__(':memory:')  # use an in-memory database

        # Store our Flatfile-specific information
        self.name = 'Flatfile'
        self.placeholder = '?'  # update
        self.connect(':memory:')
        self.file_path = file_path
        self.delimiter = delimiter
        self.quotechar = quotechar
        self.header_row_num = header_row_num
        self.pk_col = pk_col if pk_col is not None else 'pk'
        self.pk_col_is_virtual = False
        self.table = table if table is not None else 'Flatfile'
        self.con.row_factory = sqlite3.Row
        self.pre_header = [] # Store any text up to the header line, so they can be restored

        # Open the CSV file and read the header row to get column names
        with open(file_path, 'r') as f:
            reader = csv.reader(f, delimiter = self.delimiter, quotechar=self.quotechar)
            # skip lines as determined by header_row_num
            for i in range(self.header_row_num):
                self.pre_header.append(next(reader))

            # Grab the header row information
            self.columns = next(reader)

        if self.pk_col not in self.columns:
            # The pk column was not found, we will make it virutal
            self.columns.insert(0, self.pk_col)
            self.pk_col_is_virtual = True

        # Construct the SQL commands to create the table to represent the flatfile data
        q_cols = ''
        for col in self.columns:
            if col == self.pk_col:
                q_cols += f'{col} {"INTEGER PRIMARY KEY AUTOINCREMENT" if self.pk_col_is_virtual else "PRIMARY KEY"}'
            else:
                q_cols += f'{col} TEXT'

            if col != self.columns[-1]:
                q_cols += ', '

        query = f'CREATE TABLE {self.table} ({q_cols})'
        self.execute(query)

        # Load the CSV data into the table
        with open(self.file_path, 'r') as f:
            reader = csv.reader(f, delimiter = self.delimiter, quotechar=self.quotechar)
            # advance to past the header column
            for i in range(self.header_row_num+1):
                next(reader)

            # We only want to insert the pk_column if it is not virtual. We will remove it now, as it has already
            # served its purpose to create the table
            if self.pk_col_is_virtual:
                self.columns.remove(self.pk_col)

            query = f'INSERT INTO {self.table} ({", ".join(self.columns)}) VALUES ({", ".join(["?" for col in self.columns])})'
            for row in reader:
                self.execute(query, row)

        self.commit()  # commit them all at the end
        self.win_pb.close()


    def save_record(self, dataset: DataSet, changed_row: dict, where_clause: str = None) -> ResultSet:
        # Have SQlite save this record
        result = super().save_record(dataset, changed_row, where_clause)

        if result.exception is None:
            # No it is safe to write our data back out to the CSV file

            # Update the DataSet object's ResultSet with the changes, so then
            # the entire ResultSet can be written back to file sequentially
            dataset.rows[dataset.current_index] = changed_row

            # open the CSV file for writing
            with open(self.file_path, 'w', newline='\n') as csvfile:
                # create a csv writer object
                writer = csv.writer(csvfile, delimiter=self.delimiter, quotechar=self.quotechar)

                # Skip the number of lines defined by header_row_num. Write out the stored pre_header lines
                for line in self.pre_header:
                    writer.writerow(line)

                # write the header row
                writer.writerow([column for column in self.columns])

                # write the ResultSet out.  Use our columns to exclude the possible virtual pk
                rows = []
                for r in dataset.rows:
                    rows.append([r[c] for c in self.columns])


                logger.debug(f'Writing the following data to {self.file_path}')
                logger.debug(rows)
                writer.writerows(rows)

        return result


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

        self.win_pb.update('Executing SQL commands', 50)
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

        self.win_pb.close()

    def connect(self):
        con = mysql.connector.connect(
            host = self.host,
            user = self.user,
            password = self.password,
            database = self.database
        )
        return con

    def execute(self, query, values=None, silent=False, column_info=None, auto_commit_rollback: bool = False):
        if not silent: logger.info(f'Executing query: {query} {values}')
        cursor = self.con.cursor(dictionary=True)
        exception = None
        try:
            cursor.execute(query, values) if values else cursor.execute(query)
        except mysql.connector.Error as e:
            exception = e.msg
            logger.warning(f'Execute exception: {type(e).__name__}: {e}, using query: {query}')
            if auto_commit_rollback:
                self.rollback()
        else:
            if auto_commit_rollback:
                self.commit()

        try:
            rows = cursor.fetchall()
        except:
            rows = []

        lastrowid=cursor.lastrowid if cursor.lastrowid else None

        return ResultSet([dict(row) for row in rows], lastrowid, exception, column_info)


    def get_tables(self):
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
            # Capitalize and get rid of the extra information of the row type I.e. varchar(255) becomes VARCHAR
            domain = row['Type'].split('(')[0].upper()
            notnull = True if row['Null'] == 'NO' else False
            default = row['Default']
            pk = True if row['Key'] == 'PRI' else False
            col_info.append(Column(name=name, domain=domain, notnull=notnull, default=default, pk=pk))

        return col_info


    def pk_column(self,table):
        query = "SHOW KEYS FROM {} WHERE Key_name = 'PRIMARY'".format(table)
        cur = self.execute(query, silent=True)
        row = cur.fetchone()
        return row['Column_name'] if row else None

    def relationships(self):
        # Return a list of dicts {from_table,to_table,from_column,to_column,requery}
        tables= self.get_tables()
        relationships = []
        for from_table in tables:
            query = "SELECT * FROM information_schema.key_column_usage WHERE referenced_table_name IS NOT NULL AND table_name = %s"
            rows=self.execute(query, (from_table,), silent=True)

            for row in rows:
                dic = {}
                # Get the constraint information
                on_update, on_delete = self.constraint(row['CONSTRAINT_NAME'])
                if on_update == 'CASCADE':
                    dic['update_cascade'] = True
                else:
                    dic['update_cascade'] = False
                if on_delete == 'CASCADE':
                    dic['delete_cascade'] = True
                else:
                    dic['delete_cascade'] = False
                dic['from_table'] = row['TABLE_NAME']
                dic['to_table'] = row['REFERENCED_TABLE_NAME']
                dic['from_column'] = row['COLUMN_NAME']
                dic['to_column'] = row['REFERENCED_COLUMN_NAME']
                relationships.append(dic)
        return relationships

    def execute_script(self, script):
        with open(script, 'r') as file:
            logger.info(f'Loading script {script} into database.')
            # TODO

    # Not required for SQLDriver
    def constraint(self,constraint_name):
        query = f"SELECT UPDATE_RULE, DELETE_RULE FROM INFORMATION_SCHEMA.REFERENTIAL_CONSTRAINTS WHERE CONSTRAINT_NAME = '{constraint_name}'"
        rows = self.execute(query, silent=True)
        return rows[0]['UPDATE_RULE'], rows[0]['DELETE_RULE']


# ----------------------------------------------------------------------------------------------------------------------
# MARIA DRIVER
# ----------------------------------------------------------------------------------------------------------------------
# MariaDB is a fork of MySQL and backward compatible.  It technically does not need its own driver, but that could
# change in the future, plus having its own named class makes it more clear for the end user.
class Maria(Mysql):
    def __init__(self, host, user, password, database, sql_script=None, sql_commands=None):
        super().__init__(host, user, password, database, sql_script, sql_commands)
        self.name = "MariaDB"


# ----------------------------------------------------------------------------------------------------------------------
# POSTGRES DRIVER
# ----------------------------------------------------------------------------------------------------------------------
class Postgres(SQLDriver):
    def __init__(self,host,user,password,database,sql_script=None, sql_commands=None, sync_sequences=False):
        super().__init__(name='Postgres', table_quote='"')

        self.host = host
        self.user = user
        self.password = password
        self.database = database
        self.con = self.connect()

        # experiment to see if I can make a nocase collation
        # query = "CREATE COLLATION NOCASE (provider = icu, locale = 'und-u-ks-level2');"
        # self.execute(query)

        if sync_sequences:
            # synchronize the sequences with the max pk for each table. This is useful if manual records were inserted
            # without calling nextval() to update the sequencer
            q = "SELECT sequence_name FROM information_schema.sequences;"
            sequences = self.execute(q, silent=True)
            for s in sequences:
                seq = s['sequence_name']

                # get the max pk for this table
                q = f"SELECT column_name, table_name FROM information_schema.columns WHERE column_default LIKE 'nextval(%{seq}%)'"
                rows = self.execute(q, silent=True, auto_commit_rollback=True)
                row=rows.fetchone()
                table = row['table_name']
                pk_column = row['column_name']
                max_pk = self.max_pk(table, pk_column)

                # update the sequence
                # TODO: This needs fixed.  pysimplesql_user does have permissions on the sequence, but this still bombs out
                seq = self.quote_table(seq)
                if max_pk > 0:
                    q = f"SELECT setval('{seq}', {max_pk});"
                else:
                    q = f"SELECT setval('{seq}', 1, false);"
                self.execute(q, silent=True, auto_commit_rollback=True)

        self.win_pb.update('executing SQL commands', 50)
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
        self.win_pb.close()

    def connect(self):
        con = psycopg2.connect(
            host = self.host,
            user = self.user,
            password = self.password,
            database = self.database
        )
        return con

    def execute(self, query:str, values=None, silent=False, column_info=None, auto_commit_rollback: bool = False):
        if not silent: logger.info(f'Executing query: {query} {values}')
        cursor = self.con.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        exception = None
        try:
            cursor.execute(query, values) if values else cursor.execute(query)
        except psycopg2.Error as e:
            exception = e
            logger.warning(f'Execute exception: {type(e).__name__}: {e}, using query: {query}')
            if auto_commit_rollback:
                self.rollback()
        else:
            if auto_commit_rollback:
                self.commit()

        try:
            rows = cursor.fetchall()
        except psycopg2.ProgrammingError:
            rows = []

        # In Postgres, the cursor does not return a lastrowid.  We will not set it here, we will instead set it in
        # save_records() due to the RETURNING stement of the query
        return ResultSet([dict(row) for row in rows], exception=exception, column_info=column_info)

    def get_tables(self):
        query = "SELECT table_name FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE';"
        #query = "SELECT tablename FROM pg_tables WHERE table_schema='public'"
        rows = self.execute(query, silent=True)
        return [row['table_name'] for row in rows]

    def column_info(self, table: str) -> ColumnInfo:
        # Return a list of column names
        query = f"SELECT * FROM information_schema.columns WHERE table_name = '{table}'"
        rows = self.execute(query, silent=True)

        col_info = ColumnInfo(self, table)
        pk_column = self.pk_column(table)
        for row in rows:
            name = row['column_name']
            domain = row['data_type'].upper()
            notnull = False if row['is_nullable'] == 'YES' else True
            default = row['column_default']
            # Fix the default value by removing the datatype that is appended to the end
            if default is not None:
                if '::' in default:
                    default = default[:default.index('::')]

            pk = True if name == pk_column else False
            col_info.append(Column(name=name, domain=domain, notnull=notnull, default=default, pk=pk))

        return col_info

    def pk_column(self, table):
        query = f"SELECT column_name FROM information_schema.table_constraints tc JOIN information_schema.key_column_usage kcu ON tc.constraint_name = kcu.constraint_name WHERE tc.constraint_type = 'PRIMARY KEY' AND tc.table_name = '{table}' "
        cur = self.execute(query, silent=True)
        row = cur.fetchone()
        return row['column_name'] if row else None

    def relationships(self):
        # Return a list of dicts {from_table,to_table,from_column,to_column,requery}
        tables= self.get_tables()
        relationships = []
        for from_table in tables:
            query = f"SELECT conname, conrelid::regclass, confrelid::regclass, confupdtype, confdeltype,"
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
                if row['confupdtype'] == 'c':
                    dic['update_cascade'] = True
                else:
                    dic['update_cascade'] = False
                if row['confdeltype'] == 'c':
                    dic['delete_cascade'] = True
                else:
                    dic['delete_cascade'] = False
                dic['from_table'] = row['conrelid'].strip('"')
                dic['to_table'] = row['confrelid'].strip('"')
                dic['from_column'] = row['column_name']
                dic['to_column'] = row['referenced_column_name']
                relationships.append(dic)
        return relationships

    def min_pk(self, table: str, pk_column: str) -> int:
        table = self.quote_table(table)
        pk_column = self.quote_column(pk_column)
        rows = self.execute(f'SELECT COALESCE(MIN({pk_column}), 0) AS min_pk FROM {table};', silent=True)
        return rows.fetchone()[f'min_pk']

    def max_pk(self, table: str, pk_column: str) -> int:
        table = self.quote_table(table)
        pk_column = self.quote_column(pk_column)
        rows = self.execute(f'SELECT COALESCE(MAX({pk_column}), 0) AS max_pk FROM {table};', silent=True)
        return rows.fetchone()[f'max_pk']

    def next_pk(self, table: str, pk_column: str) -> int:
        # Working with case-sensitive tables is painful in Postgres.  First, the sequence must be quoted in a manner
        # similar to tables, then the quoted sequence name has to be also surrounded in single quotes to be treated
        # literally and prevent folding of the casing.
        seq = f'{table}_{pk_column}_seq' # build the default sequence name
        seq = self.quote_table(seq) # quote it like a table

        q=f"SELECT nextval('{seq}') LIMIT 1;" # wrap the quoted string in singe quotes.  Phew!
        rows = self.execute(q, silent=True)
        return rows.fetchone()['nextval']

    def insert_record(self, table: str, pk: int, pk_column: str, row: dict):
        # insert_record() for Postgres is a little different from the rest. Instead of relying on an autoincrement, we
        # first already "reserved" a primary key earlier, so we will use it directly
        # quote appropriately
        table = self.quote_table(table)

        # Remove the primary key column to ensure autoincrement is used!
        query = f"INSERT INTO {table} ({', '.join(key for key in row.keys())}) VALUES ({','.join('%s' for _ in range(len(row)))}); "
        values = [value for key, value in row.items()]
        result = self.execute(query, tuple(values))

        result.lastid = pk
        return result

    def execute_script(self, script):
        pass

# --------------------------
# TYPEDDICTS AND TYPEALIASES
# --------------------------
SaveResultsDict = Dict[str, int]
CallbacksDict = Dict[str, Callable[[Form, sg.Window], Union[None, bool]]]
PromptSaveValue = int #Union[PROMPT_SAVE_PROCEED, PROMPT_SAVE_DISCARDED, PROMPT_SAVE_NONE]


class SimpleTransform(TypedDict):
    decode: Dict[str, Callable[[str, str], None]]
    encode: Dict[str, Callable[[str, str], None]]


SimpleTransformsDict = Dict[str, SimpleTransform]


# ======================================================================================================================
# ALIASES
# ======================================================================================================================
languagepack = lang
Database=Form
Table=DataSet
record = field # for reverse capability
