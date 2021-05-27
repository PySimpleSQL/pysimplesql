#!/usr/bin/python3
import PySimpleGUI as sg
import logging
import sqlite3
import functools
import os.path
import random
from os import path
from update_checker import UpdateChecker
logger = logging.getLogger(__name__)

# -------------------------
# Check for package updates
# -------------------------
version = __version__ = '0.0.9'
checker = UpdateChecker()
result = checker.check('pysimplesql', version)
if result is not None:
    release_date=f'(released {result.release_date}) ' if result.release_date is not None else ''
    print(f'***** pysimplesql update to v{result.available_version} {release_date}available! Be sure to run pip3 install pysimplesql --upgrade *****')

# ---------------------------
# Types for automatic mapping
#----------------------------
TYPE_RECORD=1
TYPE_SELECTOR=2
TYPE_EVENT=3

# -----------
# Event types
# -----------
# Cutsom events (requires 'function' dictionary key)
EVENT_FUNCTION=0
# Table-level events (requires 'table' dictionary key)
EVENT_FIRST=1
EVENT_PREVIOUS=2
EVENT_NEXT=3
EVENT_LAST=4
EVENT_SEARCH=5
EVENT_INSERT=6
EVENT_DELETE=7
EVENT_SAVE=8
EVENT_QUICK_EDIT=9
# Database-level events
EVENT_SEARCH_DB=10
EVENT_SAVE_DB=11
EVENT_EDIT_PROTECT_DB=12

# ------------------------
# RECORD SAVE RETURN TYPES
# ------------------------
SAVE_FAIL=0     # Save failed due to callback
SAVE_SUCCESS=1  # Save was successful
SAVE_NONE=2     # There was nothing to save

# Hack for fixing false table events that are generated when the
# table.update() method is called.  Call this after each call to update()!
def eat_events(win):
    while True:
        event,values=win.read(timeout=0)
        if event=='__TIMEOUT__':
            break
    return

def escape(query_string):
    """
    Safely escape characters in strings needed for queries

    Parameters:
    query_string (str):

    Returns:
    str: escaped (safe) version of the query_string
    """
    # I'm not sure we will need this, but it's here in the case that we do
    query_string = str(query_string)
    return query_string



class Row:
    """
    @Row class. This is a convenience class used by listboxes and comboboxes to display values
    while keeping them linked to a primary key.
    You may have to cast this to a str() to get the value.  Of course, there are methods to get the
    value or primary key either way.
    """

    def __init__(self, pk, val):
        self.pk = pk
        self.val = val

    def __repr__(self):
        return str(self.val)

    def __str__(self):
        # This override is so that comboboxes can display the value
        return str(self.val)

    def get_pk(self):
        """Return the primary key portion of the row"""
        return self.pk

    def get_val(self):
        """Return the value portion of the row"""
        return self.val

    def get_instance(self):
        """Return this instance of @Row"""
        return self


class Relationship:
    """
    @Relationship class is used to track primary/foreign key relationships in the database. See the following
    for more information: @Database.add_relationship and @Database.auto_add_relationships
    Note that this class offers little to the end user, and the above Database functions are all that is needed
    by the user.
    """

    def __init__(self, join, child, fk, parent, pk, requery_table):
        self.join = join
        self.child = child
        self.fk = fk
        self.parent = parent
        self.pk = pk
        self.requery_table = requery_table

    def __str__(self):
        return f'{self.join} {self.parent} ON {self.child}.{self.fk}={self.parent}.{self.pk}'


class Table:
    """
    @Table class is used for an internal representation of database tables. These are added by the following:
    @Database.add_table @Database.auto_add_tables
    """

    def __init__(self, db_reference, con, table, pk_column, description_column, query='', order=''):
        """

        :param db_reference: This is a reference to the @ Database object, for convenience
        :param con:  This is a reference to the sqlie connection, also for convience
        :param table: Name (string) of the table
        :param pk_column: The name of the column containing the primary key for this table
        :param description_column: The name of the column used for display to users (normally in a combobox or listbox)
        :param query: You can optionally set an inital query here. If none is provided, it will default to "SELECT * FROM {table}"
        :param order: The sort order of the returned query
        """
        # todo finish the order processing!

        # No query was passed in, so we will generate a generic one
        if query == '':
            query = f'SELECT * FROM {table}'
        # No order was passed in, so we will generate generic one
        if order == '':
            order = f' ORDER BY {description_column} COLLATE NOCASE ASC'

        self.db = db_reference  # type: Database
        self._current_index = 0
        self.table = table  # type: str
        self.pk_column = pk_column
        self.description_column = description_column
        self.query = query
        self.order = order
        self.join = ''
        self.where = ''  # In addition to generated where!
        self.con = con
        self.dependents = []
        self.column_names = []
        self.rows = []
        self.search_order = []
        self.selector = []
        self.callbacks = {}
        # self.requery(True)

    # Override the [] operator to retrieve columns by key
    def __getitem__(self, key):
        return self.get_current(key)

    # Make current_index a property so that bounds can be respected
    @property
    def current_index(self):
        return self._current_index

    @current_index.setter
    def current_index(self, val):
        if val > len(self.rows) - 1:
            self._current_index = len(self.rows) - 1
        elif val < 0:
            self._current_index = 0
        else:
            self._current_index = val

    def set_search_order(self, order):
        """
        Set the search order when using the search box.
        This is a list of columns to be searched, in order.
        :param order: A list of column names to search
        :return: None
        """
        self.search_order = order

    def set_callback(self, callback, fctn):
        """
        Set table callbacks. A runtime error will be thrown if the callback is not supported.
        The following callbacks are supported:
            before_save   called before a record is saved. The save will continue if the callback returns true, or the record will rollback if the callback returns false.
            after_save    called after a record is saved. The save will commit to the database if the callback returns true, else it will rollback the transaction
            before_update Alias for before_save
            after_update  Alias for after_save
            before_delete called before a record is deleted.  The delete will move forward if the callback returns true, else the transaction will rollback
            after_delete  called after a record is deleted. The delete will commit to the database if the callback returns true, else it will rollback the transaction
            before_search called before searching.  The search will continue if the callback returns True
            after_search  called after a search has been performed.  The record change will undo if the callback returns False
        :param callback: The name of the callback, from the list above

        :param fctn: The function to call.  Note, the function must take in two parameters, a @Database instance, and a @PySimpleGUI.Window instance, and return True or False
        :return: None
        """
        logger.info(f'Callback {callback} being set on table {self.table}')
        supported = [
            'before_save', 'after_save', 'before_delete', 'after_delete',
            'before_update', 'after_update',  # Aliases for before/after_save
            'before_search', 'after_search'
        ]
        if callback in supported:
            # handle our convenience aliases
            callback = 'before_save' if callback == 'before_update' else callback
            callback = 'after_save' if callback == 'after_update' else callback
            self.callbacks[callback] = fctn
        else:
            raise RuntimeError(f'Callback "{callback}" not supported.')

    def set_query(self, q):
        """
        Set the tables query string.  This is more for advanced users.  It defautls to "SELECT * FROM {Table};
        :param q: The query string you would like to associate with the table
        :return: None
        """
        logger.info(f'Setting {self.table} query to {q}')
        self.query = q

    def set_join_clause(self, clause):
        """
        Set the table's join string.  This is more for advanced users, as it will automatically generate from the
        Relationships that have been set otherwise.
        :param clause: The join clause, such as "LEFT JOIN That on This.pk=That.fk"
        :return: None
        """
        logger.info(f'Setting {self.table} join clause to {clause}')
        self.join = clause

    def set_where_clause(self, clause):
        """
        Set the table's where clause.  This is added to the auto-generated where clause from Relationship data!
        :param clause: The where clause, such as "WHERE pkThis=100"
        :return: None
        """
        logger.info(f'Setting {self.table} where clause to {clause}')
        self.where = clause

    def set_order_clause(self, clause):
        """
        Set the table's order string. This is more for advanced users, as it will automatically generate from the
        Relationships that have been set otherwise.
        :param clause: The order clause, such as "Order by name ASC"
        :return: None
        """
        logger.info(f'Setting {self.table} order clause to {clause}')
        self.order = clause

    def set_description_column(self, column):
        """
        Set the table's description column. This is the column that will display in Listboxes, Comboboxes, etc.
        Normally, this is either the 'name' column, or the 2nd column of the table.  This allows you to specify something
        different
        :param column: The the column to use
        :return: None
        """
        self.description_column=column

    def prompt_save(self):
        """
        Prompts the user if they want to save when saving a record that has been changed.
        :return: True or False on whether the user intends to save the record
        """
        # TODO: children too?
        if self.current_index is None or self.rows == []: return
        return  # hack this in for now
        # handle dependents first
        for rel in self.db.relationships:
            if rel.parent == self.table and rel.requery_table:
                self.db[rel.child].prompt_save()

        dirty = False
        for c in self.db.element_map:
            # Compare the DB version to the GUI version
            if c['table'].table == self.table:
                element_val = c['element'].Get()
                table_val = self[c['column']]

                # Sanitize things a bit due to empty values being slightly different in the two cases
                if table_val is None: table_val = ''

                if element_val != table_val:
                    print(f'{c["element"].Key}:{c["element"].Get()} != {c["column"]}:{self[c["column"]]}')
                    dirty = True

        if dirty:
            save_changes = sg.popup_yes_no('You have unsaved changes! Would you like to save them first?')
            if save_changes == 'Yes':
                print(save_changes + 'SAVING')
                # self.save_record(True) # TODO
                # self.requery(False)

    def generate_join_clause(self):
        """
        Automatically generates a join clause from the Relationships that have been set
        :return: A join string to be used in a sqlite3 query
        """
        join = ''
        for r in self.db.relationships:
            if self.table == r.child:
                join += f' {r.join} {r.parent} ON {r.child}.{r.fk} = {r.parent}.{r.pk}'
        return join if self.join == '' else self.join

    def generate_where_clause(self):
        """
        Generates a where clause from the Relationships that have been set, as well as the Table's where clause
        :return: A where clause string to be used in a sqlite3 query
        """
        where = ''
        for r in self.db.relationships:
            if self.table == r.child:
                if r.requery_table:
                    clause=f' WHERE {self.table}.{r.fk}={str(self.db[r.parent].get_current(r.pk, 0))}'
                    if where!='': clause=clause.replace('WHERE','AND')
                    where += clause

        if where == '':
            # There was no where clause from Relationships..
            where = self.where
        else:
            # There was an auto-generated portion of the where clause.  We will add the table's where clause to it
            where = where + ' ' + self.where.replace('WHERE', 'AND')
        return where

    def generate_query(self, join=True, where=True, order=True):
        """
        Generate a query string using the relationships that have been set
        :param join: True if you want the join clause auto-generated, False if not
        :param where: True if you want the where clause auto-generated, False if not
        :param order: True if you want the order by clause auto-generated, False if not
        :return: a query string for use with sqlite3
        """
        q = self.query
        q += f' {self.join if join else ""}'
        q += f' {self.where if where else ""}'
        q += f' {self.order if order else ""}'
        return q

    def requery(self, select_first=True, filtered=True, update=True):
        """
        Requeries the table
        The @Table object maintains an internal representation of the actual database table.
        The requery method will requery the actual database  and sync the @Table objects to it
        :param select_first: If true, the first record will be selected after the requery
        :param filtered: If true, the relationships will be considered and an appropriate WHERE clause will be generated
        :return: None
        """
        if filtered:
            join = self.generate_join_clause()
            where = self.generate_where_clause()

        query = self.query + ' ' + join + ' ' + where + ' ' + self.order
        logger.info('Running query: ' + query)

        cur = self.con.execute(query)
        self.rows = cur.fetchall()
        if select_first:
            self.first(update)

    def requery_dependents(self,update=True):
        """
        Requery parent tables as defined by the relationships of the table

        :return: None
        """
        for rel in self.db.relationships:
            if rel.parent == self.table and rel.requery_table:
                logger.info(f"Requerying dependent table {self.db[rel.child].table}")
                self.db[rel.child].requery(update=update)

    def first(self,update=True, dependents=True):
        """
        Move to the first record of the table
        Only one entry in the table is ever considered "Selected"  This is one of several functions that influences
        which record is currently selected. See @Table.first, @Table.previous, @Table.next, @Table.last, @Table.search,
        @Table.set_by_pk
        :return: None
        """
        logger.info(f'Moving to the first record of table {self.table}')
        self.prompt_save()
        self.current_index = 0
        if dependents: self.requery_dependents()
        if update: self.db.update_elements()

    def last(self, update=True, dependents=True):
        """
        Move to the last record of the table
        Only one entry in the table is ever considered "Selected"  This is one of several functions that influences
        which record is currently selected. See @Table.first, @Table.previous, @Table.next, @Table.last, @Table.search,
        @Table.set_by_pk
        :return: None
        """
        self.prompt_save()
        self.current_index = len(self.rows) - 1
        if dependents: self.requery_dependents()
        if update: self.db.update_elements()

    def next(self, update=True, dependents=True):
        """
        Move to the next record of the table
        Only one entry in the table is ever considered "Selected"  This is one of several functions that influences
        which record is currently selected. See @Table.first, @Table.previous, @Table.next, @Table.last, @Table.search,
        @Table.set_by_pk
        :return: None
        """
        self.prompt_save()
        if self.current_index < len(self.rows) - 1:
            self.current_index += 1
            if dependents: self.requery_dependents()
            if update: self.db.update_elements()

    def previous(self, update=True,dependents=True):
        """
        Move to the previous record of the table
        Only one entry in the table is ever considered "Selected"  This is one of several functions that influences
        which record is currently selected. See @Table.first, @Table.previous, @Table.next, @Table.last, @Table.search,
        @Table.set_by_pk

        :return: None
        """
        self.prompt_save()
        if self.current_index > 0:
            self.current_index -= 1
            if dependents: self.requery_dependents()
            if update: self.db.update_elements()

    def search(self, string, update=True, dependents=True):
        """
        Move to the next record in the search table that contains @string.
        Successive calls will search from the current position, and wrap around back to the beginning.
        The search order from @Table.set_search_order() will be used.  If the search order is not set by the user,
        it will default to the 'name' column, or the 2nd column of the table.
        Only one entry in the table is ever considered "Selected"  This is one of several functions that influences
        which record is currently selected. See @Table.first, @Table.previous, @Table.next, @Table.last, @Table.search,
        @Table.set_by_pk

        :param string: The search string
        :return: None
        """

        # callback
        if 'before_search' in self.callbacks.keys():
            if not self.callbacks['before_search'](self.db, self.db.window):
                return

        # See if the string is an element name # TODO this is a bit of an ugly hack, but it works
        if string in self.db.window.AllKeysDict.keys():
            string = self.db.window[string].get()
        if string == '':
            return

        self.prompt_save()
        # First lets make a search order.. TODO: remove this hard coded garbage

        for o in self.search_order:
            # Perform a search for str, from the current position to the end and back
            for i in list(range(self.current_index + 1, len(self.rows))) + list(range(0, self.current_index)):
                if o in self.rows[i].keys():
                    if self.rows[i][o]:
                        if string.lower() in self.rows[i][o].lower():
                            old_index = self.current_index
                            self.current_index = i
                            if dependents: self.requery_dependents()
                            if update: self.db.update_elements()

                            # callback
                            if 'after_search' in self.callbacks.keys():
                                if not self.callbacks['after_search'](self.db, self.db.window):
                                    self.current_index = old_index
                                    self.requery_dependents()
                                    self.db.update_elements(self.table)
                                    return
        return False
        # If we have made it here, then it was not found!
        # sg.Popup('Search term "'+str+'" not found!')
        # TODO: Play sound?

    def set_by_index(self, index, update=True, dependents=True):
        self.current_index = index
        if dependents: self.requery_dependents()
        if update: self.db.update_elements()

    def set_by_pk(self, pk, update=True, dependents=True):
        """
        Move to the record with this primary key
        This is useful when modifying a record (such as renaming).  The primary key can be stored, the record re-named,
        and then the current record selection updated regardless of the new sort order.
        Only one entry in the table is ever considered "Selected"  This is one of several functions that influences
        which record is currently selected. See @Table.first, @Table.previous, @Table.next, @Table.last, @Table.search,
        @Table.set_by_pk
        :param pk: The primary key to move to
        :return: None
        """
        logger.info(f'Setting table {self.table} record by primary key {pk}')
        i = 0
        for r in self.rows:
            if r[self.pk_column] == pk:
                self.current_index = i
                break
            else:
                i += 1

        if dependents: self.requery_dependents(update=update)
        if update: self.db.update_elements(self.table)

    def get_current(self, column, default=""):
        """
        Get the current value pointed to for @column
        You can also use indexing of the @Database object to get the current value of a column
        I.e. db["{Table}].[{column'}]

        :param column: The column you want the value of
        :param default: A value to return if the record is blank
        :return: The value of the column requested
        """
        if self.rows:
            if self.get_current_row()[column] != '':
                return self.get_current_row()[column]
            else:
                return default
        else:
            return default

    def get_current_pk(self):
        """
        Get the primary key of the currently selected record
        :return: the primary key
        """
        return self.get_current(self.pk_column)

    def get_max_pk(self):
        """
        The the highest primary key for this table.
        This can give some insight on what the next inserted primary key will be
        :return: The maximum primary key value currently in the table
        """
        # TODO: Maybe get this right from the table object instead of running a query?
        q = f'SELECT MAX({self.pk_column}) AS highest FROM {self.table};'
        cur = self.con.execute(q)
        records = cur.fetchone()
        return records['highest']

    def get_current_row(self):
        """
        Get the sqlite3 row for the currently selected record of this table
        :return: @sqlite3.row
        """
        if self.rows:
            return self.rows[self.current_index]

    def add_selector(self, element):  # _listBox,_pk,_column):
        """
        Use a element such as a listbox as a selector item for this table.
        This can be done via this method, or via auto_map_elements by naming the element key "selector.{Table}"

        :param element: the @PySinpleGUI element used as a selector element
        :return: None
        """
        if type(element) not in [sg.PySimpleGUI.Listbox, sg.PySimpleGUI.Slider, sg.Combo, sg.Table]:
            raise RuntimeError(f'add_selector() error: {element} is not a supported element.')

        logger.info(f'Adding {element.Key} as a selector for the {self.table} table.')
        self.selector.append(element)

    def insert_record(self, column='', value=''):
        """
        Insert a new record. If column and value are passed, it will initially set that column to the value
        (I.e. {Table}.name='New Record). If none are provided, the default values for the column are used, as set in the
        database.
        :param column: The column to set
        :param value: The value to set (I.e "New record")
        :return:
        """
        # todo: you don't add a record if there isn't a parent!!!
        # todo: this is currently filtered out by enabling of the element, but it should be filtered here too!
        # todo: bring back the values parameter

        columns = []
        values = []
        if column != '' and value != '':
            columns.append(column)
            values.append(value)

        # Make sure we take into account the foreign key relationships...
        for r in self.db.relationships:
            if self.table == r.child:
                if r.requery_table:
                    columns.append(r.fk)
                    values.append(self.db[r.parent].get_current_pk())

        columns = ",".join([str(x) for x in columns])
        values = ",".join([str(x) for x in values])
        # We will make a blank record and insert it
        # q = f'INSERT INTO {self.table} ({columns}) VALUES ({q_marks});'
        q = f'INSERT INTO {self.table} '
        if columns != '':
            q += f'({columns}) VALUES ({values});'
        else:
            q += 'DEFAULT VALUES'
        logger.info(q)
        cur = self.con.execute(q)
        self.con.commit()

        # Now we save the new pk
        pk = cur.lastrowid

        # and move to it
        self.requery()  # Don't move to the first record
        self.set_by_pk(pk)
        self.requery_dependents()

        self.db.update_elements()
        self.db.window.refresh()

    def save_record(self, display_message=True, update_elements=True):
        """
        Save the currently selected record
        Saves any changes made via the GUI back to the database.  The before_save and after_save @callbacks will call
        your own functions for error checking if needed!
        :param display_message: Displays a message "Updates saved successfully", otherwise is silent on success
        :return: None
        """
        # Ensure that there is actually something to save
        if not len(self.rows):
            if display_message: sg.popup('There were no updates to save.',keep_on_top=True)
            return SAVE_NONE


        # callback
        if 'before_save' in self.callbacks.keys():
            if self.callbacks['before_save']()==False:
                logger.info("We are not saving!")
                if update_elements: self.db.update_elements(self.table)
                if display_message: sg.popup('Updates not saved.', keep_on_top=True)
                return SAVE_FAIL

        values = []
        # We are updating a record
        q = f'UPDATE {self.table} SET'
        for v in self.db.element_map:
            if v['table'] == self:
                q += f' {v["element"].Key.split(".", 1)[1]}=?,'

                if type(v['element'])==sg.Combo:
                    if type(v['element'].get())==str:
                        val = v['element'].get()
                    else:
                        val=v['element'].get().get_pk()
                else:
                    val=v['element'].get()

                values.append(val)
        if values:
            # there was something to update
            # Remove the trailing comma
            q = q[:-1]

            # Add the where clause
            q += f' WHERE {self.pk_column}={self.get_current(self.pk_column)};'
            logger.info(f'Performing query: {q} {str(values)}')
            self.con.execute(q, tuple(values))

            # callback
            if 'after_save' in self.callbacks.keys():
                if not self.callbacks['after_save'](self.db, self.db.window):
                    self.con.rollback()
                    return SAVE_FAIL

            # If we ,ade it here, we can commit the changes
            self.con.commit()

            # Lets refresh our data
            pk = self.get_current_pk()
            self.requery(update_elements)
            self.set_by_pk(pk,update_elements,False)
            #self.requery_dependents()
            if update_elements:self.db.update_elements(self.table)
            logger.info(f'Record Saved!')
            if display_message: sg.popup('Updates saved successfully!')
            return SAVE_SUCCESS
        else:
            logger.info('Nothing to save.')
            if display_message: sg.popup('There were no updates to save!')
            return SAVE_NONE

    def delete_record(self, cascade=True):
        """
        Delete the currently selected record
        The before_delete and after_delete callbacks are run during this process to give some control over the process

        :param cascade: Delete child records (as defined by @Relationship that were set up) before deleting this record
        :return: None
        """
        # Ensure that there is actually something to delete
        if not len(self.rows):
            return

        # callback
        if 'before_delete' in self.callbacks.keys():
            if not self.callbacks['before_delete'](self.db, self.db.window):
                return

        if cascade:
            msg = 'Are you sure you want to delete this record? Keep in mind that all children will be deleted as well!'
        else:
            msg = 'Are you sure you want to delete this record?'
        answer = sg.popup_yes_no(msg, keep_on_top=True)
        if answer == 'No':
            return True

        # Delete child records first!
        if cascade:
            for qry in self.db.tables:
                for r in self.db.relationships:
                    if r.parent == self.table:
                        q = f'DELETE FROM {r.child} WHERE {r.fk}={self.get_current(self.pk_column)}'
                        self.con.execute(q)
                        logger.info(f'Delete query executed: {q}')
                        self.db[r.child].requery(False)


        q = f'DELETE FROM {self.table} WHERE {self.pk_column}={self.get_current(self.pk_column)};'
        self.con.execute(q)

        # callback
        if 'after_delete' in self.callbacks.keys():
            if not self.callbacks['after_delete'](self.db, self.db.window):
                self.con.rollback()
            else:
                self.con.commit()
        else:
            self.con.commit()

        self.requery(False)  # Don't move to the first record
        self.current_index = self.current_index  # force the current_index to be in bounds! todo should this be done in requery?
        self.requery_dependents()

        logger.info(f'Delete query executed: {q}')
        self.requery(select_first=False)
        self.db.update_elements()

    def get_description_for_pk(self,pk):
        for row in self.rows:
            if row[self.pk_column]==pk:
                return row[self.description_column]
        return None

    def table_values(self,columns=None):
        # Populate entries
        values = []
        column_names=self.column_names if columns == None else columns
        for row in self.rows:
            lst = []
            rels = self.db.get_relationships_for_table(self)
            for col in column_names:
                found = False
                for rel in rels:
                    if col == rel.fk:
                        lst.append(self.db[rel.parent].get_description_for_pk(row[col]))
                        found = True
                        break
                if not found: lst.append(row[col])
            values.append(lst)
        return values

    def get_related_table_for_column(self,col):
        rels = self.db.get_relationships_for_table(self)
        for rel in rels:
            if col == rel.fk:
                return rel.parent
        return self.table # None could be found, return ourself

    def quick_editor(self, pk_update_funct=None,funct_param=None):
        # Reset the keygen to keep consistent naming
        keygen_reset_all()
        db = self.db
        table_name = self.table
        layout = []
        headings = self.column_names.copy()
        visible = [1] * len(headings); visible[0] = 0
        col_width=int(55/(len(headings)-1))
        for i in range(0,len(headings)):
            headings[i]=headings[i].ljust(col_width,' ')

        layout.append(
            selector('quick_edit', table_name, sg.Table, num_rows=10, headings=headings, visible_column_map=visible))
        layout.append(actions("act_quick_edit",table_name,edit_protect=False))
        layout.append([sg.Text('')])
        layout.append([sg.HorizontalSeparator()])
        for col in self.column_names:
            column=f'{table_name}.{col}'
            if col!=self.pk_column:
                layout.append([record(column)])

        quick_win = sg.Window(f'Quick Edit - {table_name}', layout, keep_on_top=True, finalize=True)
        quick_db=Database(sqlite3_database=self.db.con, win=quick_win)

        # Select the current entry to start with
        if pk_update_funct is not None:
            if funct_param is None:
                quick_db[table_name].set_by_pk(pk_update_funct())
            else:
                quick_db[table_name].set_by_pk(pk_update_funct(funct_param))

        while True:
            event, values = quick_win.read()

            if quick_db.process_events(event, values):
                logger.info(f'PySimpleDB event handler handled the event {event}!')
            if event == sg.WIN_CLOSED or event == 'Exit':
                break
            else:
                logger.info(f'This event ({event}) is not yet handled.')
        self.requery()
        quick_win.close()


class Database:
    """
    @Database class
    Maintains an internal version of the actual database
    Tables can be accessed by key, I.e. db['Table_name"] to return a @Table instance
    """

    def __init__(self, db_path=None, win=None, sql_script=None, sqlite3_database=None, sql_commands=None):
        """
        Initialize a new @Database instance

        :param db_path: the name of the database file.  It will be created if it doesn't exist.
        :param sqlite3_database: A sqlite3 database object
        :param win: @PySimpleGUI window instance
        :param sql_commands: (str) SQL commands to run if @sqlite3_database is not present
        :param sql_script: (file) SQL commands to run if @sqlite3_database is not present
        """
        if db_path is not None:
            logger.info(f'Importing database: {db_path}')
            new_database = not os.path.isfile(db_path)
            con = sqlite3.connect(db_path)  # Open our database

        self.imported_database=False
        if sqlite3_database is not None:
            con = sqlite3_database
            new_database = False
            self.imported_database=True

        self.path = db_path  # type: str
        self.window = None
        self._edit_protect=False
        self.tables = {}
        self.element_map = []
        self.event_map = [] # Array of dicts, {'event':, 'function':, 'table':}
        self.relationships = []
        self.callbacks = {}
        self.con = con
        self.con.row_factory = sqlite3.Row
        if sql_commands is not None and new_database:
            # run SQL script if the database does not yet exist
            logger.info(f'Executing sql commands')
            logger.debug(sql_commands)
            self.con.executescript(sql_commands)
            self.con.commit()
        if sql_script is not None and new_database:
            # run SQL script from the file if the database does not yet exist
            self.execute_script(sql_script)

        if win is not None:
            self.auto_bind(win)

    def __del__(self):
        # Only do cleanup if this is not an imported database
        if not self.imported_database:
            # optimize the database for long-term benefits
            if self.path != ':memory:':
                q = 'PRAGMA optimize;'
                self.con.execute(q)
            # Close the connection
            self.con.close()

    # Override the [] operator to retrieve queries by key
    def __getitem__(self, key):
        return self.tables[key]

    def execute_script(self,script):
        with open(script, 'r') as file:
            logger.info(f'Loading script {script} into database.')
            self.con.executescript(file.read())

    def execute(self, q):
        """
        Convenience function to pass along to sqlite3.execute()
        :param q: The query to execute
        :return: sqlite3.cursor
        """
        return self.con.execute(q)

    def commit(self):
        """
        Convience function to pass along to sqlite3.commit()
        :return: None
        """
        self.con.commit()

    def set_callback(self, callback, fctn):
        """
       Set @Database callbacks. A runtime error will be raised if the callback is not supported.
       The following callbacks are supported:
           update_elements Called after elements are updated via @Database.update_elements. This allows for other GUI manipulation on each update of the GUI
           edit_enable Called before editing mode is enabled. This can be useful for asking for a password for example
           edit_disable Called after the editing mode is disabled
           {element_name} Called while updating MAPPED element.  This overrides the default element update implementation.
           Note that the {element_name} callback function needs to return a value to pass to Win[element].update()

       :param callback: The name of the callback, from the list above

       :param fctn: The function to call.  Note, the function must take in two parameters, a @Database instance, and a @PySimpleGUI.Window instance
       :return: None
       """
        logger.info(f'Callback {callback} being set on database')
        supported = ['update_elements', 'edit_enable', 'edit_disable']

        # Add in mapped elements
        for element in self.element_map:
            supported.append(element['element'].Key)

        # Add in other window elements
        for element in self.window.AllKeysDict:
            supported.append(element)

        if callback in supported:
            self.callbacks[callback] = fctn
        else:
            raise RuntimeError(f'Callback "{callback}" not supported. callback: {callback} supported: {supported}')

    def auto_bind(self, win):
        """
        Auto-bind the window to the database, for the purpose of control, event and relationship mapping
        This can happen automatically on @Database creation with a parameter.
        This function literally just groups all of the auto_* methods.  See" @Database.auto_add_tables,
        @Database.auto_add_relationships, @Database.auto_map_elements, @Database.auto_map_events
        :param win: The @PySimpleGUI window
        :return:  None
        """
        self.window = win  # TODO: provide another way to set this manually?
        logger.info('Auto binding starting...')
        self.auto_add_tables()
        self.auto_add_relationships()
        self.auto_map_elements(win)
        self.auto_map_events(win)
        self.requery_all(False)
        self.update_elements()
        logger.info('Auto binding finished!')

    # Add a Table object
    def add_table(self, table, pk_column, description_column, query='', order=''):
        """
        Manually add a table to the @Database
        When you attach to an sqlite database, PySimpleSQL isn't aware of what it contains until this command is run
        Note that @Database.auto_add_tables will do this automatically, which is also called from @Database.auto_bind
        and even from the @Database.__init__ with a parameter

        :param table: The name of the table (must match sqlite)
        :param pk_column: The primary key column
        :param description_column: The column to be used to display to users
        :param query: The initial query for the table.  Set to "SELECT * FROM {Table}" if none is passed
        :param order: The initial sort order for the query
        :return: None
        """
        self.tables.update({table: Table(self, self.con, table, pk_column, description_column, query, order)})
        self[table].set_search_order([description_column])  # set a default sort order

    def add_relationship(self, join, child, fk, parent, pk, requery_table):
        """
        Add a foreign key relationship between two tables of the database
        When you attach an sqlite database, PySimpleSQL isn't aware of the relationships contained until tables are
        added via @Database.add_table, and the relationship of various tables is set with this function.
        Note that @Database.auto_add_relationships will do this automatically from the schema of the sqlite database,
        which also happens automatically with @Database.auto_bind and even from the @Database.__init__ with a parameter
        :param join: The join type of the relationship ('LEFT JOIN', 'INNER JOIN', 'RIGHT JOIN')
        :param child: The child table containing the foreign key
        :param fk: The foreign key column of the child table
        :param parent: The parent table containing the primary key
        :param pk: The primary key column of the parent table
        :param requery_table: Automatically requery the child table if the parent table changes (ON UPDATE CASCADE in sql)

        :return: None
        """
        self.relationships.append(Relationship(join, child, fk, parent, pk, requery_table))

    def get_relationships_for_table(self, table):
        """
        Return the relationships for the passed-in table.
        :param table: The table to get relationships for
        :return: A list of @Relationship objects
        """
        rel = []
        for r in self.relationships:
            if r.child == table.table:
                rel.append(r)
        return rel

    def get_cascaded_relationships(self):
        """
        Return a unique list of the relationships for this table that should requery with this table.
        :return: A unique list of table names
        """
        rel = []
        for r in self.relationships:
            if r.requery_table:
                rel.append(r.parent)
                rel.append(r.child)
        # make unique
        rel = list(set(rel))
        return rel

    def get_parent(self, table):
        """
        Return the parent table for the passed-in table
        :param table: The table (str) to get relationships for
        :return: The name of the Parent table, or '' if there is none
        """
        for r in self.relationships:
            if r.child == table and r.requery_table:
                return r.parent
        return None

    def auto_add_tables(self):
        """
        Automatically add @Table objects from an sqlite database by looping through the tables available.
        When you attach to an sqlite database, PySimpleSQL isn't aware of what it contains until this command is run.
        This is also called by @Database.auto_bind() or even from the @Database.__init__ with a parameter
        Note that @Database.add_table can do this manually on a per-table basis.
        :return: None
        """
        logger.info('Automatically adding tables from the sqlite database...')
        # Ensure we clear any current tables so that successive calls will not double the entries
        self.tables = {}
        q = 'SELECT name FROM sqlite_master WHERE type="table" AND name NOT like "sqlite%";'
        cur = self.con.execute(q)
        records = cur.fetchall()  # TODO: new version of this w/o cur
        for t in records:
            # Now lets get the pk
            # TODO: should we capture on_update, on_delete and match from PRAGMA?
            q2 = f'PRAGMA table_info({t["name"]})'
            cur2 = self.con.execute(q2)
            records2 = cur2.fetchall()
            names = []

            # auto generate description column.  Default it to the 2nd column,
            # but can be overwritten below
            description_column = records2[1]['name']

            pk_column = None
            for t2 in records2:
                names.append(t2['name'])
                if t2['pk']:
                    pk_column = t2['name']
                if t2['name'] == 'name':
                    description_column = t2['name']

            logger.debug(
                f'Adding table {t["name"]} to schema with primary key {pk_column} and description of {description_column}')
            self.add_table(t['name'], pk_column, description_column)
            self.tables[t['name']].column_names = names

    # Make sure to send a list of table names to requery if you want
    # dependent tables to requery automatically
    # TODO: clear relationships first so that successive calls don't add multiple entries.
    def auto_add_relationships(self):
        """
        Automatically add a foreign key relationship between tables of the database. This is done by foregn key constrains
        within the sqlite database.  Automatically requery the child table if the parent table changes (ON UPDATE CASCADE in sql is set)
        When you attach an sqlite database, PySimpleSQL isn't aware of the relationships contained until tables are
        added and the relationship of various tables is set.
        Note that @Database.add_relationship() can do this manually.
        which also happens automatically with @Database.auto_bind and even from the @Database.__init__ with a parameter
        :return: None
        """
        # Ensure we clear any current tables so that successive calls will not double the entries
        self.relationships = []
        for table in self.tables:
            rows = self.con.execute(f"PRAGMA foreign_key_list({table})")
            rows = rows.fetchall()

            for row in rows:
                # Add the relationship if it's in the requery list
                if row['on_update'] == 'CASCADE':
                    logger.info(f'Setting table {table} to auto requery with table {row["table"]}')
                    requery_table = True
                else:
                    requery_table = False

                logger.debug(f'Adding relationship {table}.{row["from"]} = {row["table"]}.{row["to"]}')
                self.add_relationship('LEFT JOIN', table, row['from'], row['table'], row['to'], requery_table)

    # Map an element.
    # Optionally supply an FQ (Foreign Query Object), Primary Key and Foreign Key, and Foreign Feild
    # TV=True Valeu, FV=False Value
    def map_element(self, element, table, column):
        dic = {
            'element': element,
            'table': table,
            'column': column,
        }
        logger.info(f'Mapping element {element.Key}')
        self.element_map.append(dic)

    def auto_map_elements(self, win, keys=None):
        logger.info('Automapping elements...')
        # clear out any previously mapped elements to ensure successive calls doesn't produce duplicates
        self.element_map = []
        for key in win.AllKeysDict.keys():
            element=win[key]
            # Skip this element if there is no metadata present
            if type(element.metadata) is not dict:
                continue
            # If we passed in a cutsom list of elements
            if keys is not None:
                if key not in keys: continue

            # Map Record Element
            if element.metadata['type']==TYPE_RECORD:
                table,col = key.split('.')
                if table in self.tables:
                    if col in self[table].column_names:
                        # Map this element to table.column
                        self.map_element(element, self[table], col)

            # Map Selector Element
            if element.metadata['type']==TYPE_SELECTOR:
                if element.metadata['table'] in self.tables:
                    self[element.metadata['table']].add_selector(element)
                else:
                    logger.info(f'Count not add selector {str(element)}')

    def map_event(self, event, fctn, table=None):
        dic = {
            'event': event,
            'function': fctn,
            'table': table
        }
        logger.info(f'Mapping event {event} to function {fctn}')
        self.event_map.append(dic)

    def replace_event(self,event,function,table=None):
        for e in self.event_map:
            if e['event'] == event:
                e['function'] = function
                e['table'] = table if table is not None else e['table']

    def auto_map_events(self, win):
        logger.info(f'Auto mapping events...')
        # clear out any previously mapped events to ensure successive calls doesn't produce duplicates
        self.event_map = []

        for key in win.AllKeysDict.keys():
            #key = str(key)  # sometimes I end up with an integer element 0? TODO: Research
            element = win[key]
            # Skip this element if there is no metadata present
            if type(element.metadata) is not dict:
                logger.debug(f'Skipping mapping of {key}')
                continue
            if element.metadata['type'] == TYPE_EVENT:
                event_type=element.metadata['event_type']
                table=element.metadata['table']
                function=element.metadata['function']

                funct=None

                event_table=table if table in self.tables else None
                if event_type==EVENT_FIRST:
                    if table in self.tables: funct=self[table].first
                elif event_type==EVENT_PREVIOUS:
                    if table in self.tables: funct=self[table].previous
                elif event_type==EVENT_NEXT:
                    if table in self.tables: funct=self[table].next
                elif event_type==EVENT_LAST:
                    if table in self.tables: funct=self[table].last
                elif event_type==EVENT_SAVE:
                    if table in self.tables: funct=self[table].save_record
                elif event_type==EVENT_INSERT:
                    if table in self.tables: funct=self[table].insert_record
                elif event_type==EVENT_DELETE:
                    if table in self.tables: funct=self[table].delete_record
                elif event_type==EVENT_EDIT_PROTECT_DB:
                    self.edit_protect() # Enable it!
                    funct=self.edit_protect
                elif event_type==EVENT_SAVE_DB:
                    funct=self.save_records
                elif event_type==EVENT_SEARCH:
                    # Build the search box name
                    search_element,command=key.split('.')
                    search_box=f'{search_element}.input_search'
                    if table in self.tables: funct=functools.partial(self[table].search, search_box)
                #elif event_type==EVENT_SEARCH_DB:
                elif event_type == EVENT_QUICK_EDIT:
                    t,c,e=key.split('.')
                    referring_table=table
                    table=self[table].get_related_table_for_column(c)
                    funct=functools.partial(self[table].quick_editor,self[referring_table].get_current,c)
                elif event_type == EVENT_FUNCTION:
                    funct=function
                else:
                    logger.debug(f'Unsupported event_type: {event_type}')


                if funct is not None:
                    self.map_event(key, funct, event_table)



    def edit_protect(self,event=None, values=None):
        logger.info('Toggling edit protect mode.')
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


    def save_records(self, cascade_only=False):
        logger.info(f'Preparing to save records in all tables...')
        msg = None
        #self.window.refresh()  # todo remove?
        i = 0
        tables = self.get_cascaded_relationships() if cascade_only else self.tables
        last_index = len(self.tables) - 1

        successes=0
        failures=0
        no_actions=0
        for t in tables:
            logger.info(f'Saving records for table {t}...')
            result=self[t].save_record(False,update_elements=False)
            if result==SAVE_FAIL:
                failures+=1
            elif result==SAVE_SUCCESS:
                successes+=1
            elif result==SAVE_NONE:
                no_actions+=1
        logger.debug(f'Successes: {successes}, Failures: {failures}, No Actions: {no_actions}')

        if failures==0:
            if successes==0:
                sg.popup('There was nothing to update.', keep_on_top=True)
            else:
                sg.popup('Updates saved successfully!',keep_on_top=True)
        else:
            sg.popup('There was a problem saving some updates.', keep_on_top=True)

        self.update_elements()


    def update_elements(self, table='', edit_protect_only=False):  # table type: str
        # TODO Fix bug where listbox first element is ghost selected
        # TODO: Dosctring
        logger.info('Updating PySimpleGUI elements...')
        # Update the current values
        # d= dictionary (the element map dictionary)

        # Enable/Disable elements based on the edit protection button and presence of a record
        # Note that we also must disable elements if there are no records!
        # TODO FIXME!!!
        win = self.window
        for e in self.event_map:
            if '.edit_protect' in e['event']:
                self.disable_elements(table,self._edit_protect)

        # Disable/Enable action elements based on edit_protect or other situations
        for t in self.tables:
            for m in self.event_map:
                # Disable delete and mapped elements for this table if there are no records in this table or edit protect mode
                hide = len(self[t].rows) == 0 or self._edit_protect
                if '.table_delete' in m['event']:
                    if m['table'] == t:
                        win[m['event']].update(disabled=hide)
                        self.disable_elements(t,hide)

                # Disable insert on children with no parent records or edit protect mode
                parent = self.get_parent(t)
                if parent is not None:
                    hide = len(self[parent].rows) == 0 or self._edit_protect
                else:
                    hide = self._edit_protect
                if '.table_insert' in m['event']:
                    if m['table'] == t:
                        win[m['event']].update(disabled=hide)
                    pass
                # Disable db_save when needed
                # TODO: Disable when no changes to data?
                hide = self._edit_protect
                if '.db_save' in m['event']:
                    win[m['event']].update(disabled=hide)

                # Disable table_save when needed
                # TODO: Disable when no changes to data?
                hide = self._edit_protect
                if '.table_save' in m['event']:
                    win[m['event']].update(disabled=hide)

                # Enable/Disable quick edit buttons
                if '.quick_edit' in m['event']:
                    win[m['event']].update(disabled=hide)
        if edit_protect_only: return

        for d in self.element_map:
            # If the optional table parameter was passed, we will only update elements bound to that table
            if table != '':
                if d['table'].table != table:
                    continue

            updated_val = None


            # If there is a callback for this element, use it
            if d['element'].Key in self.callbacks:
                logger.debug(f'{d["element"].Key} IS IN callbacks')
                self.callbacks[d['element'].Key]()


            elif type(d['element']) is sg.PySimpleGUI.Combo:
                # Update elements with foreign queries first
                # This will basically only be things like comboboxes
                # TODO: move this to only compute if something else changes?
                # see if we can find the relationship to determine which table to get data from
                target_table=None
                rels = self.get_relationships_for_table(d['table'])
                for rel in rels:
                    if rel.fk == d['column']:
                        target_table = self[rel.parent]
                        pk = target_table.pk_column
                        description = target_table.description_column
                        break
                lst = []
                if target_table==None:
                    logger.warning(f"Error! Cound not find a related table for element {d['element'].Key} bound to table {d['table'].table}")
                # Populate the combobox entries
                else:
                    for row in target_table.rows:
                        lst.append(Row(row[pk], row[description]))

    
                    # Map the value to the combobox, by getting the description_column and using it to set the value
                    for row in target_table.rows:
    
                        if row[target_table.pk_column] == d['table'][rel.fk]:
                            for entry in lst:
                                if entry.get_pk() == d['table'][rel.fk]:
                                    updated_val = entry
                                    break
                            break
                d['element'].update(values=lst)
            elif type(d['element']) is sg.PySimpleGUI.Table:
                # Tables use an array of arrays for values.  Note that the headings can't be changed.
                values = d['table'].table_values()
                # Select the current one
                pk = d['table'].get_current_pk()
                index = 0
                found = False
                for v in values:
                    if v[0] == pk:
                        found = True
                        break
                    index += 1
                if not found:
                    index = []
                else:
                    index = [index]
                d['element'].update(values=values, select_rows=index)
                eat_events(self.window)
                continue

            elif type(d['element']) is sg.PySimpleGUI.InputText or type(d['element']) is sg.PySimpleGUI.Multiline:
                # Lets now update the element in the GUI
                # For text objects, lets clear it first...
                d['element'].update('')  # HACK for sqlite query not making needed keys! This will blank it out at least
                updated_val = d['table'][d['column']]

            elif type(d['element']) is sg.PySimpleGUI.Checkbox:
                updated_val = d['table'][d['column']]
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
        for k, table in self.tables.items():
            if len(table.selector):
                for element in table.selector:
                    pk = table.pk_column
                    column = table.description_column
                    if element.Key in self.callbacks:
                        self.callbacks[element.Key]()

                    elif type(element) == sg.PySimpleGUI.Listbox or type(element) == sg.PySimpleGUI.Combo:
                        lst = []
                        for r in table.rows:
                            lst.append(Row(r[pk], r[column]))

                        element.update(values=lst, set_to_index=table.current_index)
                    elif type(element) == sg.PySimpleGUI.Slider:
                        # We need to re-range the element depending on the number of records
                        l = len(table.rows)
                        element.update(value=table._current_index + 1, range=(1, l))

                    elif type(element) is sg.PySimpleGUI.Table:
                        # Populate entries
                        values = table.table_values(element.metadata['columns'])

                        # Get the primary key to select.  We have to use the list above instead of getting it directly
                        # from the table, as the data has yet to be updated
                        pk = table.get_current_pk()
                        index = 0
                        found=False
                        for v in values:
                            if v[0] == pk:
                                found=True
                                break
                            index += 1
                        if not found:
                            index=[]
                        else:
                            index=[index]
                        element.update(values=values,select_rows=index)
                        eat_events(self.window)




        # Run callbacks
        if 'update_elements' in self.callbacks.keys():
            # Running user update function
            logger.info('Running the update_elements callback...')
            self.callbacks['update_elements'](self, self.window)

    def requery_all(self,update=True):
        """
        Requeries all tables in the database
        :return: None
        """
        logger.info('Requerying all tables...')
        for k in self.tables.keys():
            self[k].requery(update)

    def process_events(self, event, values):
        """
        Process mapped events.  This should be called once per iteration.
        Events handled are responsible for requerying and updating elements as needed
        :param event: The event returned by PySimpleGUI.read()
        :param values: the values returned by PySimpleGUI.read()
        :return: True if an event was handled, False otherwise
        """
        if event:
            for e in self.event_map:
                if e['event'] == event:
                    logger.info(f"Executing event {event} via event mapping.")
                    e['function']()
                    logger.info(f'Done processing event!')
                    return True

            # Check for  selector events
            for k, table in self.tables.items():
                if len(table.selector):
                    for element in table.selector:
                        pk = table.pk_column
                        column = table.description_column
                        if element.Key in event and len(table.rows) > 0:
                            if type(element) == sg.PySimpleGUI.Listbox:
                                row = values[element.Key][0]
                                table.set_by_pk(row.get_pk())
                                return True
                            elif type(element) == sg.PySimpleGUI.Slider:
                                table.set_by_index(int(values[event]) - 1)
                                return True
                            elif type(element) == sg.PySimpleGUI.Combo:
                                row = values[event]
                                table.set_by_pk(row.get_pk())
                                return True
                            elif type(element) is sg.PySimpleGUI.Table:
                                index = values[event][0]
                                pk = self.window[event].Values[index][0]
                                table.set_by_pk(pk, True)
        return False

    def disable_elements(self, table_name, disable=None, visible=None):
        """
        Disable all elements assocated with table.
        :param disable: True/False to disable/enable element(s)
        :param table: table name assocated with elements to disable/enable
        :return: None
        """
        for c in self.element_map:
            if c['table'] .table!= table_name:
                continue
            element=c['element']
            if type(element) is sg.PySimpleGUI.InputText or type(element) is sg.PySimpleGUI.MLine or type(
                    element) is sg.PySimpleGUI.Combo or type(element) is sg.PySimpleGUI.Checkbox:
                #if element.Key in self.window.AllKeysDict.keys():
                logger.info(f'Updating element {element.Key} to disabled: {disable}, visiblie: {visible}')
                if disable is not None:
                    element.update(disabled=disable)
                if visible is not None:
                    element.update(visible=visible)


# RECORD SELECTOR ICONS
first_16 = b'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'
previous_24 = b'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'
edit_16 = b'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'
next_16 = b'iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAGz3pUWHRSYXcgcHJvZmlsZSB0eXBlIGV4aWYAAHjarVdZssQmDPznFDkCEovgOCCgKjfI8dMY2fPW5L1UxmWzGAuhbi3j5l9/LvcHfhwyu5ik5Jqzxy/WWLmhU/z51etJPl5PG/i7827ePS8YUwFtOENptr5hPr0+uPeg/n7eFXvDxQTdkk1g2DszOuOtkpjnM0/RBNV5OrkWeatq59OqLbxUsTvIJfoRssfu7UQUWGkkrArMM1Dw17McDcK5G+6CJ+axzoeKfgjs0HC4jwSDvDveY0D/1kDvjHz33EfrP70Pxudm8+GDLbPZCJ0vX1D62viXid9sHB6N+P0LvCmfjmP3WqOsNc/pWsywaDZGeXdbZ3+DhR0mD9dnGZfgTujLdVVcxTevAGd49R2XUiUGKstRpEGNFs2rVVKoGHmyoGVWDtdcCcKVFShRiPuixQLEBhDkoDwdoIuBH13o2rde+ykV7DwIS5kgjPDJt5f7p5e/udxauk1Evjy2gl68mQs1NnL7iVUAhJbhli4D35fB79/wZ1M1Ytk2c8EBm+9HRE/04la4cA5Yl9AeryAnwwTARNg7QRkKQMBnCokyeWEWItixAKAGzTlE7kCAUuIBJTmGHY+E4TLYG98IXWs5ceY9jdgEIFLIQYANfApgxZjAH4kFHGoppJhSyklScammlkOOOeWcJe8g1yRIlCRZRIpUaSWUWFLJRUoptbTKNSAGppqr1FJrbY1dw0YNshrWN8x07qHHnnru0kuvvSnoo1GTZhUtWrUNHmEgTIw8ZJRRR5vkJiLFjDPNPGWWWWdb4NoKK6608pJVVl3tQc1Q/XT9AjUy1PhCaq+TBzXMOpFbBO1wkjZmQIwjAXHZCIDQvDHzhWLkjdzGzFeEsZAYSqaNjRu0EQOEcRKnRQ92L+R+hJtL5Ue48b8h5zZ0/wdyDtB9xu0L1MbOc3ohdrxw29QHeB/WNC4Ot/d4/KbFvvnq9jn8qiHMXp1NsK6mvxX4tn2nUdA6d6etHBdruWabluFnbFd/jqCT26CYCODlPNPVLeRG5NP3qdYRd1/aFF2Quc6wRoQIJOIzCnUgS15iMxNbJ7iR81EilLnYjg7+pW/tI2rm6H7p8uOsdF07bBWnyZsdfNFylrYI8SuGM8LCsZiuQQXRz/ly3EEsJkepUS3reo1Ulcc5qE6JpPUMxpSqYOb5dMa6Ik677KweoWwLimlXEeldm81ucKoiSDPXBxGBZ3I9g95EB1zpGoHJ4iA9nK9WALNbjmfUqpc6TIdKM9VmX+2axSQgaY4G8mOZwzrMSs3n+9kq7LKD9AFMsduQe4R+LtdCBI/3LaqRelTPcGcVM0q7jHIrhBAfZk6mKo0soPR5RYStJzzTPScGGbvxqGQZyNS3VM7+2CxqpQNu53iOEGkKKYzjLrkIDQv+bITS1b93Mz6SwFBY4PACBNXhgjZjZNRFqvZSqM5pCJW2ue6N5w0glBtexKwzS45mqVNsUa7qYaCLUx7nPEI51PI4G8rETWDjKGyn/tLVNX86b1qtZ1nkOL15cdxevIK3wxAOE8xeo6gucWSySxgpVBvtrbQewWh02nkDurcpuSzxM5lnVYeK4Oi52eSTnbhuP0jNuCV15U/sf7wgXkxw4AVj4U1hSKCZXyaLt7cM+I30m7apYqlaMAKvyLujNUo0ixtUDlb4h5PNvhl8e2ldy+PWRcF0gxZ/IZAE/Ne0B+vPWVOF1rb/7ATXnWJWSFAso/y8CNkxeKmdERvpjoeJtFk8jDdM+GfzBOGCDHT1HfKBsAWKjIozWfxTxFT9Md3bFfy358DljSIlaMJnZp+yK72z58AZAtLgeUGhq9qmGdnOfdQ2jl0EnL7OCqlGSdKVys3ZFfvjZ3NvO9xPVf+kOfbgR/NRHHRvt+YpjG5MZUDeqgXSHM3eUPt2moISRc0Bl9fl5HGxdecZbDazzvDQqPzA6u573ftOYXDv24OLpXS4XMWufAbwPtRQFthQ6VWLnaUOltLNY0A8/RijCf5jrydCsDf/Ql7TLIH+xUNFX066jsSS88mRUaP0XfpdqQilJf6ipSd7IuMeS++69HQjbeeQJ6z3V5xsciXInYR24ppKj//gn8MySQB5GpY+7Fpo3dYB9o+53VMbvFgTjbwoEkvJxk1UVJFfwX7xXWWEevXcBoHCriT3GrhXQglhMRBfj2H1hE5UtIcCI+rtHa3EXC2w7cL5rhZgtkyoCcd3UeVQFOUjODgsqsGgiyxBMmWpB3OgIRQ+gJbKzSAOCJWH2mD5uJ2yk/uYQkp+iD7MCjxuDfs3cfvbsuY/tD8TJKizKyD+G3PleeQObj5bAAABhGlDQ1BJQ0MgcHJvZmlsZQAAeJx9kT1Iw0AcxV9TpUVaBO0gopChOlkQFXHUKhShQqgVWnUwufQLmjQkLS6OgmvBwY/FqoOLs64OroIg+AHi5Oik6CIl/i8ptIjx4Lgf7+497t4BQqPMNKtrHND0qplKxMVMdlUMvCKIPoQxDFFmljEnSUl4jq97+Ph6F+NZ3uf+HGE1ZzHAJxLPMsOsEm8QT29WDc77xBFWlFXic+Ixky5I/Mh1xeU3zgWHBZ4ZMdOpeeIIsVjoYKWDWdHUiKeIo6qmU76QcVnlvMVZK9dY6578haGcvrLMdZpDSGARS5AgQkENJZRRRYxWnRQLKdqPe/gHHb9ELoVcJTByLKACDbLjB/+D391a+ckJNykUB7pfbPtjBAjsAs26bX8f23bzBPA/A1d6219pADOfpNfbWvQI6N0GLq7bmrIHXO4AA0+GbMqO5Kcp5PPA+xl9UxbovwV61tzeWvs4fQDS1FXyBjg4BEYLlL3u8e5gZ2//nmn19wNkDXKhWfC+CAAAAAZiS0dEAAAAAAAA+UO7fwAAAAlwSFlzAAALEwAACxMBAJqcGAAAAAd0SU1FB+QIEg0gGAVRCEYAAAJuSURBVDjLnZNLSJRRFMd/95vvMc5YOr6mEYXUoIdp9LBcFFQQVItqEUEPWkRRUC0iCCOElkKhZPs2RS6K2hRpmg+CHlNK6RAKUQRGjxltmmZ05ptv5rQoH1G66A9ncTmc3z3/e89BRJgr2Heb+fIighIRAJrujiCTUTrejvEtmaLGn48rk+QR5VyoKyf6IQSaQRY4s3c9OYaglELjty7HHD4nbOKpNIMJZ3cgL0fycnMPbrei9PQPEfoGjq5z/30Cr1WFUgpgBtC7s5z66lL6YzaM/AjUrQiwOOC78WQ02hqLJwiHetmwqoKJYhOO7pgqmwEUipBIZzEADGQiLZx9PMqZ7StOL1poHiqp3si1zmG8BmDxNwAFk3aWAhdgKZIObCnz0fb6K0srA9dDX35cHf8eIxONMFva7EMyA24FuISUgNttku+1aHsX5/CmqlOFXnP/Mj1vPoBgKgGXYGc1PG4T07RY6fPwLCyU+fNulvg8fwD0GQeCLRo6AmRxlAvLstAVKKVRqGxevXzT1DUchrJ/AADsDGgigODgwmtaKAULtDSDvX0NXS0nrgBw8uS/LTjKhYaAZMhqOm6PxYIcg4Gnzy91tpxoBpJbW+7M/QaOcv3qIJMFw8BSMPDwXkNP04GLQBrA6yv6G6CUon5dLa27KjA0KPNoqUQ8afd3d13uaT7WDEzU7jtHQ/cYpGyIjs/8vsivmTb8S5Qk47J8xxEMQy8aGP5YyYvgGxiK51asIaeglPBYjECBh08D7UztkA4QjoxTHFgtjeeP09H+gGAwGAEiePxs27yH+rU10wW2bdPYd4upi6e38X/1E3nDHDifVZPbAAAAAElFTkSuQmCC'
last_24 = b'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'
next_24 = b'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'
previous_16 = b'iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAG03pUWHRSYXcgcHJvZmlsZSB0eXBlIGV4aWYAAHjarVdpsiS9CfyvU/gIAi2g42iN8A18fKdKqF+/ZcYzX7grukpbISATULn5n38v9y/8OGR2MYnmkrPHL5ZYuKKh/vzKcycfn7t1/G18GnevCcZQwDOcrlRbXzGePl64e1D7PO7UZlhN0JVsAsPemdEY70pinM84RRNU5mnkovKuauPz7LbwUcX+QR7RLyG7794HosBLI2FVYJ6Bgn/uejQI51/xV9wxjnU+FLRDYIdHDNdWOOSTeS8H+ncHfXLybbmv3n+1vjifq42HL77M5iM0fpyg9LPzHxe/bRxeGvHnCbT1mzn2X2voWvNYV2OGR7Mxyrvrnf0OFjZICs9rGZfgn9CW5yq41FffAc7w3TdcnQoxUFmOIg2qtGg+z04dKkaeLHgydw7PmAbhwh0oEcDBRYsFiA0gyKHzdIAuBn7pQs++5dmvk2LnQVjKBGGEV355ud9N/s3l1urbReT15SvoxZu5UGMjt+9YBUBoGW7pcfC9DH7/xp9N1Yhl280KA6tvR0RL9MGt8OAcsC7heaKCnAwTABdh7wRlKAABnykkyuSFWYjgRwVAFZpziNyAAKXEA0pyDDsfCSNksDfeEXrWcuLMexi5aYdPyEGADWIKYMWYwB+JCg7VFFJMKeUkSV0qqeaQY045Z8k7yVUJEiVJFhGVIlWDRk2aVVS1aC1cAnJgKrlI0VJKrewqNqqQVbG+YqRxCy221HKTpq202kGfHnvquUvXXnodPMJAmhh5yNBRRp3kJjLFjDPNPGXqLLMucG2FFVdaecnSVVZ9oWaofrv+AjUy1PhBaq+TF2oYdSJXBO10kjZmQIwjAXHZCIDQvDHzSjHyRm5j5gsjKBJDybSxcYM2YoAwTuK06IXdB3J/hJtL+ke48f9Czm3o/h/IOUD3HbcfUBu7zvUHsROF26c+IPqwprI6/L3H7Z88sX9+mm0O51cJYbZiA9xX7f9E8KMRPX3oDl/uxvAl9FKf9opxejrjMVCLiSI4Ulp5WhKpTyk9IdUmSrOWFXrWcXrIo9Hz6eRIKs87cCED0EdkQTTXcaxQxWbFzaND7H0lPTM9A49f+wUF5FnWuobRjzErOYAyPoR7CO/pdKqfQscAVJJyduwddh+tlK/5iBZolMw4givgkcfwQFMh/0x1FQhMZ6aq9ALL6Ri+OIMyGe3to32KSJ+eIJ2JrHG/OJp5DxSmWY/PpEQZVFDGdtelXGO5mgj1mOW8VEvvgnR5JGTw9CqcY9rYmE4xQmJu7nQLdS8t2b4E3bHtuHYi3g04RlJ9RCN5fH7iNLL4CtBdcEWCWYUoOCrgHMimGlKQUYl19kOvuZOD60bCJeA4SrAaD70u5ASQ3GbjYh2GZwjFr2ws6ClM9dNdqRwG6k81jOtvwqsdAQPt0Gez910PYhEy4kSSORZkpK7qDf4oiIF6OqOi/QJXyPCb4moWvT4ahOhoZzJ76GgaLhxbsp/TWBz6ijos7pGEn2FX98n4hOx9rsLTAtYjHYVmvG8eUaRnCoeskUzjjihEyTaIKj4AbtQqDY1nAiVckvHAg+9k/MMbc/NnHGFaHEKjGB1L30SW8tHT3M7CUuJX9n9EQdl7uocw0uGvKy/S7HrIEjjWZqOlx5NZIJKNjJrPCPBwZoIwARBE6iuE86UzTngNahtAtNddQLFoJ9dxNMo5+Z9p/431KRiHcPT3sx1MZwhNwaODFYhjuuWa+aruD15FdfQjosRZUZguqrqD95ly3PB5gXxm7C9+Iu95W8hx5RsYIPvv6O7e+b7CjZ8VZv/gVdaXRb2EZjESQ7msGtqdxivW9O1x9EU3L+vER9SR2P1EUHuLLRR1RKdpTn25P1X9U6TeSId6fvlgPkLRmOXNDguIgWoPPI6TkRDi4UxC6cmmu464iM9y1yIyiOSrfH0p32N7012RkX6ruvtR92VlDXEK9adcDFDcS/8W4/lEP14GM1ATLRkOnZnHMQORZFGQhiJ5N8v+XhLq3EnJYCDayx3iq+6Du8VVpN9EqFqoZLB+SrXaNyZQk2SpTEPocpwyY9hkIjOpvdXwMBq/srzvcx1DXMMH2C29+LQf0RzaYK7lRxSxsYJYeQ7B0Mgc5lrX4e6nU8Krec8EgHZ/kr/OG+MEL75GbzktDtVP0yuT5Nhujcea24k7l9/MqsjqdLPDFFuCQwSSi9VUHGjxu4kYqQynw/ElvxTzenpFlpW+nfzNQx/MSHeR3vhkjzA2jhduN7XXW79puPbS0nIgTqvTW9ZNxcvo41qe88mg8TnIfOaH+wVh/vr5p4IEJ+3i/gvOrXnbfukWjwAAAYRpQ0NQSUNDIHByb2ZpbGUAAHicfZE9SMNAHMVfU6VFWgTtIKKQoTpZEBVx1CoUoUKoFVp1MLn0C5o0JC0ujoJrwcGPxaqDi7OuDq6CIPgB4uTopOgiJf4vKbSI8eC4H+/uPe7eAUKjzDSraxzQ9KqZSsTFTHZVDLwiiD6EMQxRZpYxJ0lJeI6ve/j4ehfjWd7n/hxhNWcxwCcSzzLDrBJvEE9vVg3O+8QRVpRV4nPiMZMuSPzIdcXlN84FhwWeGTHTqXniCLFY6GClg1nR1IiniKOqplO+kHFZ5bzFWSvXWOue/IWhnL6yzHWaQ0hgEUuQIEJBDSWUUUWMVp0UCynaj3v4Bx2/RC6FXCUwciygAg2y4wf/g9/dWvnJCTcpFAe6X2z7YwQI7ALNum1/H9t28wTwPwNXettfaQAzn6TX21r0COjdBi6u25qyB1zuAANPhmzKjuSnKeTzwPsZfVMW6L8Fetbc3lr7OH0A0tRV8gY4OARGC5S97vHuYGdv/55p9fcDZA1yoVnwvggAAAAGYktHRAAAAAAAAPlDu38AAAAJcEhZcwAACxMAAAsTAQCanBgAAAAHdElNRQfkCBINIC+97K1JAAACYElEQVQ4y52TXUiTURjHf+fd9r77MHVNrZV9WIKiZmC5vOimunB2UXQj9HVX0EVdVBC7LEZkKAp2L0JRNxIERZCiRqRWzDKlMiIvlGxpa829c9u77XThVwv1oj8c+MN5zo//c55zkFKy3qKxa919sWTmDUFb12sUgIxB/o4qbr6Z5AiTpE1WRoNhnFaN+lIXwpaP70QZwEK9EAKHtpsnEzops5mxX9AXGMWrhcnLyTntzrPJ93rqeDRh8F1P0hJJsSRl2Z1rIFaocmBvCTNj/USiOgNT4fadbue92go3jM+5A5EkdZVb6D+6bRWABg4LdHR/oqjyIJtz1TOXvRWXrr6YImZIsCAtgG5kcEm5CgBIh2cJ/Y4wFpy7U7bLfffByA8OFTuJpwBNsNEE88kMiJUz5r8B5eY8Eg550rtv+8XOz1FKHRrxNCQkYJJYBcTTZCkLUOS0I03m+0MzkiqnnQygSEkyo4BJogpJPC2zAFktNHe95N3Ih6ZNNgXVakXTVDRNIyVMQAYzkqRUEKxxBzy6Qs/tszfGB577CjSwqhoOVSOFCZALaf5pIQtwuO0hQLy77ULr8OCr5g02C1a7RkYxg0yjIBfTrAFwOAuWrNHXdOr68LPHPk0AFgukMyhyPUA4BIkkvt6fVDdeA4j1tZ5vDfT2tOjReLLYriQsCrQfK6FufzVCLMxSyMVHIYTAXeNlOhSj0JXLfOgb0YlhYE8OtZ6KmvKtXw0jNfvxaQfCmiOM4BeZ9Zl0Xcfv96Oq6jJwKDBKd/8gxIIAeDwe6r0N+G91MjP9lgKXcyXB/+oPlBYhIzCkoksAAAAASUVORK5CYII='
save_16 = b'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'
add_24 = b'iVBORw0KGgoAAAANSUhEUgAAABgAAAAYCAYAAADgdz34AAAFJElEQVR42qWWa1CUZRTHz3n3wrLLAnKNi7dEYCW5Vo4gaJI2pgx8yIb64ocosssoVqbN9KmZGMsBHafM5Itfisk+wKA5XlMR7AaIhgsIiYTI6rLALqwv7767p/O+LMiOaUXPzH9299lnz+85/+e851mExw89ax2rkJXGivLP21kdrLOs0yzpUQHwEfMG1jbQYAUui4xhISaYQRumTAPJYyLSbRfR9WFk2cBL1Ty/nyX+G0AGq1abF5caUpQMuZYcejbWgknhiRCqN6kApzSBPaMD9IvNis3WFhhv6Ca56U4Xf1fKan8cYC0atXXGMkvIyjV5ULykgIMapxZh4GIiFr86JTfU916Ey+ebwF1jHSe3XMLT5/4OkMHBGyM+yDBvyC2k7JhUFDgEIpDocaPD7ZiJrfwuwhhBBp0RFZAPkFrvduKJ5rPg+LzdxZD86UymAQZ+1xZVkZaav3YVpEctJQEJWSAwYFlEKpY8WeTfORHyqPujga47OtGnAAiJIXj1Xjc0nmsie3VHF28jSzmTacCH5tWxlZat2bAqPpvPlkAjAEwBiIHp8NKS0gAvv++thav2q0pwVV4f8FkjXBpsBevBFnBduLubl+1RAHrUYH9SVWZMTvJyjDRwtXDiGoF4WoVQRvTT+EryawEZfNtdQ+33WlANTkAcHGUfgkN00W/d17BnxxUbTy5QABtDc8KPWXZaKC0iCXUCgVYgYgj6s6Cs6JX4asq7AYBvug5Q273L6N89yX6Ax4fU4ehB62dWcLaMblIAVYvLFm5P2jgfEkxRoOegC4OfUrwH/yGDJWo5bFzycoBFx3u/A6v9GvgPWX3tE38HyQswOGGHGz/8CTcP39qnAE5mV6asT0ibR2wPmnRaOLD6uLrL2Tt+UJ5Tn2fPT79/5/yLMOHxkEMcx4GOEWjd3XVKWdBScMiSFZ0YDGF6A5h0Othf8CPMZWy7+By4PR4YlUSwD9yHC+XWNhWwviYlOzJBR2a9HkM4g72rfppTBu81roBxzsAleXD4tgdOlXW1qhatq17MFhnIpAMG6KEyt21OgF1NmQyQyO0BtkiE0xU3VYuqcrc9UZFeHEbBGi8adQI8E7uJuJKQpTwTFGfMwrTILQGAjuEjNORuQ64e4OohFv5qO8YW+Uj0arC9fgya9w9Vq2W6KC+koeTTOAjWelk+MLCCNFPSCT5ICi+G/LiDAX433tkKPaP1XJYCTHqRpQFRFuC+X3UfDUFf03iR+qAJWuh/8+jCmJh45HakALxk0PjQD6FFoSW4IvbrgAx+tr1Bfc46lLwCiF6Bdy2gKGuU4GQbJPxq8y2bT4YFM60iu9hcufnjeSrAqCXiLNDgBywwF2NG1OEAQLv9dep31c8AODC6ZQQ3A45+MoKt9a5d061iptmVfxGdkpmvAzOXqlEHEOy3Kd5UBMnhXwZY1D36Fj9QDWwNW8LigwUXl+iVRgkOvW1/qNmp7doYipd2HokMsaQFUXiQkg0BZ8HZACo+cn9Sk/DygUo+mUQZUFQAMtLI5Ah2dkzCni3DLreTHmrXMxeOKQzrd+wLNeUXhmJkUCLbpSfOAvWcidJlVQCbxNYQ755tkWB4coAazzqxarvTNTFGj7xwHlw8CLUbSvUp5e8bYOmiaDDro7m6wrgagtQFkm+Sdz0GLuku3Oizw6G9Ipyolbq4H/3jlTk91Etfq4OKguc1MYUvIOZkEsyPV9oaUP+ggK1XkM6cJLx4xmuTPfCfLv3Z43//bfkLo1muAZZ9QHcAAAAASUVORK5CYII='
last_16 = b'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'
add_16 = b'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'
delete_24 = b'iVBORw0KGgoAAAANSUhEUgAAABgAAAAYCAYAAADgdz34AAAEe0lEQVR42rWV21MTVxzHf5sLWQJjEyBAIgkhQHBEHNAXL0/MtC9KbRWofUz+AP8gn3bfnKojrZfptF4Yp30oF2VRp6ZAS7jkTshuuAUDpN9zyIbUALUPzczOZnd2P5/fOb/vOSvQ//wTyi9+aGqyWez2UdHh6NVmZoJfJRLyp0BGnM6A49w5KRsOK9urq/3XYzG1QsDgYmPjaM+tW71GUaQ/79+n5Ph48Ot4XP43uHdgQHJeukRr8/P0x507yof19f4bRYnwMVwQBIo+fUqmEydIC4dp9d27IyUPAAdYart6lZIvXtCHbJbIYqGYoij5jY3+G9GoygU/9fRM6fClx49pBw8aqqpIdLn2JaFQEMOWP4Y3X7wo+YrwtVCI37c4nUSYgdj0tPLl7GwfF4wNDRW8167R4sgI5VWMrFCgwt4eGcxmEk+eJG1hgTLoiS554HIFmi9ckHxXrlAK8GwRzt5j71g7Oig1M0OfT04K+hQFGlGNaLNRbnGR9nZ2iHZ38fz+C9UtLaQuLVFmbi7Ini/Bnz+ntffvDxJjMJDY2kobmkYJjHowGpVLTf6+uTng6OuTrA0NtIWKuQSjYAebLite1FIpMtfUEJuW1LNnfFoEFMHhRiOJHg+tMzhGOxiJyBUxZZKGs2cla309lxQg4QAmQfNq2tvJgbSkX76k7Nu3VMjnOYDBq71e2tjcpDhGqcMrBKVMnzkjWe12LiE2Ekh2WUJwNppMlItEiAXCwA5cWzs7aQOyVCIRHCqDHyrQJQ2nT0vW2lrSXr+mnXR6v4GYYwYVimfWnxo0lMET8XgF/EiBnpTP6uslC4a/NTfHp4pDGZwdDI7K1xk8FgsOLS8fulaOFdT5/ZLn8mUK375NlMsdwHGwZrOpiSeTpKpqcPi/CHR4O6KYffWK4k+ecKixCDdiVOy/CZJqTFE0FqPVTOZQiXAsfHKSYoDrYBPiygV4zgCJSZcgXQvRKK2k08FvlpaObjJb/jpcQ+UxbBt65Qxe4/fz/3lsH0zCR8JEkIg+H/2FxZhMpf4hKQlYcmyAdwCussqLcF45GloL+CZWN7u2W620gwgziQkx5RLcq2pro1nsqHEmWVw8WGgMbgecLX91YoKijx6VKjeicgbfAhxRlNm6dbvdgQZEeA8VG5Esc1FihMSMFf87UhfFmrgJCRf8fP584dTwMGVQeeThw4NmFivPAZ5MJmVEke9F99xuqa21NeDAlk7Ly7wXJUl1NQluN41PT9MXb97sb3Y/dndPdQwM9M7LMu1mMgfwri4OX2HwSCRY3q+7kHT6fAEnVryAlW0GnEtwna+ro1/GxpSBUKhPnyKbyWIZteFTuY2K9rAtMPg29qB0KlUBL5ec8vsDLQAaEdUqnKmpiX6dmFAQ2/6bCwuqUJYgm1kUR+2QCKh6G3tQZmVFHjwCXpJ4PFJ3V1fAAzBh1L9NTSlpwL8FvDKmLpcNiRnF9PTmNjdl7OfHwvXfd5B40XhtbU1Z1bQS/KiFZsPJi++p8inwMkkvTmEkRy2//zcpYDQ3Hbr/xQAAAABJRU5ErkJggg=='
save_24 = b'iVBORw0KGgoAAAANSUhEUgAAABgAAAAYCAYAAADgdz34AAAEp0lEQVR42qWWf0zUZRzH35+7+95PDksKmagXjCTAUNB+2FbN1XZXNJrhlo7MLF1WGksry7GiVm6pqS1tmStnxrIRFVaKrGmuqWvNIA1EYR5gkK418Hvc7/ve0+f5fr8I+ef53T483+fZ7v269/t5ns9BMJ5crhe5yrgsyOzZxHX82kXiyoPN9ivur52OKbMIpOuLe6dZqSrPjiyPW3jcTnI7HXA6HFAUm0in0xRPJEQ0lqBwNIbm7kHRtuPdEMJqNX/22LWALbhv+ToULhTmXAcsutNNK0qzMMnrEd4sN3lcLricdhCRGFIjdPofVSTjcfJZNHzSqYqmX7oILfWjGL3yKH/+yETAQTyyKYCcYp6RsWK1YMndWXiu/AZke9zsQoo7odisSCSTaDl/CS8f78UkxYJd5TnY0xPFdx1JIDEAfLshitDIQlZpGwMcQtXmAHKLBWwW4mIAiWV3eWnN7Bx4OSK3y0kOu4KUpiEai4sfugep/li3yFastLniZjT2p8SPPVaClgZifwk0r49BHa6R2gageksAU0sYYDUANhIr5nnppcpccDTC6bTr0cViCYSjUXGo8yJtPNopsuxWqq/Mw9eXINqG3IQUp5xKC8QGCU2vxnHl30UGoGabH9NKoYsrFn1cVenFK3PzOBoHc62IJ5KI8IaGwhG0911GS0cQlNawIN+DA8N2/KxOluJGJbmGfgeaXj9sABZ/EMCMMgFlzIFFrJ6TRa/Ny4edT00ypVE0FsNoOAo1HBGqGqYRNSSG1RANj4TQGnGLE1o+mQCBpEYY6AT217UagKU7AvAxwG4CFKuY7NDoJoe8FRYhICgtj5ZIc8z8V0uTpmkizWAtpWEUDhElF7HwOKCPAftWm4CnP/KjYBYL26T41Zh4LyRAbvr4CdMPsU4DWAua+H80EiIreAb47Hkzomc/DqCwXHdwz/RszJ/qFSxKsOjCgu826YBxeWKAQFofJUgwiE4OhXDioiqQYAcXTgO7VpkOXtjtR1E5GIDztWUoynZk1Ct61ThmNnI0CXbQy4CdK00HdZ8GMHO27iC4uBQ+jyL4xupfmb/o1feJ84nrY+99owkU7O8yHPT8AWx/xnSwbk8AxXMEHAx4rPj6AN+cE4gz4FwH8P5yE7B+bwC3mYDqW+FzZwgIM+BAjwHoZsB7y0zAhs/9KKkAAxB8uIgBtoz2oD+SQsHBXjAAONsObHzS3IP6fQGUVgg4bRT0F8LnsmXmIJJEweEL3CrYQRff5HeWmg7e+CKAskoD8OAt1wf4qY8BKUInA95+wgQ0NPoZAAYg+IAPPmeGEcU4oiP9QDQFHdBQa0b0VqPhwKVQcMEMCcjMQZQdHB0wHPx5CnizttX4wWlofAi3z9Uj2lt2I6qmeMVYY+B7KiY0iavzietj799fDuGpzmEDcOaUdKD/HmzDkrV1qFmpRyRPEmRCcnSYc7tZivn/gOw58rbKkicmnjJGHvQ1GVHzbuDLrdslIB+K/Tc8viYPFfMJLocU1e+EKW60cSlutRhdjvsOQ4yuaUCMsy/fI3GB9pOErz78G8nEHWPW87nWcpVgQhwZPrIZnuXayjX4H7Qeh+TT7afMAAAAAElFTkSuQmCC'
delete_16 = b'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'
edit_24 = b'iVBORw0KGgoAAAANSUhEUgAAABgAAAAYCAYAAADgdz34AAADqUlEQVR42qWUW2gUVxjHvzO7O7ubzDYWUZIGY7IumqiNTdHYSB9UlJS+tIog+OAFfKqJVqqg1Ni8iW0JVKxCHrRiElvSFsGHCM2lERWjsKKBjbrgBY2ablxwL9ndc/U7k1WISepuPHCYmd2Z/++c3/fNEJjBeLxuXa3DMC4QwxgmANuLL168Pd29JN/wO/X1VgFjQQwPGIaBByONIU0JzlsC3d3yvQD3hkKGeW3gL9XW9rUhpdIAJAAeFZ79i7fswN08mjEgGTq3k5Z80ZoMhYCfOAEwPKzD7ZkFvcTABoS05w1ItC+dTUDcTs36rMS5vIlQZira0UF4V5cOUVldGiRjjC2o7O19mBdgrGNJJ6OZTZRmVAp8xLWiWbnmrSVycBBSx48rFY3aAFT1IiaEf3FfXyxnAIZvFZz+lslQoJSClAIoEwDlG6Fw5UEwlQmp1lagly4BcTg2z+/p6cxZUbJ98Xwl+S0MLtIApaTiXBAhxHiRfRWgPj2sfGWrCAkGuz5cv/7LnIv84OQiY46P9KCa1TpcSokApRhj+jnldruJ/o1ypXhgR8Rauu3zkvKqcM6ARFvlfs7oUa2FMQ5OpwMVMcDVg2m6AHsUOOf6Wklw1vv3jnS/nTEtIH520TIpxDUsqhsBxOVyYZDUNbDVuN2mrUoDcBe/lO998e1UOVMCnrYucFtu4zqGfYwAu88djvHV68CCAq8N0+c4Q6hoxcL90VTOgNiZwM+o5Ltsxyivt4AwRm0AqrF3gP/jDjjF1a/C1QenMzEJ8PJMYA2q+QeL6sBigmUVKikkySCM4N2mqdVwVCMUuv++bE/kyP/VcQIgPPC3Z+6TX++kI3fLtHev14OFdSl9rnV4PB67oOMAfjk2JlcvOTAqcgYwlqlTLHUlduUHoOFO+MBn2S9WVg22KGS7hsexBjXzdv93H94xJgDw4c3Y5r+jVyWe9BB+oxlo/DnGEqJbNFtUVCN3ljY8P/Wu8KkA+xDwkwbgJHIsApmBQ8oZuaqdv179+ZJvnm3IJXwqwDEENOi3c8K8/yfwmz8CS8dHsAGqP9r1LDIjwOjo6PmioqKv3uxgHKC/DiQ5MpRhN5o3lG3B73MeYwKgtrY2WFdXV9PY2KhKS0ttQDqdFtFo9I9kItH8SU1NOJ/wSYCqqiq99dmWZUFLS4uGXEgkEk3V1dWD+QZPAvj9/kLs8zjq0Fq6i4uLm/r7+wdmGjwJUFFRsRDf0tMYfigcDve9b/Dr8QptdEU3XH9lbwAAAABJRU5ErkJggg=='
first_24 = b'iVBORw0KGgoAAAANSUhEUgAAABgAAAAYCAYAAADgdz34AAAdOXpUWHRSYXcgcHJvZmlsZSB0eXBlIGV4aWYAAHjarZtpdhw7coX/YxVeQmIGloPxHO/Ay/d3gSRFUcPrtluUWKWqIhKJiLhDADTrf/57m//iT64+mBBzSTWlhz+hhuoaT8pz/9Tz3T7hfL//+XjP/vy6+XzD8ZLn0d//5vZ+vvF6/PEDn+P0n1835X3HlXcg+znw+eN1ZT2fXyfJ6+6+bsM7UF33Saolf51qfwca7wfPVN5/4cftnT/6v/nphcwqzciFvHPLW/+c7+XOwN9/jX+F79YnPnefOxabh+DrOxgL8tPtfTw+z9cF+mmRP56Z76v/+ezb4rv2vu6/rWV614gnv33Dxm+v+8/LuK8X9p8zcj+/MbKdv9zO+2/vWfZe9+5aSKxoejPqLLb9GIYPdpbcnx9LfGX+RZ7n81X5Kk97BiGfz3g6X8NW64jKNjbYaZvddp3HYQdTDG65zKNzw/nzWvHZVTeIkiU4fNntsq9+EjXnh1vGe152n3Ox57r1XG+Q9fOZlo86y2CWH/njl/nbm//Ol9l7aInsUz7Xink55TXTUOT0nU8RELvfuMWzwB9fb/ifL/mjVA18TMtcuMH29DtEj/ZHbvkTZ8/nIo+3hKzJ8x2AJeLakclYTwSeZH20yT7ZuWwt61gIUGPm1IPrRMDG6CaTdMFTLSa74nRtfibb81kXXXJ6GWwiENEnn4lN9Y1ghRDJnxwKOdSijyHGmGKOxcQaW/IppJhSykkg17LPIceccs4l19yKL6HEkkoupdTSqqseDIw11VxLrbU1ZxoXaozV+Hzjle6676HHnnrupdfeBukzwogjjTzKqKNNN/0EJmaaeZZZZ1vWLJBihRVXWnmVVVfb5Nr2O+y408677LrbZ9TeqP7y9W9Ezb5RcydS+lz+jBqvmpw/hrCCk6iYETEXLBHPigAJ7RSzp9gQnCKnmD3VURTRMcmo2JhpFTFCGJZ1cdvP2P2I3L8UNxPLvxQ390+RMwrdfyJyhtD9GrffRG2K58aJ2K1CrenjqT4+01wx/Hsevv1/H/9DAw2ilvpgVX2zcbnY5kQMuLW2LRWerzGUQS7k7Px0PfPh0ZcDCLlP3klbz+Jq3egJmTHTLiy2bTX6SgQZg8C0HHYlE1YnLcu00GX1Wt1dwIS9AQBBlRtzGpv3yvOOvFhSvZ1Z+JjtXm3wVusRRbEfUmf7mbxrxGPq84+CG/WsbhO7nuy+U2XsCMDsj/frjjP4/WX4aAOZtFud7tltxaiB97KknylnIL96PgPmNf3epbfzflp6+77Ju/dNuKqTIcVOUvdzVHOGrZ0f4+a97rNE5j33qdcYg/Wsj53uFLIyq4Vq66IEuWAjC8nfHd1Z7LLLuVNYcFOIvhDO6N+Vjovyy9G1SNJWy/I0l0tPw8fVZyb/KZwVDdfyXpTVWoHHwrNG2I3Vj9TYHh6OrpZPcqt9WmZJ3bYdH25u1lXbzaX6mHFyivx3MHAE1eIsqyAsK4UWbRy99wE6PMkB9sBQtXOUHci4tmHWolXk9TdqM7d2EqAwFbj1S0plv1yiqOv0KxUKWJ+zUEkuI4XZIwF6Sj1rpDXNJ+z5DXs/Ubo5ofdnrjUOqrPbHVubcRU/LDMs9k0sM3/Km18GsN8T72tqMbOP5KoQZFj1YSUpqx1H4Ub8IoV7DQE8Wiz/IGnegWNk8UvYPnRdOPdxLkxgb/hZIJdPFvlFZOYgd0ZMjUoiDZAwcbSWe+LirP8KdvXnPAf530fz8UQCgZqqmfw4N2EBAcV8zRMO6EIRb5uaKGEmGHuSu2nVOSv8bXJjFqza7mDGrIVSRVplcrhG27tPjdJHMp+Eba3FNEiohECssSjJu9d6E/5dy+5a07YyxcRylR4Xmdj9SAV4gkKAcpUZdWFvtS0yeqiQwiE+PmVIKS7CxR8XezkTJaEdmD97CGvvpCC3ziIz5Ooxtt4KmR88sXDd4YM8PGIq09KsSFa/5pqx+J0SAUwUFXoRnrA1LDjDg1tMLKMByeWncsHVO+GcTyT8Z8LP7yec1ioTguwT8gORrR+U7iixr0SF1vGABolKoaaMrQMa5C9Voms7oNiDYheV4dsNghG+HWw6mNHntj083bKAWB9ocvcAi6y8J3C6HmBlBGCV6h7e9+lvXfc6FuLasTDQPMC+BjBl2wqsXmaJtuW/sxt+7NGXHYV8mwOAXwmoKWdOTxOUHOz0gNPJ73n0P68UYllbLBR0TMaPaQEOYlG0AA3ccHPAFHXtss7KBZ9lCrg8/oFkDAprJql4VKHuTY2YfgGz+qFl53bxAJOKkwYImF7vR3QVaAIJ00NCUhWz+l5I20VoMtC0wBYDkvJ31GfyerPBZf4OeAe0YUXOzWAjJhhCOFSOvAgjUuNcm6J2EGcI0wQXkBuJBBwErwisQllYHwQbNyMsXHBDx6+BHqOqELbikNdiAt0RyNy3NxCP1fhED0m5FxmXNY3S7pIOQKpoFd6Er5A5Ortx89OSYR2rQx486OwUEDU5+4e1ERYvfC2EAci6mag6rjsRf50Fj2tyKR4tqxBjxmRRot23ERARG3eN2mJs7Jlf5DeabwkvyUQRHhemKCo0efAyT6InAFmpwTlcKMfGjBjiwNWGyICLb3j1M1x1xISGrciKYXuGbwaqZgY7TB7w2FkLX3jXua5cxKhRmEiZk0mTnONDrImNGaXCYqBnDyBDJlBl39EE6ItUhFp7YilItBTcMxa0ey6QlaqUfeqTtLgaALldDnjGfGuQSRiws9UxBymSYEUkaKlrzp2A+JBIQIQt986yPTGy0mgDrHtoYyjDhfEk2LDb8EKu3QJddS3uYFGCG7u1YEZuiaHQ3RZ1DL1Sg2OuBCfGdDVDvJqBmRrnYZioVRaphgPlHtpCo1hJLJDN+9k9oUD9VDsOjrHwwZOiG3TvqsMAsAFUIXrSkMzwoVSgDdUD3GxgRk5BNwAVK1sZuU7IJuURguQFdH3E4zbtTA4bScjgh9K55xF9x+aTyaRbg6D4uGdmwqEcKnLQZ1SagGg0fIsiZLCaTHlWqn6DZcITbmRJho+ipSaP9+FTZPnyB36ibhqBEfsj5h9UmDMojIVqQ2vm4tExW2J3u4WtKAPtjHdwQw2TDjYSGebsesqoVbR/YSUhAKI3zeiJew9zIwC2bdCn1mRU5YkKnjyThRCj+jJBAzdQ5QMFwmXr9iAS2EjUgKORVEt+46ZuLV1NgstelRnuPhQK6r0ofnOE+gDqEYIC3TpSyYL0Mn5oenwRlRHszY7LIXqFeZK2cz7cBDLUIQ4gPyZN/mMRFBKcuHOLNWJ0OCoNcBA4QbFAN6tKeeEEp8CjLnzfTTzkGiw+lz8moj5BsikKPs0qbsbhZ2b1wDiysbZArqNso7hA0fHdLtkwQsn8UCOlyBEW9yjJwAzuwKhHw9uh8JHIR7gClHxq8nyA97mhleCNbcMSIO8nECjCiKzlhTApxGJQ5Cj8QTxf0JK/kQpT3w9nQe6mA7LI25vF5NeEVYSX7uYXa9PMThjNbicG1yKvESBPfzxBB3DgtnVwjcJAsJX7XE3Mnx8z/Io+QlyScVel2UVGL8DJiXeQRR3YaFTeJijK9YJuROpYOP/ctkx2R4YVMw7MndtCZzUU0v4LfLGYLNV7g097C7bGs9jAQutjZYhSEq88G/gRKSM4k9bifJhHlhn+nQ+Vg/XjP/ui0XnZLIfAyOSnqHXyzgKIACSuy6ImGAmtcjN9QWoIglM2lqVVWiDsuCco0YA6z83n583ndvJ5ZbHgfuNEQQu+4kGvBOKjxtFA+6ngmpULNaSmbB0LGiXiDiyBJFT3RqBXlppbLxJx2QqAqNOipkfwIOoPGfRcL+IgdBwtuLOWRFCWmt64aZQt9CMNwgABHvVX/NgjflgkpQgIsKtB/thruUe/jtvLOT8VHmVIAIOPsTJJAyNoiQ1KD/y3c5b+Q/0YyR975Y+zXKs8tgOdQF8dEMtGCYDU6EU0vKOa1D+FCazXXDByCLpjvAz28FqFeZ3bMYhh4U7kStBrNcJRVEEAO0dcIBElj0GzM0gD2QUlUliG+S9o/PoPhBulRWhkTD8FUKLK8lmjBeEqz4aSPJHvBCmfIFUjJYhLGT0exeFTv8hz7TsMhZlCr5Ap3GL2mfunMHn/oarVDCdx1YFAaLlCUIEdLlmYAjqdVIGEpAZxI1kKh0hR1hbC8EWeOmWwBWlVKSCnxF5mZBcG6T1IkljxlDgaImQf1i34+Rzp+PrdIAsKj0DykwwPCXkHuJ2miKkveKkm8dk4B6hwpNQDmCqAU2Y7n+bUkLdvIVVEdNBqAzdhH4z+Mm5c39xeyMdGWCS1YC8l6i15+b2olfXpBSfQpvyDg5yntkgl7ovSPD2Z/lTyGp7li3BIiZWrxIAaNMjSVkAwLdx5IMYSBpo8GWtgliYaiYpogh9GJ2/eCtjuVsAjQcHqqj8xWKMLYe47hLG+CT0yniwTCczinUirGJxwZMN46MnT9eNqgOYy/byGAyHYO5K/wWOqxdvlK/x0XJtvZy5DRInwxuWQD5ELCJdM90AmhucBOMoaGGZFPOHx8lVUaaSLz2rUbCXVomgpgk5gD66voh5bUAeBEkFTZFTBA51D+I6ANikNTc1S1eGW0GXcST4QTyzwLa1I1hqsFsJE3Y2ilRk2YylSvK5ba4b7OCb86cj+g6WVqo7HsKWlcpi4um5Yx+qelFEvSeCRXOAbbIJAhrCrbttepbOldOy5M9DcQnl7guPqt4SAFV1rFCTJnpDg4NaZT9o1PMeiNLFFPIxKclPJ2SHgJOnn0UcH7UVn5siXGwAvg46hUUdizCg17Z18VJ6FdFvbgTGUc3HHGBfmnj0ZiiYSHmH6uq8StEhj++DGcwLOICGsA5K/kS3giBqSFjiiTNSmRnbJMUqyaxFjNyWoi7bThSe5cRx3H+kWqwXfhJ7zs7SXUytHDp9kKhT31j5V2cbGn+s6q2SRSwVX7m7Q7bVblPq+YKzSr+pynGhS1z3f9uFC2R2rpSv93WhNq62IHzX9VjTg/xY1ufdZ1G9J/2yv/ljR+coJ80NPfMoJiNbiUzTk12rW5tLXenaqZ388AfRmvrjiOBR0qhoTqqs2aaMpt6VSdifPAVjmKDskN9RVyaKU3IzTSodXemCh8AWUbWUOlAolhaAop7cIq5XTgZ0hsRgTWeBVglbBXMtgcbs6XKCTGEbOQLs6k5lQFaQCil/byQAwNQWd9k7aCZHy6YiGt8duboubXJN5ijIlhP5BfMCe0BQLAXFBBjjKZp+l1oJ3D3knMS7dm+zU1pLZofYNlpGnOE5LDpXsIAkMmd8g0Wmrbpwjulp5rL9iS6qq4kfQROrmrWzkF+tJLNQL8IMJaNY9eCholmzoBZ2brlAADeWoanDaxPHqnlnudmGDo2GaUC7ThAwRapRegUB3D+DUjqcmT2cJyICT+QcLaD+WuiS4CICB1PVpmwzK2YTw2jHAxjlxG8qQQ7T+9o3a7RvhORaGH69E/VDV7ooIfbfeRAAGrBuLJWvjmRVFcTrUMZ4avHh9ez0oDfyNhKPsaoz5Au1S5Mwbsc5tW6qPISlsYA7QeWm1CqX+LPlR/IFHk+SVbftV8AOOzfkPwT/zQYdX8v8Q/B96P5sr95v/S20NUky8yEW0r6gbHq8+QRVwSW46Gqv2NKKA2WEPk5oY2FqkP8jfTkIw8HFNDkLIKCwSUk2Hg9YhvF7Tm4PWoU35AnHF/OKKHyIaUInwapAzhOHUIg2thkIZzlxfzICCDMPNPuxrY340YD8+gH5LQ+3xB9amtBDxvYJw0mVTPVHgG6sZzepIzKmmBoVJFoTpu4M8hvYjLGIgI5dVu3ZqLwIBibVACtQapKvxvOQhE1ZDk2DZAvzAMaKNOoN23xzU/aifzAD+8om6LxPkBxupQJwT7HpkF4hj+F8Rspfn3o6IJMIVH1AvDvv2flVDP2RqX037rm8nIfE58zOJ3xQmovDVU2+LNdUPeeiuPHxkfeESNRDUksHDGV0o3G0figts+9gB+vYIL/xB9F3NZ24HblCzN9X/kOkSoxZZk0AGHMGerHrIX5LU/Jql6As/hdW/VY2sgoztQomVJo7DBEd+0EjDgUbg+d11EQ9BdeAsmgL7g3F49dptAEdpeKV2jqz6FIOgYvY0HwxipdFDYDZg7pPUF7fr3P2OVzTjQs5jCtdH5YXAgYtKJJGGIWnStI6BZhqITpTMrpic8lRfKeV0NmghWCAm+evSKHQHd/XpV5C1ZrmL8QcKrVf8P0qjYqzQdwg17SoSehYtpujI5KNSovZsJLooKPJ0yWMa6/3pTIKu7RWa8925Qg7uq/3hqILxOc/hAXLaZ8Ry06Yg2ZlKy3gRKgl/yMLBg95bhCQp5VBTKev28T+1JW4fIMAZO4jhyZL7+g5mwQquwiKUKBJcncWa0MMVHMdFdtn5LGyM7eyMPMJF6SwgUeqn9Ns2D/N933x8IEujWKY0CxaghNdefameTwqIn/XzUT3UjsmSfG/pINLOYkJioZOIamjeTRYg7k979MA6RYga+Rnff27ogOzzF5H2s/GaqExutRqpa1wN9A4w2H8qDpd/4YC3tsAj7QhrUZy7DJDVy0e3q/UrT/yMuU/hVAfV1jRUCPs7vhtBMZL45k6uX3XXEyMYX7za62hDkH+c/c2zQcz9qhUeaxxI+LqNrMW3N2uW5fXTIwAx8sDLDM5NlIIqV74AaeiajgxiMlAh2a9pojTjU2N8t1Pc3U6BIfFRyBMWVIqkRa82bejI69AyBQPWkyc6fSOW6sap/xDfHY/b+SSnyY6C6tg4e+26YYRwGRTzM5ZasrgicoX1uccCtKVn1D0hM8dxsxHMqkBIlaYISUrO6+gPnMVcZ8fe6oQNVd+hBJBaW5mCFehInOQB0xRmSVaHBhKQgVZ2YF+oYQQ0MwsHzjoomyX4zjmq1TzebXpA6/sHdFogMY2Pitl/5hv12sxfCUc+QFWjmtl/rxnzS9H8VRP9tmZOxVwv8rVoflMz6lyfqrk189uKMb+TTR81k99OCX4SqVd3LmIYtKwafKCWDc7DdGdbwIgrqrrkl2WGKsSjnK5iO6lxLS+I1SbrXY6Y0p1RbGcCx3obvPd5itFADMMN4WxAfBDQ6KHjbdpqrHSCuA/gLR0b+/leZLMwudABGsYTdp0QsJcSz5a2QARnWptU77HtWImU+IjSborWtErWZHcL9m5ltKdR9dhz57DnTA0GHgFzQVV59FXuOZSJR8K7Jy5Zxw4LidMA/4Gbwl/ovAQs6ZxbCCptGNTV7VInuD5y7Eear9dLuQkzoCnrso+6+c2aB+HntLGTRqAoy0JAb7zbpkryofsKCuXTbBWQfTZbJ/AEaMSzhQ34L0CTsLmBEO7lUp56J4zj0fc6XNW9Og6DtWy4VUgu8E5YGwtUZIGkDL2ByqqL/RTeH+uu+xFP2R5Eb+N6EHD5mh1oDBFRa+//JPKatkOWgjlOc0VbGZf5rpFBqpmKJuae62p316OE18w4JNm/YGY+FJ75o5l5j5j9zc5o+2e/mxemwTQ6kOXCb+xKLKd5Zdcd9Oxf3G7D22vQmSjtDFRKJJ3NEziiFii95Qk9AaZ8r1SYepCn5H70mVCkvbnbv6He4iG3Yu6eHnIJszqE1CzqPfFwtiV+3pSYz2mS2dMke9t/6m4AOCZKvuuwQTntlf1xQmq6e4tIyHPYor7bFr/ftVD/qJ7dVBXzAJNJRHV/r1tVE5zlhhj5dLlN3LPt5WWloRanAw4BPO3TnI1gb9Oi+AboeDbQg1if2YfIig0yT8dSSpTVQ6KO8u4K3h0cgJYaMfslV/UZL72SGmrDnlvr6plqq0iK1/oW+tn/KwPAokI2FwYd9Vmj7ZX4gogfTe23t5tkG1TktJXhNo6uxVJdoPJJkEEi6iBhPnuJGX71ZgjO3dOvdbT37I5Ku6tf49TLUucK74jebcWBD9pq1fZulI1h5eXjgmk6UXQ2pdDmndDpsKR2mtzNncd/9vu01T0+NOr3940Uzxwd3fz3ogQTxy1kcjLdLmDdn1syyTidWb05wIoqF8une2vlH9xb4/GedXHGza/27cO99TjRYdpG4+Jxof5cIhW69pEg1qQOlQeQO3k8awfzyOxBoapFBB8RohpuixYfjc8MKcojaPdJlDsuEvyutW/a0DazDgOqG0pBct2oRvmDrwNDBj5EqY2JXKyptuWyH4m3UlmEN2kfzZWIFV2UWglLq1JRQC1OpFFXm0icWFvRBt67TdW1xXXP4oULg2NfBWrefae762QBLVIq1ik3JuvnDp2HS+cLzPQ6KYkf0dH50C0Z2h48bjU2FF8XHEYdaqs/BW0fZsE3wjdabTcxx1w+8Me+fH9RRNuESztaOsaIGL3nas+0CtCIjbVzNXXsBHfFARU1zUmq+3e7TI1UAE+/aTDkmUBIncDuOjVy7treK4b4HpBtu389x+G6jpuS/lFtbsy7iPCZnTxyodwToUkHNkRROjA0rLbmgfoy74boQi6T9M/pUt68HM/8ceLUdPTBc7YCffoQypgOkByV+0NJoJlRxh2Zq2PwmGid21qvh0aIFXMPYbVnfggJCKBL2ltt3hNcLJ7OpKBl3ltN6dNCY8/7cHtYvww5jDyLFaIMMU0cq0d5vUqCSM510im212KchCKn77E1RI2KKkQo24It5E3V76SMsqYcCAl1sMIdv+peu3qGItbrHgdRBs7PDKTWsAosPIFD1gQ10J3E/HjuL4uoG6BjkDmrMcli5KEk1QF+oenBEtAgmAMmatZXnf+Dxqh1T2zRVm6hg6HMiiNHNadVba3BaR/EUQ6uDmmivM9tG02WsqcM7xHTqUbI0mnIawVTH00bFsglnanMhHiT+BeydMT1TQDzW8wCi9LE+ZwDj1IhI7NG6EtSSbp4TvUozuZ/xFNRBMEMJo0Inu2cptKxwZ3R/f0EaARgyjlLrrhgdRwRZxqnPccPq7h2wI06Usmt9Y9OiN1viPMVWx+bg6NxqVSnDtSoSVMGM4ZnvHoywhEdUa1m+Rw/3eMpx3PcEdoSWwjRPsnz4hBLqgTSCXablcZ1qjKNDpxLc/onTmnm8jHDs9p8qF5Fu4+ijVfRjp0KN4b+KRYVINdoyHgCeIxKGSOhTwvydGnnAz3LdGJR6+z0aQg6krgfVUtSgdY/NKG5T6jJiXraZ9sqyFnbRxt8aC39chhOHUMaGT1WnRLR7KK2Jyo6xqPRQjaqE2pv6biIjP1K6vU3H5IC5n8E7JxwfHG6h/UWiRb4LC8JKaQe74datbqYzutEmTtHpFAfcIzlvbVDWfdAqs4AfxzmV/Qfc0/zk2go+5a071/c2l8WtlBVZeu3LT6CBHii2LRL35PAJHU7hmFpXalPxSqc37os93h+VpNPglhVWWvDYiB5b5sBQiQO+jUEYoqzzEB8NsnlOe/ipyetP0l0HbzUrzBYKU1k9pUY/bmn6CFpA2SpCDscbI9LnGqOVhIaQEnQdW71HK5FBKTVdJTauUYBSiiS3Fi3DKB0g1o8fdWKa7hnoqnvpTN61wjWdLuTOkR2me2kvvflnHNA2UfJvLvff8kPQtOQw/6fhjQ/xvz/DWl+N83fDKlWsT+t4lfQh4NGed5TS88w90ISee+F7mW4CMs7OwWiQ/j6FQ7QrRXWGiFBRrR0yxuhpY80s5R49j3xiNM8MlmdaGwPcJeZDApp1kGJoyMzFQcRTins95T2hNShozNqJAcFexvQvOi0r/cvB3yR1vKR0h3Rr/tLKjpDqObx1rHchYbU7zZ8G+eO8m0M1dc7yk9j8Lpzl0X+cT5dLnWIDEHv77vtW1aea4CQ9/zM96l29FWAURB7Cf+AhFrunu2LBIvCLI+OzwadGg0762Rdmwex45s0J5h/juXXtD6W9c0Yo0Mp+3sG/h8GMyf//gODmc9k/jFY/9PZgb89mn/3B/6tgbT/Nysi/H8BTs43XfmemcAAAAGEaUNDUElDQyBwcm9maWxlAAB4nH2RPUjDQBzFXz+kRSoKdijikKE6WRAVcdQqFKFCqBVadTC59AuaNCQpLo6Ca8HBj8Wqg4uzrg6ugiD4AeLk6KToIiX+Lym0iPHguB/v7j3u3gH+ZpWpZnAcUDXLyKSSQi6/KoReEcYAIoghKDFTnxPFNDzH1z18fL1L8Czvc3+OPqVgMsAnEM8y3bCIN4inNy2d8z5xlJUlhficeMygCxI/cl12+Y1zyWE/z4wa2cw8cZRYKHWx3MWsbKjEU8RxRdUo359zWeG8xVmt1ln7nvyFkYK2ssx1msNIYRFLECFARh0VVGEhQatGiokM7Sc9/EOOXySXTK4KGDkWUIMKyfGD/8Hvbs3i5ISbFEkCPS+2/TEChHaBVsO2v49tu3UCBJ6BK63jrzWBmU/SGx0tfgT0bwMX1x1N3gMud4DYky4ZkiMFaPqLReD9jL4pDwzeAr1rbm/tfZw+AFnqKn0DHBwCoyXKXvd4d7i7t3/PtPv7AQpfcn2R7bUHAAAABmJLR0QAAAAAAAD5Q7t/AAAACXBIWXMAAAsTAAALEwEAmpwYAAAAB3RJTUUH5AgQDBgzFbnvQQAAA7ZJREFUSMfVll1olmUYx3/Xfd/P835s794152Zuzjk7mbnFnAhRSFTUkRqdBFFgkz4OJLWDPqQwIcp0jGgRHaTMyiLN0JA+mBKIhpJF2yooIcgJ4UdzX87tfZ/nvjrY1E23fDvwoAv+Jzf3c/35/6//81yPqCo3sww3udy1B6vav5fh/nMaY1FVnIF5DXdT/VM7r2166boGK9p/lIv951QB8Xlq5y9kx+r66RWICLE4jTyfzc8mtbY0pYExZ3c+lJEv/4gRkSlo3HiAA882S1VJODg3E2rOa0tf7gYWzWlu4vSl+K5nVjXxyL31VGYSs5c8/uqy4oqaKfdaDis9b6wwGz841tVcV55Z/WA9R/vGFjU9Uf/vBDXLIBSi80Nj/NI7QOyVkQt/mXRZ5ZU7aw4rvx87zsNbDw7U3Fq6eMN3pxnNxYCyKbiBApHxw3wMHoNXQBVjx8fVvPELti8XU+aHhh69v75o7ZFe6lIhOT99YtxM0Yq84kXQSfNZ26W8c4eYde8f6VpQU1G84auT3FOW5uxoRC5SsqYAAgGcwKhCNKFAgLFzf/Jz53FWvtk5UF1dUXzgtz4Wl6YAIe2EXKwkpcD3QIDICyoGBeLcaHRoW4uk8wODK++sNZ+fHKAoGRCGjiB0JBOOvIdACrRIgLwKXsYV5GwqXPPu4RO31VUWffTrRTO3OMFV7yDhhZyHEL0xgQGsQOzBy7hADdNzZpUklpwaMVqRDrCTZoNAEiHyYAq3SMkjqDF4lOEf9pzf+m33lhozmE8mExjnCIJxOOcIg5AIg51GwYwEHgtiUYXyxgfybH9yy+Z9J96u9EOUl6TVOUcQBIRBQCIMiFQQ1cI/dhGAGR+ysYECg6MdT7d983XnenuxX9KJBKG1hNaRCByRyrTNZkyRxyLGoggo3PfKHgXOdHc8v3vH/kOtFSkIU0lsYAlDhxeL8B8U6ATB5UpmygB8uqbxbP+uda+/tf3TVjsySDZTpKEL8GIQLUCBmUBsDGLtBJlyeTGNnOqO0/MaBy988lzbwX171w//3SepVAJvLKYQBdaAEZHIgyKoCMY4b83VRI/0dsfAmZ6dL+z+cNfu1gQx+Viw0+RUJq9MEQEwy1/8ePOFvqEFgGSzRZeObHtsPTB87cPpeQ12pLcne/tT773snJ1dnLT7j7a17NXJTVX1CgCyC5stcAtQNYHysLw2mGlWqapFDpgFzAUyyapFMrmnXLv0J1RcVw0NDSxdunRqEFTp6Oi4PiCTXfnf/1X8Az84bDoS2J42AAAAAElFTkSuQmCC'

_keygen={}
def keygen(key,separator='.'):
    global _keygen
    # Generate a unique key by attaching a sequential integer to the end
    if key not in _keygen:
        _keygen[key]=0
    k=key
    if _keygen[key]>0:k+=f'{separator}{str(_keygen[key])}' # only modify the key if it is a duplicate!
    logger.debug(f'Key generated: {k}')
    _keygen[key] += 1
    return k
def keygen_reset(key):
    global _keygen
    _keygen[key]=0
def keygen_reset_all():
    global _keygen
    _keygen={}

def get_record_info(record):
    """
    Take a table.column string and return a tuple of the same
    :param record: A table.column string that needs separated
    :return: (table,column) Tuple of table and column
    """
    return record.split('.')

def actions(key, table, edit_protect=True, navigation=True, insert=True, delete=True, save=True, search=True,
            search_size=(30, 1), bind_return_key=True):
    """
    Allows for easily adding record navigation and elements to the PySimpleGUI window
    The navigation elements are separated into different sections as detailed by the parameters.
    :param table: The table that this "element" will provide actions for
    :param edit_protect: An edit protection mode to prevent accidental changes in the database. It is a button that toggles
                    the ability on an off to prevent accidental changes in the database by enabling/disabling the insert,
                    edit and save buttons.
    :param navigation: The standard << < > >> (First, previous, next, last) buttons for navigation
    :param insert: Button to insert new records
    :param delete: Button to delete current record
    :param save: Button to save record.  Note that the save button feature saves changes made to any table, therefore only one
                 save button is needed per window. This parameter only works if the @actions parameter is set.
    :param search: A search Input element. Size can be specified with the @search_size parameter
    :param search_size: The size of the search input element
    :param bind_return_key: Bind the return key to the search button. Defaults to true
    :return: An element to be used in the creation of PySimpleGUI layouts.  Note that this is already an array, so it
             will not need to be wrapped in [] in your layout code.
    """
    layout = []
    meta = {'type': TYPE_EVENT, 'event_type': None, 'table': None, 'function': None}

    # Database-level events
    if edit_protect:
        meta = {'type': TYPE_EVENT, 'event_type': EVENT_EDIT_PROTECT_DB, 'table': None, 'function': None}
        layout += [sg.B('', key=keygen(f'{key}.edit_protect'), size=(1, 1), button_color=('orange', 'yellow'), image_data=edit_16,
                        metadata=meta)]
    if save:
        meta = {'type': TYPE_EVENT, 'event_type': EVENT_SAVE_DB, 'table': None, 'function': None}
        layout += [sg.B('', key=keygen(f'{key}.db_save'), size=(1, 1), button_color=('white', 'white'), image_data=save_16, metadata=meta)]

    # Table-level events
    if navigation:
        meta = {'type': TYPE_EVENT, 'event_type': EVENT_FIRST, 'table': table, 'function': None}
        layout += [
            sg.B('', key=keygen(f'{key}.table_first'), size=(1, 1), image_data=first_16, metadata=meta)
        ]
        meta = {'type': TYPE_EVENT, 'event_type': EVENT_PREVIOUS, 'table': table, 'function': None}
        layout += [
            sg.B('', key=keygen(f'{key}.table_previous'), size=(1, 1), image_data=previous_16, metadata=meta)
        ]
        meta = {'type': TYPE_EVENT, 'event_type': EVENT_NEXT, 'table': table, 'function': None}
        layout += [
            sg.B('', key=keygen(f'{key}.table_next'), size=(1, 1), image_data=next_16, metadata=meta)
        ]
        meta = {'type': TYPE_EVENT, 'event_type': EVENT_LAST, 'table': table, 'function': None}
        layout += [
            sg.B('', key=keygen(f'{key}.table_last'), size=(1, 1), image_data=last_16, metadata=meta),
        ]
    if insert:
        meta = {'type': TYPE_EVENT, 'event_type': EVENT_INSERT, 'table': table, 'function': None}
        layout += [sg.B('', key=keygen(f'{key}.table_insert'), size=(1, 1), button_color=('black', 'chartreuse3'), image_data=add_16, metadata=meta)]
    if delete:
        meta = {'type': TYPE_EVENT, 'event_type': EVENT_DELETE, 'table': table, 'function': None}
        layout += [sg.B('', key=keygen(f'{key}.table_delete'), size=(1, 1), button_color=('white', 'red'), image_data=delete_16, metadata=meta)]
    if search:
        meta = {'type': TYPE_EVENT, 'event_type': EVENT_SEARCH, 'table': table, 'function': None}
        layout += [
            sg.Input('', key=keygen(f'{key}.input_search'), size=search_size),
            sg.B('Search', key=keygen(f'{key}.table_search'), bind_return_key=bind_return_key, metadata=meta)
        ]

    return layout


# Global variables to set default sizes for the record function below
_default_text_size = (15, 1)
_default_element_size = (30, 1)


def set_text_size(w, h):
    """
    Sets the defualt text (label) size when @record is used"
    :param w: the width desired
    :param h: the height desired
    :return: None
    """
    global _default_text_size
    _default_text_size = (w, h)


def set_element_size(w, h):
    """
    Sets the defualt text (label) size when @record is used.  The size parameter of @record will override this
    :param w: the width desiered
    :param h: the height desired
    :return: None
    """
    global _default_element_size
    _default_element_size = (w, h)


# Define a custom element for quickly adding database rows.
# The automatic functions of PySimpleSQL require the elements to have a properly setup metadata
# todo should I enable elements here for dirty checking?
def record(key, element=sg.I, size=None, label='', no_label=False, label_above=False, quick_editor=True, **kwargs):
    """
    Convenience function for adding PySimpleGUI elements to the window
    The automatic functionality of PySimpleSQL relies on PySimpleGUI elements to have the key {Table}.{name}
    This convenience function will create a text label, along with a element with this naming convention.
    See @set_text_size and @set_element_size for setting default sizes of these elements.

    :param record: The table.column in the database this element will be mapped to
    :param element: The element type desired (defaults to PySimpleGUI.Input)
    :param size: Overrides the default element size that was set with @set_element_size, for this element element only
    :param label: The text/label will automatically be generated from the @column name. If a different text/label is
                 desired, it can be specified here.
    :return: An element to be used in the creation of PySimpleGUI layouts.  Note that this is already an array, so it
             will not need to be wrapped in [] in your layout code.
    """
    global _default_text_size
    global _default_element_size
    table,column=key.split('.')
    layout_element = [
        element('', key=f'{table}.{column}', size=size or _default_element_size, metadata={'type': TYPE_RECORD}, **kwargs)
    ]
    layout_label= [
        sg.T(column.replace('fk', '').replace('_', ' ').capitalize() + ':' if label == '' else label,size=_default_text_size)
    ]
    if no_label:
        layout=layout_element
    elif label_above:
        layout=[
            sg.Col(layout=[layout_label,layout_element])
        ]
    else:
        layout=layout_label+layout_element
    if element==sg.Combo and quick_editor:
        meta = {'type': TYPE_EVENT, 'event_type': EVENT_QUICK_EDIT, 'table': table, 'function': None}
        layout+=[sg.B('', key=keygen(f'{key}.quick_edit'), size=(1, 1), image_data=edit_16, metadata=meta)]
    return layout


def selector(key, table, element=sg.LBox, size=None, columns=None,**kwargs):
    r = random.randint(0, 1000)
    meta={'type': TYPE_SELECTOR, 'table': table}
    if element == sg.Listbox:
        layout = [
            element(values=(), size=size or _default_element_size, key=key, select_mode=sg.LISTBOX_SELECT_MODE_SINGLE,
                    enable_events=True, metadata=meta)]
    elif element == sg.Slider:
        layout = [element(enable_events=True, size=size or _default_element_size, orientation='h',
                          disable_number_display=True, key=key, metadata=meta)]
    elif element == sg.Combo:
        w=_default_element_size[0]
        layout = [element(values=(), size=size or (w,10), readonly=True, enable_events=True, key=key,
                          auto_size_text=False, metadata=meta)]
    elif element == sg.Table:
        required_kwargs=['headings','visible_column_map','num_rows']
        for kwarg in required_kwargs:
            if kwarg not in kwargs:
                raise RuntimeError(f'Table selectors must use the {kwarg} keyword argument.')

        # Make an empty list of values
        vals=[]
        vals.append(['']*len(kwargs['headings']))
        meta['columns']=columns
        layout = [
            element(
                values=vals, headings=kwargs['headings'], visible_column_map=kwargs['visible_column_map'],
                num_rows=kwargs['num_rows'], enable_events=True, key=key, select_mode=sg.TABLE_SELECT_MODE_BROWSE,
                justification='left',metadata=meta
            )
        ]
    else:
        raise RuntimeError(f'Element type "{element}" not supported as a selector.')
    return layout


