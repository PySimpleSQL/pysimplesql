"""## DISCLAIMER: While **pysimplesql** works with and was inspired by the excellent
PySimpleGUI™ project, it has no affiliation.

## Rapidly build and deploy database applications in Python **pysimplesql** binds
PySimpleGUI to various databases for rapid, effortless database application
development. Makes a great replacement for MS Access or LibreOffice Base! Have the
full power and language features of Python while having the power and control of
managing your own codebase. **pysimplesql** not only allows for super simple
automatic control (not one single line of SQL needs written to use **pysimplesql**),
but also allows for very low level control for situations that warrant it.

----------------------------------------------------------------------------------------
NAMING CONVENTIONS USED THROUGHOUT THE SOURCE CODE
----------------------------------------------------------------------------------------
There is a lot of ambiguity with database terminology, as many terms are used
interchangeably in some circumstances, but not in others.  The Internet has post after
post debating this topic.  See one example here:
https://dba.stackexchange.com/questions/65609/column-vs-field-have-i-been-using-these-terms-incorrectly  # fmt: skip
To avoid confusion in the source code, specific naming conventions will be used whenever
possible.

Naming conventions can fall under 4 categories:
- referencing the database (variables, functions, etc. that relate to the database)
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
    r, row, rows, df - A row, or collection of rows from  querying the database
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
----------------------------------------------------------------------------------------
"""  # noqa: E501

from __future__ import annotations  # docstrings

import asyncio
import calendar
import contextlib
import dataclasses as dc
import datetime as dt
import enum
import functools
import inspect
import itertools
import locale
import logging
import math
import os.path
import queue
import re
import threading
import tkinter as tk
import tkinter.font as tkfont
from abc import ABC, abstractmethod
from decimal import Decimal, DecimalException
from time import sleep, time
from tkinter import ttk
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    ClassVar,
    Dict,
    List,
    Literal,
    Optional,
    Tuple,
    Type,
    TypedDict,
    TypeVar,
    Union,
)

import numpy as np
import pandas as pd
import PySimpleGUI as sg

if TYPE_CHECKING:
    from pathlib import Path

# Wrap optional imports so that pysimplesql can be imported as a single file if desired:
with contextlib.suppress(ModuleNotFoundError, ImportError):
    from .language_pack import *  # noqa F403

with contextlib.suppress(ModuleNotFoundError, ImportError):
    from .theme_pack import *  # noqa F403

try:
    from .reserved_sql_keywords import ADAPTERS as RESERVED
except (ModuleNotFoundError, ImportError):
    # Use common as minimum default
    # fmt: off
    RESERVED = {
        "common": [
            "SELECT", "INSERT", "DELETE", "UPDATE", "DROP", "CREATE", "ALTER", "WHERE",
            "FROM", "INNER", "JOIN", "AND", "OR", "LIKE", "ON", "IN", "SET", "BY",
            "GROUP", "ORDER", "LEFT", "OUTER", "IF", "END", "THEN", "LOOP", "AS",
            "ELSE", "FOR", "CASE", "WHEN", "MIN", "MAX", "DISTINCT",
        ]
    }
    # fmt: on

logger = logging.getLogger(__name__)

# -------------------------------------------
# Set up options for pandas DataFrame display
# -------------------------------------------
pd.set_option("display.max_rows", 15)  # Show a maximum of 15 rows
pd.set_option("display.max_columns", 10)  # Show a maximum of 10 columns
pd.set_option("display.width", 250)  # Set the display width to 250 characters
pd.set_option("display.max_colwidth", 25)  # Set the maximum col width to 25 characters
pd.set_option("display.precision", 2)  # Set the number of decimal places to 2

# ----------------------------------------------
# # Set the locale to the user's default setting
# ----------------------------------------------
locale.setlocale(locale.LC_ALL, "")

# ---------------------------
# Types for automatic mapping
# ---------------------------
TYPE_RECORD: int = 1
TYPE_SELECTOR: int = 2
TYPE_EVENT: int = 3
TYPE_INFO: int = 4

# -----------------
# Transform actions
# -----------------
TFORM_ENCODE: int = 1
"""TODO"""
TFORM_DECODE: int = 0
"""TODO"""

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
PROMPT_SAVE_PROCEED: int = 2
"""After prompt_save, proceeded to save"""
PROMPT_SAVE_NONE: int = 4
"""Found no records changed"""
PROMPT_SAVE_DISCARDED: int = 8
"""User declined to save"""
# ---------------------------
# PROMPT_SAVE MODES
# ---------------------------
PROMPT_MODE: int = 1
"""TODO"""
AUTOSAVE_MODE: int = 2
"""TODO"""
PROMPT_SAVE_MODES = Literal[PROMPT_MODE, AUTOSAVE_MODE]

# ---------------------------
# RECORD SAVE RETURN BITMASKS
# ---------------------------
SAVE_FAIL: int = 1
"""Save failed due to callback or database error"""
SAVE_SUCCESS: int = 2
"""Save was successful"""
SAVE_NONE: int = 4
"""There was nothing to save"""

# ----------------------
# SEARCH RETURN BITMASKS
# ----------------------
SEARCH_FAILED: int = 1  # No result was found
SEARCH_RETURNED: int = 2  # A result was found
SEARCH_ABORTED: int = 4  # The search was aborted, likely during a callback
SEARCH_ENDED: int = 8  # We have reached the end of the search

# ----------------------------
# DELETE RETURNS BITMASKS
# ----------------------------
# TODO Which ones of these are we actually using?
DELETE_FAILED: int = 1  # Delete failed
DELETE_RETURNED: int = 2  # Delete returned
DELETE_ABORTED: int = 4  # The delete was aborted, likely during a callback
DELETE_RECURSION_LIMIT_ERROR: int = 8  # We hit max nested levels

# Mysql sets this as 15 when using foreign key CASCADE DELETE
DELETE_CASCADE_RECURSION_LIMIT: int = 15

# -------
# Sorting
# -------
SORT_NONE = 0
SORT_ASC = 1
SORT_DESC = 2

# ---------------------
# TK/TTK Widget Types
# ---------------------
TK_ENTRY = "Entry"
TK_TEXT = "Text"
TK_COMBOBOX = "Combobox"
TK_CHECKBUTTON = "Checkbutton"
TK_DATEPICKER = "Datepicker"
TK_COMBOBOX_SELECTED = "35"
TK_ANCHOR_MAP = {
    "l": "w",
    "r": "e",
    "c": "center",
}

# --------------
# Misc Constants
# --------------
PK_PLACEHOLDER = "Null"
EMPTY = ["", None]
DECIMAL_PRECISION = 12
DECIMAL_SCALE = 2
TableJustify = Literal["left", "right", "center"]
ColumnJustify = Literal["left", "right", "center", "default"]
HeadingJustify = Literal["left", "right", "center", "column", "default"]

# --------------------
# DateTime formats
# --------------------
DATE_FORMAT = "%Y-%m-%d"
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
DATETIME_FORMAT_MICROSECOND = "%Y-%m-%d %H:%M:%S.%f"
TIMESTAMP_FORMAT = "%Y-%m-%dT%H:%M:%S"
TIMESTAMP_FORMAT_MICROSECOND = "%Y-%m-%dT%H:%M:%S.%f"
TIME_FORMAT = "%H:%M:%S"


class Boolean(enum.Flag):
    """
    Enumeration class providing a convenient way to differentiate when a function may
    return a 'truthy' or 'falsy' value, such as 1, "", or 0.

    Used in `DataSet.value_changed`

    """

    TRUE = True
    """Represents the boolean value True."""
    FALSE = False
    """Represents the boolean value False."""


class ValidateMode(enum.Enum):
    """
    Enumeration class representing different validation modes.
    """

    STRICT = "strict"
    """Strict prevents invalid values from being entered."""
    RELAXED = "relaxed"
    """Relaxed allows invalid input, but ensures validation occurs before saving to the
    database."""
    DISABLED = "disabled"
    """Validation is turned off, and no checks or restrictions are applied."""


class ValidateRule(enum.Enum):
    """
    Mostly internal class. May need to override if creating new custom ColumnClass.
    """

    REQUIRED = "required"
    """Required field. Either set as 'NOTNULL' in database, or later in ColumnClass"""
    PYTHON_TYPE = "python_type"
    """After casting, value is still not correct python type."""
    PRECISION = "precision"
    """Value has too many numerical places"""
    MIN_VALUE = "min_value"
    """Value less than set mininum value"""
    MAX_VALUE = "max_value"
    """Value greater than set maximum value"""
    MIN_LENGTH = "min_length"
    """Value's length is less than minimum length"""
    MAX_LENGTH = "max_length"
    """Value's length is greater than than maximum length"""
    CUSTOM = "custom"
    r"""Special enum to be used when returning a ValidateResponse in your own
    `custom_validate_fn'.

    Example:
        ```python
        import re
        def is_valid_email(email):
            valid_email = re.match(r".+\@.+\..+", email) is not None
            if not valid_email:
                return ss.ValidateResponse(
                    ss.ValidateRule.CUSTOM, email, " is not a valid email"
                )
            return ss.ValidateResponse()
        ```
    """


@dc.dataclass
class ValidateResponse:
    """
    Represents the response returned by `Column.validate` method.

    Attributes:
        exception: Indicates validation failure, if any. None for valid responses.
        value: The value that was being validated.
        rule: The specific `ValidateRule` that caused the exception, if applicable.


    Example:
         How how to create a ok popup from an exception:
        ```python
        response = frm[data_key].column_info[col].validate(value)
        if response.exception:
            msg = f"{ss.lang.dataset_save_validate_error_header}"
            field = ss.lang.dataset_save_validate_error_field.format_map(
                ss.LangFormat(field=col)
            )
            exception = ss.lang[response.exception].format_map(
                ss.LangFormat(value=response.value, rule=response.rule)
            )
            msg += f"{field}{exception}"
            frm.popup.ok(lang.dataset_save_validate_error_title, msg)
        ```

    """

    exception: Union[ValidateRule, None] = None
    value: str = None
    rule: str = None


@dc.dataclass
class _PrevSearch:
    """Internal Class. Keeps track of previous search to cycle through results"""

    search_string: str = None
    column: str = None
    pks: List[int] = dc.field(default_factory=list)


class CellFormatFn:
    """Collection of functions to pre-format values before populating `sg.Table` values.

    Each function must accept and return 1 value. Additional arguments can be filled in
    via a lambda.

    Example:
        ```python
        fn = lambda x: ss.CellFormatFn.decimal_places(x, 2)
        frm[data_key].column_info[col].cell_format_fn = fn
        ```
    """

    @staticmethod
    def bool_to_checkbox(
        val: Union[str, int, bool]
    ) -> Union[themepack.checkbox_true, themepack.checkbox_false]:
        """Converts a boolean value to a themepack.checkbox_true/false"""
        return (
            themepack.checkbox_true
            if checkbox_to_bool(val)
            else themepack.checkbox_false
        )

    @staticmethod
    def decimal_places(val: Union[int, float, Decimal], decimal_places: int):
        """Format the value to specified decimal places using the system locale."""
        format_string = f"%.{decimal_places}f"
        if val not in EMPTY:
            return locale.format_string(format_string, val)
        return val


# -------
# CLASSES
# -------
# TODO: Combine _TableRow and _ElementRow into one class for simplicity
class _TableRow(list):

    """Convenience class used by Tables to associate a primary key with a row of data.

    Note: This is typically not used by the end user.
    """

    def __init__(self, pk: int, *args, **kwargs) -> None:
        self.pk = pk
        super().__init__(*args, **kwargs)

    def __str__(self):
        return str(self[:])

    def __int__(self):
        if isinstance(self.pk, np.int64):
            return self.pk.tolist()
        return self.pk

    def __repr__(self) -> str:
        # Add some extra information that could be useful for debugging
        return f"_TableRow(pk={self.pk}): {super().__repr__()}"


class _ElementRow:

    """Convenience class used by listboxes and comboboxes to associate a primary key
    with a row of data.

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
        if isinstance(self.pk, np.int64):
            return self.pk.tolist()
        return self.pk

    def get_pk(self):
        # Return the primary key portion of the row
        return self.pk

    def get_val(self):
        # Return the value portion of the row
        return self.val

    def get_pk_ignore_placeholder(self):
        if self.pk == PK_PLACEHOLDER:
            return None
        return self.pk

    def get_instance(self):
        # Return this instance of the row
        return self


@dc.dataclass
class Relationship:
    """
    Args:
        join_type: The join type. I.e. "LEFT JOIN", "INNER JOIN", etc.
        child_table: The table name of the fk table
        fk_column: The child table's foreign key column
        parent_table: The table name of the parent table
        pk_column: The parent table's primary key column
        update_cascade: True if the child's fk_column ON UPDATE rule is 'CASCADE'
        delete_cascade: True if the child's fk_column ON DELETE rule is 'CASCADE'
        driver: A `SQLDriver` instance

    Returns:
        None
    """

    join_type: str
    child_table: str
    fk_column: Union[str, int]
    parent_table: str
    pk_column: Union[str, int]
    update_cascade: bool
    delete_cascade: bool
    driver: Driver

    @property
    def on_update_cascade(self):
        return bool(self.update_cascade and self.driver.update_cascade)

    @property
    def on_delete_cascade(self):
        return bool(self.delete_cascade and self.driver.delete_cascade)

    def __str__(self):
        """Return a join clause when cast to a string."""
        return self.driver.relationship_to_join_clause(self)


@dc.dataclass
class RelationshipStore(list):
    """Used to track primary/foreign key relationships in the database.

    See the following for more information: `SQLDriver.add_relationship` and
    `SQLDriver.auto_add_relationships`.

    Note: This class is not typically used the end user
    """

    driver: SQLDriver

    def get_rels_for(self, table: str) -> List[Relationship]:
        """Return the relationships for the passed-in table.

        Args:
            table: The table to get relationships for

        Returns:
            A list of @Relationship objects
        """
        return [r for r in self if r.child_table == table]

    def get_update_cascade_tables(self, table: str) -> List[str]:
        """Return a unique list of the relationships for this table that should requery
        with this table.

        Args:
            table: The table to get cascaded children for

        Returns:
            A unique list of table names
        """
        rel = [
            r.child_table
            for r in self
            if r.parent_table == table and r.on_update_cascade
        ]
        # make unique
        return list(set(rel))

    def get_delete_cascade_tables(self, table: str) -> List[str]:
        """Return a unique list of the relationships for this table that should be
        deleted with this table.

        Args:
            table: The table to get cascaded children for

        Returns:
            A unique list of table names
        """
        rel = [
            r.child_table
            for r in self
            if r.parent_table == table and r.on_delete_cascade
        ]
        # make unique
        return list(set(rel))

    def get_parent(self, table: str) -> Union[str, None]:
        """Return the parent table for the passed-in table.

        Args:
            table: The table (str) to get relationships for

        Returns:
            The name of the Parent table, or None if there is none
        """
        for r in self:
            if r.child_table == table and r.on_update_cascade:
                return r.parent_table
        return None

    def parent_virtual(self, table: str, frm: Form) -> Union[bool, None]:
        """Return True if current row of parent table is virtual.

        Args:
            table: The table (str) to get relationships for
            frm: Form reference

        Returns:
            True if current row of parent table is virtual
        """
        for r in self:
            if r.child_table == table and r.on_update_cascade:
                try:
                    return frm[r.parent_table].pk_is_virtual()
                except AttributeError:
                    return False
        return None

    def get_update_cascade_fk_column(self, table: str) -> Union[str, None]:
        """Return the cascade fk that filters for the passed-in table.

        Args:
            table: The table name of the child

        Returns:
            The name of the cascade-fk, or None
        """
        for r in self:
            if r.child_table == table and r.on_update_cascade:
                return r.fk_column
        return None

    def get_delete_cascade_fk_column(self, table: str) -> Union[str, None]:
        """Return the cascade fk that filters for the passed-in table.

        Args:
            table: The table name of the child

        Returns:
            The name of the cascade-fk, or None
        """
        for r in self:
            if r.child_table == table and r.on_delete_cascade:
                return r.fk_column
        return None

    def get_dependent_columns(self, frm_reference: Form, table: str) -> Dict[str, str]:
        """Returns a dictionary of the `DataSet.key` and column names that use the
        description_column text of the given parent table in their `_ElementRow`
        objects.

        This method is used to determine which GUI field and selector elements to update
        when a new `DataSet.description_column` value is saved. The returned dictionary
        contains the `DataSet.key` as the key and the corresponding column name as the
        value.

        Args:
            frm_reference: A `Form` object representing the parent form.
            table: The name of the parent table.

        Returns:
            A dictionary of `{datakey: column}` pairs.
        """
        return {
            frm_reference[dataset].key: r.fk_column
            for r in self
            for dataset in frm_reference.datasets
            if r.parent_table == table
            and frm_reference[dataset].table == r.child_table
            and not r.on_update_cascade
        }


@dc.dataclass
class ElementMap:

    """Map a PySimpleGUI element to a specific `DataSet` column.

    This is what makes the GUI automatically update to the contents of the database.
    This happens automatically when a PySimpleGUI Window is bound to a `Form` by using
    the bind parameter of `Form` creation, or by executing `Form.auto_map_elements()` as
    long as the Table.column naming convention is used, This method can be used to
    manually map any element to any `DataSet` column regardless of naming convention.

    Args:
        element: A PySimpleGUI Element
        dataset: A `DataSet` object
        column: The name of the column to bind to the element
        where_column: Used for key, value shorthand
        where_value: Used for key, value shorthand

    Returns:
        None
    """

    element: sg.Element
    dataset: DataSet
    column: str
    where_column: str = None
    where_value: str = None

    def __post_init__(self) -> None:
        self.table = self.dataset.table

    def __getitem__(self, key):
        return self.__dict__[key]

    def __setitem__(self, key, value) -> None:
        self.__dict__[key] = value

    def __contains__(self, item) -> bool:
        return item in self.__dict__


@dc.dataclass(eq=False)
class DataSet:

    """`DataSet` objects are used for an internal representation of database tables.

    `DataSet` instances are added by the following `Form` methods: `Form.add_dataset`,
    `Form.auto_add_datasets`. A `DataSet` is synonymous for a SQL Table (though you can
    technically have multiple `DataSet` objects referencing the same table, with each
    `DataSet` object having its own sorting, where clause, etc.).
    Note: While users will interact with DataSet objects often in pysimplesql, they
    typically aren't created manually by the user.

    Args:
        data_key: The name you are assigning to this `DataSet` object (I.e. 'people')
            Accessible via `DataSet.key`.
        frm_reference: This is a reference to the @ Form object, for convenience.
            Accessible via `DataSet.frm`
        table: Name of the table
        pk_column: The name of the column containing the primary key for this table.
        description_column: The name of the column used for display to users (normally
            in a combobox or listbox).
        query: You can optionally set an initial query here. If none is provided, it
            will default to "SELECT * FROM {table}"
        order_clause: The sort order of the returned query. If none is provided it will
            default to "ORDER BY {description_column} ASC"
        filtered: (optional) If True, the relationships will be considered and an
            appropriate WHERE clause will be generated. False will display all records
            in the table.
        prompt_save: (optional) Default: Mode set in `Form`. Prompt to save changes when
            dirty records are present. There are two modes available, `PROMPT_MODE`
            to prompt to save when unsaved changes are present. `AUTOSAVE_MODE` to
            automatically save when unsaved changes are present.
        save_quiet: (optional) Default: Set in `Form`. True to skip info popup on save.
            Error popups will still be shown.
        duplicate_children: (optional) Default: Set in `Form`. If record has children,
            prompt user to choose to duplicate current record, or both.
        validate_mode: `ValidateMode.STRICT` to prevent invalid values from being
            entered. `ValidateMode.RELAXED` allows invalid input, but ensures
            validation occurs before saving to the database.

    Attributes:
        [pysimplesql.pysimplesql.DataSet.key]

    Attributes:
        key: TODO
    """

    instances: ClassVar[List[DataSet]] = []  # Track our own instances

    data_key: dc.InitVar[str]
    frm_reference: dc.InitVar[Form]
    table: str
    pk_column: str
    description_column: str
    """TODO"""
    query: Optional[str] = ""
    order_clause: Optional[str] = ""
    filtered: bool = True
    prompt_save: dc.InitVar[PROMPT_SAVE_MODES] = None
    save_quiet: bool = None
    duplicate_children: bool = None
    validate_mode: ValidateMode = None

    def __post_init__(self, data_key, frm_reference, prompt_save) -> None:
        DataSet.instances.append(self)

        self.key: str = data_key
        """TODO"""
        self.frm = frm_reference
        """TODO"""
        self.driver = self.frm.driver
        """TODO"""
        self.relationships = self.driver.relationships
        """TODO"""
        self.rows: pd.DataFrame = Result.set()
        """TODO"""
        self._current_index: int = 0
        self.column_info: ColumnInfo = None
        """TODO"""
        self.selector: List[str] = []

        # initally empty clauses
        self.join_clause: str = ""
        """TODO"""
        self.where_clause: str = ""  # In addition to generated where clause!
        """TODO"""
        self.search_order: List[str] = []
        """TODO"""

        self._prev_search: _PrevSearch = _PrevSearch()
        self._search_string: tk.StringVar = None

        self.callbacks: CallbacksDict = {}
        self.transform: Optional[Callable[[pd.DataFrame, int], None]] = None
        self._simple_transform: SimpleTransformsDict = {}

        # Todo: do we need dependents?
        self.dependents: list = []

        # handle where values are not passed in:
        # ---------------------------------------
        self._prompt_save = (
            self.frm._prompt_save if prompt_save is None else prompt_save
        )
        if self.duplicate_children is None:
            self.duplicate_children = self.frm.duplicate_children
        if self.save_quiet is None:
            self.save_quiet = self.frm.save_quiet
        if self.validate_mode is None:
            self.validate_mode = self.frm.validate_mode

        # generate generic clauses if none passed in
        if not self.query:
            self.query = self.driver.default_query(self.table)
        if not self.order_clause:
            self.order_clause = self.driver.default_order(self.description_column)

    # Override the [] operator to retrieve current columns by key
    def __getitem__(self, column: str) -> Union[str, int]:
        """Retrieve the value of the specified column in the current row.

        Args:
            column: The key of the column to retrieve.

        Returns:
            The current value of the specified column.
        """
        return self.get_current(column)

    # Override the [] operator to set current columns value
    def __setitem__(self, column, value: Union[str, int]) -> None:
        """Set the value of the specified column in the current row.

        Args:
            column: The key of the column to set.
            value: The value to set the column to.

        Returns:
            None
        """
        self.set_current(column, value)

    @property
    def search_string(self):
        if self._search_string is not None:
            return self._search_string.get()
        return None

    @search_string.setter
    def search_string(self, val: str) -> None:
        if self._search_string is not None:
            self._search_string.set(val)

    # Make current_index a property so that bounds can be respected
    @property
    def current_index(self):
        return self._current_index

    @current_index.setter
    # Keeps the current_index in bounds
    def current_index(self, val: int) -> None:
        if val > self.row_count - 1:
            self._current_index = self.row_count - 1
        elif val < 0:
            self._current_index = 0
        else:
            self._current_index = val

    @classmethod
    def purge_form(cls, frm: Form, reset_keygen: bool) -> None:
        """Purge the tracked instances related to frm.

        Args:
            frm: the `Form` to purge `DataSet`` instances from
            reset_keygen: Reset the keygen after purging?

        Returns:
            None
        """
        new_instances = []
        selector_keys = []

        for dataset in DataSet.instances:
            if dataset.frm != frm:
                new_instances.append(dataset)
            else:
                logger.debug(
                    f"Removing DataSet {dataset.key} related to "
                    f"{frm.driver.__class__.__name__}"
                )
                # we need to get a list of elements to purge from the keygen
                for s in dataset.selector:
                    selector_keys.append(s["element"].key)

        # Reset the keygen for selectors and elements from this Form
        # This is probably a little hack-ish, perhaps I should relocate the keygen?
        if reset_keygen:
            for k in selector_keys:
                keygen.reset_key(k)
            keygen.reset_from_form(frm)
        # Update the internally tracked instances
        DataSet.instances = new_instances

    def set_prompt_save(self, mode: int) -> None:
        """Set the prompt to save action when navigating records.

        Args:
            mode: Use `PROMPT_MODE` to prompt to save when unsaved changes are present.
                `AUTOSAVE_MODE` to automatically save when unsaved changes are present.

        Returns:
            None
        """
        self._prompt_save = mode

    def set_search_order(self, order: List[str]) -> None:
        """Set the search order when using the search box.

        This is a list of column names to be searched, in order

        Args:
            order: A list of column names to search

        Returns:
            None
        """
        self.search_order = order

    def set_callback(
        self, callback: str, fctn: Callable[[Form, sg.Window, DataSet.key], bool]
    ) -> None:
        """Set DataSet callbacks. A runtime error will be thrown if the callback is not
        supported.

        The following callbacks are supported:
            - before_save: called before a record is saved. The save will continue if
                the callback returns true, or the record will rollback if the callback
                returns false.
            - after_save: called after a record is saved. The save will commit to the
                database if the callback returns true, else it will rollback the
                transaction
            - before_update: Alias for before_save
            - after_update:  Alias for after_save
            - before_delete: called before a record is deleted.  The delete will move
                forward if the callback returns true, else the transaction will rollback
            - after_delete: called after a record is deleted. The delete will commit to
                the database if the callback returns true, else it will rollback the
                transaction
            - before_duplicate: called before a record is duplicate.  The duplicate will
                move forward if the callback returns true, else the transaction will
                rollback
            - after_duplicate: called after a record is duplicate. The duplicate will
                commit to the database if the callback returns true, else it will
                rollback the transaction
            - before_search: called before searching.  The search will continue if the
                callback returns True
            - after_search: called after a search has been performed.  The record change
                will undo if the callback returns False
            - record_changed: called after a record has changed (previous,next, etc.)
            - after_record_edit: called after the internal `DataSet` row is edited via a
                `sg.Table` cell-edit, or `field` live-update.

        Args:
            callback: The name of the callback, from the list above
            fctn: The function to call. Note, the function must take at least two
                parameters, a `Form` instance, and a `sg.Window` instance, with
                an optional `DataSet.key`, and return True or False

        Returns:
            None
        """
        logger.info(f"Callback {callback} being set on table {self.table}")
        supported = [
            "before_save",
            "after_save",
            "before_delete",
            "after_delete",
            "before_duplicate",
            "after_duplicate",
            "before_update",
            "after_update",  # Aliases for before/after_save
            "before_search",
            "after_search",
            "record_changed",
            "after_record_edit",
        ]
        if callback in supported:
            # handle our convenience aliases
            callback = "before_save" if callback == "before_update" else callback
            callback = "after_save" if callback == "after_update" else callback
            self.callbacks[callback] = lambda *args: self._invoke_callback(fctn, *args)
        else:
            raise RuntimeError(f'Callback "{callback}" not supported.')

    def _invoke_callback(self, callback, *args):
        # Get the callback's signature
        signature = inspect.signature(callback)

        # Get the number of parameters in the signature
        expected_args = len(signature.parameters)

        if expected_args <= 3:
            return callback(*args[:expected_args])
        raise ValueError("Unexpected number of parameters in the callback function")

    def set_transform(self, fn: callable) -> None:
        """Set a transform on the data for this `DataSet`.

        Here you can set custom a custom transform to both decode data from the
        database and encode data written to the database. This allows you to have dates
        stored as timestamps in the database yet work with a human-readable format in
        the GUI and within PySimpleSQL. This transform happens only while PySimpleSQL
        actually reads from or writes to the database.

        Args:
            fn: A callable function to preform encode/decode. This function should
                take three arguments: query, row (which will be populated by a
                dictionary of the row data), and an encode parameter (1 to encode, 0 to
                decode - see constants `TFORM_ENCODE` and `TFORM_DECODE`). Note that
                this transform works on one row at a time. See the example
                'journal_with_data_manipulation.py' for a usage example.

        Returns:
            None
        """
        self.transform = fn

    def set_query(self, query: str) -> None:
        """Set the query string for the `DataSet`.

        This is more for advanced users.  It defaults to "SELECT * FROM {table};"
        This can override the default

        Args:
            query: The query string you would like to associate with the table

        Returns:
            None
        """
        logger.debug(f"Setting {self.table} query to {query}")
        self.query = query

    def set_join_clause(self, clause: str) -> None:
        """Set the `DataSet` object's join string.

        This is more for advanced users, as it will automatically generate from the
        database Relationships otherwise.

        Args:
            clause: The join clause, such as "LEFT JOIN That on This.pk=That.fk"

        Returns:
            None
        """
        logger.debug(f"Setting {self.table} join clause to {clause}")
        self.join_clause = clause

    def set_where_clause(self, clause: str) -> None:
        """Set the `DataSet` object's where clause.

        This is ADDED TO the auto-generated where clause from Relationship data

        Args:
            clause: The where clause, such as "WHERE pkThis=100"

        Returns:
            None
        """
        logger.debug(
            f"Setting {self.table} where clause to {clause} for DataSet {self.key}"
        )
        self.where_clause = clause

    def set_order_clause(self, clause: str) -> None:
        """Set the `DataSet` object's order clause.

        This is more for advanced users, as it will automatically generate from the
        database Relationships otherwise.

        Args:
            clause: The order clause, such as "Order by name ASC"

        Returns:
            None
        """
        logger.debug(f"Setting {self.table} order clause to {clause}")
        self.order_clause = clause

    def update_column_info(self, column_info: ColumnInfo = None) -> None:
        """Generate column information for the `DataSet` object.

        This may need done, for example, when a manual query using joins is used. This
        is more for advanced users.

        Args:
            column_info: (optional) A `ColumnInfo` instance. Defaults to being generated
                by the `SQLDriver`.

        Returns:
            None
        """
        # Now we need to set  new column names, as the query could have changed
        if column_info is not None:
            self.column_info = column_info
        else:
            self.column_info = self.driver.column_info(self.table)

    def set_description_column(self, column: str) -> None:
        """Set the `DataSet` object's description column.

        This is the column that will display in Listboxes, Comboboxes, Tables, etc. By
        default, this is initialized to either the 'description','name' or 'title'
        column, or the 2nd column of the table if none of those columns exist. This
        method allows you to specify a different column to use as the description for
        the record.

        Args:
            column: The name of the column to use

        Returns:
            None
        """
        self.description_column = column

    def records_changed(self, column: str = None, recursive=True) -> bool:
        """Checks if records have been changed.

        This is done by comparing PySimpleGUI control values with the stored `DataSet`
        values.

        Args:
            column: Limit the changed records search to just the supplied column name
            recursive: True to check related `DataSet` instances

        Returns:
            True or False on whether changed records were found
        """
        logger.debug(f'Checking if records have changed in table "{self.table}"...')

        # Virtual rows wills always be considered dirty
        if self.pk_is_virtual():
            return True

        if self.current_row_has_backup and not self.get_current_row().equals(
            self.get_original_current_row()
        ):
            return True

        dirty = False
        # First check the current record to see if it's dirty
        for mapped in self.frm.element_map:
            # Compare the DB version to the GUI version
            if mapped.table == self.table:
                # if passed custom column name
                if column is not None and mapped.column != column:
                    continue

                # if sg.Text
                if isinstance(mapped.element, sg.Text):
                    continue

                # don't check if there aren't any rows. Fixes checkbox = '' when no
                # rows.
                if not len(self.frm[mapped.table].rows.index):
                    continue

                # Get the element value and cast it, so we can compare it to the
                # database version.
                element_val = self.column_info[mapped.column].cast(mapped.element.get())

                # Get the table value.  If this is a keyed element, we need figure out
                # the appropriate table column.
                table_val = None
                if mapped.where_column is not None:
                    for _, row in self.rows.iterrows():
                        if row[mapped.where_column] == mapped.where_value:
                            table_val = row[mapped.column]
                else:
                    table_val = self[mapped.column]

                new_value = self.value_changed(
                    mapped.column,
                    table_val,
                    element_val,
                    bool(isinstance(mapped.element, sg.Checkbox)),
                )
                if new_value is not Boolean.FALSE:
                    dirty = True
                    logger.debug("CHANGED RECORD FOUND!")
                    logger.debug(
                        f"\telement type: {type(element_val)} "
                        f"column_type: {type(table_val)}"
                    )
                    logger.debug(
                        f"\t{mapped.element.Key}:{element_val} != "
                        f"{mapped.column}:{table_val}"
                    )
                    return dirty

        # handle recursive checking next
        if recursive:
            for rel in self.frm.relationships:
                if rel.parent_table == self.table and rel.on_update_cascade:
                    dirty = self.frm[rel.child_table].records_changed()
                    if dirty:
                        break
        return dirty

    # TODO: How to type-hint this return?
    def value_changed(
        self, column_name: str, old_value, new_value, is_checkbox: bool
    ) -> Union[Any, Boolean]:
        """Verifies if a new value is different from an old value and returns the cast
        value ready to be inserted into a database.

        Args:
            column_name: The name of the column used in casting.
            old_value: The value to check against.
            new_value: The value being checked.
            is_checkbox: Whether or not additional logic should be applied to handle
                checkboxes.

        Returns:
            The cast value ready to be inserted into a database if the new value is
            different from the old value. Returns `Boolean.FALSE` otherwise.
        """
        table_val = old_value
        # convert numpy to normal type
        with contextlib.suppress(AttributeError):
            table_val = table_val.tolist()

        # get cast new value to correct type
        for col in self.column_info:
            if col.name == column_name:
                new_value = col.cast(new_value)
                element_val = new_value
                table_val = col.cast(table_val)
                break

        if is_checkbox:
            table_val = checkbox_to_bool(table_val)
            element_val = checkbox_to_bool(element_val)

        # Sanitize things a bit due to empty values being slightly different in
        # the two cases.
        if table_val is None:
            table_val = ""

        # Strip trailing whitespace from strings
        if isinstance(table_val, str):
            table_val = table_val.rstrip()
        if isinstance(element_val, str):
            element_val = element_val.rstrip()

        # Make the comparison
        # Temporary debug output
        debug = False
        if debug:
            print(
                f"element: {element_val}({type(element_val)})"
                f"db: {table_val}({type(table_val)})"
            )
        if element_val != table_val:
            return new_value if new_value is not None else ""
        return Boolean.FALSE

    def prompt_save(
        self, update_elements: bool = True
    ) -> Union[PROMPT_SAVE_PROCEED, PROMPT_SAVE_DISCARDED, PROMPT_SAVE_NONE, SAVE_FAIL]:
        """Prompts the user, asking if they want to save when changes are detected.

        This is called when the current record is about to change.

        Args:
            update_elements: (optional) Passed to `Form.save_records()` ->
                `DataSet.save_record_recursive()` to update_elements. Additionally used to
                discard changes if user reply's 'No' to prompt.

        Returns:
            A prompt return value of one of the following: `PROMPT_SAVE_PROCEED`,
            `PROMPT_SAVE_DISCARDED`, or `PROMPT_SAVE_NONE`.
        """
        # Return False if there is nothing to check or _prompt_save is False
        if self.current_index is None or not self.row_count or not self._prompt_save:
            return PROMPT_SAVE_NONE

        # See if any rows are virtual
        vrows = len(self.virtual_pks)

        # Check if any records have changed
        changed = self.records_changed() or vrows
        if changed:
            if self._prompt_save == AUTOSAVE_MODE:
                save_changes = "yes"
            else:
                save_changes = self.frm.popup.yes_no(
                    lang.dataset_prompt_save_title, lang.dataset_prompt_save
                )
            if save_changes == "yes":
                # save this record's cascaded relationships, last to first
                if (
                    self.frm.save_records(
                        table=self.table, update_elements=update_elements
                    )
                    & SAVE_FAIL
                ):
                    logger.debug("Save failed during prompt-save. Resetting selectors")
                    # set all selectors back to previous position
                    self.frm.update_selectors()
                    return SAVE_FAIL
                return PROMPT_SAVE_PROCEED
            # if no
            self.purge_virtual()
            self.restore_current_row()

            # set_by_index already takes care of this, but just in-case this method is
            # called another way.
            if vrows and update_elements:
                self.frm.update_elements(self.key)

            return PROMPT_SAVE_DISCARDED
        # if no changes
        return PROMPT_SAVE_NONE

    def requery(
        self,
        select_first: bool = True,
        filtered: bool = True,
        update_elements: bool = True,
        requery_dependents: bool = True,
    ) -> None:
        """Requeries the table.

        The `DataSet` object maintains an internal representation of
        the actual database table. The requery method will query the actual database and
        sync the `DataSet` object to it.

        Args:
            select_first: (optional) If True, the first record will be selected after
                the requery.
            filtered: (optional) If True, the relationships will be considered and an
                appropriate WHERE clause will be generated. If False all records in the
                table will be fetched.
            update_elements: (optional) Passed to `DataSet.first()` to update_elements.
                Note that the select_first parameter must equal True to use this
                parameter.
            requery_dependents: (optional) passed to `DataSet.first()` to
                requery_dependents. Note that the select_first parameter must = True to
                use this parameter.

        Returns:
            None
        """
        join = ""
        where = ""

        if not self.filtered:
            filtered = False

        if filtered:
            # Stop requery short if parent has no records or current row is virtual
            parent_table = self.relationships.get_parent(self.table)
            if parent_table and (
                not len(self.frm[parent_table].rows.index)
                or self.relationships.parent_virtual(self.table, self.frm)
            ):
                # purge rows
                self.rows = Result.set(pd.DataFrame(columns=self.column_info.names))

                if update_elements:
                    self.frm.update_elements(self.key)
                if requery_dependents:
                    self.requery_dependents(update_elements=update_elements)
                return

            # else, get join/where clause like normal
            join = self.driver.generate_join_clause(self)
            where = self.driver.generate_where_clause(self)

        query = self.query + " " + join + " " + where + " " + self.order_clause
        # We want to store our sort settings before we wipe out the current DataFrame
        try:
            sort_settings = self.store_sort_settings()
        except (AttributeError, KeyError):
            sort_settings = [None, SORT_NONE]  # default for first query

        rows = self.driver.execute(query)
        self.rows = rows

        if self.row_count and self.pk_column is not None:
            if "sort_order" not in self.rows.attrs:
                # Store the sort order as a dictionary in the attrs of the DataFrame
                sort_order = self.rows[self.pk_column].to_list()
                self.rows.attrs["sort_order"] = {self.pk_column: sort_order}
            # now we can restore the sort order
            self.load_sort_settings(sort_settings)
            self.sort(self.table)

        # Perform transform one row at a time
        if self.transform is not None:
            self.rows = self.rows.apply(
                lambda row: self.transform(self, row, TFORM_DECODE) or row, axis=1
            )

        # Strip trailing white space, as this is what sg[element].get() does, so we
        # can have an equal comparison. Not the prettiest solution.  Will look into
        # this more on the PySimpleGUI end and make a follow-up ticket.
        # TODO: Is the [:,:] still needed now that we are working with DateFrames?
        self.rows.loc[:, :] = self.rows.applymap(
            lambda x: x.rstrip() if isinstance(x, str) else x
        )

        # fill in columns if empty
        if self.rows.columns.empty:
            self.rows = Result.set(pd.DataFrame(columns=self.column_info.names))

        # reset search string
        self.search_string = ""

        if select_first:
            self.first(
                update_elements=update_elements,
                requery_dependents=requery_dependents,
                skip_prompt_save=True,  # already saved
            )

    def requery_dependents(
        self, child: bool = False, update_elements: bool = True
    ) -> None:
        """Requery parent `DataSet` instances as defined by the relationships of the
        table.

        Args:
            child: (optional) If True, will requery self. Default False; used to skip
                requery when called by parent.
            update_elements: (optional) passed to `DataSet.requery()` ->
                `DataSet.first()` to update_elements.

        Returns:
            None
        """
        if child:
            # dependents=False: no recursive dependent requery
            self.requery(update_elements=update_elements, requery_dependents=False)

        for rel in self.relationships:
            if rel.parent_table == self.table and rel.on_update_cascade:
                logger.debug(
                    f"Requerying dependent table {self.frm[rel.child_table].table}"
                )
                self.frm[rel.child_table].requery_dependents(
                    child=True, update_elements=update_elements
                )

    def first(
        self,
        update_elements: bool = True,
        requery_dependents: bool = True,
        skip_prompt_save: bool = False,
    ) -> None:
        """Move to the first record of the table.

        Only one entry in the table is ever considered "Selected"  This is one of
        several functions that influences which record is currently selected. See
        `DataSet.first()`, `DataSet.previous()`, `DataSet.next()`, `DataSet.last()`,
        `DataSet.search()`, `DataSet.set_by_pk()`, `DataSet.set_by_index()`.

        Args:
            update_elements: (optional) Update the GUI elements after switching records.
            requery_dependents: (optional) Requery dependents after switching records
            skip_prompt_save: (optional) True to skip prompting to save dirty records

        Returns:
            None
        """
        logger.debug(f"Moving to the first record of table {self.table}")
        # prompt_save
        if (
            not skip_prompt_save
            # don't update self/dependents if we are going to below anyway
            and self.prompt_save(update_elements=False) == SAVE_FAIL
        ):
            return

        self.current_index = 0
        if update_elements:
            self.frm.update_elements(self.key)
        if requery_dependents:
            self.requery_dependents(update_elements=update_elements)
        # callback
        if "record_changed" in self.callbacks:
            self.callbacks["record_changed"](self.frm, self.frm.window, self.key)

    def last(
        self,
        update_elements: bool = True,
        requery_dependents: bool = True,
        skip_prompt_save: bool = False,
    ) -> None:
        """Move to the last record of the table.

        Only one entry in the table is ever considered "Selected". This is one of
        several functions that influences which record is currently selected. See
        `DataSet.first()`, `DataSet.previous()`, `DataSet.next()`, `DataSet.last()`,
        `DataSet.search()`, `DataSet.set_by_pk()`, `DataSet.set_by_index()`.

        Args:
            update_elements: (optional) Update the GUI elements after switching records.
            requery_dependents: (optional) Requery dependents after switching records
            skip_prompt_save: (optional) True to skip prompting to save dirty records

        Returns:
            None
        """
        logger.debug(f"Moving to the last record of table {self.table}")
        # prompt_save
        if (
            not skip_prompt_save
            # don't update self/dependents if we are going to below anyway
            and self.prompt_save(update_elements=False) == SAVE_FAIL
        ):
            return

        self.current_index = self.row_count - 1

        if update_elements:
            self.frm.update_elements(self.key)
        if requery_dependents:
            self.requery_dependents()
        # callback
        if "record_changed" in self.callbacks:
            self.callbacks["record_changed"](self.frm, self.frm.window, self.key)

    def next(
        self,
        update_elements: bool = True,
        requery_dependents: bool = True,
        skip_prompt_save: bool = False,
    ) -> None:
        """Move to the next record of the table.

        Only one entry in the table is ever considered "Selected". This is one of
        several functions that influences which record is currently selected. See
        `DataSet.first()`, `DataSet.previous()`, `DataSet.next()`, `DataSet.last()`,
        `DataSet.search()`, `DataSet.set_by_pk()`, `DataSet.set_by_index()`.

        Args:
            update_elements: (optional) Update the GUI elements after switching records.
            requery_dependents: (optional) Requery dependents after switching records
            skip_prompt_save: (optional) True to skip prompting to save dirty records

        Returns:
            None
        """
        if self.current_index < self.row_count - 1:
            logger.debug(f"Moving to the next record of table {self.table}")
            # prompt_save
            if (
                not skip_prompt_save
                # don't update self/dependents if we are going to below anyway
                and self.prompt_save(update_elements=False) == SAVE_FAIL
            ):
                return

            self.current_index += 1
            if update_elements:
                self.frm.update_elements(self.key)
            if requery_dependents:
                self.requery_dependents()
            # callback
            if "record_changed" in self.callbacks:
                self.callbacks["record_changed"](self.frm, self.frm.window, self.key)

    def previous(
        self,
        update_elements: bool = True,
        requery_dependents: bool = True,
        skip_prompt_save: bool = False,
    ) -> None:
        """Move to the previous record of the table.

        Only one entry in the table is ever considered "Selected". This is one of
        several functions that influences which record is currently selected. See
        `DataSet.first()`, `DataSet.previous()`, `DataSet.next()`, `DataSet.last()`,
        `DataSet.search()`, `DataSet.set_by_pk()`, `DataSet.set_by_index()`.

        Args:
            update_elements: (optional) Update the GUI elements after switching records.
            requery_dependents: (optional) Requery dependents after switching records
            skip_prompt_save: (optional) True to skip prompting to save dirty records

        Returns:
            None
        """
        if self.current_index > 0:
            logger.debug(f"Moving to the previous record of table {self.table}")
            # prompt_save
            if (
                not skip_prompt_save
                # don't update self/dependents if we are going to below anyway
                and self.prompt_save(update_elements=False) == SAVE_FAIL
            ):
                return

            self.current_index -= 1
            if update_elements:
                self.frm.update_elements(self.key)
            if requery_dependents:
                self.requery_dependents()
            # callback
            if "record_changed" in self.callbacks:
                self.callbacks["record_changed"](self.frm, self.frm.window, self.key)

    def search(
        self,
        search_string: str,
        update_elements: bool = True,
        requery_dependents: bool = True,
        skip_prompt_save: bool = False,
        display_message: bool = None,
    ) -> Union[SEARCH_FAILED, SEARCH_RETURNED, SEARCH_ABORTED]:
        """Move to the next record in the `DataSet` that contains `search_string`.

        Successive calls will search from the current position, and wrap around back to
        the beginning. The search order from `DataSet.set_search_order()` will be used.
        If the search order is not set by the user, it will default to the description
        column (see `DataSet.set_description_column()`). Only one entry in the table is
        ever considered "Selected"  This is one of several functions that influences
        which record is currently selected. See `DataSet.first()`, `DataSet.previous()`,
        `DataSet.next()`, `DataSet.last()`, `DataSet.search()`, `DataSet.set_by_pk()`,
        `DataSet.set_by_index()`.

        Args:
            search_string: The search string to look for
            update_elements: (optional) Update the GUI elements after switching records.
            requery_dependents: (optional) Requery dependents after switching records
            skip_prompt_save: (optional) True to skip prompting to save dirty records
            display_message: Displays a message "Search Failed: ...", otherwise is
                silent on fail.

        Returns:
            One of the following search values: `SEARCH_FAILED`, `SEARCH_RETURNED`,
            `SEARCH_ABORTED`.
        """
        # See if the string is an element name
        # TODO this is a bit of an ugly hack, but it works
        if search_string in self.frm.window.key_dict:
            search_string = self.frm.window[search_string].get()
        if not search_string or not self.row_count:
            return SEARCH_ABORTED

        logger.debug(
            f'Searching for a record of table {self.table} "'
            f'with search string "{search_string}"'
        )
        logger.debug(f"DEBUG: {self.search_order} {self.rows.columns[0]}")

        # prompt_save
        if (
            not skip_prompt_save
            # don't update self/dependents if we are going to below anyway
            and self.prompt_save(update_elements=False) == SAVE_FAIL
        ):
            return None

        # callback
        if "before_search" in self.callbacks and not self.callbacks["before_search"](
            self.frm, self.frm.window, self.key
        ):
            return SEARCH_ABORTED

        # Reset _prev_search if search_string is different
        if search_string != self._prev_search.search_string:
            self._prev_search = _PrevSearch(search_string)

        # Reorder search_columns to start with the column in _prev_search
        search_columns = self.search_order.copy()
        if self._prev_search.column in search_columns:
            idx = search_columns.index(self._prev_search.column)
            search_columns = search_columns[idx:] + search_columns[:idx]

        # reorder rows to be idx + 1, and wrap around back to the beginning
        rows = self.rows.copy().reset_index()
        idx = self.current_index + 1 % len(rows)
        rows = pd.concat([rows.loc[idx:], rows.loc[:idx]])

        # fill in descriptions for cols in search_order
        rows = self.map_fk_descriptions(rows, self.search_order)

        pk = None
        for column in search_columns:
            # update _prev_search column
            self._prev_search.column = column

            # search through processed rows, looking for search_string
            result = rows[
                rows[column].astype(str).str.contains(str(search_string), case=False)
            ]
            if not result.empty:
                # save index for later, if callback returns False
                old_index = self.current_index

                # grab the first result
                pk = result.iloc[0][self.pk_column]

                # search next column if the same pk is found again
                if pk in self._prev_search.pks:
                    continue

                # if pk is same as one we are on, we can just updated_elements
                if pk == self[self.pk_column]:
                    if update_elements:
                        self.frm.update_elements(self.key)
                    if requery_dependents:
                        self.requery_dependents()
                    return SEARCH_RETURNED

                # otherwise, this is a new pk
                break

        if pk:
            # Update _prev_search with the pk
            self._prev_search.pks.append(pk)

            # jump to the pk
            self.set_by_pk(
                pk=pk,
                update_elements=update_elements,
                requery_dependents=requery_dependents,
                skip_prompt_save=True,
            )

            # callback
            if "after_search" in self.callbacks and not self.callbacks["after_search"](
                self.frm, self.frm.window, self.key
            ):
                self.current_index = old_index
                self.frm.update_elements(self.key)
                self.requery_dependents()
                return SEARCH_ABORTED

            # record changed callback
            if "record_changed" in self.callbacks:
                self.callbacks["record_changed"](self.frm, self.frm.window, self.key)
            return SEARCH_RETURNED

        # didn't find anything
        self.frm.popup.ok(
            lang.dataset_search_failed_title,
            lang.dataset_search_failed.format_map(
                LangFormat(search_string=search_string)
            ),
        )
        return SEARCH_FAILED

    def set_by_index(
        self,
        index: int,
        update_elements: bool = True,
        requery_dependents: bool = True,
        skip_prompt_save: bool = False,
        omit_elements: List[str] = None,
    ) -> None:
        """Move to the record of the table located at the specified index in DataSet.

        Only one entry in the table is ever considered "Selected". This is one of
        several functions that influences which record is currently selected. See
        `DataSet.first()`, `DataSet.previous()`, `DataSet.next()`, `DataSet.last()`,
        `DataSet.search()`, `DataSet.set_by_pk()`, `DataSet.set_by_index()`.

        Args:
            index: The index of the record to move to.
            update_elements: (optional) Update the GUI elements after switching records.
            requery_dependents: (optional) Requery dependents after switching records
            skip_prompt_save: (optional) True to skip prompting to save dirty records
            omit_elements: (optional) A list of elements to omit from updating

        Returns:
            None
        """
        # if already there
        if self.current_index == index:
            return

        logger.debug(f"Moving to the record at index {index} on {self.table}")
        if omit_elements is None:
            omit_elements = []

        if skip_prompt_save is False:
            # see if sg.Table has potential changes
            if len(omit_elements) and self.records_changed(recursive=False):
                # most likely will need to update, either to
                # discard virtual or update after save
                omit_elements = []
            # don't update self/dependents if we are going to below anyway
            if self.prompt_save(update_elements=False) == SAVE_FAIL:
                return

        self.current_index = index
        if update_elements:
            self.frm.update_elements(self.key, omit_elements=omit_elements)
        if requery_dependents:
            self.requery_dependents()

    def set_by_pk(
        self,
        pk: int,
        update_elements: bool = True,
        requery_dependents: bool = True,
        skip_prompt_save: bool = False,
        omit_elements: list[str] = None,
    ) -> None:
        """Move to the record with this primary key.

        This is useful when modifying a record (such as renaming).  The primary key can
        be stored, the record re-named, and then the current record selection updated
        regardless of the new sort order.

        Only one entry in the table is ever considered "Selected". This is one of
        several functions that influences which record is currently selected. See
        `DataSet.first()`, `DataSet.previous()`, `DataSet.next()`, `DataSet.last()`,
        `DataSet.search()`, `DataSet.set_by_pk()`, `DataSet.set_by_index()`.

        Args:
            pk: The record to move to containing the primary key
            update_elements: (optional) Update the GUI elements after switching records.
            requery_dependents: (optional) Requery dependents after switching records
            skip_prompt_save: (optional) True to skip prompting to save dirty records
            omit_elements: (optional) A list of elements to omit from updating

        Returns:
            None
        """
        logger.debug(f"Setting table {self.table} record by primary key {pk}")

        # Get the numerical index of where the primary key is located.
        # If the pk value can't be found, set to the last index
        try:
            idx = [
                i for i, value in enumerate(self.rows[self.pk_column]) if value == pk
            ]
        except (IndexError, KeyError):
            idx = None
            logger.debug("Error finding pk!")

        idx = idx[0] if idx else self.row_count

        self.set_by_index(
            index=idx,
            update_elements=update_elements,
            requery_dependents=requery_dependents,
            skip_prompt_save=skip_prompt_save,
            omit_elements=omit_elements,
        )

    def get_current(
        self, column: str, default: Union[str, int] = ""
    ) -> Union[str, int]:
        """Get the value for the supplied column in the current row.

        You can also use indexing of the `Form` object to get the current value of a
        column I.e. frm[{DataSet}].[{column}].

        Args:
            column: The column you want to get the value from
            default: A value to return if the record is null

        Returns:
            The value of the column requested
        """
        logger.debug(f"Getting current record for {self.table}.{column}")
        if self.row_count:
            if self.get_current_row()[column] is not None:
                return self.get_current_row()[column]
            return default
        return default

    def set_current(
        self, column: str, value: Union[str, int], write_event: bool = False
    ) -> None:
        """Set the value for the supplied column in the current row, making a backup if
        needed.

        You can also use indexing of the `Form` object to set the current value of a
        column. I.e. frm[{DataSet}].[{column}] = 'New value'.

        Args:
            column: The column you want to set the value for
            value: A value to set the current record's column to
            write_event: (optional) If True, writes an event to PySimpleGui as
                `after_record_edit`.

        Returns:
            None
        """
        logger.debug(f"Setting current record for {self.key}.{column} = {value}")
        self.backup_current_row()
        self.rows.loc[self.rows.index[self.current_index], column] = value
        if write_event:
            self.frm.window.write_event_value(
                "after_record_edit",
                {
                    "frm_reference": self.frm,
                    "data_key": self.key,
                    "column": column,
                    "value": value,
                },
            )
        # call callback
        if "after_record_edit" in self.callbacks:
            self.callbacks["after_record_edit"](self.frm, self.frm.window, self.key)

    def get_keyed_value(
        self, value_column: str, key_column: str, key_value: Union[str, int]
    ) -> Union[str, int, None]:
        """Return `value_column` where` key_column`=`key_value`.

        Useful for datastores with key/value pairs.

        Args:
            value_column: The column to fetch the value from
            key_column: The column in which to search for the value
            key_value: The value to search for

        Returns:
            Returns the value found in `value_column`
        """
        for _, row in self.rows.iterrows():
            if row[key_column] == key_value:
                return row[value_column]
        return None

    def get_current_pk(self) -> int:
        """Get the primary key of the currently selected record.

        Returns:
            the primary key
        """
        return self.get_current(self.pk_column)

    def get_current_row(self) -> Union[pd.Series, None]:
        """Get the row for the currently selected record of this table.

        Returns:
            A pandas Series object
        """
        if not self.rows.empty:
            # force the current_index to be in bounds!
            # For child reparenting
            self.current_index = self.current_index

            # make sure to return as python type
            return self.rows.astype("O").iloc[self.current_index]
        return None

    def add_selector(
        self,
        element: sg.Element,
        data_key: str,
        where_column: str = None,
        where_value: str = None,
    ) -> None:
        """Use an element such as a listbox, combobox or a table as a selector item for
        this table.

        Note: This is not typically used by the end user, as this is called from the
        `selector()` convenience function.

        Args:
            element: the PySimpleGUI element used as a selector element
            data_key: the `DataSet` item this selector will operate on
            where_column: (optional)
            where_value: (optional)

        Returns:
            None
        """
        if not isinstance(element, (sg.Listbox, sg.Slider, sg.Combo, sg.Table)):
            raise RuntimeError(
                f"add_selector() error: {element} is not a supported element."
            )

        logger.debug(f"Adding {element.Key} as a selector for the {self.table} table.")
        d = {
            "element": element,
            "data_key": data_key,
            "where_column": where_column,
            "where_value": where_value,
        }
        self.selector.append(d)

    def insert_record(
        self, values: Dict[str, Union[str, int]] = None, skip_prompt_save: bool = False
    ) -> None:
        """Insert a new record virtually in the `DataSet` object.

        If values are passed, it will initially set those columns to the values (I.e.
        {'name': 'New Record', 'note': ''}), otherwise they will be fetched from the
        database if present.

        Args:
            values: column:value pairs
            skip_prompt_save: Skip prompting the user to save dirty records before the
                insert.

        Returns:
            None
        """
        # prompt_save
        if (
            not skip_prompt_save
            # don't update self/dependents if we are going to below anyway
            and self.prompt_save(update_elements=False) == SAVE_FAIL
        ):
            return

        # Don't insert if parent has no records or is virtual
        parent_table = self.relationships.get_parent(self.table)
        if (
            parent_table
            and not len(self.frm[parent_table].rows)
            or self.relationships.parent_virtual(self.table, self.frm)
        ):
            logger.debug(f"{parent_table=} is empty or current row is virtual")
            return

        # Get a new dict for a new row with default values already filled in
        new_values = self.column_info.default_row_dict(self)

        # If the values parameter was passed in, overwrite any values in the dict
        if values is not None:
            for k, v in values.items():
                if k in new_values:
                    new_values[k] = v

        # Make sure we take into account the foreign key relationships...
        for r in self.relationships:
            if self.table == r.child_table and r.on_update_cascade:
                new_values[r.fk_column] = self.frm[r.parent_table].get_current_pk()

        # Update the pk to match the expected pk the driver would generate on insert.
        new_values[self.pk_column] = self.driver.next_pk(self.table, self.pk_column)

        # Insert the new values using DataSet.insert_row(),
        # marking the new row as virtual
        self.insert_row(new_values)

        # and move to the new record
        # do this in insert_record, because possibly current_index is already 0
        # and set_by_index will return early before update/requery if so.
        self.current_index = self.row_count
        self.frm.update_elements(self.key)
        self.requery_dependents()

    def save_record(
        self,
        display_message: bool = None,
        update_elements: bool = True,
        validate_fields: bool = None,
    ) -> int:
        """Save the currently selected record.

        Saves any changes made via the GUI back to the database.  The
        before_save and after_save `DataSet.callbacks` will call your
        own functions for error checking if needed!.

        Args:
            display_message: Displays a message "Updates saved successfully", otherwise
                is silent on success.
            update_elements: Update the GUI elements after saving
            validate_fields: Validate fields before saving to database.

        Returns:
            SAVE_NONE, SAVE_FAIL or SAVE_SUCCESS masked with SHOW_MESSAGE
        """
        logger.debug(f"Saving records for table {self.table}...")
        if display_message is None:
            display_message = not self.save_quiet

        if validate_fields is None:
            validate_fields = self.validate_mode

        # Ensure that there is actually something to save
        if not self.row_count:
            self.frm.popup.info(
                lang.dataset_save_empty, display_message=display_message
            )
            return SAVE_NONE + SHOW_MESSAGE

        # callback
        if "before_save" in self.callbacks and not self.callbacks["before_save"](
            self.frm, self.frm.window, self.key
        ):
            logger.debug("We are not saving!")
            if update_elements:
                self.frm.update_elements(self.key)
            if display_message:
                self.frm.popup.ok(
                    lang.dataset_save_callback_false_title,
                    lang.dataset_save_callback_false,
                )
            return SAVE_FAIL + SHOW_MESSAGE

        # Check right away to see if any records have changed, no need to proceed any
        # further than we have to.
        if not self.records_changed(recursive=False) and self.frm.force_save is False:
            self.frm.popup.info(lang.dataset_save_none, display_message=display_message)
            return SAVE_NONE + SHOW_MESSAGE

        # Work with a copy of the original row and transform it if needed
        # While saving, we are working with just the current row of data,
        # unless it's 'keyed' via ?/=
        current_row = self.get_current_row().copy()

        # Track the keyed queries we have to run.
        # Set to None, so we can tell later if there were keyed elements
        # {'column':column, 'changed_row': row, 'where_clause': where_clause}
        keyed_queries: Optional[List] = None

        # Propagate GUI data back to the stored current_row
        for mapped in [m for m in self.frm.element_map if m.dataset == self]:
            # skip if sg.Text
            if isinstance(mapped.element, sg.Text):
                continue

            # convert the data into the correct type using the domain in ColumnInfo
            if isinstance(mapped.element, sg.Combo):
                # try to get _ElementRow pk
                try:
                    element_val = self.column_info[mapped.column].cast(
                        mapped.element.get().get_pk_ignore_placeholder()
                    )
                # of if plain-ole combobox:
                except AttributeError:
                    element_val = self.column_info[mapped.column].cast(
                        mapped.element.get()
                    )
            else:
                element_val = self.column_info[mapped.column].cast(mapped.element.get())

            # Looked for keyed elements first
            if mapped.where_column is not None:
                if keyed_queries is None:
                    # Make the list here so != None if keyed elements
                    keyed_queries = []
                for index, row in self.rows.iterrows():
                    if (
                        row[mapped.where_column] == mapped.where_value
                        and row[mapped.column] != element_val
                    ):
                        # This record has changed.  We will save it

                        # propagate the value back to self.rows
                        self.rows.loc[
                            self.rows.index[index], mapped.column
                        ] = element_val

                        changed = {mapped.column: element_val}
                        where_col = self.driver.quote_column(mapped.where_column)
                        where_val = self.driver.quote_value(mapped.where_value)
                        where_clause = f"WHERE {where_col} = {where_val}"
                        keyed_queries.append(
                            {
                                "column": mapped.column,
                                "changed_row": changed,
                                "where_clause": where_clause,
                            }
                        )
            else:
                # field elements override _CellEdit's
                current_row[mapped.column] = element_val

        # create diff of columns if not virtual
        new_dict = current_row.fillna("").to_dict()

        if self.pk_is_virtual():
            changed_row_dict = new_dict
        else:
            old_dict = self.get_original_current_row().fillna("").to_dict()
            changed_row_dict = {
                key: new_dict[key]
                for key in new_dict
                if old_dict.get(key) != new_dict[key]
            }

        # Remove the pk column, any virtual or generated columns
        changed_row_dict = {
            col: value
            for col, value in changed_row_dict.items()
            if col != self.pk_column
            and col not in self.column_info.get_virtual_names()
            and not self.column_info[col].generated
        }

        if not bool(changed_row_dict) and not keyed_queries:
            # if user is not using liveupdate, they can change something using celledit
            # but then change it back in field element (which overrides the celledit)
            # this refreshes the selector/comboboxes so that gui is up-to-date.
            if self.current_row_has_backup:
                self.restore_current_row()
                self.frm.update_selectors(self.key)
                self.frm.update_fields(self.key)
            return SAVE_NONE + SHOW_MESSAGE

        # apply any transformations
        if self.transform is not None:
            self.transform(self, changed_row_dict, TFORM_ENCODE)

        # check to make sure we have valid inputs
        if validate_fields:
            invalid_response = {}
            for col, value in changed_row_dict.items():
                response = self.column_info[col].validate(value)
                if response.exception:
                    invalid_response[col] = response
            if invalid_response:
                msg = f"{lang.dataset_save_validate_error_header}"
                for col, response in invalid_response.items():
                    field = lang.dataset_save_validate_error_field.format_map(
                        LangFormat(field=col)
                    )
                    exception = lang[response.exception].format_map(
                        LangFormat(value=response.value, rule=response.rule)
                    )
                    msg += f"{field}{exception}\n"
                self.frm.popup.ok(lang.dataset_save_validate_error_title, msg)
                return SAVE_FAIL

        # check to see if cascading-fk has changed before we update database
        cascade_fk_changed = False
        cascade_fk_column = self.relationships.get_update_cascade_fk_column(self.table)
        if cascade_fk_column:
            # check if fk
            for mapped in self.frm.element_map:
                if mapped.dataset == self and mapped.column == cascade_fk_column:
                    cascade_fk_changed = self.records_changed(
                        column=cascade_fk_column, recursive=False
                    )

        # Update the database from the stored rows
        # ----------------------------------------

        # reset search string
        self.search_string = ""

        # Save or Insert the record as needed
        if keyed_queries is not None:
            # Now execute all the saved queries from earlier
            for q in keyed_queries:
                # Update the database from the stored rows
                if self.transform is not None:
                    self.transform(self, q["changed_row"], TFORM_ENCODE)
                result = self.driver.save_record(
                    self, q["changed_row"], q["where_clause"]
                )
                if result.attrs["exception"] is not None:
                    self.frm.popup.ok(
                        lang.dataset_save_keyed_fail_title,
                        lang.dataset_save_keyed_fail.format_map(
                            LangFormat(exception=result.exception)
                        ),
                    )
                    self.driver.rollback()
                    return SAVE_FAIL  # Do not show the message in this case

        else:
            if self.pk_is_virtual():
                result = self.driver.insert_record(
                    self.table, self.get_current_pk(), self.pk_column, changed_row_dict
                )
            else:
                result = self.driver.save_record(self, changed_row_dict)

            if result.attrs["exception"] is not None:
                self.frm.popup.ok(
                    lang.dataset_save_fail_title,
                    lang.dataset_save_fail.format_map(
                        LangFormat(exception=result.attrs["exception"])
                    ),
                )
                self.driver.rollback()
                return SAVE_FAIL  # Do not show the message in this case

            # Store the pk, so we can move to it later - use the value returned in the
            # attrs if possible. The expected pk may have changed from autoincrement
            # and/or concurrent access.
            pk = (
                result.attrs["lastrowid"]
                if result.attrs["lastrowid"] is not None
                else self.get_current_pk()
            )
            self.set_current(self.pk_column, pk, write_event=False)

            # then update the current row data
            self.rows.iloc[self.current_index] = current_row

            # If child changes parent, move index back and requery/requery_dependents
            if (
                cascade_fk_changed and not self.pk_is_virtual()
            ):  # Virtual rows already requery, and have no dependents.
                self.frm[self.table].requery(select_first=False)  # keep spot in table
                self.frm[self.table].requery_dependents()

            # Lets refresh our data
            if self.pk_is_virtual():
                # Requery so that the new row honors the order clause
                self.requery(select_first=False, update_elements=False)
                if update_elements:
                    # Then move to the record
                    self.set_by_pk(
                        pk,
                        skip_prompt_save=True,
                        requery_dependents=False,
                    )
                    # only need to reset the Insert button
                    self.frm.update_actions()

        # callback
        if "after_save" in self.callbacks and not self.callbacks["after_save"](
            self.frm, self.frm.window, self.key
        ):
            self.driver.rollback()
            return SAVE_FAIL + SHOW_MESSAGE

        # If we made it here, we can commit the changes, since the save and insert above
        # do not commit or rollback
        self.driver.commit()

        # Sort so the saved row honors the current order.
        if "sort_column" in self.rows.attrs and self.rows.attrs["sort_column"]:
            self.sort(self.table)

        # Discard backup
        self.purge_row_backup()

        if update_elements:
            self.frm.update_elements(self.key)

        # if the description_column has changed, make sure to update other elements
        # that may depend on it, that otherwise wouldn't be requeried because they are
        # not setup as on_update_cascade.
        if self.description_column in changed_row_dict:
            dependent_columns = self.relationships.get_dependent_columns(
                self.frm, self.table
            )
            for key, col in dependent_columns.items():
                self.frm.update_fields(key, columns=[col], combo_values_only=True)
                if self.frm[key].column_likely_in_selector(col):
                    self.frm.update_selectors(key)

        logger.debug("Record Saved!")
        self.frm.popup.info(lang.dataset_save_success, display_message=display_message)

        return SAVE_SUCCESS + SHOW_MESSAGE

    def save_record_recursive(
        self,
        results: SaveResultsDict,
        display_message=False,
        check_prompt_save: bool = False,
        update_elements: bool = True,
    ) -> SaveResultsDict:
        """Recursively save changes, taking into account the relationships of the
        tables.

        Args:
            results: Used in Form.save_records to collect DataSet.save_record returns.
                Pass an empty dict to get list of {table : result}
            display_message: Passed to DataSet.save_record. Displays a message that
                updates were saved successfully, otherwise is silent on success.
            check_prompt_save: Used when called from Form.prompt_save. Updates elements
                without saving if individual `DataSet._prompt_save()` is False.

        Returns:
            dict of {table : results}
        """
        for rel in self.relationships:
            if rel.parent_table == self.table and rel.on_update_cascade:
                self.frm[rel.child_table].save_record_recursive(
                    results=results,
                    display_message=display_message,
                    check_prompt_save=check_prompt_save,
                    update_elements=update_elements,
                )
        # if dataset-level doesn't allow prompt_save
        if check_prompt_save and self._prompt_save is False:
            if update_elements:
                self.frm.update_elements(self.key)
            results[self.table] = PROMPT_SAVE_NONE
            return results
        # otherwise, proceed
        result = self.save_record(
            display_message=display_message, update_elements=update_elements
        )
        results[self.table] = result
        return results

    def delete_record(
        self, cascade: bool = True
    ):  # TODO: check return type, we return True below
        """Delete the currently selected record.

        The before_delete and after_delete callbacks are run during this process
        to give some control over the process.

        Args:
            cascade: Delete child records (as defined by `Relationship`s that were set
                up) before deleting this record.

        Returns:
            None
        """
        # Ensure that there is actually something to delete
        if not self.row_count:
            return None

        # callback
        if "before_delete" in self.callbacks and not self.callbacks["before_delete"](
            self.frm, self.frm.window, self.key
        ):
            return None

        children = []
        if cascade:
            children = self.relationships.get_delete_cascade_tables(self.table)

        msg_children = ", ".join(children)
        if len(children):
            msg = lang.delete_cascade.format_map(LangFormat(children=msg_children))
        else:
            msg = lang.delete_single
        answer = self.frm.popup.yes_no(lang.delete_title, msg)
        if answer == "no":
            return True

        if self.pk_is_virtual():
            self.purge_virtual()
            self.frm.update_elements(self.key)
            # only need to reset the Insert button
            self.frm.update_actions()
            return None

        # Delete child records first!
        result = self.driver.delete_record(self, True)

        if (
            not isinstance(result, pd.DataFrame)
            and result == DELETE_RECURSION_LIMIT_ERROR
        ):
            self.frm.popup.ok(
                lang.delete_failed_title,
                lang.delete_failed.format_map(
                    LangFormat(exception=lang.delete_recursion_limit_error)
                ),
            )
        elif result.attrs["exception"] is not None:
            self.frm.popup.ok(
                lang.delete_failed_title,
                lang.delete_failed.format_map(LangFormat(exception=result.exception)),
            )

        # callback
        if "after_delete" in self.callbacks:
            if not self.callbacks["after_delete"](self.frm, self.frm.window, self.key):
                self.driver.rollback()
            else:
                self.driver.commit()
        else:
            self.driver.commit()

        self.requery(select_first=False)
        self.frm.update_elements(self.key)
        self.requery_dependents()
        return None

    def duplicate_record(
        self,
        children: bool = None,
        skip_prompt_save: bool = False,
    ) -> Union[bool, None]:  # TODO check return type, returns True within
        """Duplicate the currently selected record.

        The before_duplicate and after_duplicate callbacks are run during this
        process to give some control over the process.

        Args:
            children: Duplicate child records (as defined by `Relationship`s that were
                set up) before duplicating this record.
            skip_prompt_save: (optional) True to skip prompting to save dirty records

        Returns:
            None
        """
        # Ensure that there is actually something to duplicate
        if not self.row_count or self.pk_is_virtual():
            return None

        # prompt_save
        if (
            not skip_prompt_save
            # don't update self/dependents if we are going to below anyway
            and self.prompt_save(update_elements=False) == SAVE_FAIL
        ):
            return None

        # callback
        if "before_duplicate" in self.callbacks and not self.callbacks[
            "before_duplicate"
        ](self.frm, self.frm.window, self.key):
            return None

        if children is None:
            children = self.duplicate_children

        child_list = []
        if children:
            child_list = self.relationships.get_update_cascade_tables(self.table)

        msg_children = ", ".join(child_list)
        msg = lang.duplicate_child.format_map(
            LangFormat(children=msg_children)
        ).splitlines()
        layout = [[sg.T(line, font="bold")] for line in msg]
        if len(child_list):
            answer = sg.Window(
                lang.duplicate_child_title,
                [
                    layout,
                    [
                        sg.Button(
                            button_text=lang.duplicate_child_button_dupparent,
                            key="parent",
                            use_ttk_buttons=themepack.use_ttk_buttons,
                            pad=themepack.popup_button_pad,
                        )
                    ],
                    [
                        sg.Button(
                            button_text=lang.duplicate_child_button_dupboth,
                            key="cascade",
                            use_ttk_buttons=themepack.use_ttk_buttons,
                            pad=themepack.popup_button_pad,
                        )
                    ],
                    [
                        sg.Button(
                            button_text=lang.button_cancel,
                            key="cancel",
                            use_ttk_buttons=themepack.use_ttk_buttons,
                            pad=themepack.popup_button_pad,
                        )
                    ],
                ],
                keep_on_top=True,
                modal=True,
                ttk_theme=themepack.ttk_theme,
                icon=themepack.icon,
            ).read(close=True)
            if answer[0] == "parent":
                children = False
            elif answer[0] in ["cancel", None]:
                return True
        else:
            msg = lang.duplicate_single
            answer = self.frm.popup.yes_no(lang.duplicate_single_title, msg)
            if answer == "no":
                return True
        # Store our current pk, so we can move to it if the duplication fails
        pk = self.get_current_pk()

        # Have the driver duplicate the record
        result = self.driver.duplicate_record(self, children)
        if result.attrs["exception"]:
            self.driver.rollback()
            self.frm.popup.ok(
                lang.duplicate_failed_title,
                lang.duplicate_failed.format_map(
                    LangFormat(exception=result.attrs["exception"])
                ),
            )
        else:
            pk = result.attrs["lastrowid"]

        # callback
        if "after_duplicate" in self.callbacks:
            if not self.callbacks["after_duplicate"](
                self.frm, self.frm.window, self.key
            ):
                self.driver.rollback()
            else:
                self.driver.commit()
        else:
            self.driver.commit()
        self.driver.commit()

        # requery and move to new pk
        self.requery(select_first=False)
        self.set_by_pk(pk, skip_prompt_save=True)
        return None

    def get_description_for_pk(self, pk: int) -> Union[str, int, None]:
        """Get the description from the `DataSet` on the matching pk.

        Return the description from `DataSet.description_column` for the row where the
        `DataSet.pk_column` = `pk`.

        Args:
            pk: The primary key from which to find the description for

        Returns:
            The value found in the description column, or None if nothing is found
        """
        # We don't want to update other views comboboxes/tableviews until row is
        # actually saved. So first check their current
        current_row = self.get_original_current_row()
        if current_row[self.pk_column] == pk:
            return current_row[self.description_column]
        try:
            index = self.rows.loc[self.rows[self.pk_column] == pk].index[0]
            return self.rows[self.description_column].iloc[index]
        except IndexError:
            return None

    @property
    def virtual_pks(self):
        return self.rows.attrs["virtual"]

    def pk_is_virtual(self, pk: int = None) -> bool:
        """Check whether pk is virtual.

        Args:
            pk: The pk to check. If None, the pk of the current row will be checked.

        Returns:
            True or False based on whether the row is virtual
        """
        if not self.row_count:
            return False

        if pk is None:
            pk = self.get_current_row()[self.pk_column]

        return bool(pk in self.virtual_pks)

    @property
    def row_count(self) -> int:
        """Returns the number of rows in the dataset. If the dataset is not a pandas
        DataFrame, returns 0.

        Returns:
            The number of rows in the dataset.
        """
        if isinstance(self.rows, pd.DataFrame):
            return len(self.rows.index)
        return 0

    @property
    def current_row_has_backup(self) -> bool:
        """Returns True if the current_row has a backup row, and False otherwise.

        A pandas Series object is stored rows.attrs["row_backup"] before a 'CellEdit' or
        'LiveUpdate' operation is initiated, so that it can be compared in
        `DataSet.records_changed` and `DataSet.save_record` or used to restore if
        changes are discarded during a `DataSet.prompt_save` operations.

        Returns:
            True if a backup row is present that matches, and False otherwise.
        """
        if self.rows is None or self.rows.empty:
            return False
        if (
            isinstance(self.rows.attrs["row_backup"], pd.Series)
            and self.rows.attrs["row_backup"][self.pk_column]
            == self.get_current_row()[self.pk_column]
        ):
            return True
        return False

    def purge_row_backup(self) -> None:
        """Deletes the backup row from the dataset.

        This method sets the "row_backup" attribute of the dataset to None.
        """
        self.rows.attrs["row_backup"] = None

    def restore_current_row(self) -> None:
        """Restores the backup row to the current row in `DataSet.rows`.

        This method replaces the current row in the dataset with the backup row, if a
        backup row is present.
        """
        if self.current_row_has_backup:
            self.rows.iloc[self.current_index] = self.rows.attrs["row_backup"].copy()

    def get_original_current_row(self) -> pd.Series:
        """Returns a copy of current row as it was fetched in a query from `SQLDriver`.

        If a backup of the current row is present, this method returns a copy of that
        row. Otherwise, it returns a copy of the current row. Returns None if
        `DataSet.rows` is empty.
        """
        if self.current_row_has_backup:
            return self.rows.attrs["row_backup"].copy()
        if not self.rows.empty:
            return self.get_current_row().copy()
        return None

    def backup_current_row(self) -> None:
        """Creates a backup copy of the current row in `DataSet.rows`"""
        if not self.current_row_has_backup:
            self.rows.attrs["row_backup"] = self.get_current_row().copy()

    def table_values(
        self,
        columns: List[str] = None,
        mark_unsaved: bool = False,
        apply_search_filter: bool = False,
        apply_cell_format_fn: bool = True,
    ) -> List[_TableRow]:
        """Create a values list of `_TableRows`s for use in a PySimpleGUI Table element.

        Args:
            columns: A list of column names to create table values for. Defaults to
                getting them from the `DataSet.rows` DataFrame.
            mark_unsaved: Place a marker next to virtual records, or records with
                unsaved changes.
            apply_search_filter: Filter rows to only those columns in
                `DataSet.search_order` that contain `DataSet.search_string`.
            apply_cell_format_fn: If set, apply()
                `DataSet.column_info[col].cell_format_fn` to rows column

        Returns:
            A list of `_TableRow`s suitable for using with PySimpleGUI Table element
            values.
        """
        if not self.row_count:
            return []

        try:
            all_columns = list(self.rows.columns)
        except IndexError:
            all_columns = []

        columns = all_columns if columns is None else columns

        rows = self.rows.copy()
        pk_column = self.pk_column

        if mark_unsaved:
            virtual_row_pks = self.virtual_pks.copy()
            # add pk of current row if it has changes
            if self.current_row_has_backup and not self.get_current_row().equals(
                self.get_original_current_row()
            ):
                virtual_row_pks.append(
                    self.rows.loc[
                        self.rows[pk_column] == self.get_current_row()[pk_column],
                        pk_column,
                    ].to_numpy()[0]
                )

            # Create a new column 'marker' with the desired values
            rows["marker"] = " "
            mask = rows[pk_column].isin(virtual_row_pks)
            rows.loc[mask, "marker"] = themepack.marker_unsaved
        else:
            rows["marker"] = " "

        # get fk descriptions
        rows = self.map_fk_descriptions(rows, columns)

        # return early if empty
        if rows.empty:
            return []

        # filter rows to only contain search, or virtual/unsaved row
        if apply_search_filter and self.search_string not in EMPTY:
            masks = [
                rows[col].astype(str).str.contains(self.search_string, case=False)
                | rows[pk_column].isin(virtual_row_pks)
                for col in self.search_order
            ]
            mask_pd = pd.concat(masks, axis=1).any(axis=1)
            # Apply the mask to filter the DataFrame
            rows = rows[mask_pd]

        # apply cell format functions
        if apply_cell_format_fn:
            for column in columns:
                if self.column_info[column] and self.column_info[column].cell_format_fn:
                    fn = self.column_info[column].cell_format_fn
                    rows[column] = rows[column].apply(fn)

        # set the pk to the index to use below
        rows["pk_idx"] = rows[pk_column].copy()
        rows = rows.set_index("pk_idx")

        # insert the marker
        columns.insert(0, "marker")

        # resort rows with requested columns
        rows = rows[columns]

        # fastest way yet to generate list of _TableRows
        return [
            _TableRow(pk, values.tolist())
            for pk, values in zip(
                rows.index,
                np.vstack((rows.fillna("").astype("O").to_numpy().T, rows.index)).T,
            )
        ]

    def column_likely_in_selector(self, column: str) -> bool:
        """Determines whether the given column is likely to be displayed in a selector.

        Args:
            column: The name of the column to check.

        Returns:
            True if the column is likely to be displayed, False otherwise.
        """
        # If there are no sg.Table selectors, return False
        if not any(
            isinstance(e["element"], sg.PySimpleGUI.Table) for e in self.selector
        ):
            return False

        # If table headings are not used, assume the column is displayed, return True
        if not any("TableBuilder" in e["element"].metadata for e in self.selector):
            return True

        # Otherwise, Return True/False if the column is in the list of table headings
        return any(
            "TableBuilder" in e["element"].metadata
            and column in e["element"].metadata["TableBuilder"].columns
            for e in self.selector
        )

    def combobox_values(
        self, column_name, insert_placeholder: bool = True
    ) -> Union[List[_ElementRow], None]:
        """Returns the values to use in a sg.Combobox as a list of _ElementRow objects.

        Args:
            column_name: The name of the table column for which to get the values.

        Returns:
            A list of _ElementRow objects representing the possible values for the
            combobox column, or None if no matching relationship is found.
        """
        if not self.row_count:
            return None

        rels = self.relationships.get_rels_for(self.table)
        rel = next((r for r in rels if r.fk_column == column_name), None)
        if rel is None:
            return None

        if not self.frm[rel.parent_table].row_count:
            return None

        rows = self.frm[rel.parent_table].rows.copy()
        pk_column = self.frm[rel.parent_table].pk_column
        description = self.frm[rel.parent_table].description_column

        # revert to original row (so unsaved changes don't show up in dropdowns)
        parent_current_row = self.frm[rel.parent_table].get_original_current_row()
        rows.iloc[self.frm[rel.parent_table].current_index] = parent_current_row

        # fastest way yet to generate this list of _ElementRow
        combobox_values = [
            _ElementRow(*values)
            for values in np.column_stack((rows[pk_column], rows[description]))
        ]

        if insert_placeholder:
            combobox_values.insert(0, _ElementRow("Null", lang.combo_placeholder))
        return combobox_values

    def get_related_table_for_column(self, column: str) -> str:
        """Get parent table name as it relates to this column.

        Args:
            column: The column name to get related table information for

        Returns:
            The name of the related table, or the current table if none are found
        """
        rels = self.relationships.get_rels_for(self.table)
        for rel in rels:
            if column == rel.fk_column:
                return rel.parent_table
        return self.table  # None could be found, return our own table instead

    def map_fk_descriptions(self, rows: pd.DataFrame, columns: list[str] = None):
        """Maps foreign key descriptions to the specified columns in the given
        DataFrame. If passing in a DataSet rows, please pass in a copy:
        frm[data_key].rows.copy()

        Args:
            rows: The DataFrame containing the data to be processed.
            columns: (Optional) The list of column names to map foreign key descriptions
                to. If none are provided, all columns of the DataFrame will be searched
                for foreign-key relationships.

        Returns:
            The processed DataFrame with foreign key descriptions mapped to the
            specified columns.
        """
        if columns is None:
            columns = rows.columns

        # get fk descriptions
        rels = self.relationships.get_rels_for(self.table)
        for col in columns:
            for rel in rels:
                if col == rel.fk_column:
                    # return early if parent is empty
                    if not self.frm[rel.parent_table].row_count:
                        return rows

                    parent_df = self.frm[rel.parent_table].rows
                    parent_pk_column = self.frm[rel.parent_table].pk_column

                    # get this before map(), to revert below
                    parent_current_row = self.frm[
                        rel.parent_table
                    ].get_original_current_row()
                    condition = rows[col] == parent_current_row[parent_pk_column]

                    # map descriptions to fk column
                    description_column = self.frm[rel.parent_table].description_column
                    mapping_dict = parent_df.set_index(parent_pk_column)[
                        description_column
                    ].to_dict()
                    rows[col] = rows[col].map(mapping_dict)

                    # revert any unsaved changes for the single row
                    rows.loc[condition, col] = parent_current_row[description_column]

                    # we only want transform col once
                    break
        return rows

    def quick_editor(
        self,
        pk_update_funct: callable = None,
        funct_param: any = None,
        skip_prompt_save: bool = False,
        column_attributes: dict = None,
    ) -> None:
        """The quick editor is a dynamic PySimpleGUI Window for quick editing of tables.
        This is very useful for putting a button next to a combobox or listbox so that
        the available values can be added/edited/deleted easily.
        Note: This is not typically used by the end user, as it can be configured from
        the `field()` convenience function.

        Args:
            pk_update_funct: (optional) A function to call to determine the pk to select
                by default when the quick editor loads.
            funct_param: (optional) A parameter to pass to the 'pk_update_funct'
            skip_prompt_save: (Optional) True to skip prompting to save dirty records
            column_attributes: (Optional) Dictionary specifying column attributes for
                `DataSet.column_info`. The dictionary should be in the form
                {column_name: {attribute: value}}.

        Returns:
            None
        """
        # prompt_save
        if (
            not skip_prompt_save
            # don't update self/dependents if we are going to below anyway
            and self.prompt_save(update_elements=False) == SAVE_FAIL
        ):
            return

        # Reset the keygen to keep consistent naming
        logger.info("Creating Quick Editor window")
        keygen.reset()
        data_key = self.key
        layout = []
        table_builder = TableBuilder(
            num_rows=10,
            sort_enable=True,
            allow_cell_edits=True,
            add_save_heading_button=True,
            style=TableStyler(row_height=25),
        )

        for col in self.column_info.names:
            # set widths
            width = int(55 / (len(self.column_info.names) - 1))
            if col == self.pk_column:
                # make pk column either max length of contained pks, or len of name
                width = int(
                    np.nanmax([self.rows[col].astype(str).map(len).max(), len(col) + 1])
                )
                justify = "left"
            elif self.column_info[col] and self.column_info[col].python_type in [
                int,
                float,
                Decimal,
            ]:
                justify = "right"
            else:
                justify = "left"
            table_builder.add_column(
                col, col.capitalize(), width=width, col_justify=justify
            )

        layout.append(
            [
                selector(
                    data_key,
                    table_builder,
                    key=f"{data_key}:quick_editor",
                )
            ]
        )
        y_pad = 10
        layout.append([actions(data_key, edit_protect=False)])
        layout.append([sg.Sizer(h_pixels=0, v_pixels=y_pad)])

        fields_layout = [[sg.Sizer(h_pixels=0, v_pixels=y_pad)]]

        rels = self.relationships.get_rels_for(self.table)
        for col in self.column_info.names:
            found = False
            column = f"{data_key}.{col}"
            # make sure isn't pk
            if col != self.pk_column:
                # display checkboxes
                if (
                    self.column_info[column]
                    and self.column_info[column].python_type == bool
                ):
                    fields_layout.append([field(column, sg.Checkbox)])
                    found = True
                    break
                # or display sg.combos
                for rel in rels:
                    if col == rel.fk_column:
                        fields_layout.append(
                            [field(column, sg.Combo, quick_editor=False)]
                        )
                        found = True
                        break
                # otherwise, just display a regular input
                if not found:
                    fields_layout.append([field(column)])

        fields_layout.append([sg.Sizer(h_pixels=0, v_pixels=y_pad)])
        layout.append([sg.Frame("Fields", fields_layout, expand_x=True)])
        layout.append([sg.Sizer(h_pixels=0, v_pixels=10)])
        layout.append(
            [
                sg.StatusBar(
                    " " * 100, key="info:quick_editor", metadata={"type": TYPE_INFO}
                )
            ],
        )

        quick_win = sg.Window(
            lang.quick_edit_title.format_map(LangFormat(data_key=data_key)),
            layout,
            keep_on_top=True,
            modal=True,
            finalize=True,
            ttk_theme=themepack.ttk_theme,  # Must, otherwise will redraw window
            icon=themepack.icon,
            enable_close_attempted_event=True,
        )
        quick_frm = Form(
            self.frm.driver,
            bind_window=quick_win,
            live_update=True,
        )

        # Select the current entry to start with
        if pk_update_funct is not None:
            if funct_param is None:
                quick_frm[data_key].set_by_pk(pk_update_funct())
            else:
                quick_frm[data_key].set_by_pk(pk_update_funct(funct_param))

        if column_attributes:
            for col, kwargs in column_attributes.items():
                if quick_frm[data_key].column_info[col]:
                    for attr, value in kwargs.items():
                        quick_frm[data_key].column_info[col][attr] = value

        while True:
            event, values = quick_win.read()

            if quick_frm.process_events(event, values):
                logger.debug(
                    f"PySimpleSQL Quick Editor event handler handled the event {event}!"
                )
            if event == "-WINDOW CLOSE ATTEMPTED-":
                if quick_frm.popup.popup_info:
                    quick_frm.popup.popup_info.close()
                self.requery()
                self.frm.update_elements()
                quick_win.close()
                quick_frm.close(close_driver=False)
                break
            logger.debug(f"This event ({event}) is not yet handled.")

    def add_simple_transform(self, transforms: SimpleTransformsDict) -> None:
        """Merge a dictionary of transforms into the `DataSet._simple_transform`
        dictionary.

        Example:
            ```python
            {'entry_date' : {
                'decode' : lambda row,col: datetime.utcfromtimestamp(int(row[col])).strftime('%m/%d/%y'),
                'encode' : lambda row,col: datetime.strptime(row[col], '%m/%d/%y').replace(tzinfo=timezone.utc).timestamp(),
            }}
            ```

        Args:
            transforms: A dict of dicts containing either 'encode' or 'decode' along
                with a callable to do the transform. See example above

        Returns:
            None
        """  # noqa: E501
        for k, v in transforms.items():
            if not callable(v):
                RuntimeError(f"Transform for {k} must be callable!")
            self._simple_transform[k] = v

    def purge_virtual(self) -> None:
        """Purge virtual rows from the DataFrame.

        Returns:
            None
        """
        # remove the rows where virtual is True in place, along with the corresponding
        # virtual attribute
        virtual_rows = self.rows[self.rows[self.pk_column].isin(self.virtual_pks)]
        self.rows = self.rows.drop(index=virtual_rows.index)
        self.rows.attrs["virtual"] = []

    def sort_by_column(self, column: str, table: str, reverse=False) -> None:
        """Sort the DataFrame by column. Using the mapped relationships of the database,
        foreign keys will automatically sort based on the parent table's description
        column, rather than the foreign key number.

        Args:
            column: The name of the column to sort the DataFrame by
            table: The name of the table the column belongs to
            reverse: Reverse the sort; False = ASC, True = DESC

        Returns:
            None
        """
        # Target sorting by this DataFrame

        # We don't want to sort by foreign keys directly - we want to sort by the
        # description column of the foreign table that the foreign key references
        tmp_column = None
        rels = self.relationships.get_rels_for(table)

        transformed = False
        for rel in rels:
            if column == rel.fk_column:
                # Copy the specified column and apply mapping to obtain fk descriptions
                column_copy = pd.DataFrame(self.rows[column].copy())
                column_copy = self.map_fk_descriptions(column_copy, [column])[column]

                # Assign the transformed column to the temporary column
                tmp_column = f"temp_{rel.parent_table}.{rel.pk_column}"
                self.rows[tmp_column] = column_copy

                # Use the temporary column as the new sorting column
                column = tmp_column

                transformed = True
                break

        # handling datetime
        # TODO: user-defined format
        if (
            not transformed
            and self.column_info[column]
            and self.column_info[column].python_type in (dt.date, dt.time, dt.datetime)
        ):
            tmp_column = f"temp_{column}"
            self.rows[tmp_column] = pd.to_datetime(self.rows[column])
            column = tmp_column

        # sort
        try:
            self.rows = self.rows.sort_values(
                column,
                ascending=not reverse,
            )
        except (KeyError, TypeError) as e:
            logger.debug(f"DataFrame could not sort by column {column}. {e}")
        finally:
            # Drop the temporary description column (if it exists)
            if tmp_column is not None:
                self.rows = self.rows.drop(columns=tmp_column, errors="ignore")

    def sort_by_index(self, index: int, table: str, reverse=False) -> None:
        """Sort the self.rows DataFrame by column index Using the mapped relationships
        of the database, foreign keys will automatically sort based on the parent
        table's description column, rather than the foreign key number.

        Args:
            index: The index of the column to sort the DateFrame by
            table: The name of the table the column belongs to
            reverse: Reverse the sort; False = ASC, True = DESC

        Returns:
            None
        """
        column = self.rows.columns[index]
        self.sort_by_column(column, table, reverse)

    def store_sort_settings(self) -> list:
        """Store the current sort settingg. Sort settings are just the sort column and
        reverse setting. Sort order can be restored with `DataSet.load_sort_settings()`.

        Returns:
            A list containing the sort_column and the sort_reverse
        """
        return [self.rows.attrs["sort_column"], self.rows.attrs["sort_reverse"]]

    def load_sort_settings(self, sort_settings: list) -> None:
        """Load a previously stored sort setting. Sort settings are just the sort columm
        and reverse setting.

        Args:
            sort_settings: A list as returned by `DataSet.store_sort_settings()`
        """
        self.rows.attrs["sort_column"] = sort_settings[0]
        self.rows.attrs["sort_reverse"] = sort_settings[1]

    def sort_reset(self) -> None:
        """Reset the sort order to the original order as defined by the DataFram index.

        Returns:
            None
        """
        # Restore the original sort order
        self.rows = self.rows.sort_index()

    def sort(self, table: str, update_elements: bool = True, sort_order=None) -> None:
        """Sort according to the internal sort_column and sort_reverse variables. This
        is a good way to re-sort without changing the sort_cycle.

        Args:
            table: The table associated with this DataSet.  Passed along to
                `DataSet.sort_by_column()`
            update_elements: Update associated selectors and navigation buttons, and
                table header sort marker.
            sort_order: A SORT_* constant (SORT_NONE, SORT_ASC, SORT_DESC).
                Note that the update_elements parameter must = True to use

        Returns:
            None
        """
        pk = self.get_current_pk()
        if self.rows.attrs["sort_column"] is None:
            logger.debug("Sort column is None.  Resetting sort.")
            self.sort_reset()
        else:
            logger.debug(f"Sorting by column {self.rows.attrs['sort_column']}")
            self.sort_by_column(
                self.rows.attrs["sort_column"], table, self.rows.attrs["sort_reverse"]
            )
        self.set_by_pk(
            pk,
            update_elements=False,
            requery_dependents=False,
            skip_prompt_save=True,
        )
        if update_elements and self.row_count:
            self.frm.update_selectors(self.key)
            self.frm.update_actions(self.key)
            self._update_headings(self.rows.attrs["sort_column"], sort_order)

    def sort_cycle(self, column: str, table: str, update_elements: bool = True) -> int:
        """Cycle between original sort order of the DataFrame, ASC by column, and DESC
        by column with each call.

        Args:
            column: The column name to cycle the sort on
            table: The table that the column belongs to
            update_elements: Passed to `DataSet.sort` to update update associated
                selectors and navigation buttons, and table header sort marker.

        Returns:
            A sort constant; SORT_NONE, SORT_ASC, or SORT_DESC
        """
        if column != self.rows.attrs["sort_column"]:
            self.rows.attrs["sort_column"] = column
            self.rows.attrs["sort_reverse"] = False
            self.sort(table, update_elements=update_elements, sort_order=SORT_ASC)
            return SORT_ASC
        if not self.rows.attrs["sort_reverse"]:
            self.rows.attrs["sort_reverse"] = True
            self.sort(table, update_elements=update_elements, sort_order=SORT_DESC)
            return SORT_DESC
        self.rows.attrs["sort_reverse"] = False
        self.rows.attrs["sort_column"] = None
        self.sort(table, update_elements=update_elements, sort_order=SORT_NONE)
        return SORT_NONE

    def _update_headings(self, column, sort_order) -> None:
        for e in self.selector:
            element = e["element"]
            if (
                "TableBuilder" in element.metadata
                and element.metadata["TableBuilder"].sort_enable
            ):
                element.metadata["TableBuilder"]._update_headings(
                    element, column, sort_order
                )

    def insert_row(self, row: dict, idx: int = None) -> None:
        """Insert a new virtual row into the DataFrame. Virtual rows are ones that exist
        in memory, but not in the database. When a save action is performed, virtual
        rows will be added into the database.

        Args:
            row: A dict representation of a row of data
            idx: The index where the row should be inserted (default to last index)

        Returns:
            None
        """
        row_series = pd.Series(row, dtype=object)
        # Infer better data types for the Series
        # row_series = row_series.infer_objects()
        if self.rows.empty:
            self.rows = Result.set(
                pd.concat([self.rows, row_series.to_frame().T], ignore_index=True)
            )
        else:
            attrs = self.rows.attrs.copy()

            # TODO: idx currently does nothing
            if idx is None:
                idx = self.row_count

            self.rows = pd.concat(
                [self.rows, row_series.to_frame().T], ignore_index=True
            )
            self.rows.attrs = attrs

        self.rows.attrs["virtual"].append(row[self.pk_column])

    def validate_field(
        self,
        column_name: str,
        new_value: Any,
        widget=None,
        display_message: bool = False,
    ) -> bool:
        """Validate the given field value for the specified column.

        Args:
            column_name: The name of the column to validate the field against.
            new_value: The new value to validate.
            widget: The widget associated with the field. (Optional)
            display_message: Flag to display validation messages. (Default: False)

        Returns:
            True if the field value is valid, False otherwise.
        """

        if column_name in self.column_info:
            # Validate the new value against the column's validation rules
            response = self.column_info[column_name].validate(new_value)
            # If validation fails, display an error message and return False
            if response.exception:
                self.frm.popup.info(
                    lang[response.exception].format_map(
                        LangFormat(value=response.value, rule=response.rule)
                    ),
                    display_message=display_message,
                )
                if widget and themepack.validate_exception_animation is not None:
                    themepack.validate_exception_animation(widget)
                return False
            # If validation passes, update the info element and return True
            self.frm.popup.update_info_element(erase=True)
            return True
        logger.debug(f"{column_name} not in dataset.column_info!")
        return None


@dc.dataclass(eq=False)
class Form:

    """`Form` class.

    Maintains an internal version of the actual database
    `DataSet` objects can be accessed by key, I.e. frm['data_key'].

    Args:
        driver: Supported `SQLDriver`. See `Sqlite()`, `Mysql()`, `Postgres()`
        bind_window: Bind this window to the `Form`
        parent: (optional)Parent `Form` to base dataset off of
        filter: (optional) Only import elements with the same filter set. Typically set
            with `field()`, but can also be set manually as a dict with the key 'filter'
            set in the element's metadata
        select_first: (optional) Default:True. For each top-level parent, selects first
            row, populating children as well.
        prompt_save: (optional) Default:PROMPT_MODE. Prompt to save changes when
            dirty records are present. There are two modes available, `PROMPT_MODE`
            to prompt to save when unsaved changes are present. `AUTOSAVE_MODE` to
            automatically save when unsaved changes are present.
        save_quiet: (optional) Default:False. True to skip info popup on save. Error
            popups will still be shown.
        duplicate_children: (optional) Default:True. If record has children, prompt user
            to choose to duplicate current record, or both.
        description_column_names: (optional) A list of names to use for the DataSet
            object's description column, displayed in Listboxes, Comboboxes, and Tables
            instead of the primary key. The first matching column of the table is given
            priority. If no match is found, the second column is used. Default list:
            ['description', 'name', 'title'].
        live_update: (optional) Default value is False. If True, changes made in a field
            will be immediately pushed to associated selectors. If False, changes will
            be pushed only after a save action.
        validate_mode: Passed to `DataSet` init to set validate mode.
            `ValidateMode.STRICT` to prevent invalid values from being entered.
            `ValidateMode.RELAXED` allows invalid input, but ensures validation
            occurs before saving to the database.

    Returns:
        None
    """

    instances: ClassVar[List[Form]] = []  # Track our instances

    driver: SQLDriver
    bind_window: dc.InitVar[sg.Window] = None
    parent: Form = None  # TODO: This doesn't seem to really be used
    filter: str = None
    select_first: dc.InitVar[bool] = True
    prompt_save: dc.InitVar[PROMPT_SAVE_MODES] = PROMPT_MODE
    save_quiet: bool = False
    duplicate_children: bool = True
    description_column_names: List[str] = dc.field(
        default_factory=lambda: ["description", "name", "title"]
    )
    live_update: bool = False
    validate_mode: ValidateMode = ValidateMode.RELAXED

    def __post_init__(
        self,
        bind_window,
        select_first,
        prompt_save,
    ) -> None:
        Form.instances.append(self)

        self.window: Optional[sg.Window] = 0
        self.datasets: Dict[str, DataSet] = {}
        self.element_map: List[ElementMap] = []
        self.event_map: List = []  # Array of dicts, {'event':, 'function':, 'table':}
        self._edit_protect: bool = False
        self.relationships: RelationshipStore = self.driver.relationships
        self.callbacks: CallbacksDict = {}
        self.force_save: bool = False
        # empty variables, just in-case bind() never called
        self.popup: Popup = None
        self._celledit: _CellEdit = None
        self._liveupdate: _LiveUpdate = None
        self._liveupdate_binds: dict = {}

        self._prompt_save: PROMPT_SAVE_MODES = prompt_save

        win_pb = ProgressBar(lang.startup_form)
        win_pb.update(lang.startup_init, 0)
        # Add our default datasets and relationships
        win_pb.update(lang.startup_datasets, 25)
        self.auto_add_datasets()
        win_pb.update(lang.startup_relationships, 50)
        self.requery_all(
            select_first=select_first, update_elements=False, requery_dependents=True
        )
        if bind_window is not None:
            win_pb.update(lang.startup_binding, 75)
            self.window = bind_window
            self.bind(self.window)
        win_pb.close()

    def __del__(self) -> None:
        self.close()

    # Override the [] operator to retrieve dataset by key
    def __getitem__(self, key: str) -> DataSet:
        try:
            return self.datasets[key]
        except KeyError as e:
            raise RuntimeError(
                f"The DataSet for `{key}` does not exist. This can be caused because "
                f"the database does not exist, the database user does not have the "
                f"proper permissions set, or any number of db configuration issues."
            ) from e

    def close(self, reset_keygen: bool = True, close_driver: bool = True) -> None:
        """Safely close out the `Form`.

        Args:
            reset_keygen: True to reset the keygen for this `Form`
        """
        # First delete the dataset associated
        DataSet.purge_form(self, reset_keygen)
        if self.popup.popup_info:
            self.popup.popup_info.close()
        Form.purge_instance(self)
        if close_driver:
            self.driver.close()

    def bind(self, win: sg.Window) -> None:
        """Bind the PySimpleGUI Window to the Form for the purpose of GUI element, event
        and relationship mapping. This can happen automatically on `Form` creation with
        the bind parameter and is not typically called by the end user. This function
        literally just groups all the auto_* methods. `Form.auto_map_elements()`,
        `Form.auto_map_events()`.

        Args:
            win: The PySimpleGUI window

        Returns:
            None
        """
        logger.info("Binding Window to Form")
        self.window = win
        self.popup = Popup(self.window)
        self.auto_map_elements(win)
        self.auto_map_events(win)
        self.update_elements()
        # Creating cell edit instance, even if we arn't going to use it.
        self._celledit = _CellEdit(self)
        self.window.TKroot.bind("<Double-Button-1>", self._celledit)
        self._liveupdate = _LiveUpdate(self)
        if self.live_update:
            self.set_live_update(enable=True)
        logger.debug("Binding finished!")

    def execute(self, query: str) -> pd.DataFrame:
        """Convenience function to pass along to `SQLDriver.execute()`.

        Args:
            query: The query to execute

        Returns:
            A pandas DataFrame object with attrs set for lastrowid and exception
        """
        return self.driver.execute(query)

    def commit(self) -> None:
        """Convenience function to pass along to `SQLDriver.commit()`.

        Returns:
            None
        """
        self.driver.commit()

    def set_callback(
        self, callback_name: str, fctn: Callable[[Form, sg.Window], Union[None, bool]]
    ) -> None:
        """Set `Form` callbacks. A runtime error will be raised if the callback is not
        supported. The following callbacks are supported: update_elements Called after
        elements are updated via `Form.update_elements()`. This allows for other GUI
        manipulation on each update of the GUI edit_enable Called before editing mode is
        enabled. This can be useful for asking for a password for example edit_disable
        Called after the editing mode is disabled.

        {element_name} Called while updating MAPPED element. This overrides the default
        element update implementation. Note that the {element_name} callback function
        needs to return a value to pass to Win[element].update()

        Args:
            callback_name: The name of the callback, from the list above
            fctn: The function to call. Note, the function must take in two parameters,
                a Form instance, and a PySimpleGUI.Window instance

        Returns:
            None
        """
        logger.info(f"Callback {callback_name} being set on Form")
        supported = ["update_elements", "edit_enable", "edit_disable"]

        # Add in mapped elements
        for mapped in self.element_map:
            supported.append(mapped.element.key)

        # Add in other window elements
        for element in self.window.key_dict:
            supported.append(element)

        if callback_name in supported:
            self.callbacks[callback_name] = fctn
        else:
            raise RuntimeError(
                f'Callback "{callback_name}" not supported. callback: {callback_name} '
                f"supported: {supported}"
            )

    def add_dataset(
        self,
        data_key: str,
        table: str,
        pk_column: str,
        description_column: str,
        query: str = "",
        order_clause: str = "",
    ) -> None:
        """Manually add a `DataSet` object to the `Form` When you attach to a database,
        PySimpleSQL isn't aware of what it contains until this command is run Note that
        `Form.auto_add_datasets()` does this automatically, which is called when a
        `Form` is created.

        Args:
            data_key: The key to give this `DataSet`.  Use frm['data_key'] to access it.
            table: The name of the table in the database
            pk_column: The primary key column of the table in the database
            description_column: The column to be used to display to users in listboxes,
                comboboxes, etc.
            query: The initial query for the table.  Auto generates "SELECT * FROM
                {table}" if none is passed
            order_clause: The initial sort order for the query

        Returns:
            None
        """
        self.datasets.update(
            {
                data_key: DataSet(
                    data_key,
                    self,
                    table,
                    pk_column,
                    description_column,
                    query,
                    order_clause,
                )
            }
        )
        # set a default sort order
        self[data_key].set_search_order([description_column])

    def set_fk_column_cascade(
        self,
        child_table: str,
        fk_column: str,
        update_cascade: bool = None,
        delete_cascade: bool = None,
    ) -> None:
        """Set a foreign key's update_cascade and delete_cascade behavior.

        `SQLDriver.auto_add_relationships()` does this automatically from the database
        schema.

        Args:
            child_table: Child table with the foreign key.
            fk_column: Foreign key column of the child table.
            update_cascade: True to requery and filter child table on selected parent
                primary key.
            delete_cascade: True to delete dependent child records if parent record is
                deleted.

        Returns:
            None
        """
        for rel in self.relationships:
            if rel.child_table == child_table and rel.fk_column == fk_column:
                logger.info(f"Updating {fk_column=} self.relationships.")
                if update_cascade is not None:
                    rel.update_cascade = update_cascade
                if delete_cascade is not None:
                    rel.delete_cascade = delete_cascade

    def auto_add_datasets(self) -> None:
        """Automatically add `DataSet` objects from the database by looping through the
        tables available and creating a `DataSet` object for each. Each dataset key is
        an optional prefix plus the name of the table. When you attach to a sqlite
        database, PySimpleSQL isn't aware of what it contains until this command is run.
        This is called automatically when a `Form ` is created. Note that
        `Form.add_dataset()` can do this manually on a per-table basis.

        Returns:
            None
        """
        logger.info(
            "Automatically generating dataset for each table in the sqlite database"
        )
        # Clear any current dataset so successive calls won't double the entries
        self.datasets = {}
        tables = self.driver.get_tables()
        for table in tables:
            column_info = self.driver.column_info(table)

            # auto generate description column.  Default it to the 2nd column,
            # but can be overwritten below
            description_column = column_info.col_name(1)
            for col in column_info.names:
                if col in self.description_column_names:
                    description_column = col
                    break

            # Get our pk column
            pk_column = self.driver.pk_column(table)

            data_key = table
            logger.debug(
                f'Adding DataSet "{data_key}" on table {table} to Form with primary '
                f"key {pk_column} and description of {description_column}"
            )
            self.add_dataset(data_key, table, pk_column, description_column)
            self.datasets[data_key].column_info = column_info

    # Map an element to a DataSet.
    # Optionally a where_column and a where_value.  This is useful for key,value pairs!
    def map_element(
        self,
        element: sg.Element,
        dataset: DataSet,
        column: str,
        where_column: str = None,
        where_value: str = None,
    ) -> None:
        """Map a PySimpleGUI element to a specific `DataSet` column.  This is what makes
        the GUI automatically update to the contents of the database.  This happens
        automatically when a PySimpleGUI Window is bound to a `Form` by using the bind
        parameter of `Form` creation, or by executing `Form.auto_map_elements()` as long
        as the element metadata is configured properly. This method can be used to
        manually map any element to any `DataSet` column regardless of metadata
        configuration.

        Args:
            element: A PySimpleGUI Element
            dataset: A `DataSet` object
            column: The name of the column to bind to the element
            where_column: Used for ke, value shorthand TODO: expand on this
            where_value: Used for ey, value shorthand TODO: expand on this

        Returns:
            None
        """
        logger.debug(f"Mapping element {element.key}")
        self.element_map.append(
            ElementMap(element, dataset, column, where_column, where_value)
        )

    def add_info_element(self, element: Union[sg.StatusBar, sg.Text]) -> None:
        """Add an element to be updated with info messages.

        Must be either

        Args:
            element: A PySimpleGUI Element

        Returns:
            None
        """
        if not isinstance(element, (sg.StatusBar, sg.Text)):
            logger.debug(f"Can only add info {element!s}")
            return
        logger.debug(f"Mapping element {element.key}")
        self.popup.info_elements.append(element)

    def auto_map_elements(self, win: sg.Window, keys: List[str] = None) -> None:
        """Automatically map PySimpleGUI Elements to `DataSet` columns. A special naming
        convention has to be used for automatic mapping to happen.  Note that
        `Form.map_element()` can be used to manually map an Element to a column.
        Automatic mapping relies on a special naming convention as well as certain data
        in the Element's metadata. The convenience functions `field()`, `selector()`,
        and `actions()` do this automatically and should be used in almost all cases to
        make elements that conform to this standard, but this information will allow you
        to do this manually if needed. For individual fields, Element keys must be named
        'Table.column'. Additionally, the metadata must contain a dict with the key of
        'type' set to `TYPE_RECORD`. For selectors, the key can be named whatever you
        want, but the metadata must contain a dict with the key of 'type' set to
        TPE_SELECTOR.

        Args:
            win: A PySimpleGUI Window
            keys: (optional) Limit the auto mapping to this list of Element keys

        Returns:
            None
        """
        logger.info("Automapping elements")
        # Clear previously mapped elements so successive calls won't produce duplicates
        self.element_map = []
        for key in win.key_dict:
            element = win[key]

            # Skip this element if there is no metadata present
            if not isinstance(element.metadata, dict):
                continue

            # Process the filter to ensure this element should be mapped to this Form
            if (
                "filter" in element.metadata
                and element.metadata["filter"] == self.filter
            ):
                element.metadata["Form"] = self
            if self.filter is None and "filter" not in element.metadata:
                element.metadata["Form"] = self

            # Skip this element if it's an event
            if element.metadata["type"] == TYPE_EVENT:
                continue

            if element.metadata["Form"] != self:
                continue
            # If we passed in a custom list of elements
            if keys is not None and key not in keys:
                continue

            # Map Record Element
            if element.metadata["type"] == TYPE_RECORD:
                # Does this record imply a where clause (indicated by ?)
                # If so, we can strip out the information we need
                data_key = element.metadata["data_key"]
                field = element.metadata["field"]
                if "?" in field:
                    table_info, where_info = field.split("?")
                else:
                    table_info = field
                    where_info = None
                try:
                    table, col = table_info.split(".")
                except ValueError:
                    table, col = table_info, None

                if where_info is None:
                    where_column = where_value = None
                else:
                    where_column, where_value = where_info.split("=")

                # make sure we don't use reserved keywords that could end up in a query
                for keyword in [table, col, where_column, where_value]:
                    if keyword is not None and keyword:
                        self.driver.check_keyword(keyword)

                # DataSet objects are named after the tables they represent
                # (with an optional prefix)
                # TODO: How to handle the prefix?
                # TODO: check in DataSet.table
                if table in self.datasets and col in self[table].column_info:
                    # Map this element to DataSet.column
                    self.map_element(
                        element, self[table], col, where_column, where_value
                    )
                    if isinstance(element, (_EnhancedInput, _EnhancedMultiline)) and (
                        col in self[table].column_info.names
                        and self[table].column_info[col].notnull
                    ):
                        element.add_placeholder(
                            placeholder=lang.notnull_placeholder,
                            color=themepack.placeholder_color,
                        )
                    if (
                        isinstance(element, _EnhancedInput)
                        and col in self[table].column_info.names
                    ):
                        element.add_validate(self[table], col)

            # Map Selector Element
            elif element.metadata["type"] == TYPE_SELECTOR:
                k = element.metadata["table"]
                if k is None:
                    continue
                if element.metadata["Form"] != self:
                    continue
                if "?" in k:
                    table_info, where_info = k.split("?")
                    where_column, where_value = where_info.split("=")
                else:
                    table_info = k
                    where_column = where_value = None
                data_key = table_info

                if data_key in self.datasets:
                    self[data_key].add_selector(
                        element, data_key, where_column, where_value
                    )

                    # Enable sorting if TableBuilder is present
                    if (
                        isinstance(element, sg.Table)
                        and "TableBuilder" in element.metadata
                    ):
                        table_builder: TableBuilder = element.metadata["TableBuilder"]
                        # We need a whole chain of things to happen
                        # when a heading is clicked on:
                        # 1 Run the ResultRow.sort_cycle() with the correct column name
                        # 2 Run TableBuilder._update_headings() with the:
                        #   Table element, sort_column, sort_reverse
                        # 3 Run update_elements() to see the changes
                        table_builder.enable_heading_function(
                            element,
                            _HeadingCallback(self, data_key),
                        )

                else:
                    logger.debug(f"Can not add selector {element!s}")

            elif element.metadata["type"] == TYPE_INFO:
                self.add_info_element(element)

    def set_element_clauses(
        self, element: sg.Element, where_clause: str = None, order_clause: str = None
    ) -> None:
        """Set the where and/or order clauses for the specified element in the element
        map.

        Args:
            element: A PySimpleGUI Element
            where_clause: (optional) The where clause to set
            order_clause: (optional) The order clause to set

        Returns:
            None
        """
        for mapped in self.element_map:
            if mapped.element == element:
                mapped.where_clause = where_clause
                mapped.order_clause = order_clause

    def map_event(
        self, event: str, fctn: Callable[[None], None], table: str = None
    ) -> None:
        """Manually map a PySimpleGUI event (returned by Window.read()) to a callable.
        The callable will execute when the event is detected by `Form.process_events()`.
        Most users will not have to manually map any events, as `Form.auto_map_events()`
        will create most needed events when a PySimpleGUI Window is bound to a `Form` by
        using the bind parameter of `Form` creation, or by executing
        `Form.auto_map_elements()`.

        Args:
            event: The event to watch for, as returned by PySimpleGUI Window.read() (an
                element name for example)
            fctn: The callable to run when the event is detected. It should take no
                parameters and have no return value
            table: (optional) currently not used

        Returns:
            None
        """
        dic = {"event": event, "function": fctn, "table": table}
        logger.debug(f"Mapping event {event} to function {fctn}")
        self.event_map.append(dic)

    def replace_event(
        self, event: str, fctn: Callable[[None], None], table: str = None
    ) -> None:
        """Replace an event that was manually mapped with `Form.auto_map_events()` or
        `Form.map_event()`. The callable will execute.

        Args:
            event: The event to watch for, as returned by PySimpleGUI Window.read() (an
                element name for example)
            fctn: The callable to run when the event is detected. It should take no
                parameters and have no return value
            table: (optional) currently not used

        Returns:
            None
        """
        for e in self.event_map:
            if e["event"] == event:
                e["function"] = fctn
                e["table"] = table if table is not None else e["table"]

    def auto_map_events(self, win: sg.Window) -> None:
        """Automatically map events. pysimplesql relies on certain events to function
        properly. This method maps all the record navigation (previous, next, etc.) and
        database actions (insert, delete, save, etc.).  Note that the event mapper is
        very general-purpose, and you can add your own event triggers to the mapper
        using `Form.map_event()`, or even replace one of the auto-generated ones if you
        have specific needs by using `Form.replace_event()`.

        Args:
            win: A PySimpleGUI Window

        Returns:
            None
        """
        logger.info("Automapping events")
        # Clear mapped events to ensure successive calls won't produce duplicates
        self.event_map = []

        for key in win.key_dict:
            # key = str(key)  # sometimes end up with an integer element 0?TODO:Research
            element = win[key]
            # Skip this element if there is no metadata present
            if not isinstance(element.metadata, dict):
                logger.debug(f"Skipping mapping of {key}")
                continue
            if element.metadata["Form"] != self:
                continue
            if element.metadata["type"] == TYPE_EVENT:
                event_type = element.metadata["event_type"]
                table = element.metadata["table"]
                column = element.metadata["column"]
                function = element.metadata["function"]
                funct = None

                data_key = table
                data_key = data_key if data_key in self.datasets else None
                if event_type == EVENT_FIRST:
                    if data_key:
                        funct = self[data_key].first
                elif event_type == EVENT_PREVIOUS:
                    if data_key:
                        funct = self[data_key].previous
                elif event_type == EVENT_NEXT:
                    if data_key:
                        funct = self[data_key].next
                elif event_type == EVENT_LAST:
                    if data_key:
                        funct = self[data_key].last
                elif event_type == EVENT_SAVE:
                    if data_key:
                        funct = self[data_key].save_record
                elif event_type == EVENT_INSERT:
                    if data_key:
                        funct = self[data_key].insert_record
                elif event_type == EVENT_DELETE:
                    if data_key:
                        funct = self[data_key].delete_record
                elif event_type == EVENT_DUPLICATE:
                    if data_key:
                        funct = self[data_key].duplicate_record
                elif event_type == EVENT_EDIT_PROTECT_DB:
                    self.edit_protect()  # Enable it!
                    funct = self.edit_protect
                elif event_type == EVENT_SAVE_DB:
                    funct = self.save_records
                elif event_type == EVENT_SEARCH:
                    # Build the search box name
                    search_element, command = key.split(":")
                    search_box = f"{search_element}:search_input"
                    if data_key:
                        funct = functools.partial(self[data_key].search, search_box)
                        # add placeholder
                        self.window[search_box].add_placeholder(
                            placeholder=lang.search_placeholder,
                            color=themepack.placeholder_color,
                        )
                        # bind dataset
                        self.window[search_box].bind_dataset(self[data_key])
                # elif event_type==EVENT_SEARCH_DB:
                elif event_type == EVENT_QUICK_EDIT:
                    quick_editor_kwargs = {}
                    if "quick_editor_kwargs" in element.metadata:
                        quick_editor_kwargs = element.metadata["quick_editor_kwargs"]
                    referring_table = table
                    table = self[table].get_related_table_for_column(column)
                    funct = functools.partial(
                        self[table].quick_editor,
                        self[referring_table].get_current,
                        column,
                        **quick_editor_kwargs if quick_editor_kwargs else {},
                    )
                elif event_type == EVENT_FUNCTION:
                    funct = function
                else:
                    logger.debug(f"Unsupported event_type: {event_type}")

                if funct is not None:
                    self.map_event(key, funct, data_key)

    def edit_protect(self) -> None:
        """The edit protect system allows records to be protected from accidental
        editing by disabling the insert, delete, duplicate and save buttons on the GUI.
        A button to toggle the edit protect mode can easily be added by using the
        `actions()` convenience function.

        Returns:
            None
        """
        logger.debug("Toggling edit protect mode.")
        # Callbacks
        if (
            self._edit_protect
            and "edit_enable" in self.callbacks
            and not self.callbacks["edit_enable"](self, self.window)
        ):
            return
        if (
            not self._edit_protect
            and "edit_disable" in self.callbacks
            and not self.callbacks["edit_disable"](self, self.window)
        ):
            return

        self._edit_protect = not self._edit_protect
        self.update_elements(edit_protect_only=True)

    def get_edit_protect(self) -> bool:
        """Get the current edit protect state.

        Returns:
            True if edit protect is enabled, False if not enabled
        """
        return self._edit_protect

    def prompt_save(self) -> PromptSaveValue:
        """Prompt to save if any GUI changes are found the affect any table on this
        form. The helps prevent data entry loss when performing an action that changes
        the current record of a `DataSet`.

        Returns:
            One of the prompt constant values: PROMPT_SAVE_PROCEED,
            PROMPT_SAVE_DISCARDED, PROMPT_SAVE_NONE
        """
        user_prompted = False  # Has the user been prompted yet?
        for data_key in self.datasets:
            if not self[data_key]._prompt_save:
                continue

            if self[data_key].records_changed(recursive=False) and not user_prompted:
                # only show popup once, regardless of how many dataset have changed
                user_prompted = True
                if self._prompt_save == AUTOSAVE_MODE:
                    save_changes = "yes"
                else:
                    save_changes = self.popup.yes_no(
                        lang.form_prompt_save_title, lang.form_prompt_save
                    )
                if save_changes != "yes":
                    # update the elements to erase any GUI changes,
                    # since we are choosing not to save
                    for data_key_ in self.datasets:
                        self[data_key_].purge_virtual()
                        self[data_key_].restore_current_row()
                    self.update_elements()
                    # We did have a change, regardless if the user chose not to save
                    return PROMPT_SAVE_DISCARDED
                break
        if user_prompted:
            self.save_records(check_prompt_save=True)
        return PROMPT_SAVE_PROCEED if user_prompted else PROMPT_SAVE_NONE

    def set_prompt_save(self, mode: int) -> None:
        """Set the prompt to save action when navigating records for all `DataSet`
        objects associated with this `Form`.

        Args:
            mode: Use `PROMPT_MODE` to prompt to save when unsaved changes are present.
                `AUTOSAVE_MODE` to autosave when unsaved changes are present.

        Returns:
            None
        """
        self._prompt_save = mode
        for data_key in self.datasets:
            self[data_key].set_prompt_save(mode)

    def set_force_save(self, force: bool = False) -> None:
        """Force save without checking for changes first, so even an unchanged record
        will be written back to the database.

        Args:
            force: True to force unchanged records to save.

        Returns:
            None
        """
        self.force_save = force

    def set_live_update(self, enable: bool) -> None:
        """Toggle the immediate sync of field elements with other elements in Form.

        When live-update is enabled, changes in a field element are immediately
        reflected in other elements in the same Form. This is achieved by binding the
        Window to watch for events that may trigger updates, such as mouse clicks, key
        presses, or selection changes in a combo box.

        Args:
            enable: If True, changes in a field element are immediately reflected in
                other elements in the same Form. If False, live-update is disabled.
        """
        bind_events = ["<ButtonRelease-1>", "<KeyPress>", "<<ComboboxSelected>>"]
        if enable and not self._liveupdate_binds:
            self.live_update = True
            for event in bind_events:
                self._liveupdate_binds[event] = self.window.TKroot.bind(
                    event, self._liveupdate, "+"
                )
        elif not enable and self._liveupdate_binds:
            for event, bind in self._liveupdate_binds.items():
                self.window.TKroot.unbind(event, bind)
            self._liveupdate_binds = {}
            self.live_update = False

    def save_records(
        self,
        table: str = None,
        cascade_only: bool = False,
        check_prompt_save: bool = False,
        update_elements: bool = True,
    ) -> Union[SAVE_SUCCESS, SAVE_FAIL, SAVE_NONE]:
        """Save records of all `DataSet` objects` associated with this `Form`.

        Args:
            table: Name of table to save, as well as any cascaded relationships. Used in
                `DataSet.prompt_save()`
            cascade_only: Save only tables with cascaded relationships. Default False.
            check_prompt_save: Passed to `DataSet.save_record_recursive` to check if
                individual `DataSet` has prompt_save enabled. Used when
                `Form.save_records()` is called from `Form.prompt_save()`.
            update_elements: (optional) Passed to `Form.save_record_recursive()`

        Returns:
            result - can be used with RETURN BITMASKS
        """
        if check_prompt_save:
            logger.debug("Saving records in all datasets that allow prompt_save...")
        else:
            logger.debug("Saving records in all datasets...")

        display_message = not self.save_quiet

        result = 0
        show_message = True
        failed_tables = []

        if table:
            tables = [table]  # if passed single table
        # for cascade_only, build list of top-level dataset that have children
        elif cascade_only:
            tables = [
                dataset.table
                for dataset in self.datasets.values()
                if len(self.relationships.get_update_cascade_tables(dataset.table))
                and self.relationships.get_parent(dataset.table) is None
            ]
        # default behavior, build list of top-level dataset (ones without a parent)
        else:
            tables = [
                dataset.table
                for dataset in self.datasets.values()
                if self.relationships.get_parent(dataset.table) is None
            ]

        # call save_record_recursive on tables, which saves from last to first.
        result_list = []
        for q in tables:
            res = self[q].save_record_recursive(
                results={},
                display_message=False,
                check_prompt_save=check_prompt_save,
                update_elements=update_elements,
            )
            result_list.append(res)

        # flatten list of result dicts
        results = {k: v for d in result_list for k, v in d.items()}
        logger.debug(f"Form.save_records - results of tables - {results}")

        # get tables that failed
        for t, res in results.items():
            if not res & SHOW_MESSAGE:
                show_message = (
                    False  # Only one instance of not showing the message hides all
                )
            if res & SAVE_FAIL:
                failed_tables.append(t)
            result |= res

        # Build a descriptive message, since the save spans many tables potentially
        msg = ""
        msg_tables = ", ".join(failed_tables)
        if result & SAVE_FAIL:
            if result & SAVE_SUCCESS:
                msg = lang.form_save_partial
            msg += lang.form_save_problem.format_map(LangFormat(tables=msg_tables))
            if show_message:
                self.popup.ok(lang.form_save_problem_title, msg)
            return result
        msg = lang.form_save_success if result & SAVE_SUCCESS else lang.form_save_none
        if show_message:
            self.popup.info(msg, display_message=display_message)
        return result

    def update_elements(
        self,
        target_data_key: str = None,
        edit_protect_only: bool = False,
        omit_elements: List[str] = None,
    ) -> None:
        """Updated the GUI elements to reflect values from the database for this `Form`
        instance only. Not to be confused with the main `update_elements()`, which
        updates GUI elements for all `Form` instances. This method also executes
        `update_selectors()`, which updates selector elements.

        Args:
            target_data_key: (optional) dataset key to update elements for, otherwise
                updates elements for all datasets
            edit_protect_only: (optional) If true, only update items affected by
                edit_protect
            omit_elements: A list of elements to omit updating

        Returns:
            None
        """
        if omit_elements is None:
            omit_elements = []

        msg = "edit protect" if edit_protect_only else "PySimpleGUI"
        logger.debug(f"update_elements(): Updating {msg} elements")
        # Disable/Enable action elements based on edit_protect or other situations

        for data_key in self.datasets:
            if target_data_key is not None and data_key != target_data_key:
                continue

            # disable mapped elements for this table if
            # there are no records in this table or edit protect mode
            disable = not self[data_key].row_count or self._edit_protect
            self.update_element_states(data_key, disable)

        self.update_actions(target_data_key)

        if edit_protect_only:
            return

        self.update_fields(target_data_key, omit_elements)

        self.update_selectors(target_data_key, omit_elements)

        # Run callbacks
        if "update_elements" in self.callbacks:
            # Running user update function
            logger.info("Running the update_elements callback...")
            self.callbacks["update_elements"](self, self.window)

    def update_actions(self, target_data_key: str = None) -> None:
        """Update state for action-buttons.

        Args:
            target_data_key: (optional) dataset key to update elements for, otherwise
                updates elements for all datasets
        """
        win = self.window
        for data_key in self.datasets:
            if target_data_key is not None and data_key != target_data_key:
                continue

            # call row_count @property once
            row_count = self[data_key].row_count

            for m in (m for m in self.event_map if m["table"] == self[data_key].table):
                # Disable delete and mapped elements for this table if there are no
                # records in this table or edit protect mode
                if ":table_delete" in m["event"]:
                    disable = not row_count or self._edit_protect
                    win[m["event"]].update(disabled=disable)

                # Disable duplicate if no rows, edit protect, or current row virtual
                elif ":table_duplicate" in m["event"]:
                    disable = bool(
                        not row_count
                        or self._edit_protect
                        or self[data_key].pk_is_virtual()
                    )
                    win[m["event"]].update(disabled=disable)

                # Disable first/prev if only 1 row, or first row
                elif ":table_first" in m["event"] or ":table_previous" in m["event"]:
                    disable = row_count < 2 or self[data_key].current_index == 0
                    win[m["event"]].update(disabled=disable)

                # Disable next/last if only 1 row, or last row
                elif ":table_next" in m["event"] or ":table_last" in m["event"]:
                    disable = row_count < 2 or (
                        self[data_key].current_index == row_count - 1
                    )
                    win[m["event"]].update(disabled=disable)

                # Disable insert on children with no parent/virtual parent records or
                # edit protect mode
                elif ":table_insert" in m["event"]:
                    parent = self.relationships.get_parent(data_key)
                    if parent is not None:
                        disable = bool(
                            not self[parent].row_count
                            or self._edit_protect
                            or self.relationships.parent_virtual(data_key, self)
                        )
                    else:
                        disable = self._edit_protect
                    win[m["event"]].update(disabled=disable)

                # Disable db_save when needed
                elif ":db_save" in m["event"] or ":save_table" in m["event"]:
                    disable = not row_count or self._edit_protect
                    win[m["event"]].update(disabled=disable)

                # Enable/Disable quick edit buttons
                elif ":quick_edit" in m["event"]:
                    win[m["event"]].update(disabled=disable)

    def update_fields(
        self,
        target_data_key: str = None,
        omit_elements: List[str] = None,
        columns: List[str] = None,
        combo_values_only: bool = False,
    ) -> None:
        """Updated the field elements to reflect their `rows` DataFrame for this `Form`
        instance only.

        Args:
            target_data_key: (optional) dataset key to update elements for, otherwise
                updates elements for all datasets
            omit_elements: A list of elements to omit updating
            columns: A list of column names to update
            combo_values_only: Updates the value list only for comboboxes.
        """
        if omit_elements is None:
            omit_elements = []

        if columns is None:
            columns = []

        # Render GUI Elements
        # d= dictionary (the element map dictionary)
        for mapped in self.element_map:
            # If the optional target_data_key parameter was passed, we will only update
            # elements bound to that table
            if (
                target_data_key is not None
                and mapped.table != self[target_data_key].table
            ):
                continue

            # skip updating this element if requested
            if mapped.element in omit_elements:
                continue

            if combo_values_only and not isinstance(mapped.element, sg.Combo):
                continue

            if len(columns) and mapped.column not in columns:
                continue

            # Update Markers
            # --------------------------------------------------------------------------
            # Show the Required Record marker if the column has notnull set and
            # this is a virtual row
            marker_key = mapped.element.key + ":marker"
            try:
                if mapped.dataset.pk_is_virtual():
                    # get the column name from the key
                    col = mapped.column
                    # get notnull from the column info
                    if (
                        col in mapped.dataset.column_info.names
                        and mapped.dataset.column_info[col].notnull
                    ):
                        self.window[marker_key].update(
                            visible=True,
                            text_color=themepack.marker_required_color,
                        )
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

            if mapped.where_column is not None:
                # We are looking for a key,value pair or similar.
                # Sift through and see what to put
                updated_val = mapped.dataset.get_keyed_value(
                    mapped.column, mapped.where_column, mapped.where_value
                )
                # TODO, may need to add more??
                if isinstance(mapped.element, sg.Checkbox):
                    updated_val = checkbox_to_bool(updated_val)

            elif isinstance(mapped.element, sg.Combo):
                # Update elements with foreign dataset first
                # This will basically only be things like comboboxes
                # Find the relationship to determine which table to get data from
                combo_vals = mapped.dataset.combobox_values(mapped.column)
                if not combo_vals:
                    logger.info(
                        f"Error! Could not find related data for element "
                        f"{mapped.element.key} bound to DataSet "
                        f"key {mapped.table}, column: {mapped.column}"
                    )
                    # we don't want to update the list in this case, as it was most
                    # likely supplied and not tied to data
                    updated_val = mapped.dataset[mapped.column]
                    mapped.element.update(updated_val)
                    continue

                # else, first...
                # set to currently selected pk in gui
                if combo_values_only:
                    match_val = mapped.element.get().get_pk()
                # or set to what is saved in current row
                else:
                    match_val = mapped.dataset[mapped.column]

                # grab first matching entry (value)
                updated_val = next(
                    (entry for entry in combo_vals if entry.get_pk() == match_val),
                    None,
                )
                # and update element
                mapped.element.update(values=combo_vals)

            elif isinstance(mapped.element, sg.Text):
                rels = self.relationships.get_rels_for(mapped.dataset.table)
                found = False
                # try to get description of linked if foreign-key
                for rel in rels:
                    if mapped.column == rel.fk_column:
                        updated_val = mapped.dataset.frm[
                            rel.parent_table
                        ].get_description_for_pk(mapped.dataset[mapped.column])
                        found = True
                        break
                if not found:
                    updated_val = mapped.dataset[mapped.column]
                mapped.element.update("")

            elif isinstance(mapped.element, sg.Table):
                # Tables use an array of arrays for values.  Note that the headings
                # can't be changed.
                values = mapped.dataset.table_values()
                # Select the current one
                pk = mapped.dataset.get_current_pk()

                if len(values):  # noqa SIM108
                    # set index to pk
                    index = [[v[0] for v in values].index(pk)]
                else:  # if empty
                    index = []

                # Update table, and set vertical scroll bar to follow selected element
                update_table_element(self.window, mapped.element, values, index)
                continue

            elif isinstance(mapped.element, (sg.Input, sg.Multiline)):
                # Update the element in the GUI
                # For text objects, lets clear it first...

                # HACK for sqlite query not making needed keys! This will clear
                mapped.element.update("")

                updated_val = mapped.dataset[mapped.column]

            elif isinstance(mapped.element, sg.Checkbox):
                updated_val = checkbox_to_bool(mapped.dataset[mapped.column])

            elif isinstance(mapped.element, sg.Image):
                val = mapped.dataset[mapped.column]

                try:
                    val = eval(val)
                except:  # noqa: E722
                    # treat it as a filename
                    mapped.element.update(val)
                else:
                    # update the bytes data
                    mapped.element.update(data=val)
                # Prevent the update from triggering below, since we are doing it here
                updated_val = None
            else:
                sg.popup(f"Unknown element type {type(mapped.element)}")

            # Finally, we will update the actual GUI element!
            if updated_val is not None:
                mapped.element.update(updated_val)

    def update_selectors(
        self,
        target_data_key: str = None,
        omit_elements: List[str] = None,
        search_filter_only: bool = False,
    ) -> None:
        """Updated the selector elements to reflect their `rows` DataFrame.

        Args:
            target_data_key: (optional) dataset key to update elements for, otherwise
                updates elements for all datasets.
            omit_elements: A list of elements to omit updating

        Returns:
            None
        """
        if omit_elements is None:
            omit_elements = []

        # ---------
        # SELECTORS
        # ---------
        # We can update the selector elements
        # We do it down here because it's not a mapped element...
        # Check for selector events
        for data_key, dataset in self.datasets.items():
            if target_data_key is not None and target_data_key != data_key:
                continue

            if len(dataset.selector):
                for e in dataset.selector:
                    logger.debug("update_elements: SELECTOR FOUND")
                    # skip updating this element if requested
                    if e["element"] in omit_elements:
                        continue

                    element: sg.Element = e["element"]
                    logger.debug(f"{type(element)}")
                    pk_column = dataset.pk_column
                    description_column = dataset.description_column
                    if element.key in self.callbacks:
                        self.callbacks[element.key]()

                    if isinstance(element, (sg.Listbox, sg.Combo)):
                        logger.debug("update_elements: List/Combo selector found...")
                        lst = []
                        for _, r in dataset.rows.iterrows():
                            if e["where_column"] is not None:
                                # TODO: Kind of a hackish way to check for equality.
                                if str(r[e["where_column"]]) == str(e["where_value"]):
                                    lst.append(
                                        _ElementRow(r[pk_column], r[description_column])
                                    )
                                else:
                                    pass
                            else:
                                lst.append(
                                    _ElementRow(r[pk_column], r[description_column])
                                )

                        element.update(
                            values=lst,
                            set_to_index=dataset.current_index,
                        )

                        # set vertical scroll bar to follow selected element
                        # (for listboxes only)
                        if isinstance(element, sg.Listbox):
                            try:
                                element.set_vscroll_position(
                                    dataset.current_index / len(lst)
                                )
                            except ZeroDivisionError:
                                element.set_vscroll_position(0)

                    elif isinstance(element, sg.Slider):
                        # Re-range the element depending on the number of records
                        l = dataset.row_count  # noqa: E741
                        element.update(value=dataset._current_index + 1, range=(1, l))

                    elif isinstance(element, sg.Table):
                        logger.debug("update_elements: Table selector found...")
                        # Populate entries
                        apply_search_filter = False
                        try:
                            columns = element.metadata["TableBuilder"].columns
                            apply_search_filter = element.metadata[
                                "TableBuilder"
                            ].apply_search_filter
                        except KeyError:
                            columns = None  # default to all columns

                        # skip Tables that don't request search_filter
                        if search_filter_only and not apply_search_filter:
                            continue

                        values = dataset.table_values(
                            columns,
                            mark_unsaved=True,
                            apply_search_filter=apply_search_filter,
                        )

                        # Get the primary key to select.
                        # Use the list above instead of getting it directly
                        # from the table, as the data has yet to be updated
                        pk = dataset.get_current_pk()

                        found = False
                        if len(values):
                            # set to index by pk
                            try:
                                index = [[v.pk for v in values].index(pk)]
                                found = True
                            except ValueError:
                                index = []
                        else:  # if empty
                            index = []

                        logger.debug(f"Selector:: index:{index} found:{found}")

                        # Update table, and set vertical scroll bar to follow
                        update_table_element(self.window, element, values, index)

    def requery_all(
        self,
        select_first: bool = True,
        filtered: bool = True,
        update_elements: bool = True,
        requery_dependents: bool = True,
    ) -> None:
        """Requeries all `DataSet` objects associated with this `Form`. This effectively
        re-loads the data from the database into `DataSet` objects.

        Args:
            select_first: passed to `DataSet.requery()` -> `DataSet.first()`. If True,
                the first record will be selected after the requery
            filtered: passed to `DataSet.requery()`. If True, the relationships will be
                considered and an appropriate WHERE clause will be generated. False will
                display all records from the table.
            update_elements: passed to `DataSet.requery()` -> `DataSet.first()` to
                `Form.update_elements()`. Note that the select_first parameter must =
                True to use this parameter.
            requery_dependents: passed to `DataSet.requery()` -> `DataSet.first()` to
                `Form.requery_dependents()`. Note that the select_first parameter must =
                True to use this parameter.

        Returns:
            None
        """

        logger.info("Requerying all datasets")

        # first let datasets requery through cascade
        for data_key in self.datasets:
            if self.relationships.get_parent(data_key) is None:
                self[data_key].requery(
                    select_first=select_first,
                    filtered=filtered,
                    update_elements=update_elements,
                    requery_dependents=requery_dependents,
                )

        # fill in any datasets that are empty
        for data_key in self.datasets:
            if self[data_key].rows.columns.empty:
                self[data_key].rows = Result.set(
                    pd.DataFrame(columns=self[data_key].column_info.names)
                )

    def process_events(self, event: str, values: list) -> bool:
        """Process mapped events for this specific `Form` instance.

        Not to be confused with the main `process_events()`, which processes events for
        ALL `Form` instances. This should be called once per iteration in your event
        loop. Note: Events handled are responsible for requerying and updating elements
        as needed.

        Args:
            event: The event returned by PySimpleGUI.read()
            values: the values returned by PySimpleGUI.read()

        Returns:
            True if an event was handled, False otherwise
        """
        if self.window is None:
            logger.info(
                "***** Form appears to be unbound. "
                "Do you have frm.bind(win) in your code? *****"
            )
            return False
        if event:
            for e in self.event_map:
                if e["event"] == event:
                    logger.debug(f"Executing event {event} via event mapping.")
                    e["function"]()
                    logger.debug("Done processing event!")
                    return True

            # Check for  selector events
            for _data_key, dataset in self.datasets.items():
                if len(dataset.selector):
                    for e in dataset.selector:
                        element: sg.Element = e["element"]
                        if element.key == event and len(dataset.rows) > 0:
                            changed = False  # assume that a change will not take place
                            if isinstance(element, sg.Listbox):
                                row = values[element.Key][0]
                                dataset.set_by_pk(row.get_pk())
                                changed = True
                            elif isinstance(element, sg.Slider):
                                dataset.set_by_index(int(values[event]) - 1)
                                changed = True
                            elif isinstance(element, sg.Combo):
                                row = values[event]
                                dataset.set_by_pk(row.get_pk())
                                changed = True
                            elif isinstance(element, sg.Table) and len(values[event]):
                                if isinstance(element, LazyTable):
                                    pk = int(values[event])
                                else:
                                    index = values[event][0]
                                    pk = self.window[event].Values[index].pk
                                # no need to update the selector!
                                dataset.set_by_pk(pk, True, omit_elements=[element])

                                changed = True
                            if changed and "record_changed" in dataset.callbacks:
                                dataset.callbacks["record_changed"](self, self.window)
                            return changed
        return False

    def update_element_states(
        self, table: str, disable: bool = None, visible: bool = None
    ) -> None:
        """Disable/enable and/or show/hide all elements associated with a table.

        Args:
            table: table name associated with elements to disable/enable
            disable: True/False to disable/enable element(s), None for no change
            visible: True/False to make elements visible or not, None for no change

        Returns:
            None
        """
        for mapped in self.element_map:
            if mapped.table != table:
                continue
            element = mapped.element
            if isinstance(element, (sg.Input, sg.Multiline, sg.Combo, sg.Checkbox)):
                # if element.Key in self.window.key_dict.keys():
                logger.debug(
                    f"Updating element {element.Key} to disabled: "
                    f"{disable}, visible: {visible}"
                )
                if disable is not None:
                    element.update(disabled=disable)
                if visible is not None:
                    element.update(visible=visible)

    @classmethod
    def purge_instance(cls, frm: Form) -> None:
        """Remove self from Form.instances.

        Args:
            frm: the `Form` to purge

        Returns:
            None
        """
        cls.instances = [i for i in cls.instances if i != frm]


# =====================================================================================
# MAIN PYSIMPLESQL UTILITY FUNCTIONS
# =====================================================================================
# These functions exist as utilities to the pysimplesql module
# This is a dummy class for documenting utility functions
class Utility:

    """Utility functions are a collection of functions and classes that directly improve
    on aspects of the pysimplesql module.

    See the documentation for the following utility functions:
    `process_events()`, `update_elements()`, `bind()`, `simple_transform()`, `KeyGen()`,

    Note: This is a dummy class that exists purely to enhance documentation and has no
    use to the end user.
    """


def process_events(event: str, values: list) -> bool:
    """Process mapped events for ALL Form instances.

    Not to be confused with `Form.process_events()`, which processes events for
    individual `Form` instances. This should be called once per iteration in your event
    loop. Note: Events handled are responsible for requerying and updating elements as
    needed.

    Args:
        event: The event returned by PySimpleGUI.read()
        values: the values returned by PySimpleGUI.read()

    Returns:
        True if an event was handled, False otherwise
    """
    handled = False
    for i in Form.instances:
        if i.process_events(event, values):
            handled = True
    return handled


def update_elements(data_key: str = None, edit_protect_only: bool = False) -> None:
    """Updated the GUI elements to reflect values from the database for ALL Form
    instances. Not to be confused with `Form.update_elements()`, which updates GUI
    elements for individual `Form` instances.

    Args:
        data_key: (optional) key of `DataSet` to update elements for, otherwise updates
            elements for all datasets.
        edit_protect_only: (optional) If true, only update items affected by
            edit_protect.

    Returns:
        None
    """
    for i in Form.instances:
        i.update_elements(data_key, edit_protect_only)


def bind(win: sg.Window) -> None:
    """Bind ALL forms to window. Not to be confused with `Form.bind()`, which binds
    specific forms to the window.

    Args:
        win: The PySimpleGUI window to bind all forms to

    Returns:
        None
    """
    for i in Form.instances:
        i.bind(win)


def simple_transform(dataset: DataSet, row, encode) -> None:
    """Convenience transform function that makes it easier to add transforms to your
    records."""
    for col, function in dataset._simple_transform.items():
        if col in row:
            msg = f"Transforming {col} from {row[col]}"
            if encode == TFORM_DECODE:
                row[col] = function["decode"](row, col)
            else:
                row[col] = function["encode"](row, col)
            logger.debug(f"{msg} to {row[col]}")


def update_table_element(
    window: sg.Window,
    element: Type[sg.Table],
    values: List[_TableRow],
    select_rows: List[int],
) -> None:
    """Updates a PySimpleGUI sg.Table with new data and suppresses extra events emitted.

    Call this function instead of simply calling update() on a sg.Table element.
    Without unbinding the virtual "<<TreeviewSelect>>" event, updating the selection or
    values will in turn fire more changed events, creating an endless loop of events.

    Args:
        window: A PySimpleGUI Window containing the sg.Table element to be updated.
        element: The sg.Table element to be updated.
        values: A list of table rows to update the sg.Table with.
        select_rows: List of rows to select as if user did.

    Returns:
        None
    """
    # Disable handling for "<<TreeviewSelect>>" event
    element.widget.unbind("<<TreeviewSelect>>")
    # update element
    element.update(values=values, select_rows=select_rows)

    # make sure row_iid is visible
    if not isinstance(element, LazyTable) and len(values) and select_rows:
        row_iid = element.tree_ids[select_rows[0]]
        element.widget.see(row_iid)

    window.refresh()  # Event handled and bypassed
    # Enable handling for "<<TreeviewSelect>>" event
    element.widget.bind("<<TreeviewSelect>>", element._treeview_selected)


def checkbox_to_bool(value: Union[str, int, bool]) -> bool:
    """Allows a variety of checkbox values to still return True or False.

    Args:
        value: Value to convert into True or False

    Returns:
        bool
    """
    return str(value).lower() in [
        "y",
        "yes",
        "t",
        "true",
        "1",
        "on",
        "enabled",
        themepack.checkbox_true,
    ]


def shake_widget(
    widget: Union[sg.Element, tk.Widget], pixels=4, delay_ms=50, repeat=2
) -> None:
    """Shakes the given widget by modifying its padx attribute.

    Args:
        widget: The widget to shake. Must be an instance of sg.Element or tk.Widget.
        pixels: The number of pixels by which to shake the widget horizontally.
        delay_ms: The delay in milliseconds between each shake movement.
        repeat: The number of times to repeat the shaking movement.
    """
    if isinstance(widget, sg.Element):
        widget = widget.Widget
    elif not isinstance(widget, tk.Widget):
        logger.debug(f"{widget} not a valid sg.Element or tk.Widget")
        return
    padx = widget.pack_info().get("padx", 0)

    # Adjust padx based on its current value
    if isinstance(padx, tuple):
        padx_left = padx[0] + pixels
        padx_right = padx[1] - pixels
        new_padx = (padx_left, padx_right)
    else:
        padx_left = padx + pixels
        padx_right = max(padx - pixels, 0)
        new_padx = (padx_left, padx_right)

    widget.update()

    # Perform the shaking movement
    for _ in range(repeat):
        widget.pack_configure(padx=new_padx)
        widget.update()
        widget.after(delay_ms)
        widget.pack_configure(padx=padx)
        widget.update()
        widget.after(delay_ms)


class Popup:

    """Popup helper class.

    Has popup functions for internal use. Stores last info popup as last_info
    """

    def __init__(self, window: sg.Window = None) -> None:
        """Create a new Popup instance :returns: None."""
        self.window = window
        self.popup_info = None
        self.last_info_msg: str = ""
        self.last_info_time = None
        self.info_elements = []
        self._timeout_id = None
        self._window_kwargs = {
            "keep_on_top": True,
            "element_justification": "center",
            "enable_close_attempted_event": True,
            "icon": themepack.icon,
            "ttk_theme": themepack.ttk_theme,
            "finalize": True,
        }

    def ok(self, title, msg) -> None:
        """Internal use only.

        Creates sg.Window with LanguagePack OK button
        """
        msg_lines = msg.splitlines()
        layout = [[sg.Text(line, font="bold")] for line in msg_lines]
        layout.append(
            sg.Button(
                button_text=lang.button_ok,
                key="ok",
                use_ttk_buttons=themepack.use_ttk_buttons,
                pad=themepack.popup_button_pad,
            )
        )
        popup_win = sg.Window(title, layout=[layout], modal=True, **self._window_kwargs)

        while True:
            event, values = popup_win.read()
            if event in ["ok", "-WINDOW CLOSE ATTEMPTED-"]:
                break
        popup_win.close()

    def yes_no(self, title, msg):
        """Internal use only.

        Creates sg.Window with LanguagePack Yes/No button
        """
        msg_lines = msg.splitlines()
        layout = [[sg.Text(line, font="bold")] for line in msg_lines]
        layout.append(
            sg.Button(
                button_text=lang.button_yes,
                key="yes",
                use_ttk_buttons=themepack.use_ttk_buttons,
                pad=themepack.popup_button_pad,
            )
        )
        layout.append(
            sg.Button(
                button_text=lang.button_no,
                key="no",
                use_ttk_buttons=themepack.use_ttk_buttons,
                pad=themepack.popup_button_pad,
            )
        )
        popup_win = sg.Window(title, layout=[layout], modal=True, **self._window_kwargs)

        while True:
            event, values = popup_win.read()
            if event in ["no", "yes", "-WINDOW CLOSE ATTEMPTED-"]:
                result = event
                break
        popup_win.close()
        return result

    def info(
        self, msg: str, display_message: bool = True, auto_close_seconds: int = None
    ) -> None:
        """Displays a popup message and saves the message to self.last_info, auto-
        closing after x seconds. The title of the popup window is defined in
        lang.info_popup_title.

        Args:
            msg: The message to display.
            display_message: (optional) If True (default), displays the message in the
                popup window. If False, only saves `msg` to `self.last_info_msg`.
            auto_close_seconds: (optional) The number of seconds before the popup window
                auto-closes. If not provided, it is obtained from
                themepack.popup_info_auto_close_seconds.
        """

        title = lang.info_popup_title
        if auto_close_seconds is None:
            auto_close_seconds = themepack.popup_info_auto_close_seconds
        self.last_info_msg = msg
        self.update_info_element()
        if display_message:
            msg_lines = msg.splitlines()
            layout = [[sg.Text(line, font="bold")] for line in msg_lines]
            if self.popup_info:
                return
            self.popup_info = sg.Window(
                title=title,
                layout=layout,
                alpha_channel=themepack.popup_info_alpha_channel,
                **self._window_kwargs,
            )
            self.popup_info.TKroot.after(
                int(auto_close_seconds * 1000), self._auto_close
            )

    def _auto_close(self) -> None:
        """Use in a tk.after to automatically close the popup_info."""
        if self.popup_info:
            self.popup_info.close()
            self.popup_info = None

    def update_info_element(
        self,
        message: str = None,
        auto_erase_seconds: int = None,
        timeout=False,
        erase: bool = False,
    ) -> None:
        """Update any mapped info elements:

        Args:
            message: Text message to update info elements with
            auto_erase_seconds: The number of seconds before automatically erasing the
                information element. If None, the default value from themepack will be
                used.
            timeout: A boolean flag indicating whether to erase the information element.
                If True, and the elapsed time since the information element was last
                updated exceeds the auto_erase_seconds, the element will be cleared.
            erase: Default False. Erase info elements
        """
        if auto_erase_seconds is None:
            auto_erase_seconds = themepack.info_element_auto_erase_seconds

        # set the text-string to update
        message = message or self.last_info_msg
        if erase:
            message = ""
            if self._timeout_id:
                self.window.TKroot.after_cancel(self._timeout_id)

        elif timeout and self.last_info_time:
            elapsed_sec = time() - self.last_info_time
            if elapsed_sec >= auto_erase_seconds:
                message = ""

        # update elements
        for element in self.info_elements:
            element.update(message)

        # record time of update, and tk.after
        if not erase and self.window:
            self.last_info_time = time()
            if self._timeout_id:
                self.window.TKroot.after_cancel(self._timeout_id)
            self._timeout_id = self.window.TKroot.after(
                int(auto_erase_seconds * 1000),
                lambda: self.update_info_element(timeout=True),
            )


class ProgressBar:
    def __init__(self, title: str, max_value: int = 100, hide_delay: int = 100) -> None:
        """Creates a progress bar window with a message label and a progress bar.

        The progress bar is updated by calling the `ProgressBar.update` method to update
        the progress in incremental steps until the `ProgressBar.close` method is called

        Args:
            title: Title of the window
            max_value: Maximum value of the progress bar
            hide_delay: Delay in milliseconds before displaying the Window

        Returns:
            None
        """
        self.win = None
        self.title = title
        self.layout = [
            [sg.Text("", key="message", size=(50, 2))],
            [
                sg.ProgressBar(
                    max_value,
                    orientation="h",
                    size=(30, 20),
                    key="bar",
                    style=themepack.ttk_theme,
                )
            ],
        ]

        self.max = max
        self.hide_delay = hide_delay
        self.start_time = time() * 1000
        self.update_queue = queue.Queue()  # Thread safe
        self.animate_thread = None
        self._stop_event = threading.Event()  # Added stop event
        self.last_phrase_time = None
        self.phrase_index = 0

    def update(self, message: str, current_count: int) -> None:
        """Updates the progress bar with the current progress message and value.

        Args:
            message: Message to display
            current_count: Current value of the progress bar

        Returns:
            None
        """
        if time() * 1000 - self.start_time < self.hide_delay:
            return

        if self.win is None:
            self._create_window()

        self.win["message"].update(message)
        self.win["bar"].update(current_count=current_count)

    def close(self) -> None:
        """Closes the progress bar window.

        Returns:
            None
        """
        if self.win is not None:
            self.win.close()

    def _create_window(self) -> None:
        self.win = sg.Window(
            self.title,
            layout=self.layout,
            keep_on_top=True,
            finalize=True,
            ttk_theme=themepack.ttk_theme,
            icon=themepack.icon,
        )


class ProgressAnimate:
    def __init__(self, title: str, config: dict = None):
        """Creates an animated progress bar with a message label.

        The progress bar will animate indefinitely, until the process passed in to the
        `ProgressAnimate.run` method finishes.

        The config for the animated progress bar contains oscillators for the bar
        divider and colors, a list of phrases to be displayed, and the number of seconds
        to elapse between phrases.  This is all specified in the config dict
        as follows:
        my_oscillators = {
            # oscillators for the bar divider and colors
            "bar": {"value_start": 0, "value_range": 100, "period": 3, "offset": 0},
            "red": {"value_start": 0, "value_range": 255, "period": 2, "offset": 0},
            "green": {"value_start": 0, "value_range": 255, "period": 3, "offset": 120},
            "blue": {"value_start": 0, "value_range": 255, "period": 4, "offset": 240},

            # phrases to display and the number of seconds to elapse between phrases
            "phrases": [
                "Loading...", "Please be patient...", "This may take a while...",
                "Almost done...", "Almost there...", "Just a little longer...",
                "Please wait...", "Still working...",
            ],
            "phrase_delay": 2
        }
        Defaults are used for any keys that are not specified in the dictionary.

        Args:
            title: Title of the window
            config: Dictionary of configuration options as listed above

        Returns:
            None
        """
        default_config = {
            # oscillators for the bar divider and colors
            "bar": {"value_start": 0, "value_range": 100, "period": 3, "offset": 0},
            "red": {"value_start": 0, "value_range": 255, "period": 2, "offset": 0},
            "green": {"value_start": 0, "value_range": 255, "period": 3, "offset": 120},
            "blue": {"value_start": 0, "value_range": 255, "period": 4, "offset": 240},
            # phrases to display and the number of seconds to elapse between phrases
            "phrases": lang.animate_phrases,
            "phrase_delay": 5,
        }
        if config is None:
            config = {}

        if type(config) is not dict:
            raise ValueError("config must be a dictionary")

        if set(config.keys()) - set(default_config.keys()):
            raise NotImplementedError(
                f"config may only contain keys: {default_config.keys()}"
            )

        for k in ["bar", "red", "green", "blue"]:
            if k in config and not all(isinstance(v, (int, float)) for v in config[k]):
                raise ValueError(f"values for {k} component must all be numeric")
            required_keys = {"value_start", "value_range", "period", "offset"}
            if k in config and not required_keys.issubset(set(config.keys())):
                raise ValueError(f"{k} must contain all of {required_keys}")

        if "phrases" in config:
            if type(config["phrases"]) is not list:
                raise ValueError("phrases must be a list")
            if not all(isinstance(v, str) for v in config["phrases"]):
                raise ValueError("phrases must be a list of strings")

        if "phrase_delay" in config and not all(
            isinstance(v, (int, float)) for v in config["phrase_delay"]
        ):
            raise ValueError("phrase_delay must be numeric")

        self.config = {**default_config, **config}

        self.title = title
        self.win: sg.Window = None
        self.layout = [
            [sg.Text("", key="message", size=(50, 2))],
            [
                sg.ProgressBar(
                    100,
                    orientation="h",
                    size=(30, 20),
                    key="bar",
                    style=themepack.ttk_theme,
                )
            ],
        ]
        self.last_phrase_time = None
        self.phrase_index = 0
        self.completed = asyncio.Event()

    def run(self, fn: callable, *args, **kwargs):
        """Runs the function in a separate co-routine, while animating the progress bar
        in another."""
        if not callable(fn):
            raise ValueError("fn must be a callable")

        return asyncio.run(self._dispatch(fn, *args, **kwargs))

    def close(self) -> None:
        self.win = None

    async def _gui(self) -> None:
        if self.win is None:
            self.win = sg.Window(
                self.title,
                layout=self.layout,
                keep_on_top=True,
                finalize=True,
                ttk_theme=themepack.ttk_theme,
                icon=themepack.icon,
            )

        current_count = 0
        while not self.completed.is_set():
            current_count += 1
            self._animate(self.config)
            await asyncio.sleep(0.05)
        self.win.close()

    async def run_process(self, fn: callable, *args, **kwargs):
        loop = asyncio.get_running_loop()
        try:
            return await loop.run_in_executor(
                None, functools.partial(fn, *args, **kwargs)
            )
        except Exception as e:
            print(f"\nAn error occurred in the process: {e}")
            raise e  # Pass the exception along to the caller
        finally:
            self.completed.set()

    async def _dispatch(self, fn: callable, *args, **kwargs):
        # Dispatch to the multiple asyncio co-processes
        gui_task = asyncio.create_task(self._gui())
        result = await self.run_process(fn, *args, **kwargs)
        await gui_task
        return result

    def _animate(self, config: dict = None) -> None:
        def _oscillate_params(oscillator):
            return (
                oscillator["value_start"],
                oscillator["value_range"],
                oscillator["period"],
                oscillator["offset"],
            )

        # oscillate the bar back and forth
        count = self._oscillate(*_oscillate_params(config["bar"]))

        # oscillate red color channel
        cr = self._oscillate(*_oscillate_params(config["red"]))

        # oscillate green color channel
        cg = self._oscillate(*_oscillate_params(config["blue"]))

        # oscillate blue color channel
        cb = self._oscillate(*_oscillate_params(config["green"]))

        color_1 = f"#{cr:02x}{cg:02x}{cb:02x}"
        color_2 = f"#{255-cg:02x}{255-cb:02x}{255-cr:02x}"
        message = self._animated_message(config["phrases"], config["phrase_delay"])

        self.win["message"].update(message)
        self.win["bar"].update(current_count=count, bar_color=(color_1, color_2))

    @staticmethod
    def _oscillate(value_start: int, value_range: int, period: float, offset: int):
        millis = int(round(time() * 1000))
        t = (millis % (period * 1000)) / (period * 1000)
        angle = t * 2 * math.pi + math.radians(offset)
        sin_value = math.sin(angle)
        return int((sin_value + 1) * value_range / 2 + value_start)

    def _animated_message(self, phrases: list, phrase_delay: float):
        # Cycle through the messages at the specified interval
        current_time = time()
        if (
            self.last_phrase_time is None
            or current_time - self.last_phrase_time > phrase_delay
        ):
            current_message = phrases[self.phrase_index]
            self.phrase_index = (self.phrase_index + 1) % len(phrases)
            self.last_phrase_time = current_time
        else:
            current_message = phrases[(self.phrase_index - 1)]
        return current_message


class KeyGen:

    """The keygen system provides a mechanism to generate unique keys for use as
    PySimpleGUI element keys.

    This is needed because many auto-generated items will have the same name.  If for
    example you had two save buttons on the screen at the same time, they must have
    unique names.  The keygen will append a separator and an incremental number to keys
    that would otherwise be duplicates. A global KeyGen instance is created
    automatically, see `keygen` for info.
    """

    def __init__(self, separator="!") -> None:
        """Create a new KeyGen instance.

        Args:
            separator: The default separator that goes between the key and the
                incremental number

        Returns:
            None
        """
        self._keygen = {}
        self._separator = separator

    def get(self, key: str, separator: str = None) -> str:
        """Get a generated key from the `KeyGen`.

        Args:
            key: The key from which to generate the new key. If the key has not been
                used before, then it will be returned unmodified. For each successive
                call with the same key, it will be appended with the separator character
                and an incremental number. For example, if the key 'button' was passed
                to `KeyGen.get()` 3 times in a row, then the keys 'button', 'button:1',
                and 'button:2' would be returned respectively.
            separator: (optional) override the default separator wth this separator

        Returns:
            None
        """
        if separator is None:
            separator = self._separator

        # Generate a unique key by attaching a sequential integer to the end
        if key not in self._keygen:
            self._keygen[key] = 0
        return_key = key
        if self._keygen[key] > 0:
            # only modify the key if it is a duplicate!
            return_key += f"{separator}{self._keygen[key]!s}"
        logger.debug(f"Key generated: {return_key}")
        self._keygen[key] += 1
        return return_key

    def reset_key(self, key: str) -> None:
        """Reset the generation sequence for the supplied key.

        Args:
            key: The base key to reset te sequence for
        """
        with contextlib.suppress(KeyError):
            del self._keygen[key]

    def reset(self) -> None:
        """Reset the entire `KeyGen` and remove all keys.

        Returns:
            None
        """
        self._keygen = {}

    def reset_from_form(self, frm: Form) -> None:
        """Reset keys from the keygen that were from mapped PySimpleGUI elements of that
        `Form`.

        Args:
            frm: The `Form` from which to get the list of mapped elements

        Returns:
            None
        """
        # reset keys related to form
        for mapped in frm.element_map:
            self.reset_key(mapped.element.key)


# create a global KeyGen instance
keygen = KeyGen(separator=":")
"""This is a global keygen instance for general purpose use.

See `KeyGen` for more info
"""


class LazyTable(sg.Table):

    """The LazyTable is a subclass of sg.Table for improved performance by loading rows
    lazily during scroll events. Updating a sg.Table is generally fast, but with large
    DataSets that contain thousands of rows, there may be some noticeable lag. LazyTable
    overcomes this by only inserting a slice of rows during an `update()`.

    To use, simply replace `sg.Table` with `LazyTable` as the `element` argument in a
    selector() function call in your layout.

    Expects values in the form of [_TableRow(pk, values)], and only becomes active after
    a update(values=, selected_rows=[int]) call. Please note that LazyTable does not
    support the `sg.Table` `row_colors` argument.
    """

    def __init__(self, *args, lazy_loading=False, **kwargs) -> None:
        # remove LazyTable only
        self.headings_justification = kwargs.pop("headings_justification", None)
        cols_justification = kwargs.pop("cols_justification", None)
        self.frame_pack_kwargs = kwargs.pop("frame_pack_kwargs", None)

        super().__init__(*args, **kwargs)

        # set cols_justification after, since PySimpleGUI sets it in its init
        self.cols_justification = cols_justification

        self.data = []  # lazy slice of rows
        self.lazy_loading: bool = True
        self.lazy_insert_qty: int = 100

        self._start_index = 0
        self._end_index = 0
        self._start_alt_color = False
        self._end_alt_color = False
        self._finalized = False
        self._lock = threading.Lock()
        self._bg = None
        self._fg = None

    def __setattr__(self, name, value) -> None:
        if name == "SelectedRows":
            # Handle PySimpleGui attempts to set our SelectedRows property
            return
        super().__setattr__(name, value)

    @property
    def insert_qty(self):
        """Number of rows to insert during an `update(values=)` and scroll events."""
        if self.lazy_loading:
            return max(self.NumRows, self.lazy_insert_qty)
        return len(self.Values)

    @property
    def SelectedRows(self):  # noqa N802
        """Returns the selected row(s) in the LazyTable.

        Returns:
            - If the LazyTable has data:
                - Retrieves the index of the selected row by matching the primary key
                  (pk) value with the first selected item in the widget.
                - Returns the corresponding row from the data list based on the index.
            - If the LazyTable has no data:
                - Returns None.

        :note:
            This property assumes that the LazyTable is using a primary key (pk) value
            to uniquely identify rows in the data list.
        """
        if self.data and self.widget.selection():
            index = [
                [v.pk for v in self.data].index(
                    next(int(x) for x in self.widget.selection())
                )
            ][0]
            return self.data[index]
        return None

    def update(
        self,
        values=None,
        num_rows=None,
        visible=None,
        select_rows=None,
        alternating_row_color=None,
    ) -> None:
        # check if we shouldn't be doing this update
        # PySimpleGUI version support (PyPi version doesn't support quick_check)
        kwargs = {}
        is_closed_sig = inspect.signature(self.ParentForm.is_closed)
        if "quick_check" in is_closed_sig.parameters:
            kwargs = {"quick_check": True}

        if not self._widget_was_created() or (
            self.ParentForm is not None and self.ParentForm.is_closed(**kwargs)
        ):
            return

        # update total list
        self.values = values  # noqa PD011
        # Update current_index with the selected index
        self.current_index = select_rows[0] if select_rows else 0

        # needed, since PySimpleGUI doesn't create tk widgets during class init
        if not self._finalized:
            self.widget.configure(yscrollcommand=self._handle_scroll)
            self._handle_extra_kwargs()
            self._finalized = True

        # delete all current
        children = self.widget.get_children()
        for i in children:
            self.widget.detach(i)
            self.widget.delete(i)
        self.tree_ids = []

        # background color
        self._bg = (
            self.BackgroundColor
            if self.BackgroundColor is not None
            and self.BackgroundColor != sg.COLOR_SYSTEM_DEFAULT
            else "#FFFFFF"
        )

        # text color
        self._fg = (
            self.TextColor
            if self.TextColor is not None and self.TextColor != sg.COLOR_SYSTEM_DEFAULT
            else "#000000"
        )

        # alternating color
        if alternating_row_color is not None:
            self.AlternatingRowColor = alternating_row_color
            self._start_alt_color = True

        # get values to insert
        if select_rows is not None:
            # Slice the list to show visible rows before and after the current index
            self._start_index = max(0, self.current_index - self.insert_qty)
            self._end_index = min(len(values), self.current_index + self.insert_qty + 1)
            self.data = values[self._start_index : self._end_index]
        else:
            self.data = values

        # insert values
        if values is not None:
            # insert the rows
            for row in self.data:
                iid = self.widget.insert(
                    "", "end", text=row, iid=row.pk, values=row, tag=row.pk
                )
                self._end_alt_color = self._set_colors(iid, self._end_alt_color)
                self.tree_ids.append(iid)

        # handle visible
        if visible is not None:
            self._visible = visible
            if visible:
                self._pack_restore_settings(self.element_frame)
            else:
                self._pack_forget_save_settings(self.element_frame)

        # handle number of rows
        if num_rows is not None:
            self.widget.config(height=num_rows)

        # finally, select rows and make first visible
        if select_rows is not None:
            # Offset select_rows index for the sliced values
            offset_select_rows = [i - self._start_index for i in select_rows]
            if offset_select_rows and offset_select_rows[0] < len(self.data):
                # select the row
                self.widget.selection_set(self.tree_ids[offset_select_rows[0]])
                # Get the row iid based on the offset_select_rows index
                row_iid = self.tree_ids[offset_select_rows[0]]
                # and make sure its visible
                self.widget.see(row_iid)

    def _handle_scroll(self, x0, x1) -> None:
        if float(x0) == 0.0 and self._start_index > 0:
            with self._lock:
                self._handle_start_scroll()
            return
        if float(x1) == 1.0 and self._end_index < len(self.values):
            with self._lock:
                self._handle_end_scroll()
            return
        # else, set the scroll
        self.vsb.set(x0, x1)

    def _handle_start_scroll(self) -> None:
        # determine slice
        num_rows = min(self._start_index, self.insert_qty)
        new_start_index = max(0, self._start_index - num_rows)
        new_rows = self.values[new_start_index : self._start_index]  # noqa PD011

        # insert
        for row in reversed(new_rows):
            iid = self.widget.insert(
                "", "0", text=row, iid=row.pk, values=row, tag=row.pk
            )
            self._start_alt_color = self._set_colors(iid, self._start_alt_color)
            self.tree_ids.insert(0, iid)

        # set new start
        self._start_index = new_start_index

        # Insert new_rows to beginning
        # don't use data.insert(0, new_rows), it breaks _TableRow
        self.data[:0] = new_rows

        # to avoid an infinite scroll, move scroll a little after 0.0
        with contextlib.suppress(IndexError):
            row_iid = self.tree_ids[self.insert_qty + self.NumRows - 1]
            self.widget.see(row_iid)

    def _handle_end_scroll(self) -> None:
        num_rows = len(self.values)
        # determine slice
        start_index = max(0, self._end_index)
        end_index = min(self._end_index + self.insert_qty, num_rows)
        new_rows = self.values[start_index:end_index]  # noqa PD011

        # insert
        for row in new_rows:
            iid = self.widget.insert(
                "", "end", text=row, iid=row.pk, values=row, tag=row.pk
            )
            self._end_alt_color = self._set_colors(iid, self._end_alt_color)
            self.tree_ids.append(iid)

        # set new end
        self._end_index = end_index

        # Extend self.data with new_rows
        self.data.extend(new_rows)

        # to avoid an infinite scroll, move scroll a little before 1.0
        with contextlib.suppress(IndexError):
            row_iid = self.tree_ids[len(self.data) - self.insert_qty]
            self.widget.see(row_iid)

    def _set_colors(self, iid, toggle_color):
        if self.AlternatingRowColor is not None:
            if not toggle_color:
                self.widget.tag_configure(
                    iid, background=self.AlternatingRowColor, foreground=self._fg
                )
            else:
                self.widget.tag_configure(iid, background=self._bg, foreground=self._fg)
            toggle_color = not toggle_color
        else:
            self.widget.tag_configure(iid, background=self._bg, foreground=self._fg)
        return toggle_color

    def _handle_extra_kwargs(self) -> None:
        if self.headings_justification:
            for i, heading_id in enumerate(self.Widget["columns"]):
                self.Widget.heading(
                    heading_id, anchor=TK_ANCHOR_MAP[self.headings_justification[i]]
                )
        if self.cols_justification:
            for i, column_id in enumerate(self.Widget["columns"]):
                self.Widget.column(
                    column_id, anchor=TK_ANCHOR_MAP[self.cols_justification[i]]
                )
        if self.frame_pack_kwargs:
            self.table_frame.pack(**self.frame_pack_kwargs)


class _StrictInput:
    def strict_validate(self, value, action) -> bool:
        if hasattr(self, "active_placeholder"):
            active_placeholder = self.active_placeholder
        else:
            active_placeholder = None

        if (
            not active_placeholder
            and action == "1"
            and self.dataset.validate_mode is ValidateMode.STRICT
        ) and not self.dataset.validate_field(self.column_name, value):
            return False
        return True

    def add_validate(self, dataset: DataSet, column_name: str) -> None:
        self.dataset: DataSet = dataset
        self.column_name = column_name
        widget = self.widget if isinstance(self, sg.Input) else self
        widget["validate"] = "key"
        widget["validatecommand"] = (
            widget.register(self.strict_validate),
            "%P",
            "%d",
        )


class _TtkStrictInput(ttk.Entry, _StrictInput):
    """Internal Ttk Entry with validate commands."""


class _PlaceholderText(ABC):
    """An abstract class for PySimpleGUI text-entry elements that allows for the display
    of a placeholder text when the input is empty."""

    # fmt: off
    _non_keys: ClassVar[List[str]] = {"Control_L","Control_R","Alt_L","Alt_R","Shift_L",
                "Shift_R","Caps_Lock","Return","Escape","Tab","BackSpace","Up","Down",
                "Left", "Right","Home","End","Page_Up","Page_Down","F1","F2","F3","F4",
                "F5","F6","F7","F8","F9","F10","F11","F12", "Delete"}
    # fmt: on
    binds: dict = dc.field(default_factory=lambda: dict)
    placeholder_feature_enabled: bool = False
    normal_color: str = None
    normal_font: str = None
    placeholder_text: str = ""
    placeholder_color: str = None
    placeholder_font: str = None
    active_placeholder: bool = False

    def add_placeholder(
        self, placeholder: str, color: str = None, font: str = None
    ) -> None:
        """Adds a placeholder text to the element.

        The placeholder text is displayed in the element when the element is empty and
        unfocused. When the element is clicked or focused, the placeholder text
        disappears and the element becomes blank. When the element loses focus and is
        still empty, the placeholder text reappears.

        This function is based on the recipe by Miguel Martinez Lopez, licensed under
        MIT. It has been updated to work with PySimpleGUI elements.

        Args:
            placeholder: The text to display as placeholder when the input is empty.
            color: The color of the placeholder text (default None).
            font: The font of the placeholder text (default None).
        """
        normal_color = self.widget.cget("fg")
        normal_font = self.widget.cget("font")

        if font is None:
            font = normal_font

        self.normal_color = normal_color
        self.normal_font = normal_font
        self.placeholder_color = color
        self.placeholder_font = font
        self.placeholder_text = placeholder
        self.active_placeholder = True
        self.placeholder_feature_enabled = True
        self._add_binds()

    @abstractmethod
    def _add_binds(self):
        pass

    def update(self, *args, **kwargs) -> None:
        """Updates the input widget with a new value and displays the placeholder text
        if the value is empty.

        Args:
            *args: Optional arguments to pass to `sg.Element.update`.
            **kwargs: Optional keyword arguments to pass to `sg.Element.update`.
        """
        if not self.placeholder_feature_enabled:
            super().update(*args, **kwargs)
            return

        if "value" in kwargs and kwargs["value"] is not None:
            # If the value is not None, use it as the new value
            value = kwargs.pop("value", None)
        elif len(args) > 0 and args[0] is not None:
            # If the value is passed as an argument, use it as the new value
            value = args[0]
            # Remove the value argument from args
            args = args[1:]
        else:
            # Otherwise, use the current value
            value = self.get()

        if self.active_placeholder and value not in EMPTY:
            # Replace the placeholder with the new value
            self.active_placeholder = False
            super().update(value=value)
            self.Widget.config(fg=self.normal_color, font=self.normal_font)
        elif value in EMPTY:
            # If the value is empty, reinsert the placeholder
            self.active_placeholder = True
            super().update(value=self.placeholder_text, **kwargs)
            self.Widget.config(fg=self.placeholder_color, font=self.placeholder_font)
        else:
            super().update(*args, **kwargs)

    def get(self) -> str:
        """Returns the current value of the input, or an empty string if the input
        displays the placeholder text.

        Returns:
            The current value of the input.
        """
        if self.active_placeholder:
            return ""
        return super().get()

    @abstractmethod
    def insert_placeholder(self):
        pass

    @abstractmethod
    def delete_placeholder(self):
        pass


class _EnhancedInput(_PlaceholderText, sg.Input, _StrictInput):
    """An Input that allows for the display of a placeholder text when empty."""

    def __init__(self, *args, **kwargs) -> None:
        self.binds = {}
        super().__init__(*args, **kwargs)

    def _add_binds(self) -> None:
        widget = self.widget
        if self.binds:
            # remove any existing binds
            for event, funcid in self.binds.items():
                self.widget.unbind(event, funcid)
            self.binds = {}

        def on_key(event):
            if self.active_placeholder and widget.get() == self.placeholder_text:
                # dont clear for non-text-producing keys
                if event.keysym in self._non_keys:
                    return "break"
                # Clear the placeholder when the user starts typing
                self.delete_placeholder()
            return None

        def on_key_release(event) -> None:
            if widget.get() in EMPTY:
                with contextlib.suppress(tk.TclError):
                    self.insert_placeholder()
                    widget.icursor(0)

        def on_focusin(event) -> None:
            if self.active_placeholder:
                # Move cursor to the beginning if the field has a placeholder
                widget.icursor(0)

        def on_focusout(event) -> None:
            if not widget.get():
                self.insert_placeholder()

        def disable_placeholder_select(event):
            # Disable selecting the placeholder
            if self.active_placeholder:
                return "break"
            return None

        self.binds["<KeyPress>"] = widget.bind("<KeyPress>", on_key, "+")
        self.binds["<KeyRelease>"] = widget.bind("<KeyRelease>", on_key_release, "+")
        self.binds["<FocusIn>"] = widget.bind("<FocusIn>", on_focusin, "+")
        self.binds["<FocusOut>"] = widget.bind("<FocusOut>", on_focusout, "+")
        for event in ["<<SelectAll>>", "<Control-a>", "<Control-slash>"]:
            self.binds[event] = widget.bind(event, disable_placeholder_select, "+")

        if not widget.get():
            self.insert_placeholder()

    def insert_placeholder(self) -> None:
        self.active_placeholder = True
        self.widget.delete(0, "end")
        self.widget.insert(0, self.placeholder_text)
        self.widget.config(fg=self.placeholder_color, font=self.placeholder_font)

    def delete_placeholder(self) -> None:
        self.active_placeholder = False
        self.widget.delete(0, "end")
        self.widget.config(fg=self.normal_color, font=self.normal_font)


class _EnhancedMultiline(_PlaceholderText, sg.Multiline):
    """A Multiline that allows for the display of a placeholder text when focus-out
    empty."""

    def __init__(self, *args, **kwargs) -> None:
        self.binds = {}
        super().__init__(*args, **kwargs)

    def _add_binds(self) -> None:
        widget = self.widget
        if self.binds:
            for event, bind in self.binds.items():
                self.widget.unbind(event, bind)
            self.binds = {}

        def on_focusin(event) -> None:
            if self.active_placeholder:
                self.delete_placeholder()

        def on_focusout(event) -> None:
            if not widget.get("1.0", "end-1c").strip():
                self.insert_placeholder()

        if not widget.get("1.0", "end-1c").strip() and self.active_placeholder:
            self.insert_placeholder()

        self.binds["<FocusIn>"] = widget.bind("<FocusIn>", on_focusin, "+")
        self.binds["<FocusOut>"] = widget.bind("<FocusOut>", on_focusout, "+")

    def insert_placeholder(self) -> None:
        self.widget.insert("1.0", self.placeholder_text)
        self.widget.config(fg=self.placeholder_color, font=self.placeholder_font)
        self.active_placeholder = True

    def delete_placeholder(self) -> None:
        self.widget.delete("1.0", "end")
        self.widget.config(fg=self.normal_color, font=self.normal_font)
        self.active_placeholder = False


class _SearchInput(_EnhancedInput):
    def __init__(self, *args, **kwargs) -> None:
        self.dataset = None
        self.search_string = None  # Track the StringVar
        super().__init__(*args, **kwargs)
        self.search_non_keys = self._non_keys.copy()
        self.search_non_keys.remove("BackSpace")
        self.search_non_keys.remove("Delete")

    def _add_binds(self) -> None:
        super()._add_binds()  # Call the parent method to maintain existing binds

        def on_key_release(event) -> None:
            # update selectors after each key-release
            if (
                event.keysym not in self.search_non_keys
                and self.search_string.get() != self.get()
            ):
                self.search_string.set(self.get())
                self.dataset.frm.update_selectors(
                    self.dataset.key, search_filter_only=True
                )

        self.binds["<KeyRelease>"] = self.widget.bind(
            "<KeyRelease>", on_key_release, "+"
        )

    def bind_dataset(self, dataset) -> None:
        self.dataset = dataset
        self.search_string = dataset._search_string
        if self.search_string is None:
            self.search_string = dataset._search_string = tk.StringVar()
        self.search_string.trace_add("write", self._on_search_string_change)

    def _on_search_string_change(self, *args) -> None:
        if (
            not self.active_placeholder
            and self.get() != self.search_string.get()
            and self.search_string.get() in EMPTY
        ):
            # reinsert placeholder if DataSet.search_string == ""
            self.insert_placeholder()


class _AutoCompleteLogic:
    _completion_list: List[Union[str, _ElementRow]] = dc.field(default_factory=list)
    _hits: List[int] = dc.field(default_factory=list)
    _hit_index: int = 0
    position: int = 0
    finalized: bool = False

    def _autocomplete_combo(self, completion_list, delta=0):
        widget = self.Widget
        """Perform autocompletion on a Combobox widget based on the current input."""
        if delta:
            # Delete text from current position to end
            widget.delete(widget.position, tk.END)
        else:
            # Set the position to the length of the current input text
            widget.position = len(widget.get())

        prefix = widget.get().lower()
        hits = [
            element for element in completion_list if element.lower().startswith(prefix)
        ]
        # Create a list of elements that start with the lowercase prefix

        if hits:
            closest_match = min(hits, key=len)
            if prefix != closest_match.lower():
                # Insert the closest match at the beginning, move the cursor to the end
                widget.delete(0, tk.END)
                widget.insert(0, closest_match)
                widget.icursor(len(closest_match))

                # Highlight the remaining text after the closest match
                widget.select_range(widget.position, tk.END)

            if len(hits) == 1 and closest_match.lower() != prefix:
                # If there is only one hit and it's not equal to the lowercase prefix,
                # open dropdown
                widget.event_generate("<Down>")
                widget.event_generate("<<ComboboxSelected>>")

        else:
            # If there are no hits, move the cursor to the current position
            widget.icursor(widget.position)

        return hits

    def autocomplete(self, delta=0) -> None:
        """Perform autocompletion based on the current input."""
        self._hits = self._autocomplete_combo(self._completion_list, delta)
        self._hit_index = 0

    def handle_keyrelease(self, event) -> None:
        """Handle key release event for autocompletion and navigation."""
        if event.keysym == "BackSpace":
            self.Widget.delete(self.Widget.position, tk.END)
            self.position = self.Widget.position
        if event.keysym == "Left":
            if self.position < self.Widget.index(tk.END):
                self.Widget.delete(self.position, tk.END)
            else:
                self.position -= 1
                self.Widget.delete(self.position, tk.END)
        if event.keysym == "Right":
            self.position = self.Widget.index(tk.END)
        if event.keysym == "Return":
            self.Widget.icursor(tk.END)
            self.Widget.selection_clear()
            return

        if len(event.keysym) == 1:
            self.autocomplete()


class _AutocompleteCombo(_AutoCompleteLogic, sg.Combo):
    """Customized Combo widget with autocompletion feature.

    Please note that due to how PySimpleSql initilizes widgets, you must call update()
    once to activate autocompletion, eg `window['combo_key'].update(values=values)`
    """

    def update(self, *args, **kwargs) -> None:
        """Update the Combo widget with new values."""
        if "values" in kwargs and kwargs["values"] is not None:
            self._completion_list = [str(row) for row in kwargs["values"]]
            if not self.finalized:
                self.Widget.bind("<KeyRelease>", self.handle_keyrelease, "+")
            self._hits = []
            self._hit_index = 0
            self.position = 0
        super().update(*args, **kwargs)


class _TtkCombo(_AutoCompleteLogic, ttk.Combobox):
    """Customized Combo widget with autocompletion feature."""

    def __init__(self, *args, **kwargs) -> None:
        """Initialize the Combo widget."""
        self._completion_list = [str(row) for row in kwargs["values"]]
        self.Widget = self
        super().__init__(*args, **kwargs)


class _TtkCalendar(ttk.Frame):
    """Internal Class."""

    # Modified from Tkinter GUI Application Development Cookbook, MIT License.

    def __init__(self, master, init_date, textvariable, **kwargs) -> None:
        # TODO, set these in themepack?
        fwday = kwargs.pop("firstweekday", calendar.MONDAY)
        sel_bg = kwargs.pop("selectbackground", "#ecffc4")
        sel_fg = kwargs.pop("selectforeground", "#05640e")

        super().__init__(master, **kwargs)

        self.master = master
        self.cal_date = init_date
        self.textvariable = textvariable
        self.cal = calendar.TextCalendar(fwday)
        self.font = tkfont.Font(self)
        self.header = self.create_header()
        self.table = self.create_table()
        self.canvas = self.create_canvas(sel_bg, sel_fg)
        self.build_calendar()

    def create_header(self):
        left_arrow = {"children": [("Button.leftarrow", None)]}
        right_arrow = {"children": [("Button.rightarrow", None)]}
        style = ttk.Style(self)
        style.layout("L.TButton", [("Button.focus", left_arrow)])
        style.layout("R.TButton", [("Button.focus", right_arrow)])

        hframe = ttk.Frame(self)
        btn_left = ttk.Button(
            hframe, style="L.TButton", command=lambda: self.move_month(-1)
        )
        btn_right = ttk.Button(
            hframe, style="R.TButton", command=lambda: self.move_month(1)
        )
        label = ttk.Label(hframe, width=15, anchor="center")

        hframe.pack(pady=5, anchor=tk.CENTER)
        btn_left.grid(row=0, column=0)
        label.grid(row=0, column=1, padx=12)
        btn_right.grid(row=0, column=2)
        return label

    def create_table(self):
        cols = self.cal.formatweekheader(3).split()
        table = ttk.Treeview(self, show="", selectmode="none", height=7, columns=cols)
        table.bind("<Map>", self.minsize, "+")
        table.pack(expand=1, fill=tk.BOTH)
        table.tag_configure("header", background="grey90")
        table.insert("", tk.END, values=cols, tag="header")
        for _ in range(6):
            table.insert("", tk.END)

        width = max(map(self.font.measure, cols))
        for col in cols:
            table.column(col, width=width, minwidth=width, anchor=tk.E)
        return table

    def create_canvas(self, bg, fg):
        canvas = tk.Canvas(
            self.table, background=bg, borderwidth=1, highlightthickness=0
        )
        canvas.text = canvas.create_text(0, 0, fill=fg, anchor=tk.W)
        self.table.bind("<ButtonPress-1>", self.pressed_callback, "+")
        return canvas

    def build_calendar(self) -> None:
        year, month = self.cal_date.year, self.cal_date.month
        month_name = self.cal.formatmonthname(year, month, 0)
        month_weeks = self.cal.monthdayscalendar(year, month)

        self.header.config(text=month_name.title())
        items = self.table.get_children()[1:]
        for week, item in itertools.zip_longest(month_weeks, items):
            fmt_week = [f"{day:02d}" if day else "" for day in (week or [])]
            self.table.item(item, values=fmt_week)

    def pressed_callback(self, event) -> None:
        x, y, widget = event.x, event.y, event.widget
        item = widget.identify_row(y)
        column = widget.identify_column(x)
        items = self.table.get_children()[1:]

        if not column or item not in items:
            # clicked te header or outside the columns
            return

        index = int(column[1]) - 1
        values = widget.item(item)["values"]
        text = values[index] if len(values) else None
        bbox = widget.bbox(item, column)
        if bbox and text:
            self.cal_date = dt.date(self.cal_date.year, self.cal_date.month, int(text))
            self.draw_selection(bbox)
            self.textvariable.set(self.cal_date.strftime(DATE_FORMAT))

    def draw_selection(self, bbox) -> None:
        canvas, text = self.canvas, "%02d" % self.cal_date.day
        x, y, width, height = bbox
        textw = self.font.measure(text)
        canvas.configure(width=width, height=height)
        canvas.coords(canvas.text, width - textw, height / 2 - 1)
        canvas.itemconfigure(canvas.text, text=text)
        canvas.place(x=x, y=y)

    def set_date(self, dateobj) -> None:
        self.cal_date = dateobj
        self.canvas.place_forget()
        self.build_calendar()

    def select_date(self) -> None:
        bbox = self.get_bbox_for_date(self.cal_date)
        if bbox:
            self.draw_selection(bbox)

    def get_bbox_for_date(self, new_date):
        items = self.table.get_children()[1:]
        for item in items:
            values = self.table.item(item)["values"]
            for i, value in enumerate(values):
                if isinstance(value, int) and value == new_date.day:
                    column = "#{}".format(i + 1)
                    self.table.update()
                    return self.table.bbox(item, column)
        return None

    def move_month(self, offset) -> None:
        self.canvas.place_forget()
        month = self.cal_date.month - 1 + offset
        year = self.cal_date.year + month // 12
        month = month % 12 + 1
        self.cal_date = dt.date(year, month, 1)
        self.build_calendar()

    def minsize(self, e) -> None:
        width, height = self.master.geometry().split("x")
        height = height[: height.index("+")]
        self.master.minsize(width, height)


class _DatePicker(_TtkStrictInput):
    def __init__(self, master, dataset, column_name, init_date, **kwargs) -> None:
        self.dataset = dataset
        self.column_name = column_name
        textvariable = kwargs["textvariable"]
        self.calendar = _TtkCalendar(
            self.dataset.frm.window.TKroot, init_date, textvariable
        )
        self.calendar.place_forget()
        self.button = ttk.Button(master, text="▼", width=2, command=self.show_calendar)
        super().__init__(master, **kwargs)

        self.bind("<KeyRelease>", self.on_entry_key_release, "+")
        self.calendar.bind("<Leave>", self.hide_calendar, "+")

    def show_calendar(self, event=None) -> None:
        self.configure(state=tk.DISABLED)
        self.calendar.place(in_=self, relx=0, rely=1)
        self.calendar.focus_force()
        self.calendar.select_date()

    def hide_calendar(self, event=None) -> None:
        self.configure(state=tk.NORMAL)
        self.calendar.place_forget()
        self.focus_force()

    def on_entry_key_release(self, event=None) -> None:
        date = self.get()
        date = self.dataset.column_info[self.column_name].cast(date)
        # Check if the user has typed a valid date
        if not isinstance(date, dt.date):
            return

        # Update the calendar to show the new date
        self.calendar.set_date(date)


# -------------------------------------------------------------------------------------
# CONVENIENCE FUNCTIONS
# -------------------------------------------------------------------------------------
# Convenience functions aide in building PySimpleGUI interfaces
# that work well with pysimplesql.
# TODO: How to save Form in metadata?  Perhaps give forms names and reference them?
#       For example - give forms names!  and reference them by name string
#       They could even be converted later to a real form during form creation?


# This is a dummy class for documenting convenience functions
class Convenience:

    """Convenience functions are a collection of functions and classes that aide in
    building PySimpleGUI layouts that conform to pysimplesql standards so that your
    database application is up and running quickly, and with all the great automatic
    functionality pysimplesql has to offer. See the documentation for the following
    convenience functions: `field()`, `selector()`, `actions()`, `TableBuilder`.

    Note: This is a dummy class that exists purely to enhance documentation and has no
    use to the end user.
    """


def field(
    field: str,
    element: Union[
        Type[sg.Checkbox],
        Type[sg.Combo],
        Type[sg.Input],
        Type[sg.Multiline],
    ] = _EnhancedInput,
    size: Tuple[int, int] = None,
    label: str = "",
    no_label: bool = False,
    label_above: bool = False,
    quick_editor: bool = True,
    quick_editor_kwargs: dict = None,
    filter=None,
    key=None,
    use_ttk_buttons=None,
    pad=None,
    **kwargs,
) -> sg.Column:
    """Convenience function for adding PySimpleGUI elements to the Window, so they are
    properly configured for pysimplesql. The automatic functionality of pysimplesql
    relies on accompanying metadata so that the `Form.auto_map_elements()` can pick them
    up. This convenience function will create a text label, along with an element with
    the above metadata already set up for you. Note: The element key will default to the
    field name if none is supplied.

    Args:
        field: The database record in the form of table.column I.e. 'Journal.entry'
        element: (optional) The element type desired (defaults to PySimpleGUI.Input)
        size: Overrides the default element size for this element only.
        label: The text/label will automatically be generated from the column name. If a
            different text/label is desired, it can be specified here.
        no_label: Do not automatically generate a label for this element
        label_above: Place the label above the element instead of to the left.
        quick_editor: For records that reference another table, place a quick edit
            button next to the element
        quick_editor_kwargs: Additional keyword arguments to pass to quick editor.
        filter: Can be used to reference different `Form`s in the same layout. Use a
            matching filter when creating the `Form` with the filter parameter.
        key: (optional) The key to give this element. See note above about the default
            auto generated key.
        **kwargs: Any additional arguments will be passed to the PySimpleGUI element.

    Returns:
        Element(s) to be used in the creation of PySimpleGUI layouts.  Note that this
        function actually creates multiple Elements wrapped in a PySimpleGUI Column, but
        can be treated as a single Element.
    """
    # TODO: See what the metadata does after initial setup is complete - needed anymore?
    element = _EnhancedInput if element == sg.Input else element
    element = _EnhancedMultiline if element == sg.Multiline else element
    element = _AutocompleteCombo if element == sg.Combo else element

    if use_ttk_buttons is None:
        use_ttk_buttons = themepack.use_ttk_buttons
    if pad is None:
        pad = themepack.default_element_pad

    # if Record imply a where clause (indicated by ?) If so, strip out the info we need
    if "?" in field:
        table_info, where_info = field.split("?")
        label_text = (
            where_info.split("=")[1].replace("fk", "").replace("_", " ").capitalize()
            + ":"
        )
    else:
        table_info = field
        label_text = (
            table_info.split(".")[1].replace("fk", "").replace("_", " ").capitalize()
            + ":"
        )
    table, column = table_info.split(".")

    key = field if key is None else key
    key = keygen.get(key)

    if "values" in kwargs:
        first_param = kwargs["values"]
        del kwargs["values"]  # make sure we don't put it in twice
    else:
        first_param = ""

    if element == _EnhancedMultiline:
        layout_element = element(
            first_param,
            key=key,
            size=size or themepack.default_mline_size,
            metadata={
                "type": TYPE_RECORD,
                "Form": None,
                "filter": filter,
                "field": field,
                "data_key": key,
            },
            pad=pad,
            **kwargs,
        )
    else:
        layout_element = element(
            first_param,
            key=key,
            size=size or themepack.default_element_size,
            metadata={
                "type": TYPE_RECORD,
                "Form": None,
                "filter": filter,
                "field": field,
                "data_key": key,
            },
            pad=pad,
            **kwargs,
        )
    layout_label = sg.Text(
        label if label else label_text,
        size=themepack.default_label_size,
        key=f"{key}:label",
    )
    # Marker for required (notnull) records
    layout_marker = sg.Column(
        [
            [
                sg.T(
                    themepack.marker_required,
                    key=f"{key}:marker",
                    text_color=sg.theme_background_color(),
                    visible=True,
                )
            ]
        ],
        pad=(0, 0),
    )
    if no_label:
        layout = [[layout_marker, layout_element]]
    elif label_above:
        layout = [[layout_label], [layout_marker, layout_element]]
    else:
        layout = [[layout_label, layout_marker, layout_element]]
    # Add the quick editor button where appropriate
    if element == _AutocompleteCombo and quick_editor:
        meta = {
            "type": TYPE_EVENT,
            "event_type": EVENT_QUICK_EDIT,
            "table": table,
            "column": column,
            "function": None,
            "Form": None,
            "filter": filter,
            "quick_editor_kwargs": quick_editor_kwargs,
        }
        if type(themepack.quick_edit) is bytes:
            layout[-1].append(
                sg.B(
                    "",
                    key=keygen.get(f"{key}.quick_edit"),
                    size=(1, 1),
                    image_data=themepack.quick_edit,
                    metadata=meta,
                    use_ttk_buttons=use_ttk_buttons,
                    pad=pad,
                )
            )
        else:
            layout[-1].append(
                sg.B(
                    themepack.quick_edit,
                    key=keygen.get(f"{key}.quick_edit"),
                    metadata=meta,
                    use_ttk_buttons=use_ttk_buttons,
                    pad=pad,
                )
            )
    # return layout
    return sg.Col(layout=layout, pad=(0, 0))


def actions(
    table: str,
    key=None,
    default: bool = True,
    edit_protect: bool = None,
    navigation: bool = None,
    insert: bool = None,
    delete: bool = None,
    duplicate: bool = None,
    save: bool = None,
    search: bool = None,
    search_size: Tuple[int, int] = (30, 1),
    bind_return_key: bool = True,
    filter: str = None,
    use_ttk_buttons: bool = None,
    pad=None,
    **kwargs,
) -> sg.Column:
    """Allows for easily adding record navigation and record action elements to the
    PySimpleGUI window The navigation elements are generated automatically (first,
    previous, next, last and search).  The action elements can be customized by
    selecting which ones you want generated from the parameters available.  This allows
    full control over what is available to the user of your database application. Check
    out `ThemePack` to give any of these autogenerated controls a custom look!.

    Note: By default, the base element keys generated for PySimpleGUI will be
    `table:action` using the name of the table passed in the table parameter plus the
    action strings below separated by a colon: (I.e. Journal:table_insert) edit_protect,
    db_save, table_first, table_previous, table_next, table_last, table_duplicate,
    table_insert, table_delete, search_input, search_button. If you supply a key with
    the key parameter, then these additional strings will be appended to that key. Also
    note that these autogenerated keys also pass through the `KeyGen`, so it's possible
    that these keys could be table_last:action!1, table_last:action!2, etc.

    Args:
        table: The table name that this "element" will provide actions for
        key: (optional) The base key to give the generated elements
        default: Default edit_protect, navigation, insert, delete, save and search to
            either true or false (defaults to True) The individual keyword arguments
            will trump the default parameter.  This allows for starting with all actions
            defaulting to False, then individual ones can be enabled with True - or the
            opposite by defaulting them all to True, and disabling the ones not needed
            with False.
        edit_protect: An edit protection mode to prevent accidental changes in the
            database. It is a button that toggles the ability on and off to prevent
            accidental changes in the database by enabling/disabling the insert, edit,
            duplicate, delete and save buttons.
        navigation: The standard << < > >> (First, previous, next, last) buttons for
            navigation
        insert: Button to insert new records
        delete: Button to delete current record
        duplicate: Button to duplicate current record
        save: Button to save record.  Note that the save button feature saves changes
            made to any table, therefore only one save button is needed per window.
        search: A search Input element. Size can be specified with the 'search_size'
            parameter
        search_size: The size of the search input element
        bind_return_key: Bind the return key to the search button. Defaults to true.
        filter: Can be used to reference different `Form`s in the same layout.  Use a
            matching filter when creating the `Form` with the filter parameter.
        pad: The padding to use for the generated elements.

    Returns:
        An element to be used in the creation of PySimpleGUI layouts.  Note that this is
        technically multiple elements wrapped in a PySimpleGUI.Column, but acts as one
        element for the purpose of layout building.
    """

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
    key = f"{table}:" if key is None else f"{key}:"

    layout = []

    # Form-level events
    if edit_protect:
        meta = {
            "type": TYPE_EVENT,
            "event_type": EVENT_EDIT_PROTECT_DB,
            "table": None,
            "column": None,
            "function": None,
            "Form": None,
            "filter": filter,
        }
        if type(themepack.edit_protect) is bytes:
            layout.append(
                sg.B(
                    "",
                    key=keygen.get(f"{key}edit_protect"),
                    size=(1, 1),
                    image_data=themepack.edit_protect,
                    metadata=meta,
                    use_ttk_buttons=use_ttk_buttons,
                    pad=pad,
                    **kwargs,
                )
            )
        else:
            layout.append(
                sg.B(
                    themepack.edit_protect,
                    key=keygen.get(f"{key}edit_protect"),
                    metadata=meta,
                    use_ttk_buttons=use_ttk_buttons,
                    pad=pad,
                    **kwargs,
                )
            )
    if save:
        meta = {
            "type": TYPE_EVENT,
            "event_type": EVENT_SAVE_DB,
            "table": None,
            "column": None,
            "function": None,
            "Form": None,
            "filter": filter,
        }
        if type(themepack.save) is bytes:
            layout.append(
                sg.B(
                    "",
                    key=keygen.get(f"{key}db_save"),
                    image_data=themepack.save,
                    metadata=meta,
                    use_ttk_buttons=use_ttk_buttons,
                    pad=pad,
                    **kwargs,
                )
            )
        else:
            layout.append(
                sg.B(themepack.save, key=keygen.get(f"{key}db_save"), metadata=meta)
            )

    # DataSet-level events
    if navigation:
        # first
        meta = {
            "type": TYPE_EVENT,
            "event_type": EVENT_FIRST,
            "table": table,
            "column": None,
            "function": None,
            "Form": None,
            "filter": filter,
        }
        if type(themepack.first) is bytes:
            layout.append(
                sg.B(
                    "",
                    key=keygen.get(f"{key}table_first"),
                    size=(1, 1),
                    image_data=themepack.first,
                    metadata=meta,
                    use_ttk_buttons=use_ttk_buttons,
                    pad=pad,
                    **kwargs,
                )
            )
        else:
            layout.append(
                sg.B(
                    themepack.first,
                    key=keygen.get(f"{key}table_first"),
                    metadata=meta,
                    use_ttk_buttons=use_ttk_buttons,
                    pad=pad,
                    **kwargs,
                )
            )
        # previous
        meta = {
            "type": TYPE_EVENT,
            "event_type": EVENT_PREVIOUS,
            "table": table,
            "column": None,
            "function": None,
            "Form": None,
            "filter": filter,
        }
        if type(themepack.previous) is bytes:
            layout.append(
                sg.B(
                    "",
                    key=keygen.get(f"{key}table_previous"),
                    size=(1, 1),
                    image_data=themepack.previous,
                    metadata=meta,
                    use_ttk_buttons=use_ttk_buttons,
                    pad=pad,
                    **kwargs,
                )
            )
        else:
            layout.append(
                sg.B(
                    themepack.previous,
                    key=keygen.get(f"{key}table_previous"),
                    metadata=meta,
                    use_ttk_buttons=use_ttk_buttons,
                    pad=pad,
                    **kwargs,
                )
            )
        # next
        meta = {
            "type": TYPE_EVENT,
            "event_type": EVENT_NEXT,
            "table": table,
            "column": None,
            "function": None,
            "Form": None,
            "filter": filter,
        }
        if type(themepack.next) is bytes:
            layout.append(
                sg.B(
                    "",
                    key=keygen.get(f"{key}table_next"),
                    size=(1, 1),
                    image_data=themepack.next,
                    metadata=meta,
                    use_ttk_buttons=use_ttk_buttons,
                    pad=pad,
                    **kwargs,
                )
            )
        else:
            layout.append(
                sg.B(
                    themepack.next,
                    key=keygen.get(f"{key}table_next"),
                    metadata=meta,
                    use_ttk_buttons=use_ttk_buttons,
                    pad=pad,
                    **kwargs,
                )
            )
        # last
        meta = {
            "type": TYPE_EVENT,
            "event_type": EVENT_LAST,
            "table": table,
            "column": None,
            "function": None,
            "Form": None,
            "filter": filter,
        }
        if type(themepack.last) is bytes:
            layout.append(
                sg.B(
                    "",
                    key=keygen.get(f"{key}table_last"),
                    size=(1, 1),
                    image_data=themepack.last,
                    metadata=meta,
                    use_ttk_buttons=use_ttk_buttons,
                    pad=pad,
                    **kwargs,
                )
            )
        else:
            layout.append(
                sg.B(
                    themepack.last,
                    key=keygen.get(f"{key}table_last"),
                    metadata=meta,
                    use_ttk_buttons=use_ttk_buttons,
                    pad=pad,
                    **kwargs,
                )
            )
    if duplicate:
        meta = {
            "type": TYPE_EVENT,
            "event_type": EVENT_DUPLICATE,
            "table": table,
            "column": None,
            "function": None,
            "Form": None,
            "filter": filter,
        }
        if type(themepack.duplicate) is bytes:
            layout.append(
                sg.B(
                    "",
                    key=keygen.get(f"{key}table_duplicate"),
                    size=(1, 1),
                    image_data=themepack.duplicate,
                    metadata=meta,
                    use_ttk_buttons=use_ttk_buttons,
                    pad=pad,
                    **kwargs,
                )
            )
        else:
            layout.append(
                sg.B(
                    themepack.duplicate,
                    key=keygen.get(f"{key}table_duplicate"),
                    metadata=meta,
                    use_ttk_buttons=use_ttk_buttons,
                    pad=pad,
                    **kwargs,
                )
            )
    if insert:
        meta = {
            "type": TYPE_EVENT,
            "event_type": EVENT_INSERT,
            "table": table,
            "column": None,
            "function": None,
            "Form": None,
            "filter": filter,
        }
        if type(themepack.insert) is bytes:
            layout.append(
                sg.B(
                    "",
                    key=keygen.get(f"{key}table_insert"),
                    size=(1, 1),
                    image_data=themepack.insert,
                    metadata=meta,
                    use_ttk_buttons=use_ttk_buttons,
                    pad=pad,
                    **kwargs,
                )
            )
        else:
            layout.append(
                sg.B(
                    themepack.insert,
                    key=keygen.get(f"{key}table_insert"),
                    metadata=meta,
                    use_ttk_buttons=use_ttk_buttons,
                    pad=pad,
                    **kwargs,
                )
            )
    if delete:
        meta = {
            "type": TYPE_EVENT,
            "event_type": EVENT_DELETE,
            "table": table,
            "column": None,
            "function": None,
            "Form": None,
            "filter": filter,
        }
        if type(themepack.delete) is bytes:
            layout.append(
                sg.B(
                    "",
                    key=keygen.get(f"{key}table_delete"),
                    size=(1, 1),
                    image_data=themepack.delete,
                    metadata=meta,
                    use_ttk_buttons=use_ttk_buttons,
                    pad=pad,
                    **kwargs,
                )
            )
        else:
            layout.append(
                sg.B(
                    themepack.delete,
                    key=keygen.get(f"{key}table_delete"),
                    metadata=meta,
                    use_ttk_buttons=use_ttk_buttons,
                    pad=pad,
                    **kwargs,
                )
            )
    if search:
        meta = {
            "type": TYPE_EVENT,
            "event_type": EVENT_SEARCH,
            "table": table,
            "column": None,
            "function": None,
            "Form": None,
            "filter": filter,
        }
        if type(themepack.search) is bytes:
            layout += [
                _SearchInput(
                    "", key=keygen.get(f"{key}search_input"), size=search_size
                ),
                sg.B(
                    "",
                    key=keygen.get(f"{key}search_button"),
                    bind_return_key=bind_return_key,
                    size=(1, 1),
                    image_data=themepack.search,
                    metadata=meta,
                    use_ttk_buttons=use_ttk_buttons,
                    pad=pad,
                    **kwargs,
                ),
            ]
        else:
            layout += [
                _SearchInput(
                    "", key=keygen.get(f"{key}search_input"), size=search_size
                ),
                sg.B(
                    themepack.search,
                    key=keygen.get(f"{key}search_button"),
                    bind_return_key=bind_return_key,
                    metadata=meta,
                    use_ttk_buttons=use_ttk_buttons,
                    pad=pad,
                    **kwargs,
                ),
            ]
    return sg.Col(layout=[layout], pad=(0, 0))


def selector(
    table: str,
    element: Union[
        Type[sg.Combo],
        Type[LazyTable],
        Type[sg.Listbox],
        Type[sg.Slider],
        Type[sg.Table],
        TableBuilder,
    ] = sg.Listbox,
    size: Tuple[int, int] = None,
    filter: str = None,
    key: str = None,
    **kwargs,
) -> sg.Element:
    """Selectors in pysimplesql are special elements that allow the user to change
    records in the database application. For example, Listboxes, Comboboxes and Tables
    all provide a convenient way to users to choose which record they want to select.
    This convenience function makes creating selectors very quick and as easy as using a
    normal PySimpleGUI element.

    Args:
        table: The table name that this selector will act on.
        element: The type of element you would like to use as a selector (defaults to a
            Listbox)
        size: The desired size of this selector element
        filter: Can be used to reference different `Form`s in the same layout. Use a
            matching filter when creating the `Form` with the filter parameter.
        key: (optional) The key to give to this selector. If no key is provided, it will
            default to table:selector using the name specified in the table parameter.
            This is also passed through the keygen, so if selectors all use the default
            name, they will be made unique. ie: Journal:selector!1, Journal:selector!2,
            etc.
        **kwargs: Any additional arguments supplied will be passed on to the PySimpleGUI
            element. Note: TableBuilder objects bring their own kwargs.
    """
    element = _AutocompleteCombo if element == sg.Combo else element

    key = f"{table}:selector" if key is None else key
    key = keygen.get(key)

    meta = {"type": TYPE_SELECTOR, "table": table, "Form": None, "filter": filter}
    if element == sg.Listbox:
        layout = element(
            values=(),
            size=size or themepack.default_element_size,
            key=key,
            select_mode=sg.LISTBOX_SELECT_MODE_SINGLE,
            enable_events=True,
            metadata=meta,
        )
    elif element == sg.Slider:
        layout = element(
            enable_events=True,
            size=size or themepack.default_element_size,
            orientation="h",
            disable_number_display=True,
            key=key,
            metadata=meta,
        )
    elif element == _AutocompleteCombo:
        w = themepack.default_element_size[0]
        layout = element(
            values=(),
            size=size or (w, 10),
            enable_events=True,
            key=key,
            auto_size_text=False,
            metadata=meta,
        )
    elif element in [sg.Table, LazyTable]:
        required_kwargs = ["headings", "visible_column_map", "num_rows"]
        for kwarg in required_kwargs:
            if kwarg not in kwargs:
                raise RuntimeError(
                    f"DataSet selectors must use the {kwarg} keyword argument."
                )
        # Create a narrow column for displaying a * character for virtual rows.
        # This will be the 1st column
        kwargs["headings"].insert(0, "")
        kwargs["visible_column_map"].insert(0, 1)
        if "col_widths" in kwargs:
            kwargs["col_widths"].insert(0, themepack.unsaved_column_width)

        # Create other kwargs that are required
        kwargs["enable_events"] = True
        kwargs["select_mode"] = sg.TABLE_SELECT_MODE_BROWSE
        kwargs["justification"] = "left"

        # Make an empty list of values
        vals = [[""] * len(kwargs["headings"])]
        layout = element(values=vals, key=key, metadata=meta, **kwargs)
    elif isinstance(element, TableBuilder):
        table_builder = element
        element = table_builder.element
        lazy = table_builder.lazy_loading
        kwargs = table_builder.get_table_kwargs()

        meta["TableBuilder"] = table_builder
        # Make an empty list of values
        vals = [[""] * len(kwargs["headings"])]
        layout = element(
            vals,
            lazy_loading=lazy,
            key=key,
            metadata=meta,
            **kwargs,
        )
    else:
        raise RuntimeError(f'Element type "{element}" not supported as a selector.')

    return layout


@dc.dataclass
class TableStyler:
    """TODO"""

    # pysimplesql specific
    frame_pack_kwargs: Dict[str] = dc.field(default_factory=dict)

    # PySimpleGUI Table kwargs that are compatible with pysimplesql
    justification: TableJustify = "left"
    row_height: int = None
    font: Union[str, Tuple[str, int], None] = None
    text_color: str = None
    background_color: str = None
    alternating_row_color: str = None
    selected_row_colors: Tuple[str, str] = (None, None)
    header_text_color: str = None
    header_background_color: str = None
    header_font: Union[str, Tuple[str, int], None] = None
    header_border_width: int = None
    header_relief: str = None
    vertical_scroll_only: bool = True
    hide_vertical_scroll: bool = False
    border_width: int = None
    sbar_trough_color: str = None
    sbar_background_color: str = None
    sbar_arrow_color: str = None
    sbar_width: int = None
    sbar_arrow_width: int = None
    sbar_frame_color: str = None
    sbar_relief: str = None
    pad: Union[int, Tuple[int, int], Tuple[Tuple[int, int], Tuple[int, int]]] = None
    tooltip: str = None
    right_click_menu: List[Union[List[str], str]] = None
    expand_x: bool = False
    expand_y: bool = False
    visible: bool = True

    def __repr__(self) -> str:
        attrs = self.get_table_kwargs()
        return f"TableStyler({attrs})"

    def get_table_kwargs(self):
        non_default_attributes = {}
        for field in dc.fields(self):
            if (
                getattr(self, field.name) != field.default
                and getattr(self, field.name)
                and field.name not in []
            ):
                non_default_attributes[field.name] = getattr(self, field.name)
        return non_default_attributes


@dc.dataclass
class TableBuilder(list):

    """This is a convenience class used to build table headings for PySimpleGUI.

    In addition, `TableBuilder` objects can sort columns in ascending or descending
    order by clicking on the column in the heading in the PySimpleGUI Table element if
    the sort_enable parameter is set to True.

    Args:
        num_rows: Number of rows to display in the table.
        sort_enable: True to enable sorting by heading column.
        allow_cell_edits: Double-click to edit a cell value if True. Accepted edits
            update both `sg.Table` and associated `field` element. Note: primary key,
            generated, or `readonly` columns don't allow cell edits.
        lazy_loading: For larger DataSets (see `LazyTable`).
        add_save_heading_button: Adds a save button to the left-most heading column if
            True.
        apply_search_filter: Filter rows to only those columns in `DataSet.search_order`
            that contain `Dataself.search_string`.
        style: see `TableStyler`.

    Returns:
        None
    """

    # store our instances
    instances: ClassVar[List[TableBuilder]] = []

    num_rows: int
    """Number of rows to display in the table."""
    sort_enable: bool = True
    """True to enable sorting by heading column."""
    allow_cell_edits: bool = False
    """Double-click to edit a cell value if True. Accepted edits update both `sg.Table`
    and associated `field` element. Note: primary key, generated, or `readonly` columns
    don't allow cell edits."""
    lazy_loading: bool = False
    """For larger DataSets (see `LazyTable`)."""
    add_save_heading_button: bool = False
    """Adds a save button to the left-most heading column if True."""
    apply_search_filter: bool = False
    """Filter rows to only those columns in `DataSet.search_order` that contain
    `Dataself.search_string`."""
    style: TableStyler = dc.field(default_factory=TableStyler)

    def __post_init__(self) -> None:
        # Store this instance in the master list of instances
        TableBuilder.instances.append(self)

        self._width_map: List[int] = []
        self._col_justify_map: List[int] = []
        self._heading_justify_map: List[int] = []
        self._visible_map: List[bool] = []
        self.readonly_columns: List[str] = []

        if self.add_save_heading_button:
            self.insert(0, themepack.unsaved_column_header)
        else:
            self.insert(0, "")

    def add_column(
        self,
        column: str,
        heading: str,
        width: int,
        col_justify: ColumnJustify = "default",
        heading_justify: HeadingJustify = "column",
        readonly: bool = False,
        visible: bool = True,
    ) -> None:
        """Add a new heading column to this TableBuilder object.  Columns are added in
        the order that this method is called. Note that the primary key column does not
        need to be included, as primary keys are stored internally in the `_TableRow`
        class.

        Args:
            column: The name of the column in the database
            heading: The name of this columns heading (title)
            width: The width for this column to display within the Table element
            col_justify: Default 'left'. Available options: 'left', 'right', 'center',
                'default'.
            heading_justify: Defaults to 'column' inherity `col_justify`. Available
                options: 'left', 'right', 'center', 'column', 'default'.
            readonly: Indicates if the column is read-only when
                `TableBuilder.allow_cell_edits` is True.
            visible: True if the column is visible.  Typically, the only hidden column
                would be the primary key column if any. This is also useful if the
                `DataSet.rows` DataFrame has information that you don't want to display.

        Returns:
            None
        """
        self.append({"heading": heading, "column": column})
        self._width_map.append(width)

        # column justify
        if col_justify == "default":
            col_justify = self.style.justification
        self._col_justify_map.append(col_justify)

        # heading justify
        if heading_justify == "column":
            heading_justify = col_justify
        if heading_justify == "default":
            heading_justify = self.style.justification
        self._heading_justify_map.append(heading_justify)

        self._visible_map.append(visible)
        if readonly:
            self.readonly_columns.append(column)

    def get_table_kwargs(self) -> Dict[str]:
        kwargs = {}

        kwargs["num_rows"] = self.num_rows
        kwargs["headings_justification"] = self.heading_justify_map
        kwargs["cols_justification"] = self.col_justify_map
        kwargs["headings"] = self.heading_names
        kwargs["visible_column_map"] = self.visible_map
        kwargs["col_widths"] = self.width_map
        kwargs["auto_size_columns"] = False
        kwargs["enable_events"] = True
        kwargs["select_mode"] = sg.TABLE_SELECT_MODE_BROWSE

        # Create a narrow column for displaying a * character for virtual rows.
        # This will be the 1st column
        kwargs["visible_column_map"].insert(0, 1)
        kwargs["col_widths"].insert(0, themepack.unsaved_column_width)

        return kwargs | self.style.get_table_kwargs()

    @property
    def element(self) -> Type[LazyTable]:
        return LazyTable

    @property
    def heading_names(self) -> List[str]:
        """Return a list of heading_names for use with the headings parameter of
        PySimpleGUI.Table.

        Returns:
            a list of heading names
        """
        headings = [c["heading"] for c in self]
        if self.add_save_heading_button:
            headings.insert(0, themepack.unsaved_column_header)
        else:
            headings.insert(0, "")
        return [c["heading"] for c in self]

    @property
    def columns(self):
        """Return a list of column names.

        Returns:
            a list of column names
        """
        return [c["column"] for c in self if c["column"] is not None]

    @property
    def col_justify_map(self) -> List[str]:
        """Convenience method for creating PySimpleGUI tables.

        Returns:
            a list column justifications for use with PySimpleGUI Table
            cols_justification parameter
        """
        justify = [justify[0].lower() for justify in self._col_justify_map]
        justify.insert(0, "l")
        return justify

    @property
    def heading_justify_map(self) -> List[str]:
        """Convenience method for creating PySimpleGUI tables.

        Returns:
            a list heading justifications for use with LazyTable
            `headings_justification`
        """
        justify = [justify[0].lower() for justify in self._heading_justify_map]
        justify.insert(0, "l")
        return justify

    @property
    def heading_anchor_map(self) -> List[str]:
        """Internal method for passing directly to treeview heading() function.

        Returns:
            a list heading anchors for use with treeview heading() function.
        """
        justify = [
            TK_ANCHOR_MAP[justify[0].lower()] for justify in self._heading_justify_map
        ]
        justify.insert(0, "w")
        return justify

    @property
    def visible_map(self) -> List[Union[bool, int]]:
        """Convenience method for creating PySimpleGUI tables.

        Returns:
            a list of visible columns for use with th PySimpleGUI Table
            visible_column_map parameter
        """
        return list(self._visible_map)

    @property
    def width_map(self) -> List[int]:
        """Convenience method for creating PySimpleGUI tables.

        Returns:
            a list column widths for use with th PySimpleGUI Table col_widths parameter
        """
        return list(self._width_map)

    def _update_headings(
        self, element: sg.Table, sort_column=None, sort_order: int = None
    ) -> None:
        """Perform the actual update to the PySimpleGUI Table heading.
        Note: Not typically called by the end user.

        Args:
            element: The PySimpleGUI Table element
            sort_column: The column to show the sort direction indicators on
            sort_order: A SORT_* constant (SORT_NONE, SORT_ASC, SORT_DESC)

        Returns:
            None
        """

        # Load in our marker characters.  We will use them to both display the
        # sort direction and to detect current direction
        try:
            asc = themepack.marker_sort_asc
        except AttributeError:
            asc = "\u25BC"
        try:
            desc = themepack.marker_sort_desc
        except AttributeError:
            desc = "\u25B2"

        for i, x in zip(range(len(self)), self):
            anchor = self.heading_anchor_map[i]
            # Clear the direction markers
            x["heading"] = x["heading"].replace(asc, "").replace(desc, "")
            if (
                x["column"] == sort_column
                and sort_column is not None
                and sort_order != SORT_NONE
            ):
                marker = asc if sort_order == SORT_ASC else desc
                if anchor == "e":
                    x["heading"] = marker + x["heading"]
                else:
                    x["heading"] += marker
            element.Widget.heading(
                i, text=x["heading"], anchor=self.heading_anchor_map[i]
            )

    def enable_heading_function(self, element: sg.Table, fn: callable) -> None:
        """Enable the sorting callbacks for each column index, or saving by click the
        unsaved changes column
        Note: Not typically used by the end user. Called from `Form.auto_map_elements()`

        Args:
            element: The PySimpleGUI Table element associated with this TableBuilder
            fn: A callback functions to run when a heading is clicked. The callback
                should take one column parameter.

        Returns:
            None
        """
        if self.sort_enable:
            for i in range(len(self)):
                if self[i]["column"] is not None:
                    element.widget.heading(
                        i, command=functools.partial(fn, self[i]["column"], False)
                    )
            self._update_headings(element)
        if self.add_save_heading_button:
            element.widget.heading(0, command=functools.partial(fn, None, save=True))

    def insert(self, idx, heading: str, column: str = None, *args, **kwargs) -> None:
        super().insert(idx, {"heading": heading, "column": column})


class _HeadingCallback:

    """Internal class used when sg.Table column headings are clicked."""

    def __init__(self, frm_reference: Form, data_key: str) -> None:
        """Create a new _HeadingCallback object.

        Args:
            frm_reference: `Form` object
            data_key: `DataSet` key

        Returns:
            None
        """
        self.frm: Form = frm_reference
        self.data_key = data_key

    def __call__(self, column, save) -> None:
        dataset = self.frm[self.data_key]
        if save:
            dataset.save_record()
            # force a timeout, without this
            # info popup creation broke pysimplegui events, weird!
            self.frm.window.read(timeout=1)
        elif dataset.row_count:  # len(dataset.rows.index) - len(dataset.virtual_pks):
            dataset.sort_cycle(column, self.data_key, update_elements=True)


class _CellEdit:

    """Internal class used when sg.Table cells are double-clicked if edit enabled."""

    def __init__(self, frm_reference: Form) -> None:
        self.frm = frm_reference
        self.active_edit = False

    def __call__(self, event) -> None:
        # if double click a treeview
        if isinstance(event.widget, ttk.Treeview):
            tk_widget = event.widget
            # identify region
            region = tk_widget.identify("region", event.x, event.y)
            if region == "cell":
                self.edit(event)

    def edit(self, event) -> None:
        treeview = event.widget

        # only allow 1 edit at a time
        if self.active_edit or self.frm._edit_protect:
            return

        # get row and column
        row = int(treeview.identify_row(event.y))
        col_identified = treeview.identify_column(event.x)
        if col_identified:
            col_idx = int(treeview.identify_column(event.x)[1:]) - 1

        try:
            data_key, element = self.get_datakey_and_sgtable(treeview, self.frm)
        except TypeError:
            return

        if not element:
            return

        # get table_builders
        table_builder = element.metadata["TableBuilder"]

        # get column name
        columns = table_builder.columns
        column = columns[col_idx - 1]

        # use table_element to distinguish
        table_element = element.Widget
        root = table_element.master

        # get text, coordinates, width and height
        x, y, width, height = table_element.bbox(row, col_idx)
        text = self.frm[data_key][column]

        # return early due to following conditions:
        if col_idx == 0:
            return

        if column in table_builder.readonly_columns:
            logger.debug(f"{column} is readonly")
            return

        if column == self.frm[data_key].pk_column:
            logger.debug(f"{column} is pk_column")
            return

        if self.frm[data_key].column_info[column].generated:
            logger.debug(f"{column} is a generated column")
            return

        if not table_builder.allow_cell_edits:
            logger.debug("This Table element does not allow editing")
            return

        # else, we can continue:
        self.active_edit = True

        # see if we should use a combobox
        combobox_values = self.frm[data_key].combobox_values(
            column, insert_placeholder=False
        )

        if combobox_values:
            # overwrite text with description from sg.Table
            text = table_element.item(row, "values")[col_idx]
            widget_type = TK_COMBOBOX
            width = (
                width
                if width >= themepack.combobox_min_width
                else themepack.combobox_min_width
            )

        # or a checkbox
        elif self.frm[data_key].column_info[column].python_type == bool:
            widget_type = TK_CHECKBUTTON
            width = (
                width
                if width >= themepack.checkbox_min_width
                else themepack.checkbox_min_width
            )

        # or a date
        elif self.frm[data_key].column_info[column].python_type == dt.date:
            text = self.frm[data_key].column_info[column].cast(text)
            widget_type = TK_DATEPICKER
            width = (
                width
                if width >= themepack.datepicker_min_width
                else themepack.datepicker_min_width
            )

        # else, its a normal ttk.entry
        else:
            widget_type = TK_ENTRY
            width = (
                width if width >= themepack.text_min_width else themepack.text_min_width
            )

        # float a frame over the cell
        frame = tk.Frame(root)
        frame.place(x=x, y=y, anchor="nw", width=width, height=height)

        # setup the widgets
        # ------------------

        # checkbutton
        # need to use tk.IntVar for checkbox
        if widget_type == TK_CHECKBUTTON:
            field_var = tk.BooleanVar()
            field_var.set(checkbox_to_bool(text))
            self.field = tk.Checkbutton(frame, variable=field_var)
            expand = False
        else:
            # create tk.StringVar for combo/entry
            field_var = tk.StringVar()
            field_var.set(text)

        # entry
        if widget_type == TK_ENTRY:
            self.field = _TtkStrictInput(frame, textvariable=field_var, justify="left")
            expand = True

        if widget_type == TK_DATEPICKER:
            text = dt.date.today() if type(text) is str else text
            self.field = _DatePicker(
                frame,
                self.frm[data_key],
                column_name=column,
                init_date=text,
                textvariable=field_var,
            )
            expand = True

        # combobox
        if widget_type == TK_COMBOBOX:
            self.field = _TtkCombo(
                frame, textvariable=field_var, justify="left", values=combobox_values
            )
            self.field.bind("<Configure>", self.combo_configure)
            expand = True

        if isinstance(self.field, _TtkStrictInput):
            self.field.add_validate(self.frm[data_key], column)

        # bind text to Return (for save), and Escape (for discard)
        # event is discarded
        accept_dict = {
            "data_key": data_key,
            "table_element": table_element,
            "row": row,
            "column": column,
            "col_idx": col_idx,
            "combobox_values": combobox_values,
            "widget_type": widget_type,
            "field_var": field_var,
        }

        self.field.bind(
            "<Return>",
            lambda event: self.accept(**accept_dict),
        )
        self.field.bind("<Escape>", lambda event: self.destroy())

        if themepack.use_cell_buttons:
            # buttons
            self.accept_button = tk.Button(
                frame,
                text="\u2714",
                foreground="green",
                relief=tk.GROOVE,
                command=lambda: self.accept(**accept_dict),
            )
            self.cancel_button = tk.Button(
                frame,
                text="\u274E",
                foreground="red",
                relief=tk.GROOVE,
                command=lambda: self.destroy(),
            )
            # pack buttons
            self.cancel_button.pack(side="right")
            self.accept_button.pack(side="right")

        if widget_type == TK_DATEPICKER:
            self.field.button.pack(side="right")
        # have entry use remaining space
        self.field.pack(side="left", expand=expand, fill="both")

        # select text and focus to begin with
        if widget_type != TK_CHECKBUTTON:
            self.field.select_range(0, tk.END)
            self.field.focus_force()

        if widget_type == TK_COMBOBOX:
            self.field.bind("<KeyRelease>", self.field.handle_keyrelease, "+")

        # bind single-clicks
        self.destroy_bind = self.frm.window.TKroot.bind(
            "<Button-1>",
            lambda event: self.single_click_callback(event, accept_dict),
            "+",
        )

    def accept(
        self,
        data_key,
        table_element,
        row,
        column,
        col_idx,
        combobox_values: _ElementRow,
        widget_type,
        field_var,
    ) -> None:
        # get current entry text
        new_value = field_var.get()

        # get current table row
        values = list(table_element.item(row, "values"))

        # if combo, set the value to the parent pk
        if widget_type == TK_COMBOBOX:
            new_value = combobox_values[self.field.current()].get_pk()

        dataset = self.frm[data_key]

        # validate the field
        if dataset.validate_mode:
            widget = (
                self.field
                if themepack.validate_exception_animation is not None
                else None
            )
            valid = dataset.validate_field(column, new_value, widget)
            if not valid:
                return

        # see if there was a change
        old_value = dataset.get_current_row().copy()[column]
        cast_new_value = dataset.value_changed(
            column, old_value, new_value, bool(widget_type == TK_CHECKBUTTON)
        )
        if cast_new_value is not Boolean.FALSE:
            # push row to dataset and update
            dataset.set_current(column, cast_new_value, write_event=True)
            # Update matching field
            self.frm.update_fields(data_key, columns=[column])
            # TODO: make sure we actually want to set new_value to cast
            new_value = cast_new_value

        # now we can update the GUI table
        # -------------------------------

        # if combo, set new_value to actual text (not pk)
        if widget_type == TK_COMBOBOX:
            new_value = combobox_values[self.field.current()]

        # apply cell format fn
        if self.frm[data_key].column_info[column].cell_format_fn:
            fn = self.frm[data_key].column_info[column].cell_format_fn
            new_value = fn(new_value)

        # update value row with new text
        values[col_idx] = new_value

        # set marker
        values[0] = (
            themepack.marker_unsaved
            if dataset.current_row_has_backup
            and not dataset.get_current_row().equals(dataset.get_original_current_row())
            else " "
        )

        # push changes to table element row
        table_element.item(row, values=values)

        self.destroy()

    def destroy(self) -> None:
        # unbind
        self.frm.window.TKroot.unbind("<Button-1>", self.destroy_bind)

        # destroy widets and window
        self.field.destroy()
        if themepack.use_cell_buttons:
            self.accept_button.destroy()
            self.cancel_button.destroy()
        self.field.master.destroy()
        # reset edit
        self.active_edit = False

    def single_click_callback(
        self,
        event,
        accept_dict,
    ) -> None:
        # destroy if you click a heading while editing
        if isinstance(event.widget, ttk.Treeview):
            tk_widget = event.widget
            # identify region
            region = tk_widget.identify("region", event.x, event.y)
            if region == "heading":
                self.destroy()
                return
        # disregard if you click the field/buttons of celledit
        widget_list = [self.field]
        if themepack.use_cell_buttons:
            widget_list.append(self.accept_button)
            widget_list.append(self.cancel_button)

        # for datepicker
        with contextlib.suppress(AttributeError):
            widget_list.append(self.field.button)
        if "ttkcalendar" in str(event.widget):
            return

        if event.widget in widget_list:
            return
        self.accept(**accept_dict)

    def get_datakey_and_sgtable(self, treeview, frm):
        # loop through datasets, trying to identify sg.Table selector
        for data_key in [
            data_key for data_key in frm.datasets if len(frm[data_key].selector)
        ]:
            for e in frm[data_key].selector:
                element = e["element"]
                if element.widget == treeview and "TableBuilder" in element.metadata:
                    return data_key, element
        return None

    def combo_configure(self, event) -> None:
        """Configures combobox drop-down to be at least as wide as longest value."""

        combo = event.widget
        style = ttk.Style()

        # get longest value
        long = max(combo.cget("values"), key=len)
        # get font
        font = tkfont.nametofont(str(combo.cget("font")))
        # set initial width
        width = font.measure(long.strip() + "0")
        # make it width size if smaller
        width = width if width > combo["width"] else combo["width"]
        style.configure("SS.TCombobox", postoffset=(0, 0, width, 0))
        combo.configure(style="SS.TCombobox")


class _LiveUpdate:

    """Internal class used to automatically sync selectors with field changes."""

    def __init__(self, frm_reference: Form) -> None:
        self.frm = frm_reference
        self.last_event_widget = None
        self.last_event_time = None
        self.delay_seconds = themepack.live_update_typing_delay_seconds

    def __call__(self, event) -> None:
        # keep track of time on same widget
        if event.widget == self.last_event_widget:
            self.last_event_time = time()
        self.last_event_widget = event.widget

        # get widget type
        widget_type = event.widget.__class__.__name__

        # if <<ComboboxSelected>> and a combobox, or a checkbutton
        if (
            event.type == TK_COMBOBOX_SELECTED and widget_type == TK_COMBOBOX
        ) or widget_type == TK_CHECKBUTTON:
            self.sync(event.widget, widget_type)

        # use tk.after() for text, so waits for pause in typing to update selector.
        elif widget_type in [TK_ENTRY, TK_TEXT]:
            self.frm.window.TKroot.after(
                int(self.delay_seconds * 1000),
                lambda: self.delay(event.widget, widget_type),
            )

    def sync(self, widget, widget_type) -> None:
        for e in self.frm.element_map:
            if e["element"].widget == widget:
                data_key = e["table"]
                column = e["column"]
                element = e["element"]
                if widget_type == TK_COMBOBOX and isinstance(
                    element.get(), _ElementRow
                ):
                    new_value = element.get().get_pk_ignore_placeholder()
                else:
                    new_value = element.get()

                dataset = self.frm[data_key]

                # validate the field
                if dataset.validate_mode == ValidateMode.RELAXED or (
                    not isinstance(e["element"], _EnhancedInput)
                    and dataset.validate_mode == ValidateMode.STRICT
                ):
                    widget = (
                        e["element"].Widget
                        if themepack.validate_exception_animation is not None
                        else None
                    )
                    valid = dataset.validate_field(column, new_value, widget)
                    if not valid:
                        return

                # see if there was a change
                old_value = dataset.get_current_row()[column]
                new_value = dataset.value_changed(
                    column, old_value, new_value, bool(widget_type == TK_CHECKBUTTON)
                )
                if new_value is not Boolean.FALSE:
                    # push row to dataset and update
                    dataset.set_current(column, new_value, write_event=True)

                    # Update tableview if uses column:
                    if dataset.column_likely_in_selector(column):
                        self.frm.update_selectors(dataset.key)

    def delay(self, widget, widget_type) -> None:
        if self.last_event_time:
            elapsed_sec = time() - self.last_event_time
            if elapsed_sec >= self.delay_seconds:
                self.sync(widget, widget_type)
        else:
            self.sync(widget, widget_type)


# ======================================================================================
# THEMEPACKS
# ======================================================================================
# Change the look and feel of your database application all in one place.
class ThemePack:

    """ThemePacks are user-definable objects that allow for the look and feel of
    database applications built with PySimpleGUI + pysimplesql.  This includes
    everything from icons, the ttk themes, to sounds. Pysimplesql comes with 3 pre-made
    ThemePacks: default (aka ss_small), ss_large and ss_text. Creating your own is easy
    as well! In fact, a ThemePack can be as simple as one line if you just want to
    change one aspect of the default ThemePack. Example: my_tp = {'search': 'Click here
    to search'} # I want a different search button.

    Once a ThemePack is created, it's very easy to use.  Here is a very simple example
    of using a ThemePack:
        ss.themepack(my_tp_dict_variable)
        # make a search button, using the 'search' key from the ThemePack
        sg.Button(ss.themepack.search, key='search_button')
    """

    default: ClassVar[Dict[Any]] = {
        # Theme to use with ttk widgets.
        # -------------------------------
        # Choices (on Windows) include:
        # 'default', 'winnative', 'clam', 'alt', 'classic', 'vista', 'xpnative'
        "ttk_theme": "default",
        # Defaults for actions() buttons & popups
        # ----------------------------------------
        "use_ttk_buttons": True,
        "default_element_pad": (5, 0),
        "action_button_pad": (3, 0),
        "popup_button_pad": (5, 5),
        # Action buttons
        # ----------------------------------------
        # fmt: off
        'edit_protect': b'iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAGJ3pUWHRSYXcgcHJvZmlsZSB0eXBlIGV4aWYAAHjarVdZsuQmEPznFD4CVSwFx2GN8A18fCeiUG/zZtoRfnrdQoCKpDJJaDP++Xuav/DH7L3xQVLMMVr8+ewzFxSS3X/5+ibrr299sKfwUm/uBkaVw93tRynav6A+PF44Y1B9rTdJWzhpILoDX39ujbzK/Rkk6nnXk9dAeexCzEmeoVYN1LTjBUU//oa1b+vZvFQIstQDBnLMw5Gz13faCNz+FHwSvlGPftZllJ0jc92iBkNCXqZ3J9A+J+glyadk3rN/l96Sz0Xr3Vsuo+YIhV82UHird/cw/DywuxHxa0MaVj6mo585e5pz7NkVH5HRqIq6kk0nDDpWpNxdr0Vcgk9AWa4r40q22AbKu2224mqUicHKNOSpU6FJ47o3aoDoebDgztzYXXXJCWduYImcXxdNFjDWwSC7xsOAM+/4xkLXuPkar1HCyJ3QlQnBCK/8eJnfNf6Xy8zZVorIpjtXwMVL14CxmFvf6AVCaCpv4UrwuZR++6SfJVWPbivNCRMstu4QNdBDW+7i2aFfwH0vITLSNQBShLEDwJADAzaSCxTJCrMQIY8JBBUgZ+e5ggEKgTtAssfSYCOMJYOx8Y7Q1ZcDR17V8CYQEVx0Am6wpkCW9wH6EZ+goRJc8CGEGCQkE3Io0UUfQ4xR4jK5Ik68BIkikiRLSS75FFJMklLKqWTODh4YcsySU865FDYFAxXEKuhfUFO5uuprqLFKTTXX0iCf5ltosUlLLbfSubsOm+ixS0899zLIDDjF8COMOGSkkUeZ0Np0088w45SZZp7lZk1Z/bj+A2ukrPHF1OonN2uoNSInBC07CYszMMaewLgsBiBoXpzZRN7zYm5xZjNjUQQGyLC4MZ0WY6DQD+Iw6ebuwdxXvJmQvuKN/8ScWdT9H8wZUPfJ2y9Y62ufaxdjexWunFqH1Yf2kYrhVNamVr66TynlKlOengN5/LcEGP4KxHWInT2n0cr1xiiwKpqr29qb9N20X8QeqQ3otEeYEQ7Zhv8Wzwe+GvfAM1dnenTIwYWrtgGOx36Irqbh40boXZ/c+kIE7qMbO5TnvkHCis3bIDg8XHF6chNb7J6V/eJuroIbTVENSTP6svMDvy+0XHshmR5tTeD9qwlyrVEs7X5E0/jiNv4MvwpXtAz1F4VY69XV55qzhkiIP1hDlCaIj5JZ+dfAn3fpUV9AbzzYncCMhbdhYrPaWRmmYguAmve8cpu2VdHBGCsm00U61EoTqyfs9zP14vf0cU5C6rcg13kE60uVNti9of4BbOgHbANYYzUJt84cKNukAodmqmTNMBLk9wvSoRSXe1bEZubhaYjSBE35JHSTNtBx5x2ScjsdEf1fUJcVyvwAex7YEbB1cTTvdw+mEx6nIIVviHQJ0ZZpSHCJoUsI0lEhYL7DteDKESzAt+ULu6dtZnabpu1Pes7vunUgfbfDXfDQqtO8IsuKgszGA2KVNktdJxhEa1Snj8jMR05JjkhNsSKauQ6XcXDArCKssNX4G60e+mGIXczhuFvvd3icEarivBezf8WCwg2XdgGn2q0RbEJasLQXHza31s6oiYH0trbDzzxSb9ZIoDMVGM4YpMRikr2pC1xHeS2cmjunis2g5N5QYkJnSR43KwREPRx4/hOeeeAcVTsi2zNAMAp7Yl363YQDk8p7DLa6uvlCYF4pP5z4Uwib+pK8Tgp7+4hBZYUj1vBtJ/u35j530Vs15+bF6eLBjymhtucH0MVI9aq82poT5TAm/Lx8T522rV9Km1ZWnYRiE1Z/3WxjfDfCF3vQfK+6RjQQeir12E0Rqg8tgBp1y1axTSVtkpyJuko2azhjb61AfnL4TaDOvsnvpztN6X350aqrGoxP4zEXbQkZvzwUUIIyovDRCk4dDe6x9/413X6sYeak4u7rwX23S5on2+n9eHQ+/jdDP63l1n05sPPJSvTdbOsW6nCMWxTw4kCqieHKAqnnDpwUZ+Yft+wPTyz3+rv97qRR3MOS0m2C1by7oDu7dcR2FV6PSH8+RHwiuhNST0LKAXLOMtTqw5eiOWV3V9LZYb4V0nU3v1QYzoHmX+RGJBpl98L8AAABhGlDQ1BJQ0MgcHJvZmlsZQAAeJx9kT1Iw0AcxV9TpUVaBO0gopChOlkQFXHUKhShQqgVWnUwufQLmjQkLS6OgmvBwY/FqoOLs64OroIg+AHi5Oik6CIl/i8ptIjx4Lgf7+497t4BQqPMNKtrHND0qplKxMVMdlUMvCKIPoQxDFFmljEnSUl4jq97+Ph6F+NZ3uf+HGE1ZzHAJxLPMsOsEm8QT29WDc77xBFWlFXic+Ixky5I/Mh1xeU3zgWHBZ4ZMdOpeeIIsVjoYKWDWdHUiKeIo6qmU76QcVnlvMVZK9dY6578haGcvrLMdZpDSGARS5AgQkENJZRRRYxWnRQLKdqPe/gHHb9ELoVcJTByLKACDbLjB/+D391a+ckJNykUB7pfbPtjBAjsAs26bX8f23bzBPA/A1d6219pADOfpNfbWvQI6N0GLq7bmrIHXO4AA0+GbMqO5Kcp5PPA+xl9UxbovwV61tzeWvs4fQDS1FXyBjg4BEYLlL3u8e5gZ2//nmn19wNkDXKhWfC+CAAAAAZiS0dEAAAAAAAA+UO7fwAAAAlwSFlzAAALEwAACxMBAJqcGAAAAAd0SU1FB+QIEg0fJQXnbmsAAAKVSURBVDjLhZJPSFRRFMa/c++b55tGTZpSMZRStCyJFlEoLkSyWtQiyI1FUWRtIooWFS2yKHcG0aICN1IWCNWmQhfixqQokDAHpY3lFJiTZo7ju/e9e0+LwP6o9W3O6vvxfeccwjK6dPEirrS2IkmUE2loeCGkTBFwjIAxw4yinh4AAC0HMIlbSL0zmHs72SV7extldjaElDOS6CoDNwCgsLsbYjmA+q6Rk//xaN6p5kbRfIJDIjZK5YbWtjHQWRCNYqS+fukEmQebIYQTD3R6eJ7z883W83C8LZRpucRIJkl6HtZWVNBIIgH5t3n2fhUIBmxNu1K6WmdSUIl2aJLIab4MGEFhcvz41OfPgyGwuIIkA0Cc01o1KaXBzIC7Clnjd2j2yWFS1WsSBR2POiURNvX1/arw6W4ZYlEHjqD1YaAH5+f9XCEIvq8QiTgAiIIgNGZ4stDZ1ZIqaWwBfk9QFJdwBcOEpsv31UoiwFoGEUFKB8YYWLb7Ubk6FSZvLyQWAPD+1WPM2HKExlxXyt9mrWE34pIxhqJRD9ZastZ2Z2a/Pg2NRenZiQUAAUDHbmBvEzayj0FfF3qx2ArWWpMQPwMqpWbSGbXGy3KCdWdSf+xMAMDBZxorD5kGt67b8/KqGDwHImIpBRsTGiLsiXpuMOcvPrlYGMzlXulOxPbdI17biCwxTsYwMXOn6zovBQGbL6SWBjAzAGwgMNjNY7fuJnj7QxhZ8EFk5RxRyqL49JclP1YCgNYa/f3910pKSvLi8Tjp+TR9Q36XjhYf4NmxtFQTaHueXhJAZWVlcF0X1loeHR0NBgYG3sRisZORSGTo29QUampr8S8Jay2mp6dzieh1ZWXljpqamtogCIbCMPyvGQB+AKK0L000MH1KAAAAAElFTkSuQmCC',  # noqa E501
        'quick_edit': b'iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAGJ3pUWHRSYXcgcHJvZmlsZSB0eXBlIGV4aWYAAHjarVdZsuQmEPznFD4CVSwFx2GN8A18fCeiUG/zZtoRfnrdQoCKpDJJaDP++Xuav/DH7L3xQVLMMVr8+ewzFxSS3X/5+ibrr299sKfwUm/uBkaVw93tRynav6A+PF44Y1B9rTdJWzhpILoDX39ujbzK/Rkk6nnXk9dAeexCzEmeoVYN1LTjBUU//oa1b+vZvFQIstQDBnLMw5Gz13faCNz+FHwSvlGPftZllJ0jc92iBkNCXqZ3J9A+J+glyadk3rN/l96Sz0Xr3Vsuo+YIhV82UHird/cw/DywuxHxa0MaVj6mo585e5pz7NkVH5HRqIq6kk0nDDpWpNxdr0Vcgk9AWa4r40q22AbKu2224mqUicHKNOSpU6FJ47o3aoDoebDgztzYXXXJCWduYImcXxdNFjDWwSC7xsOAM+/4xkLXuPkar1HCyJ3QlQnBCK/8eJnfNf6Xy8zZVorIpjtXwMVL14CxmFvf6AVCaCpv4UrwuZR++6SfJVWPbivNCRMstu4QNdBDW+7i2aFfwH0vITLSNQBShLEDwJADAzaSCxTJCrMQIY8JBBUgZ+e5ggEKgTtAssfSYCOMJYOx8Y7Q1ZcDR17V8CYQEVx0Am6wpkCW9wH6EZ+goRJc8CGEGCQkE3Io0UUfQ4xR4jK5Ik68BIkikiRLSS75FFJMklLKqWTODh4YcsySU865FDYFAxXEKuhfUFO5uuprqLFKTTXX0iCf5ltosUlLLbfSubsOm+ixS0899zLIDDjF8COMOGSkkUeZ0Np0088w45SZZp7lZk1Z/bj+A2ukrPHF1OonN2uoNSInBC07CYszMMaewLgsBiBoXpzZRN7zYm5xZjNjUQQGyLC4MZ0WY6DQD+Iw6ebuwdxXvJmQvuKN/8ScWdT9H8wZUPfJ2y9Y62ufaxdjexWunFqH1Yf2kYrhVNamVr66TynlKlOengN5/LcEGP4KxHWInT2n0cr1xiiwKpqr29qb9N20X8QeqQ3otEeYEQ7Zhv8Wzwe+GvfAM1dnenTIwYWrtgGOx36Irqbh40boXZ/c+kIE7qMbO5TnvkHCis3bIDg8XHF6chNb7J6V/eJuroIbTVENSTP6svMDvy+0XHshmR5tTeD9qwlyrVEs7X5E0/jiNv4MvwpXtAz1F4VY69XV55qzhkiIP1hDlCaIj5JZ+dfAn3fpUV9AbzzYncCMhbdhYrPaWRmmYguAmve8cpu2VdHBGCsm00U61EoTqyfs9zP14vf0cU5C6rcg13kE60uVNti9of4BbOgHbANYYzUJt84cKNukAodmqmTNMBLk9wvSoRSXe1bEZubhaYjSBE35JHSTNtBx5x2ScjsdEf1fUJcVyvwAex7YEbB1cTTvdw+mEx6nIIVviHQJ0ZZpSHCJoUsI0lEhYL7DteDKESzAt+ULu6dtZnabpu1Pes7vunUgfbfDXfDQqtO8IsuKgszGA2KVNktdJxhEa1Snj8jMR05JjkhNsSKauQ6XcXDArCKssNX4G60e+mGIXczhuFvvd3icEarivBezf8WCwg2XdgGn2q0RbEJasLQXHza31s6oiYH0trbDzzxSb9ZIoDMVGM4YpMRikr2pC1xHeS2cmjunis2g5N5QYkJnSR43KwREPRx4/hOeeeAcVTsi2zNAMAp7Yl363YQDk8p7DLa6uvlCYF4pP5z4Uwib+pK8Tgp7+4hBZYUj1vBtJ/u35j530Vs15+bF6eLBjymhtucH0MVI9aq82poT5TAm/Lx8T522rV9Km1ZWnYRiE1Z/3WxjfDfCF3vQfK+6RjQQeir12E0Rqg8tgBp1y1axTSVtkpyJuko2azhjb61AfnL4TaDOvsnvpztN6X350aqrGoxP4zEXbQkZvzwUUIIyovDRCk4dDe6x9/413X6sYeak4u7rwX23S5on2+n9eHQ+/jdDP63l1n05sPPJSvTdbOsW6nCMWxTw4kCqieHKAqnnDpwUZ+Yft+wPTyz3+rv97qRR3MOS0m2C1by7oDu7dcR2FV6PSH8+RHwiuhNST0LKAXLOMtTqw5eiOWV3V9LZYb4V0nU3v1QYzoHmX+RGJBpl98L8AAABhGlDQ1BJQ0MgcHJvZmlsZQAAeJx9kT1Iw0AcxV9TpUVaBO0gopChOlkQFXHUKhShQqgVWnUwufQLmjQkLS6OgmvBwY/FqoOLs64OroIg+AHi5Oik6CIl/i8ptIjx4Lgf7+497t4BQqPMNKtrHND0qplKxMVMdlUMvCKIPoQxDFFmljEnSUl4jq97+Ph6F+NZ3uf+HGE1ZzHAJxLPMsOsEm8QT29WDc77xBFWlFXic+Ixky5I/Mh1xeU3zgWHBZ4ZMdOpeeIIsVjoYKWDWdHUiKeIo6qmU76QcVnlvMVZK9dY6578haGcvrLMdZpDSGARS5AgQkENJZRRRYxWnRQLKdqPe/gHHb9ELoVcJTByLKACDbLjB/+D391a+ckJNykUB7pfbPtjBAjsAs26bX8f23bzBPA/A1d6219pADOfpNfbWvQI6N0GLq7bmrIHXO4AA0+GbMqO5Kcp5PPA+xl9UxbovwV61tzeWvs4fQDS1FXyBjg4BEYLlL3u8e5gZ2//nmn19wNkDXKhWfC+CAAAAAZiS0dEAAAAAAAA+UO7fwAAAAlwSFlzAAALEwAACxMBAJqcGAAAAAd0SU1FB+QIEg0fJQXnbmsAAAKVSURBVDjLhZJPSFRRFMa/c++b55tGTZpSMZRStCyJFlEoLkSyWtQiyI1FUWRtIooWFS2yKHcG0aICN1IWCNWmQhfixqQokDAHpY3lFJiTZo7ju/e9e0+LwP6o9W3O6vvxfeccwjK6dPEirrS2IkmUE2loeCGkTBFwjIAxw4yinh4AAC0HMIlbSL0zmHs72SV7extldjaElDOS6CoDNwCgsLsbYjmA+q6Rk//xaN6p5kbRfIJDIjZK5YbWtjHQWRCNYqS+fukEmQebIYQTD3R6eJ7z883W83C8LZRpucRIJkl6HtZWVNBIIgH5t3n2fhUIBmxNu1K6WmdSUIl2aJLIab4MGEFhcvz41OfPgyGwuIIkA0Cc01o1KaXBzIC7Clnjd2j2yWFS1WsSBR2POiURNvX1/arw6W4ZYlEHjqD1YaAH5+f9XCEIvq8QiTgAiIIgNGZ4stDZ1ZIqaWwBfk9QFJdwBcOEpsv31UoiwFoGEUFKB8YYWLb7Ubk6FSZvLyQWAPD+1WPM2HKExlxXyt9mrWE34pIxhqJRD9ZastZ2Z2a/Pg2NRenZiQUAAUDHbmBvEzayj0FfF3qx2ArWWpMQPwMqpWbSGbXGy3KCdWdSf+xMAMDBZxorD5kGt67b8/KqGDwHImIpBRsTGiLsiXpuMOcvPrlYGMzlXulOxPbdI17biCwxTsYwMXOn6zovBQGbL6SWBjAzAGwgMNjNY7fuJnj7QxhZ8EFk5RxRyqL49JclP1YCgNYa/f3910pKSvLi8Tjp+TR9Q36XjhYf4NmxtFQTaHueXhJAZWVlcF0X1loeHR0NBgYG3sRisZORSGTo29QUampr8S8Jay2mp6dzieh1ZWXljpqamtogCIbCMPyvGQB+AKK0L000MH1KAAAAAElFTkSuQmCC',  # noqa E501
        'save': b'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',  # noqa E501
        'first': b'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',  # noqa E501
        'previous': b'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',  # noqa E501
        'next': b'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',  # noqa E501
        'last': b'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',  # noqa E501
        'insert': b'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',  # noqa E501
        'delete': b'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',  # noqa E501
        'duplicate': b'iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAABhGlDQ1BJQ0MgcHJvZmlsZQAAKJF9kT1Iw1AUhU9TRZGKQztIcchQnSyIFnHUKhShQqgVWnUweekfNGlIUlwcBdeCgz+LVQcXZ10dXAVB8AfE1cVJ0UVKvC8ptIjxwuN9nHfP4b37AKFZZZrVMwFoum1mUkkxl18V+14hIIAwokjIzDLmJCkN3/q6p16quzjP8u/7swbVgsWAgEg8ywzTJt4gnt60Dc77xBFWllXic+Jxky5I/Mh1xeM3ziWXBZ4ZMbOZeeIIsVjqYqWLWdnUiBPEMVXTKV/Ieaxy3uKsVeusfU/+wlBBX1nmOq0RpLCIJUgQoaCOCqqwEaddJ8VChs6TPv6o65fIpZCrAkaOBdSgQXb94H/we7ZWcWrSSwolgd4Xx/kYBfp2gVbDcb6PHad1AgSfgSu94681gZlP0hsdLXYEDG0DF9cdTdkDLneA4SdDNmVXCtISikXg/Yy+KQ+Eb4GBNW9u7XOcPgBZmlX6Bjg4BMZKlL3u8+7+7rn929Oe3w9rHnKk7x4JKQAAAAZiS0dEAAAAAAAA+UO7fwAAAAlwSFlzAAAuIwAALiMBeKU/dgAAAAd0SU1FB+cCARMnD1HzB0IAAAAZdEVYdENvbW1lbnQAQ3JlYXRlZCB3aXRoIEdJTVBXgQ4XAAABJUlEQVQ4y6WTT2qDQBTGvxnLwFTETZfZZCu9hPdwJei2B3GThZcovUJAkx6hdXqBisxOycI/YF43VWxiTEo+eAy8gW9+35sZMMYeAWxM0zwAoEvFOSfbtvcA1piIAdhEUfTieR4451iSUgqu634BcMamaZqHoihoqqZpLtYv0WpqTFprIiLK85x836elKJP6GOKMBr7vU5ZldIuSJCEhxHY0GPBuldaaDMOg5akBqOsaYRjO7vV9j6sEZVnO9rXWBIAelk7uug5VVQHAuEopIYTA2S2cEgRBMDv9OI7/EIBzflcEblnWu1IK92gNQA2Ip2rbdsSeI5garf77DqSUx+ktfAP4TNP02XGcq9i73Q51Xb+dxRFCbA3DWPwHUsojgFfG2NMPCKbWh17KiKEAAAAASUVORK5CYII=',  # noqa E501
        'icon' : b'iVBORw0KGgoAAAANSUhEUgAAAEAAAAA+CAYAAACbQR1vAAAACXBIWXMAAAOwAAADsAEnxA+tAAAAGXRFWHRTb2Z0d2FyZQB3d3cuaW5rc2NhcGUub3Jnm+48GgAAFwBJREFUaIHNe3uYVMWd9ltV55w+fZnu6Z77nevIRUYYFCIo8gHRaEyMUZPgRlBcTXSzxtXdmOT5Askav2TXPJ/myZqo6G4w6Caa4KpkTYwK4hDRhTBcHAGZYaDn3tMzfe9zrfr+ON0zDczAcDPf+zzn6cupc0793vpVnfq99SsihMD5BCGkDsDFAOoAVAOoAVAFoBJAEAABUFzwKQDETvgcAtAPoBtAT+4zDGCvEKLvvNb3XAgghJQAWAFgEYAmAJfAMfJCYgDAXgB7ALQAeFsIkTjbm50xAYSQiwF8GcA1AOYDoGf78PMEC8AOAH8E8GshxOEzuloIcdoDgApgFRzGxf/HBwfwJwA3A5AnYptUSMbGjzJV2+LKyqTOrzI4D5m26I68/3rUHQh9NhsfajgTYhljdigUipWXlw+XlJQki4uLM6FQKOP3+3Wfz2coimIXltc0TcpkMnI8HncNDg564/G4Z3Bw0B+JRIKxWCxg2/ZEPI3A6ZIrAHwo1c75NrlprWWF2t4Q69bxMS8QQqCtDcpP4/xfUrZYYxPqFyCwOWBwQLc40rFB9L37Mo4+/SCsbHrMJ5eWlg41Nzcfbm5u7l6+fHn30qVLhyRJOi8jrKZp9K233irdunVr9a5du2pbW1unDQ8PB053HamYJjz3bhDmUN8hommf15689eOTygghyOr3sMGwxa2MEgYAtgAsAeg2oHNAswHN4kj2dKD7qfuR+OD3AACXy2UsW7Zs1wMPPLBrxYoV0fNh7ETx6quvVjz++OOXtbS0XGKapjR2KQL5tp+i5Ia/Q/wvb8aMSORW6+m/ef24Et/fJxZ9GBNvMkLclDgdyeKAmfMAjY8SoduAnk4i+tZz8P7hJz0vb/rdb5qbm896BD4fePvtt0tWrlz5lYGBgdKxzpOqi+C//wV4ps3D8AdvZLRI9wrx7Jr38ufp/hi+aQvi5nBavdB4nQOG7fy2uOMZQi1C0TVfh//hba7Q9LnmJ2bpOFi2bFn0oYce+uN450XvQWRa34YQHIFLrvTIbs9rZNWvvPnzVLfFHEvkjLZz7l7Q8kaODDNHgC0AQRnivtqST/8+fu9/HkzXfzKmjg3LssjmzZtnnLLM208j277XpqoHvlkLS5hqb8ifo4YNj5EzVuNANkdC1sqRUEDAiBcAEIQgqwZ939ppfvXvtsYWX3BLx8ALL7xQM2fOnK9u2bJl/qnKif7DyHbsNQHAVVYDqSh0LfnS0wEAkAzbTkE4YwgXo93AKOgO+ZbPG8/zJAhAeIrlTT2pFW/+6zuXPDw19l+f/+w1faqqjvnKOVekUin22muvVb7yyivTtm/fflFXV1fVxK4UsCOdcQihEkmBUlbjsRJDywFskmK94S61vGE2KB0lIGe8JU4wXhTMOgpecMTtQ2LK4rKv7d9+1233XGTV+FhfXV3dQH19/fC0adOGJk+enKyurs40NDRkp0+fnhmvmpZlkfb2dndnZ6enp6fH097e7u/o6AiGw+HQ0aNHy3t6eips22ZnQ57QUoYQAoQQyIEyCIhmAJskM534L72v6xqlvBaCUOcVOEarj2d8/ithEtSmJaBr35R6fv292iPbflM7XmUIIUJVVb3wv2w264IzkbkgYBVTignNzaUIAOFM4WmpGN6YTSeHE71hZHVzdNTPeQLPH8i5/hjGjxgGAlfNdAS+9hSKHngR1F82ZmWEECSbzaqFBy6g8XT2CvguWebJ/7biURCQwwBAt9y7NMUF7tLSyWyq+wiyyfiI64uc4YWtXjjxHg/MF4Bv8U0IPrId7pvXgsjqhbLt1KAM9MrV8N36MNT6ixgAcF2DHglnbUPbDBREg+WP7rpFMGk9qBQgLi8kfwjUUwSRa5izndMK24R+ZB+09zZBf/Mp8OTgebDsNFB9YPOuhzzvehR96npIvtysWQhkjx1E8sM/b7bWr/kccEI4XPZ/dlVZDBsFN68iLh8jsguSPwTm8YNI8jnVSdgWzEgY+oH3oP/5RVgfvQORjp3TPUfAZJDiKtDGyyHNWAKlYQ7cjc1gqne0jBDQI2Ekdm/rs1hiunji3hQwjh5AK6b9zrX4K1+U5ywH8QRAZAXU5QHzBsDcPlDFdU715XoWVrQXRl8HrCN/gXVkN3j3R+BD3RBGFrBNgBcGiwRgEojsAlQfaEk9SNVFoOVTQCsmQQpWQ6meBjlUAaqc3N2EbUHv60Sy7f0By9AWiGfuPDpy57EIIIQ0A9gBJsmsvgnSpZ+H3PgpEHcAxOUFlRUwjw9U9YK5PCCycm6EmAa4ngFPxWCnE+BGBtCz4JyDMAoQCsIUUK8f1FcMprjB3F6HkFNBcFjJYWQ69kPv/vhDSzGvFD+/Z/g4W8dThAghtwH4dyCnGRAKEqoFmzIfcuMi0NrZIF4/qOp4BHV5QV3ukWPklfNXADd02Ok4tO7DyHbsQ1Wm85muF398txjD2FNKYoSQJV6v98V0Ol0xxkkQXwlozUywqQvAJs0F8ZeBuX0gLg+oywPq9jrkyCqo7AKRlAvzshMctpYB1zIw4xHovZ0wj+5HMPz+0M//cdVvb/niFx4FMKZUdmoCvvQS63x0wQ1r166955VXXlkYj8eLTlkRJoMUlYJWTAOtmQlaNR2sfDLgLgL1+EFkFUzNkSNJIJICwvKfDKBsfM8RAsK2ICwLwjbBLQPC0GBl0rCTQ7CG+2BFjoIf3A5//97Eqi985p1//vGjbcc0qfitXntHb8rc3xTyHPqbaTgufB97DPjBD6g0OOM7hEn/9M2rpj/66I1NsqZp9LHHHmvcuHHj/AMHDkzlnE+8LRU3iL8ctGwSaGUjSEkdSLAKxFcCMAmUSc44IqsgTHbIyNsNOAOibUNwGzybgtBTsLNp8P52oPcA+LE9oLEefnHj1EO33377rkUr70k91mZfm+KszAZTJUaJTMEliDggti6vzN59d2PR4JgEkDt+qcpu+p7/kmVN2a7D0bb7F369ocTdVFimv79f2bBhw6TXX3+9cc+ePROSp8YGASQFkF0gihtQPCCeACC7crMtDnAOITigpwAtBaElAVMDbAuhUGi4qampY+nSpR2rV6/uKKmeZK/emrql35QaqOJSVEagMkChACMAJQAXAoSL/llBunTdHBw4jgCy6ide5qk4GFx4bQ2RGIY2PfZ+4vlvP+LxeE4Zbu7cudO/devWitbW1opDhw5VhsPhsuHh4WJd18/t9ZCDqqpaKBSK19fX9zc2Ng7Mnz+/b9myZf0XX3xxKl9m81G95ns79S9birfIJTOoDHAxwE0BhQEyHdXvnRhH9NwxjUwfIYAQEOmuX7b55y+b4Sqvx9BbG6E/uQZBv6/9iSee2LJy5cruM614JBKRW1tbA+3t7b6jR4/6M5mMnMlkJF3XpWw2KxuGIQGAy+WyVFU13W63paqq5fV6jalTpyamTJmSbGpqSpaUlIyrPHEA39gWX/KnPno5UYtUOdfiKgNc+c8CLyDIa54CKiP3jRDA7t7wsLtu+rf9sy+XzEQUQz+9Hbz19yMPmjJlSnjVqlU7HnrooQMXKt4/U2Qszq5+NXZr2PI0EJfKGHFaWqaO8QoF3AUESLlukNc9uRBbiBAC5Lqfudikkr6SRdcXM68fwy2bTO3xL8vg1kkPDQQCyUsvvfTADTfccODOO+/s9Hg8fxUyDgyZvs/9d2xNWg0GmSSB5oxjcAhQcq6vUEDNdwPieIHASLB3mAghIK155ga1YcYmf9MVFAIYeP4HMXvT94tPVwmXy2VMmjSpe/bs2eHLL7+86+qrr+5tampKne66swXnHLt27Qr8rKVj7hueBYtpWYNMCAXJuXaeBCl3FJLgooCU8wLkCOC2OOYQcNeGF/zzrlypVk2B4DYi/3ZPr711/QTlpuPhcrn08vLyaHV1dbSmpma4tLQ0U1ZWlq6vr0+VlZVpZWVlOgBUVVVpjDEBALqu00gk4gKA/v5+ta+vz93d3e2NRCLegYEBb09PT7Cnp6ckMjhYIn/2Adnz6bshV04eeSYBTklC3iPkgnGAAxBc7JAAgAu7niqOXkAIAXylZx3t6LruCofD1eFwuPps7zEWiLsIRfe/CLVpGZjn5PmYEACII9oAzoopAICPLhraIkdArlx2sH+nM88XGOCGlnsShdK4oCireABjXPnuE4V88TJ4V/0E7ilNAD1ZEhSFX8iokJMnQfCcqkVzHiIEUtH+rNFz5FcUAIiw3jYi3SODmX/hdbL8lR8D6qlnvhcaNFSDogd/i8D9G+GeNm9M409E3vi8lFe42KPbgG7aiPaGRSrS/9aRhxb9j9MFDP05rbf9Ee/UOX7m9YPKCkKfvRuJyskwtj0Pe9fLgKmf5tHnDzRQAffN/xuuphVw1TQCE4wscw4w0h3yZIx8TyehDfYIYRk7miXvzV1CiNF5wJ3//oSrquFvA5csUQrVHysVR+aj92AcfA/2X14D7/7ImYqebzAZ0vQFcH/mG5CnNEOpmgzCzl6FKhwYhZ6BGRuElRxKM0l5ZmnNhw++eMstNlAQC5AvvcSoL7lbbWic6Z+1UDpRAhOcw4wNQOv8EHb/EdhdbeBHdoH3HoTIxADTwBkph7IK6i+FNOMKKJd+Hqx8MpSaRkhFQafm5wpuwU6nYCUGYA31QcT698mV9ddFv7Wwq7DY8bHAfT9zsYxvixQsm1c0+1Oq7C8ZtzKC27BSMViJIVjRbvBUDEJPQ8T6wbMJIJsAuAmYJoiiOkGO2w8arAQLVIB5/GChKkj+ElDVM+YzzghCOEJINgk7GYc51A0M9UB/79dgh97t0BLDTUKIk5IbTo4GCQi989nvESY96Klt9Kv1MyEVBc64VYRtjXZGAERiI9/PGUJAWCa4oYHrGViZJOzYALiWhN25F9aeP8A6/AGgp1FZWRm57777bvrOd77z7li3Gl8Su/XpUuJmz8oSu1Yqr5fVmqmQfEFQt++Tk7uEgLAM8JyxwjRgaynYqTh4Jg6ejoMf2wv7QAvsY3shUtGRBQxJkqwbb7yxZf369dsDgcAvcTaKEAC83z74lXW/efsfth1JzLNkVZZL6yCHKiB5/aCKG0RRQCXl7GVzwcEt01F6LAPCNEZEUlvLQOhpRwTJJsD7PobduRf20d0Q0fCYg7HL5dKvuOKKfWvXrv3zkiVL8gLoxgkR8OpBFL06aH4xYfFFwgaRCN+/bp6SmFHMJnEAW3cfKln3zO+u2DtoN2a8pR7mDYLlFlCo4gZV1JzEJQFk9J1NKANETtjgHILbjgubOoRlOq2cTUGYGoSehRg8Bh7pAO9qA+8/DJEYBKzxX8OMMXvKlCnha6+9dt93v/vd/RUVFUbh+Ydf37dl7autH4lf3DYwLgH/tNNaEdbIRg5aARAnZrY5bNvS3LBSt02T/nh9ndJOqTPURyIR+akNG6f9Ydv/zDgYzdbFiTcg/BUUvpAjbUkSiORy1GTVBxgZR/M3ss5gmYwCiQHwxAAw3AORikJkk86awGkgy7JVWVkZmTVr1rEVK1a0r169urOsrGzMCxOJBCu///m/l2pmUn2490fmv6380UkEPLwH89qSYhsI8ZHcpMHOZY2Y+SQJ3eRF0AYeWeD57SUl7KSEKMMwyLZt20ItLS2V+/fvL+/r6wtEo9GiWCxWFIvFijRNO6MFQlVVtUAgkCwuLk6WlJQkKysr43PmzBlYvHhx/1VXXRVVFOW079xt27YF77jjjhuP1i2tK733CaQOtRp69+Efmb/46vdHCNiyRUhPMtEGSqazglDRFqPpMUYue8TgAlzL6MvKxfZ/WehryXvDRBCNRuVkMsl6e3tV27ZJb2+vKoQghBABONEhANTW1mYDgYAVDAZPFiMmiK6uLtcDDzxw+csvv7zYsiyJVM9EaO0fQT1+JD/6QNOGwleKJ9fsBABy31/E8p60eIMSZ2zPz6OPa/0cCXo+Y8QyRalIdm36TPHGMpUap67OJ4fNmzeXP/7445e9++67TYZhjOqRkgL3gy8bxQuvU/TeTsT3vdtpV3ZMFevWcaknzW+xOKWMADYcAvL5AXnDzVzKTD5/0KYy6bKL6xa9FPnmIws8v/7SRUXhv4bBqVSKvfTSSzWbNm26aMeOHTMGBwdDYxa0DJi9HVkAihyqhKusri5zzFwEoEXSbDJbCMAqcP9CAvKekM8ky3cPTij0ogrPfe+G1zz4f5+NNw+8s6957tzeuXPnRpcsWRI9FxceC729vUpLS0tJa2tr6e7du6sOHDhQGw6Hqy3LmlDKDO8/PCwsK0BdKpSyGqb3Hf06gBbJsGHayGeNjLq/JU423OKjwkI+ZUYqrYO99K7AO3unXvHaj1ZC6GkAEMXFxYmSkpJ4IBBIhUKhdDAYTJeVlWUkSeKBQEBnjHGPx2MJIZDNZiXTNGkymXQZhkGj0ah3aGjIOzg46Esmk97BwcHiRCJxbrF5eijLLR1MkiB5/SCUNgGA1BM+eiBQWf+/CKUj/b8wSaowX6gwTaYwX4ioXnguvQ70hy1Irr8H1qEdJBaLBWKx2FkumJx/EH+Fl+ZXsSmDECIAANSrZR/rP9qZyZiWkySZO47LEj1NvpDI3VSdOhfBb22C9+4nT790/UmCSpAmN5eNhNdcQAgMAwDd8bWZH8M0Hol0tpvpdAaaPdrvTYHj8oUKM8aAsXOFpFAVij59J4p/2ALXp24CyF95PwVlkD73EAKXf86d/8uMDQCCvwHkJkIEIDVPHPihqRv/oATL3HKwApzQcdPjJvry59kUtPbdyL7yKIzdr2OsdYYLBkJBJ8+HvPzr8C+5GZLX79RJy2D4gzfSRqKrUTz7jZ7jYoHqn7VdqWn680Rx1cr+UiL5QwCTztjwE8HTSWjhNph73oD25nrwaNc53O0UIBQkUAF68XJIc66Gd84SuCoaRqJwwTnSh/eIzMetz1nP3HE7MJYe8NJLzPvbtl+RqQtWskAlpEAJmK8YzOM7Z3cW3IY52AOztx3mx+/D3PUa7PB+JwYQZ7jARIgTcxRXgjbMBWuYB1Y7E676WVCqJoG5jhdZBLeR6WxDpm3nHqvj2KViyzprTAKcexMJhPyJNcxd6lq6BrRhjpMg5S0G8/lBVS+opJyTdCWEAM+kYA52wY5HYMcj4AMd4MO9EIkBCC3piCpMdrRB1QviCYIUl4MGa0C9QdCiIOTSOsiBElC3b9xn2ekE0u17La374+12V+oa8d9/PxJanipHyAPgOQA3QVLAJjdDvuwLYJPmgrr9IO4iMG+Rk/Ehu0FVtxP2niOE4EAuEwSCj0jhhNJcis0ESRcCdiYJbeAYMh0fxrmR/TZff8dTJ+YJnVYQIYSsBPBjAPW5P0ACFWBTF0KatQS0eoaT8uL15xKkfKCKAiK7QBUnL+h8EDMh5HKF7FQCxmAXtN4jKW7ov7SNoe+J/7h/zKTECe0bJIS4ANwE4GsAlpxwFsQTAK2cBjb1MrD6JpDSOhBZBfUUOQQobjBFBZFlRzSRFCcVRpLPWl4TtgVh6uBmXhtMw4pHYUZ7bSsxOAjG/tXKsKfEc7eNvcvrTAg47gJCZsHZOHk1gMvgrEifWAhQi0BDtaC1s8FqZgLlk0F9Icd41QOqeBz1iMlO4iWljqdQCkJobsDlEPnFPsEhbBvCNiFsK2e0BjsZhZ2JWTw51EVMc4OllK8XG1ZNOJnjXLfOBgEsx/FbZ8fcvORcQAGXB8QbclJbS+tAgtUg/jJALQJxBwDFfXw/5zwnpwlAz4Cnh00Y2pBIDhwUmdhb3Fv5IgILPxYv3mKP+9xT2XABNk9XA5gDoDZ3VOeOCjibpRlGN08HgZFN0zaABAALhAwDGAAhXeDoA0gYsLsA7BFCnKTrnQv+H10/3LLabVHFAAAAAElFTkSuQmCC',  # noqa E501
        "search": "Search",
        # fmt: on
        # Markers
        # ----------------------------------------
        "unsaved_column_header": "💾",
        "unsaved_column_width": 3,
        "marker_unsaved": "✱",
        "marker_required": "✱",
        "marker_required_color": "red2",
        "placeholder_color": "grey",
        # Sorting icons
        # ----------------------------------------
        "marker_sort_asc": "▼",
        "marker_sort_desc": "▲",
        # GUI settings
        # ----------------------------------------
        "popup_info_auto_close_seconds": 1.5,
        "popup_info_alpha_channel": 0.85,
        "info_element_auto_erase_seconds": 5,
        "live_update_typing_delay_seconds": 0.3,
        # Default sizes for elements
        # ---------------------------
        # Label Size
        # Sets the default label (text) size when `field()` is used.
        # A label is static text that is displayed near the element to describe it.
        "default_label_size": (15, 1),  # (width, height)
        # Element Size
        # Sets the default element size when `field()` is used.
        # The size= parameter of `field()` will override this.
        "default_element_size": (30, 1),  # (width, height)
        # Mline size
        # Sets the default multi-line text size when `field()` is used.
        # The size= parameter of `field()` will override this.
        "default_mline_size": (30, 7),  # (width, height)
        # CellEdit widgets:
        "use_cell_buttons": True,
        # Default minimum sizes for
        "text_min_width": 80,
        "combobox_min_width": 80,
        "checkbox_min_width": 75,
        "datepicker_min_width": 80,
        # Display python_type `bool` columns as checkboxes in sg.Tables
        "display_bool_as_checkbox": True,
        "checkbox_true": "☑",
        "checkbox_false": "☐",
        # invalid input animation
        "validate_exception_animation": lambda widget: shake_widget(widget),
    }
    """Default Themepack."""

    def __init__(self, tp_dict: Dict[str, str] = None) -> None:
        self.tp_dict = tp_dict or ThemePack.default

    def __getattr__(self, key):
        # Try to get the key from the internal tp_dict first.
        # If it fails, then check the default dict.
        try:
            return self.tp_dict[key]
        except KeyError:
            try:
                return ThemePack.default[key]
            except KeyError as e:
                raise AttributeError(
                    f"ThemePack object has no attribute '{key}'"
                ) from e

    def __call__(self, tp_dict: Dict[str, str] = None) -> None:
        """Update the ThemePack object from tp_dict.

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
                'marker_unsaved' : string eg '', f'',  unicode
                'marker_required' : string eg '', f'',  unicode
                'marker_required_color': string eg 'red', Tuple eg (255,0,0)
                'marker_sort_asc': string eg '', f'',  unicode
                'marker_sort_desc': string eg '', f'',  unicode
            }
        For Base64, you can convert a whole folder using https://github.com/PySimpleGUI/PySimpleGUI-Base64-Encoder # fmt: skip
        Remember to us b'' around the string.

        Args:
            tp_dict: (optional) A dict formatted as above to create the ThemePack from.
                If one is not supplied, a default ThemePack will be generated.  Any keys
                not present in the supplied tp_dict will be generated from the default
                values.  Additionally, tp_dict may contain additional keys not specified
                in the minimal default ThemePack.

        Returns:
            None
        """  # noqa: E501
        # For default use cases, load the default directly to avoid the overhead
        # of __getattr__() going through 2 key reads
        self.tp_dict = tp_dict or ThemePack.default


# set a default themepack
themepack = ThemePack()


# ======================================================================================
# LANGUAGEPACKS
# ======================================================================================
# Change the language text used throughout the program.
class LanguagePack:

    """LanguagePacks are user-definable collections of strings that allow for
    localization of strings and messages presented to the end user.

    Creating your own is easy as well! In fact, a LanguagePack can be as simple as one
    line if you just want to change one aspect of the default LanguagePack. Example: # I
    want the save popup to display this text in English in all caps     lp_en =
    {'save_success': 'SAVED!'}
    """

    default: ClassVar[Dict[Any]] = {
        # ------------------------------------------------------------------------------
        # Buttons
        # ------------------------------------------------------------------------------
        "button_cancel": " Cancel ",
        "button_ok": "  OK  ",
        "button_yes": " Yes ",
        "button_no": "  No  ",
        # ------------------------------------------------------------------------------
        # General
        # ------------------------------------------------------------------------------
        # ------------------------------------------------------------------------------
        # Prepopulate record values/prepends
        # ------------------------------------------------------------------------------
        # Text, Varchar, Char, Null Default, used exclusively for description_column
        "description_column_str_null_default": "New Record",
        # Placeholder automatically added to Input/Multiline
        # that represent Not-Null fields.
        "notnull_placeholder": "*Required",
        "search_placeholder": "🔍 Search...",
        "combo_placeholder": "Please select one:",
        # Prepended to parent description_column
        "duplicate_prepend": "Copy of ",
        # ------------------------------------------------------------------------------
        # Startup progress bar
        # ------------------------------------------------------------------------------
        "startup_form": "Creating Form",
        "startup_init": "Initializing",
        "startup_datasets": "Adding datasets",
        "startup_relationships": "Adding relationships",
        "startup_binding": "Binding window to Form",
        # ------------------------------------------------------------------------------
        # Progress bar displayed during SQLDriver operations
        # ------------------------------------------------------------------------------
        "SQLDriver_init": "{name} connection",
        "SQLDriver_connecting": "Connecting to database",
        "SQLDriver_execute": "Executing SQL commands",
        "SQLDriver_file_not_found_title": "Trouble finding db file",
        "SQLDriver_file_not_found": "Could not find file\n{file}",
        # ------------------------------------------------------------------------------
        # Default ProgressAnimate Phrases
        # ------------------------------------------------------------------------------
        "animate_phrases": [
            "Please wait...",
            "Still working...",
        ],
        # ------------------------------------------------------------------------------
        # Info Popups - no buttons
        # ------------------------------------------------------------------------------
        # Info Popup Title - universal
        "info_popup_title": "Info",
        # Form save_records
        "form_save_success": "Updates saved successfully.",
        "form_save_none": "There were no updates to save.",
        # DataSet save_record
        "dataset_save_empty": "There were no updates to save.",
        "dataset_save_none": "There were no changes to save!",
        "dataset_save_success": "Updates saved successfully.",
        # ------------------------------------------------------------------------------
        # Yes/No Popups
        # ------------------------------------------------------------------------------
        # Form prompt_save
        "form_prompt_save_title": "Unsaved Changes",
        "form_prompt_save": "You have unsaved changes!\nWould you like to save them first?",  # fmt: skip # noqa: E501
        # DataSet prompt_save
        "dataset_prompt_save_title": "Unsaved Changes",
        "dataset_prompt_save": "You have unsaved changes!\nWould you like to save them first?",  # fmt: skip # noqa: E501
        # Form save_records
        "form_save_problem_title": "Problem Saving",
        "form_save_partial": "Some updates were saved successfully;",
        "form_save_problem": "There was a problem saving updates to the following tables:\n{tables}.",  # fmt: skip # noqa: E501
        # DataSet save_record
        "dataset_save_callback_false_title": "Callback Prevented Save",
        "dataset_save_callback_false": "Updates not saved.",
        "dataset_save_keyed_fail_title": "Problem Saving",
        "dataset_save_keyed_fail": "Query failed: {exception}.",
        "dataset_save_fail_title": "Problem Saving",
        "dataset_save_fail": "Query failed: {exception}.",
        # DataSet search
        "dataset_search_failed_title": "Search Failed",
        "dataset_search_failed": "Failed to find:\n{search_string}",
        # ------------------------------------------------------------------------------
        # Delete
        # ------------------------------------------------------------------------------
        # DataSet delete_record
        "delete_title": "Confirm Deletion",
        "delete_cascade": "Are you sure you want to delete this record?\nKeep in mind that child records:\n({children})\nwill also be deleted!",  # fmt: skip # noqa: E501
        "delete_single": "Are you sure you want to delete this record?",
        # Failed Ok Popup
        "delete_failed_title": "Problem Deleting",
        "delete_failed": "Query failed: {exception}.",
        "delete_recursion_limit_error": "Delete Cascade reached max recursion limit.\nDELETE_CASCADE_RECURSION_LIMIT",  # fmt: skip # noqa: E501
        # ------------------------------------------------------------------------------
        # Duplicate
        # ------------------------------------------------------------------------------
        # Popup when record has children
        "duplicate_child_title": "Confirm Duplication",
        "duplicate_child": "This record has child records:\n(in {children})\nWhich records would you like to duplicate?",  # fmt: skip # noqa: E501
        "duplicate_child_button_dupparent": "Only duplicate this record.",
        "duplicate_child_button_dupboth": "++ Duplicate this record and its children.",
        # Popup when record is single
        "duplicate_single_title": "Confirm Duplication",
        "duplicate_single": "Are you sure you want to duplicate this record?",
        # Failed Ok Popup
        "duplicate_failed_title": "Problem Duplicating",
        "duplicate_failed": "Query failed: {exception}.",
        # ------------------------------------------------------------------------------
        # General OK poups
        # ------------------------------------------------------------------------------
        "error_title": "Error",
        # ------------------------------------------------------------------------------
        # Quick Editor
        # ------------------------------------------------------------------------------
        "quick_edit_title": "Quick Edit - {data_key}",
        # ------------------------------------------------------------------------------
        # For Error when importing module for driver
        # ------------------------------------------------------------------------------
        "import_module_failed_title": "Problem importing module",
        "import_module_failed": "Unable to import module neccessary for {name}\nException: {exception}\n\nTry `pip install {requires}`",  # fmt: skip # noqa: E501
        # ------------------------------------------------------------------------------
        # Overwrite file prompt
        # ------------------------------------------------------------------------------
        "overwrite_title": "Overwrite file?",
        "overwrite": "File exists, type YES to overwrite",
        "overwrite_prompt": "YES",
        # ------------------------------------------------------------------------------
        # Validate Msgs
        # ------------------------------------------------------------------------------
        "dataset_save_validate_error_title": "Error: Invalid Input(s)",
        "dataset_save_validate_error_header": "The following fields(s) have issues:\n",
        "dataset_save_validate_error_field": "{field}: ",
        ValidateRule.REQUIRED: "Field is required",
        ValidateRule.PYTHON_TYPE: "{value} could not be cast to correct type, {rule}",
        ValidateRule.PRECISION: "{value} exceeds max precision length, {rule}",
        ValidateRule.MIN_VALUE: "{value} less than minimum value, {rule}",
        ValidateRule.MAX_VALUE: "{value} more than max value, {rule}",
        ValidateRule.MIN_LENGTH: "{value} less than minimum length, {rule}",
        ValidateRule.MAX_LENGTH: "{value} more than max length, {rule}",
        ValidateRule.CUSTOM: "{value}{rule}",
    }
    """Default LanguagePack."""

    def __init__(self, lp_dict=None) -> None:
        self.lp_dict = lp_dict or type(self).default

    def __getattr__(self, key):
        # Try to get the key from the internal lp_dict first.
        # If it fails, then check the default dict.
        try:
            return self.lp_dict[key]
        except KeyError:
            try:
                return type(self).default[key]
            except KeyError as e:
                raise AttributeError(
                    f"LanguagePack object has no attribute '{key}'"
                ) from e

    def __getitem__(self, key):
        try:
            return self.lp_dict[key]
        except KeyError:
            try:
                return type(self).default[key]
            except KeyError as e:
                raise AttributeError(
                    f"LanguagePack object has no attribute '{key}'"
                ) from e

    def __call__(self, lp_dict=None) -> None:
        """Update the LanguagePack instance."""
        # For default use cases, load the default directly to avoid the overhead
        # of __getattr__() going through 2 key reads
        self.lp_dict = lp_dict or type(self).default


# set a default languagepack
lang = LanguagePack()


class LangFormat(dict):

    """This is a convenience class used by LanguagePack format_map calls, allowing users
    to not include expected variables.

    Note: This is typically not used by the end user.
    """

    def __missing__(self, key):
        return None


# ======================================================================================
# ABSTRACTION LAYERS
# ======================================================================================
# Database abstraction layers for a uniform API
# --------------------------------------------------------------------------------------


# This is a dummy class for documenting convenience functions
class Abstractions:

    """Supporting multiple databases in your application can quickly become very
    complicated and unmanageable. pysimplesql abstracts all of this complexity and
    presents a unified API via abstracting the main concepts of database programming.
    See the following documentation for a better understanding of how this is
    accomplished. `Column`, `ColumnInfo`, `SQLDriver`, `Sqlite`, `Mysql`, `Postgres`.

    Note: This is a dummy class that exists purely to enhance documentation and has no
    use to the end user.
    """


T = TypeVar("T")


# ======================================================================================
# COLUMN ABSTRACTION
# ======================================================================================
# The column abstraction hides the complexity of dealing with SQL columns, getting their
# names, default values, data types, primary key status and notnull status
# --------------------------------------------------------------------------------------
@dc.dataclass
class Column:

    """The `Column` class is a generic column class.  It holds a dict containing the
    column name, type  whether the column is notnull, whether the column is a primary
    key and the default value, if any. `Column`s are typically stored in a `ColumnInfo`
    collection. There are multiple ways to get information from a `Column`, including
    subscript notation, and via properties. The available column info via these methods
    are name, domain, notnull, default and pk See example:

    .. literalinclude:: ../doc_examples/Column.1.py
        :language: python
        :caption: Example code
    """

    name: str
    domain: str
    notnull: bool
    default: Any
    pk: bool
    virtual: bool = False
    generated: bool = False
    python_type: Type[T] = object
    custom_cast_fn: callable = None
    custom_validate_fn: callable = None
    cell_format_fn: callable = None
    domain_args: List[str, int] = None

    def __getitem__(self, key):
        return self.__dict__[key]

    def __setitem__(self, key, value) -> None:
        self.__dict__[key] = value

    def __contains__(self, item) -> bool:
        return item in self.__dict__

    def cast(self, value: Any) -> Any:
        """Cast a value to the appropriate data type as defined by the column info for
        the column. This can be useful for comparing values between the database and the
        GUI.

        :param value: The value you would like to cast
        :returns: The value, cast to a type as defined by the domain
        """
        if self.custom_cast_fn:
            try:
                return self.custom_cast_fn(value)
            except Exception as e:  # noqa: BLE001
                logger.debug(f"Error running custom_cast_fn, {e}")
        return str(value)

    def validate(self, value: Any) -> bool:
        """TODO"""
        value = self.cast(value)

        if self.notnull and value in EMPTY:
            return ValidateResponse(ValidateRule.REQUIRED, value, self.notnull)

        if value in EMPTY:
            return ValidateResponse()

        if self.custom_validate_fn:
            try:
                response = self.custom_validate_fn(value)
                if response.exception:
                    return response
            except Exception as e:  # noqa: BLE001
                logger.debug(f"Error running custom_validate_fn, {e}")

        if not isinstance(value, self.python_type):
            return ValidateResponse(
                ValidateRule.PYTHON_TYPE, value, self.python_type.__name__
            )

        return ValidateResponse()


@dc.dataclass
class MinMaxCol(Column):
    """Base ColumnClass for columns with minimum and maximum constraints.

    This class extends the functionality of the base `Column` class to include optional
    validation based on minimum and maximum values.

    Args:
        min_value (Any valid value type compatible with the column's data type.): The
            minimum allowed value for the column (inclusive). Defaults to None,
            indicating no minimum constraint.
        max_value (Any valid value type compatible with the column's data type.): The
            maximum allowed value for the column (inclusive). Defaults to None,
            indicating no maximum constraint.
    """

    min_value: Any = None
    max_value: Any = None

    def validate(self, value):
        response = super().validate(value)
        if response.exception:
            return response

        value = self.cast(value)

        if self.min_value is not None and value < self.min_value:
            return ValidateResponse(ValidateRule.MIN_VALUE, value, self.min_value)

        if self.max_value is not None and value > self.max_value:
            return ValidateResponse(ValidateRule.MAX_VALUE, value, self.max_value)

        return ValidateResponse()


@dc.dataclass
class LengthCol(Column):
    """Base ColumnClass for length-constrained columns.

    This class represents a column with length constraints. It inherits from the base
    `Column` class and adds attributes to store the maximum and minimum length values.
    The `validate` method is overridden to include length validations.

    Args:
        max_length: Maximum length allowed for the column value.
        min_length: Minimum length allowed for the column value.
    """

    min_length: int = None
    max_length: int = None

    def __post_init__(self) -> None:
        if self.domain_args and self.max_length is None:
            self.max_length = (
                int(self.domain_args[0]) if self.domain_args[0] is not None else None
            )

    def cast(self, value):
        if value in EMPTY:
            return ""
        return super().cast(value)

    def validate(self, value):
        response = super().validate(value)
        if response.exception:
            return response

        if self.min_length is not None and len(str(value)) < self.min_length:
            return ValidateResponse(ValidateRule.MIN_LENGTH, value, self.min_length)

        if self.max_length is not None and len(str(value)) > self.max_length:
            return ValidateResponse(ValidateRule.MAX_LENGTH, value, self.max_length)

        return ValidateResponse()


@dc.dataclass
class LocaleCol(Column):
    """Base ColumnClass that provides Locale functions.

    Args:
        negative_symbol: The symbol representing negative values in the locale.
        currency_symbol: The symbol representing the currency in the locale.

    Example:
        col = LocaleCol()
        normalized_value = col.strip_locale("$1,000.50")
    """

    negative_symbol: str = locale.localeconv()["negative_sign"]
    currency_symbol: str = locale.localeconv()["currency_symbol"]

    def strip_locale(self, value):
        if value == self.negative_symbol:
            return "0"
        value = str(value)
        if value == self.currency_symbol:
            return "0"
        if self.currency_symbol in value:
            value = value.replace(self.currency_symbol, "")
        return locale.delocalize(value)


@dc.dataclass
class BoolCol(Column):
    python_type: Type[bool] = dc.field(default=bool, init=False)

    def __post_init__(self) -> None:
        if themepack.display_bool_as_checkbox:
            self.cell_format_fn: callable = CellFormatFn.bool_to_checkbox

    def cast(self, value):
        return checkbox_to_bool(value)


@dc.dataclass
class DateCol(MinMaxCol):
    date_format: str = DATE_FORMAT
    python_type: Type[dt.date] = dc.field(default=dt.date, init=False)

    def cast(self, value):
        if isinstance(value, self.python_type):
            return value
        try:
            return dt.datetime.strptime(value, self.date_format).date()
        except (TypeError, ValueError) as e:
            # Value contains seconds, remove them and try parsing again
            if len(value.split(":")) > 2:
                value_without_seconds = ":".join(value.split(":")[:2])
                try:
                    return dt.datetime.strptime(
                        value_without_seconds, self.date_format
                    ).date()
                except ValueError:
                    pass

            # try to match partial date
            if value.endswith("-"):
                value = value.rstrip("-")
            sections = re.split(r"(%[^%])", self.date_format)
            partial_formats = [
                "".join(sections[: i + 1])
                for i in range(len(sections))
                if sections[i].startswith("%")
            ]
            for format_str in partial_formats:
                try:
                    return dt.datetime.strptime(value, format_str).date()
                except (TypeError, ValueError):
                    pass
            logger.debug(
                f"Unable to cast {value} to a datetime.date object. "
                f"Casting to string instead. "
                f"{e=}"
            )
            # else, cast to str
            return super().cast(value)


@dc.dataclass
class DateTimeCol(MinMaxCol):
    datetime_format_list: List[str] = dc.field(
        default_factory=lambda: [
            DATETIME_FORMAT,
            DATETIME_FORMAT_MICROSECOND,
            TIMESTAMP_FORMAT,
            TIMESTAMP_FORMAT_MICROSECOND,
        ]
    )
    python_type: Type[dt.datetime] = dc.field(default=dt.datetime, init=False)

    def cast(self, value):
        if isinstance(value, self.python_type):
            return value
        for datetime_format in self.datetime_format_list:
            try:
                return dt.datetime.strptime(value, datetime_format)
            except ValueError:
                pass
        logger.debug(
            "Unable to cast datetime/time/timestamp. Casting to string instead."
        )
        return super().cast(value)


@dc.dataclass
class DecimalCol(LocaleCol, MinMaxCol):
    precision: int = DECIMAL_PRECISION
    scale: int = DECIMAL_SCALE
    python_type: Type[Decimal] = dc.field(default=Decimal, init=False)

    def __post_init__(self) -> None:
        if self.domain_args:
            try:
                self.precision = (
                    int(self.domain_args[0])
                    if self.domain_args[0] is not None
                    else None
                )
            except ValueError:
                logger.debug(
                    f"Unable to set {self.NAME} column decimal precision to "
                    f"{self.domain_args[0]}"
                )
        if len(self.domain_args) >= 2:
            try:
                self.scale = (
                    int(self.domain_args[1])
                    if self.domain_args[1] is not None
                    else None
                )
            except ValueError:
                logger.debug(
                    f"Unable to set {self.NAME} column decimal scale to "
                    f"{self.domain_args[1]}"
                )
            self.cell_format_fn: callable = lambda x: CellFormatFn.decimal_places(
                x, self.scale
            )

    def cast(self, value):
        value = self.strip_locale(value)
        try:
            decimal_value = Decimal(value)
            return decimal_value.quantize(Decimal("0." + "0" * self.scale))
        except (DecimalException, TypeError):
            return super().cast(value)

    def validate(self, value):
        response = super().validate(value)
        if response.exception:
            return response

        value = self.cast(value)

        if isinstance(value, str) and value in EMPTY:
            return ValidateResponse()

        value_precision = len(value.as_tuple().digits)
        if self.precision is not None and value_precision > self.precision:
            return ValidateResponse(ValidateRule.PRECISION, value, self.precision)

        return ValidateResponse()


@dc.dataclass
class FloatCol(LocaleCol, LengthCol, MinMaxCol):
    python_type: Type[float] = dc.field(default=float, init=False)

    def cast(self, value):
        value = self.strip_locale(value)
        try:
            return float(value)
        except ValueError:
            return super().cast(value)


@dc.dataclass
class IntCol(LocaleCol, LengthCol, MinMaxCol):
    truncate_decimals: bool = False
    python_type: Type[int] = dc.field(default=int, init=False)

    def cast(self, value, truncate_decimals: bool = None):
        truncate_decimals = (
            truncate_decimals
            if truncate_decimals is not None
            else self.truncate_decimals
        )
        value_backup = value
        if isinstance(value, int):
            return value
        if isinstance(value, _ElementRow):
            return int(value)
        try:
            value = self.strip_locale(value)
            if type(value) is str:
                value = float(value)
            if type(value) is float:
                int_value = int(value)
                if value == int_value or self.truncate_decimals:
                    return int_value
                return str(value_backup)
        except (ValueError, TypeError):
            return super().cast(value_backup)


@dc.dataclass
class StrCol(LengthCol):
    python_type: Type[str] = dc.field(default=str, init=False)

    def cast(self, value):
        return super().cast(value)


@dc.dataclass
class TimeCol(MinMaxCol):
    time_format: str = TIME_FORMAT
    python_type: Type[dt.time] = dc.field(default=dt.time, init=False)

    def cast(self, value):
        if isinstance(value, self.python_type):
            return value
        try:
            return dt.datetime.strptime(value, self.time_format).time()
        except (TypeError, ValueError) as e:
            logger.debug(
                f"Unable to cast {value} to a datetime.time object. "
                f"Casting to string instead. "
                f"{e=}"
            )
            return super().cast(value)


class ColumnInfo(List):

    """Column Information Class.

    The `ColumnInfo` class is a custom container that behaves like a List containing a
    collection of `Columns`. This class is responsible for maintaining information about
    all the columns (`Column`) in a table. While the individual `Column` elements of
    this collection contain information such as default values, primary key status, SQL
    data type, column name, and the notnull status - this class ties them all together
    into a collection and adds functionality to set default values for null columns and
    retrieve a dict representing a table row with all defaults already assigned.
    See example below:
    .. literalinclude:: ../doc_examples/ColumnInfo.1.py
        :language: python
        :caption: Example code
    """

    # List of required SQL types to check against when user sets custom values
    _python_types: ClassVar[List[str]] = [
        "str",
        "int",
        "float",
        "Decimal",
        "bool",
        "time",
        "date",
        "datetime",
    ]

    def __init__(self, driver: SQLDriver, table: str) -> None:
        self.driver = driver
        self.table = table

        # Defaults to use for Null values returned from the database. These can be
        # overwritten by the user and support function calls as well by using
        # ColumnInfo.set_null_default() and ColumnInfo.set_null_defaults()
        self.null_defaults = {
            "str": lang.description_column_str_null_default,
            "int": 0,
            "float": 0.0,
            "Decimal": Decimal(0),
            "bool": 0,
            "time": lambda: dt.datetime.now().strftime(TIME_FORMAT),
            "date": lambda: dt.date.today().strftime(DATE_FORMAT),
            "datetime": lambda: dt.datetime.now().strftime(DATETIME_FORMAT),
        }
        super().__init__()

    def __contains__(self, item):
        if isinstance(item, str):
            return self._contains_key_value_pair("name", item)
        return super().__contains__(item)

    def __getitem__(self, item):
        if isinstance(item, str):
            return next((i for i in self if i.name == item), None)
        return super().__getitem__(item)

    @property
    def pk_column(self) -> Union[str, None]:
        """Get the pk_column for this colection of column_info.

        Returns:
            A string containing the column name of the PK column, or None if one was not
            found
        """
        for c in self:
            if c.pk:
                return c.name
        return None

    @property
    def names(self) -> List[str]:
        """Return a List of column names from the `Column`s in this collection.

        Returns:
            List of column names
        """
        return self._get_list("name")

    def col_name(self, idx: int) -> str:
        """Get the column name located at the specified index in this collection of
        `Column`s.

        Args:
            idx: The index of the column to get the name from

        Returns:
            The name of the column at the specified index
        """
        return self[idx].name

    def default_row_dict(self, dataset: DataSet) -> dict:
        """Return a dictionary of a table row with all defaults assigned.

        This is useful for inserting new records to prefill the GUI elements.

        Args:
            dataset: a pysimplesql DataSet object

        Returns:
            dict
        """
        d = {}
        for c in self:
            default = c.default
            python_type = c.python_type.__name__

            # First, check to see if the default might be a database function
            if self._looks_like_function(default):
                table = self.driver.quote_table(self.table)

                q = f"SELECT {default} AS val FROM {table};"

                rows = self.driver.execute(q)
                if rows.attrs["exception"] is None:
                    try:
                        default = rows.iloc[0]["val"]
                    except IndexError:
                        try:
                            default = rows.iloc[0]["VAL"]
                        except IndexError:
                            default = None
                    if default is not None:
                        d[c.name] = default
                        continue
                logger.warning(
                    "There was an exception getting the default: "
                    f"{rows.attrs['exception']}"
                )

            # The stored default is a literal value, lets try to use it:
            if default in [None, "None"]:
                try:
                    null_default = self.null_defaults[python_type]
                except KeyError:
                    # Perhaps our default dict does not yet support this datatype
                    null_default = None

                # return PK_PLACEHOLDER if this is a fk_relationships.
                # trick used in Combo for the pk to display placeholder
                rels = self.driver.relationships.get_rels_for(dataset.table)
                rel = next((r for r in rels if r.fk_column == c.name), None)
                if rel:
                    null_default = PK_PLACEHOLDER

                # skip primary keys
                if not c.pk:
                    # put default in description_column
                    if c.name == dataset.description_column:
                        default = null_default

                    # put defaults in other fields

                    #  don't put txt in other txt fields
                    elif c.python_type != str:
                        # If our default is callable, call it.
                        if callable(null_default):
                            default = null_default()
                        # Otherwise, assign it
                        else:
                            default = null_default
                    # string-like, not description_column
                    else:
                        default = ""
            else:
                # Load the default that was fetched from the database
                # during ColumnInfo creation
                if c.python_type == str:
                    # strip quotes from default strings as they seem to get passed with
                    # some database-stored defaults
                    # strip leading and trailing quotes
                    default = c.default.strip("\"'")

            d[c.name] = default
            logger.debug(
                f"Default fetched from database function. Default value is: {default}"
            )
        if dataset.transform is not None:
            dataset.transform(dataset, d, TFORM_DECODE)
        return d

    def set_null_default(self, python_type: str, value: object) -> None:
        """Set a Null default for a single python type.

        Args:
            python_type: This should be equal to what calling `.__name__` on the Column
                `python_type` would equal: 'str', 'int', 'float', 'Decimal', 'bool',
                'time', 'date', or 'datetime'.
            value: The new value to set the SQL type to. This can be a literal or even a
                callable

        Returns:
            None
        """
        if python_type not in self._python_types:
            RuntimeError(
                f"Unsupported SQL Type: {python_type}. Supported types are: "
                f"{self._python_types}"
            )

        self.null_defaults[python_type] = value

    def set_null_defaults(self, null_defaults: dict) -> None:
        """Set Null defaults for all python types.

        Supported types: 'str', 'int', 'float', 'Decimal', 'bool',
            'time', 'date', or 'datetime'.

        Args:
            null_defaults: A dict of python types and default values. This can be a
                literal or even a callable

        Returns:
            None
        """
        # Check if the null_defaults dict has all the required keys:
        if not all(key in null_defaults for key in self._python_types):
            RuntimeError(
                f"The supplied null_defaults dictionary does not havle all required SQL"
                f" types. Required: {self._python_types}"
            )

        self.null_defaults = null_defaults

    def get_virtual_names(self) -> List[str]:
        """Get a list of virtual column names.

        Returns:
            A List of column names that are virtual, or [] if none are present in this
            collections
        """
        return [c.name for c in self if c.virtual]

    def _contains_key_value_pair(self, key, value):  # used by __contains__
        return any(key in d and d[key] == value for d in self)

    # TODO: check if something looks like a statement for complex defaults?  Regex?
    def _looks_like_function(self, s: str):
        # check if the string is empty
        if s in EMPTY:
            return False

        # If string is in the driver's list of sql_constants
        # (like in MySQL CURRENT_TIMESTAMP)
        if s.upper() in self.driver.SQL_CONSTANTS:
            return True

        # Check if the string starts with a valid function name followed by parentheses
        pattern = r"^\w+\(.*\)$"
        return bool(re.match(pattern, s))

    def _get_list(self, key: str) -> List:
        # returns a list of any key in the underlying Column instances. For example,
        # column names, types, defaults, etc.
        return [d[key] for d in self]


# ======================================================================================
# DATABASE ABSTRACTION
# ======================================================================================
# The database abstraction hides the complexity of dealing with multiple databases. The
# concept relies on individual "drivers" that derive from the SQLDriver class, and
# return a pandas DataFrame populated with the data, along with attrs set for the
# lastrowid and exceptions passed from the driver.
# --------------------------------------------------------------------------------------
class Result:
    """This is a "dummy" Result object that is a convenience for constructing a
    DataFrame that has the expected attrs set."""

    @classmethod
    def set(
        cls,
        row_data: dict = None,
        lastrowid: int = None,
        exception: Exception = None,
        column_info: ColumnInfo = None,
        row_backup: pd.Series = None,
    ):
        """Create a pandas DataFrame with the row data and expected attrs set.

        Args:
            row_data: A list of dicts of row data
            lastrowid: The inserted row ID from the last INSERT statement
            exception: Exceptions passed back from the SQLDriver
            column_info: An optional ColumnInfo object
        """
        rows = pd.DataFrame(row_data)
        rows.attrs["lastrowid"] = lastrowid
        rows.attrs["exception"] = exception
        rows.attrs["column_info"] = column_info
        rows.attrs["row_backup"] = row_backup
        rows.attrs["virtual"] = []
        rows.attrs["sort_column"] = None
        rows.attrs["sort_reverse"] = None
        return rows


class ReservedKeywordError(Exception):
    pass


@dc.dataclass
class SqlChar:
    # Each database type expects their SQL prepared in a certain way.  Below are
    # defaults for how various elements in the SQL string should be quoted and
    # represented as placeholders. Override these in the derived class as needed to
    # satisfy SQL requirements

    # The placeholder for values in the query string.  This is typically '?' or'%s'
    placeholder: str = "%s"  # override this in derived subclass SqlChar

    # These are the quote characters for tables, columns and values.
    # It varies between different databases

    # override this in derived subclass SqlChar (defaults to no quotes)
    table_quote: str = ""
    # override this in derived subclass SqlChar (defaults to no quotes)
    column_quote: str = ""
    # override this in derived subclass SqlChar (defaults to single quotes)
    value_quote: str = "'"


@dc.dataclass
class SQLDriver(ABC):

    """Abstract SQLDriver class.  Derive from this class to create drivers that conform
    to PySimpleSQL.  This ensures that the same code will work the same way regardless
    of which database is used.  There are a few important things to note: The commented
    code below is broken into methods that **MUST** be implemented in the derived class,
    methods that.

    **SHOULD** be implemented in the derived class, and methods that **MAY** need to be
    implemented in the derived class for it to work as expected. Most derived drivers
    will at least partially work by implementing the **MUST** have methods.

    See the source code for `Sqlite`, `Mysql` and `Postgres` for examples of how to
    construct your own driver.

    NOTE: SQLDriver.execute() should return a pandas DataFrame.  Additionally, by
    pysimplesql convention, the attrs["lastrowid"] should always be None unless and
    INSERT query is executed with SQLDriver.execute() or a record is inserted with
    SQLDriver.insert_record()

    Args:
        update_cascade: (optional) Default:True. Requery and filter child table on
            selected parent primary key. (ON UPDATE CASCADE in SQL)
        delete_cascade: (optional) Default:True. Delete the dependent child records if
            the parent table record is deleted. (ON UPDATE DELETE in SQL)
    """

    host: str = None
    user: str = None
    password: str = None
    database: str = None

    sql_commands: str = None
    sql_script: str = None
    sql_script_encoding: str = "utf-8"

    update_cascade: bool = True
    delete_cascade: bool = True

    sql_char: dc.InitVar[SqlChar] = SqlChar()  # noqa RUF009

    # ---------------------------------------------------------------------
    # MUST implement
    # in order to function
    # ---------------------------------------------------------------------

    # ---------------------------------------------------------------------
    # ClassVars, replace in derived subclass with your own
    # ---------------------------------------------------------------------
    NAME: ClassVar[str] = "SQLDriver"
    REQUIRES: ClassVar[List[str]] = None

    # TODO: Document these
    COLUMN_CLASS_MAP: ClassVar[Dict[str, ColumnClass]] = {}
    SQL_CONSTANTS: ClassVar[List[str]] = []
    _CHECK_RESERVED_KEYWORDS: ClassVar[bool] = True

    def __post_init__(self, sql_char) -> None:
        # if derived subclass implements __init__, call `super()__post_init__()`
        # unpack quoting
        self.placeholder = sql_char.placeholder
        self.quote_table_char = sql_char.table_quote
        self.quote_column_char = sql_char.column_quote
        self.quote_value_char = sql_char.value_quote

        self.win_pb = ProgressBar(
            lang.SQLDriver_init.format_map(LangFormat(name=self.NAME)), 100
        )
        self.win_pb.update(lang.SQLDriver_connecting, 0)
        self._import_required_modules()
        self._init_db()
        self.relationships = RelationshipStore(self)
        self.auto_add_relationships()
        self.win_pb.close()

    @abstractmethod
    def _import_required_modules(self) -> None:
        pass

    @abstractmethod
    def _init_db(self) -> None:
        pass

    @abstractmethod
    def connect(self, *args, **kwargs):
        """Connect to a database.

        Connect to a database in the connect() method, assigning the connection to
        self.con.

        Implementation varies by database, you may need only one parameter, or several
        depending on how a connection is established with the target database.
        """

    @abstractmethod
    def execute(
        self,
        query,
        values=None,
        column_info: ColumnInfo = None,
        auto_commit_rollback: bool = False,
    ):
        """Implements the native SQL implementation's execute() command.

        Args:
            query: The query string to execute
            values: Values to pass into the query to replace the placeholders
            column_info: An optional ColumnInfo object
            auto_commit_rollback: Automatically commit or rollback depending on whether
                an exception was handled. Set to False by default. Set to True to have
                exceptions and commit/rollbacks happen automatically

        Returns:
        """

    @abstractmethod
    def execute_script(self, script: str, encoding: str):
        pass

    @abstractmethod
    def get_tables(self):
        pass

    @abstractmethod
    def column_info(self, table):
        pass

    @abstractmethod
    def pk_column(self, table):
        pass

    @abstractmethod
    def get_relationships(self):
        pass

    # ---------------------------------------------------------------------
    # SHOULD implement
    # based on specifics of the database
    # ---------------------------------------------------------------------
    # This is a generic way to estimate the next primary key to be generated.
    # This is not always a reliable way, as manual inserts which assign a
    # primary key value don't always update the sequencer for the given database.  This
    # is just a default way to "get things working", but the best bet is to override
    # this in the derived class and get the value right from the sequencer.
    def next_pk(self, table: str, pk_column: str) -> int:
        max_pk = self.max_pk(table, pk_column)
        if max_pk is not None:
            return max_pk + 1
        return 1

    def check_keyword(self, keyword: str, key: str = None) -> None:
        """Check keyword to see if it is a reserved word.  If it is raise a
        ReservedKeywordError. Checks to see if the database name is in keys and uses the
        database name for the key if it exists, otherwise defaults to 'common' in the
        RESERVED set. Override this with the specific key for the database if needed for
        best results.

        Args:
            keyword: the value to check against reserved words
            key: The key in the RESERVED set to check in

        Returns:
            None
        """
        if not self.check_reserved_keywords:
            return

        if key is None:
            # First try using the name of the driver
            key = self.NAME.lower() if self.NAME.lower() in RESERVED else "common"

        if keyword.upper() in RESERVED[key] or keyword.upper in RESERVED["common"]:
            raise ReservedKeywordError(
                f"`{keyword}` is a reserved keyword and cannot be used for table or "
                f"column names."
            )

    # ---------------------------------------------------------------------
    # MAY need to be implemented
    # These default implementations will likely work for most SQL databases.
    # Override any of the following methods as needed.
    # ---------------------------------------------------------------------
    @staticmethod
    def quote(val: str, chars: str):
        if not len(chars):
            return val
        left_quote = chars[0]
        right_quote = chars[1] if len(chars) == 2 else left_quote
        return f"{left_quote}{val}{right_quote}"

    def quote_table(self, table: str):
        return self.quote(table, self.quote_table_char)

    def quote_column(self, column: str):
        return self.quote(column, self.quote_column_char)

    def quote_value(self, value: str):
        return self.quote(value, self.quote_value_char)

    def commit(self) -> None:
        """TODO"""
        self.con.commit()

    def rollback(self) -> None:
        self.con.rollback()

    def close(self) -> None:
        self.con.close()

    def default_query(self, table) -> str:
        table = self.quote_table(table)
        return f"SELECT {table}.* FROM {table}"

    def default_order(self, description_column) -> str:
        description_column = self.quote_column(description_column)
        return f" ORDER BY {description_column} ASC"

    def relationship_to_join_clause(self, r_obj: Relationship) -> str:
        parent = self.quote_table(r_obj.parent_table)
        child = self.quote_table(r_obj.child_table)
        fk = self.quote_column(r_obj.fk_column)
        pk = self.quote_column(r_obj.pk_column)

        return f"{r_obj.join_type} {parent} ON {child}.{fk}={parent}.{pk}"

    def min_pk(self, table: str, pk_column: str) -> int:
        rows = self.execute(f"SELECT MIN({pk_column}) as min_pk FROM {table}")
        if rows.iloc[0]["min_pk"] is not None:
            return rows.iloc[0]["min_pk"].tolist()
        return 0

    def max_pk(self, table: str, pk_column: str) -> int:
        rows = self.execute(f"SELECT MAX({pk_column}) as max_pk FROM {table}")
        if rows.iloc[0]["max_pk"] is not None:
            return rows.iloc[0]["max_pk"].tolist()
        return 0

    def generate_join_clause(self, dataset: DataSet) -> str:
        """Automatically generates a join clause from the Relationships that have been
        set.

        This typically isn't used by end users.

        Returns:
            str: A join string to be used in a sqlite3 query
        """
        join = ""
        for r in self.relationships:
            if dataset.table == r.child_table:
                join += f" {self.relationship_to_join_clause(r)}"
        return join if not dataset.join_clause else dataset.join_clause

    def generate_where_clause(self, dataset: DataSet) -> str:
        """Generates a where clause from the Relationships that have been set, as well
        as the DataSet's where clause.

        This is not typically used by end users.

        Returns:
            str: A where clause string to be used in a sqlite3 query
        """
        where = ""
        for r in self.relationships:
            if dataset.table == r.child_table and r.on_update_cascade:
                table = dataset.table
                parent_pk = dataset.frm[r.parent_table].get_current(r.pk_column)

                # Children without cascade-filtering parent aren't displayed
                if not parent_pk:
                    parent_pk = PK_PLACEHOLDER

                clause = f" WHERE {table}.{r.fk_column}={parent_pk!s}"
                if where:
                    clause = clause.replace("WHERE", "AND")
                where += clause

        if not where:
            # There was no where clause from Relationships..
            where = dataset.where_clause
        else:
            # There was an auto-generated portion of the where clause.
            # We will add the table's where clause to it
            where = where + " " + dataset.where_clause.replace("WHERE", "AND")

        return where

    @staticmethod
    def generate_query(
        dataset: DataSet,
        join_clause: bool = True,
        where_clause: bool = True,
        order_clause: bool = True,
    ) -> str:
        """Generate a query string using the relationships that have been set.

        Args:
            dataset: A `DataSet` object
            join_clause: True to auto-generate 'join' clause, False to not
            where_clause: True to auto-generate 'where' clause, False to not
            order_clause: True to auto-generate 'order by' clause, False to not

        Returns:
            a query string for use with sqlite3
        """
        return (
            f"{dataset.query}"
            f' {dataset.join_clause if join_clause else ""}'
            f' {dataset.where_clause if where_clause else ""}'
            f' {dataset.order_clause if order_clause else ""}'
        )

    def delete_record(self, dataset: DataSet, cascade=True):
        # Get data for query
        table = self.quote_table(dataset.table)
        pk_column = self.quote_column(dataset.pk_column)
        pk = dataset.get_current(dataset.pk_column)

        # Create clauses
        delete_clause = f"DELETE FROM {table} "  # leave a space at end for joining
        where_clause = f"WHERE {table}.{pk_column} = {pk}"

        # Delete child records first!
        if cascade:
            recursion = 0
            result = self._delete_record_recursive(
                dataset, "", where_clause, table, pk_column, recursion
            )

        # Then delete self
        if result == DELETE_RECURSION_LIMIT_ERROR:
            return DELETE_RECURSION_LIMIT_ERROR
        q = delete_clause + where_clause + ";"
        return self.execute(q)

    def _delete_record_recursive(
        self, dataset: DataSet, inner_join, where_clause, parent, pk_column, recursion
    ):
        for child in self.relationships.get_delete_cascade_tables(dataset.table):
            # Check to make sure we arn't at recursion limit
            recursion += 1  # Increment, since this is a child
            if recursion >= DELETE_CASCADE_RECURSION_LIMIT:
                return DELETE_RECURSION_LIMIT_ERROR

            # Get data for query
            fk_column = self.quote_column(
                self.relationships.get_delete_cascade_fk_column(child)
            )
            pk_column = self.quote_column(dataset.frm[child].pk_column)
            child_table = self.quote_table(child)
            select_clause = f"SELECT {child_table}.{pk_column} FROM {child} "
            delete_clause = f"DELETE FROM {child} WHERE {pk_column} IN "

            # Create new inner join and add it to beginning of passed in inner_join
            inner_join_clause = (
                f"INNER JOIN {parent} ON {parent}.{pk_column} = "
                f"{child}.{fk_column} {inner_join}"
            )

            # Call function again to create recursion
            result = self._delete_record_recursive(
                dataset.frm[child],
                inner_join_clause,
                where_clause,
                child,
                self.quote_column(dataset.frm[child].pk_column),
                recursion,
            )

            # Break out of recursive call if at recursion limit
            if result == DELETE_RECURSION_LIMIT_ERROR:
                return DELETE_RECURSION_LIMIT_ERROR

            # Create query and execute
            q = (
                delete_clause
                + "("
                + select_clause
                + inner_join_clause
                + where_clause
                + ");"
            )
            self.execute(q)
            logger.debug(f"Delete query executed: {q}")

            # Reset limit for next Child stack
            recursion = 0
        return None

    def duplicate_record(self, dataset: DataSet, children: bool) -> pd.DataFrame:
        """Duplicates a record in a database table and optionally duplicates its
        dependent records.

        The function uses all columns found in `DataSet.column_info` and
        select all except the primary key column, inserting a duplicate record with the
        same column values.

        If the 'children' parameter is set to 'True', the function duplicates the
        dependent records by setting the foreign key column of the child records to the
        primary key value of the newly duplicated record before inserting them.

        Note that this function assumes the primary key column is auto-incrementing and
        that no columns are set to unique.

        Args:
            dataset: The `DataSet` of the the record to be duplicated.
            children: (optional) Whether to duplicate dependent records. Defaults to
                False.
        """

        # Get variables
        table = self.quote_table(dataset.table)
        columns = [
            self.quote_column(column.name)
            for column in dataset.column_info
            if column.name != dataset.pk_column and not column.generated
        ]
        columns = ", ".join(columns)
        pk_column = dataset.pk_column
        pk = dataset.get_current(dataset.pk_column)

        # Insert new record
        res = self._insert_duplicate_record(table, columns, pk_column, pk)

        if res.attrs["exception"]:
            return res

        # Get pk of new record
        new_pk = res.attrs["lastrowid"]
        # now wrap pk_column
        pk_column = self.quote_column(dataset.pk_column)

        # Set description if TEXT
        if dataset.column_info[dataset.description_column].python_type == str:
            description_column = self.quote_column(dataset.description_column)
            description = (
                f"{lang.duplicate_prepend}{dataset.get_description_for_pk(pk)}"
            )
            query = (
                f"UPDATE {table} "
                f"SET {description_column} = {self.placeholder} "
                f"WHERE {pk_column} = {new_pk};"
            )
            res = self.execute(query, [description])
            if res.attrs["exception"]:
                return res

        # create list of which children we have duplicated
        child_duplicated = []
        # Next, duplicate the child records!
        if children:
            for _ in dataset.frm.datasets:
                for r in self.relationships:
                    if (
                        r.parent_table == dataset.table
                        and r.on_update_cascade
                        and (r.child_table not in child_duplicated)
                    ):
                        child = self.quote_table(r.child_table)
                        fk_column = self.quote_column(r.fk_column)

                        # all columns except pk_column
                        columns = [
                            self.quote_column(column.name)
                            for column in dataset.frm[r.child_table].column_info
                            if column.name != dataset.frm[r.child_table].pk_column
                            and not column.generated
                        ]

                        # replace fk_column value with pk of new parent
                        select_columns = [
                            str(new_pk)
                            if column == self.quote_column(r.fk_column)
                            else column
                            for column in columns
                        ]

                        # prepare query & execute
                        columns = ", ".join(columns)
                        select_columns = ", ".join(select_columns)
                        query = (
                            f"INSERT INTO {child} ({columns}) "
                            f"SELECT {select_columns} FROM {child} "
                            f"WHERE {fk_column} = {pk};"
                        )
                        res = self.execute(query)
                        if res.attrs["exception"]:
                            return res

                        child_duplicated.append(r.child_table)
        # If we made it here, we can return the pk.
        # Since the pk was stored earlier, we will just send an empty dataframe.
        return Result.set(lastrowid=new_pk)

    def _insert_duplicate_record(
        self, table: str, columns: str, pk_column: str, pk: int
    ) -> pd.DataFrame:
        """Inserts duplicate record, sets attrs["lastrowid"] to new record's pk.

        Used by `SQLDriver.duplicate_record` to handle database-specific differences in
        returning new primary keys.

        Args:
            table: Escaped table name of record to be duplicated
            columns: Escaped and comman (,) seperated list of columns
            pk_column: Non-escaped pk_column
            pk: Primary key of record
        """
        query = (
            f"INSERT INTO {table} ({columns}) "
            f"SELECT {columns} FROM {table} "
            f"WHERE {self.quote_column(pk_column)} = {pk} "
            f"RETURNING {self.quote_column(pk_column)};"
        )
        res = self.execute(query)
        if res.attrs["exception"]:
            return res
        res.attrs["lastrowid"] = res.iloc[0][pk_column].tolist()
        return res

    def save_record(
        self, dataset: DataSet, changed_row: dict, where_clause: str = None
    ) -> pd.DataFrame:
        pk = dataset.get_current_pk()
        pk_column = dataset.pk_column

        # quote columns
        changed_row = {self.quote_column(k): v for k, v in changed_row.items()}

        # Set empty fields to None
        for k, v in changed_row.items():
            if v in EMPTY:
                changed_row[k] = None

        # quote appropriately
        table = self.quote_table(dataset.table)
        pk_column = self.quote_column(pk_column)

        # Create the WHERE clause
        if where_clause is None:
            where_clause = f"WHERE {pk_column} = {pk}"

        # Generate an UPDATE query
        query = f"UPDATE {table} SET {', '.join(f'{k}={self.placeholder}' for k in changed_row)} {where_clause};"  # fmt: skip # noqa: E501
        values = list(changed_row.values())

        result = self.execute(query, tuple(values))
        # manually clear the rowid since it is not needed for updated records
        # (we already know the key)
        result.attrs["lastrowid"] = None
        return result

    def insert_record(self, table: str, pk: int, pk_column: str, row: dict):
        # Remove the pk column
        row = {self.quote_column(k): v for k, v in row.items() if k != pk_column}

        # Set empty fields to None
        for k, v in row.items():
            if v in EMPTY:
                row[k] = None

        # quote appropriately
        table = self.quote_table(table)

        query = (
            f"INSERT INTO {table} ({', '.join(key for key in row)}) VALUES "
            f"({','.join(self.placeholder for _ in range(len(row)))}); "
        )
        values = [value for key, value in row.items()]
        return self.execute(query, tuple(values))

    # ---------------------------------------------------------------------
    # Probably won't need to implement the following functions
    # ---------------------------------------------------------------------

    def add_relationship(
        self,
        join: str,
        child_table: str,
        fk_column: str,
        parent_table: str,
        pk_column: str,
        update_cascade: bool,
        delete_cascade: bool,
    ) -> None:
        """Add a foreign key relationship between two dataset of the database When you
        attach a database, PySimpleSQL isn't aware of the relationships contained until
        datasets are added via `Form.add_dataset`, and the relationship of various tables
        is set with this function. Note that `SQLDriver.auto_add_relationships()` will
        do this automatically from the schema of the database, which also happens
        automatically when a `SQLDriver` is created.

        Args:
            join: The join type of the relationship ('LEFT JOIN', 'INNER JOIN', 'RIGHT
                JOIN')
            child_table: The child table containing the foreign key
            fk_column: The foreign key column of the child table
            parent_table: The parent table containing the primary key
            pk_column: The primary key column of the parent table
            update_cascade: Requery and filter child table results on selected parent
                primary key (ON UPDATE CASCADE in SQL)
            delete_cascade: Delete the dependent child records if the parent table
                record is deleted (ON UPDATE DELETE in SQL)

        Returns:
            None
        """
        self.relationships.append(
            Relationship(
                join,
                child_table,
                fk_column,
                parent_table,
                pk_column,
                update_cascade,
                delete_cascade,
                self,
            )
        )

    # Make sure to send a list of table names to requery if you want
    # dependent dataset to requery automatically
    def auto_add_relationships(self) -> None:
        """Automatically add a foreign key relationship between tables of the database.
        This is done by foreign key constraints within the database.  Automatically
        requery the child table if the parent table changes (ON UPDATE CASCADE in sql is
        set) When you attach a database, PySimpleSQL isn't aware of the relationships
        contained until tables are added and the relationship of various tables is set.
        This happens automatically during `SQLDriver` creation. Note that
        `SQLDriver.add_relationship()` can do this manually.

        Returns:
            None
        """
        logger.info("Automatically adding foreign key relationships")
        # Clear any current rels so that successive calls will not double the entries
        self.relationships = RelationshipStore(
            self
        )  # clear any relationships already stored
        relationships = self.get_relationships()
        for r in relationships:
            logger.debug(
                f'Adding relationship {r["from_table"]}.{r["from_column"]} = '
                f'{r["to_table"]}.{r["to_column"]}'
            )
            self.add_relationship(
                "LEFT JOIN",
                r["from_table"],
                r["from_column"],
                r["to_table"],
                r["to_column"],
                r["update_cascade"],
                r["delete_cascade"],
            )

    def check_reserved_keywords(self, value: bool) -> None:
        """SQLDrivers can check to make sure that field names respect their own reserved
        keywords.  By default, all SQLDrivers will check for their respective keywords.
        You can choose to disable this feature with this method.

        Args:
            value: True to check for reserved keywords in field names, false to skip
                this check

        Returns:
            None
        """
        self._CHECK_RESERVED_KEYWORDS = value

    def _import_failed(self, exception) -> None:
        popup = Popup()
        requires = ", ".join(self.REQUIRES)
        popup.ok(
            lang.import_module_failed_title,
            lang.import_module_failed.format_map(
                LangFormat(name=self.NAME, requires=requires, exception=exception)
            ),
        )
        exit(0)

    def _parse_domain(self, domain):
        domain_parts = domain.split("(")
        domain_name = domain_parts[0].strip().upper()

        if len(domain_parts) > 1:
            domain_args = domain_parts[1].rstrip(")").split(",")
            domain_args = [arg.strip() for arg in domain_args]
        else:
            domain_args = []

        return domain_name, domain_args

    def _get_column_class(self, domain) -> Union[ColumnClass, None]:
        if domain in self.COLUMN_CLASS_MAP:
            return self.COLUMN_CLASS_MAP[domain]
        logger.info(f"Mapping {domain} to generic Column class")
        return None


# --------------------------------------------------------------------------------------
# SQLITE3 DRIVER
# --------------------------------------------------------------------------------------
@dc.dataclass
class Sqlite(SQLDriver):
    """The SQLite driver supports SQLite3 databases."""

    global sqlite3  # noqa PLW0603
    import sqlite3

    sql_char: dc.InitVar[SqlChar] = SqlChar(  # noqa RUF009
        placeholder="?", table_quote='"', column_quote='"'
    )

    NAME: ClassVar[str] = "SQLite"
    REQUIRES: ClassVar[str] = ["sqlite3"]

    DECIMAL_DOMAINS: ClassVar[List[str]] = ["DECIMAL", "DECTEXT", "MONEY", "NUMERIC"]

    COLUMN_CLASS_MAP: ClassVar[List[str]] = {}

    SQL_CONSTANTS: ClassVar[List[str]] = [
        "CURRENT_DATE",
        "CURRENT_TIME",
        "CURRENT_TIMESTAMP",
        "NULL",
    ]

    def __init__(
        self,
        database: Union[
            str,
            Path,
            Literal[":memory:"],
            sqlite3.Connection,
        ] = None,
        *,
        sql_commands=None,
        sql_script=None,
        sql_script_encoding: str = "utf-8",
        update_cascade: bool = True,
        delete_cascade: bool = True,
        sql_char: SqlChar = sql_char,
        create_file: bool = True,
        skip_sql_if_db_exists: bool = True,
    ) -> None:
        """
        Args:
            update_cascade: (optional) Default:True. Requery and filter child table on
                selected parent primary key. (ON UPDATE CASCADE in SQL)
            delete_cascade: (optional) Default:True. Delete the dependent child records
                if the parent table record is deleted. (ON UPDATE DELETE in SQL)
        """
        self._database = str(database)
        self.sql_commands = sql_commands
        self.sql_script = sql_script
        self.sql_script_encoding = sql_script_encoding
        self.update_cascade = update_cascade
        self.delete_cascade = delete_cascade
        self.create_file = create_file
        self.skip_sql_if_db_exists = skip_sql_if_db_exists

        super().__post_init__(sql_char)

    def _import_required_modules(self) -> None:
        # Sqlite needs Sqlite3.Connection for a type-hint, so we already imported
        pass

    def _init_db(self) -> None:
        # register adapters and converters
        self._register_type_callables()

        # if str, try opening
        if isinstance(self._database, str):
            logger.info(f"Opening database: {self._database}")
            new_database = not os.path.isfile(self._database)
            if self._database != ":memory:" and new_database and not self.create_file:
                popup = Popup()
                popup.ok(
                    lang.SQLDriver_file_not_found_title,
                    lang.SQLDriver_file_not_found.format_map(
                        LangFormat(file=self._database)
                    ),
                )
                exit(0)
            self.connect(self._database)  # Open our database

        # or use passed preexisting connection
        elif isinstance(self._database, sqlite3.Connection):
            self.con = self._database
            new_database = False

        self.win_pb.update(lang.SQLDriver_execute, 50)
        self.con.row_factory = sqlite3.Row

        # execute sql
        if (
            not self.skip_sql_if_db_exists
            or self.sql_commands is not None
            and new_database
        ):
            # run SQL script if the database does not yet exist
            logger.info("Executing sql commands passed in")
            logger.debug(self.sql_commands)
            self.con.executescript(self.sql_commands)
            self.con.commit()
        if (
            not self.skip_sql_if_db_exists
            or self.sql_script is not None
            and new_database
        ):
            # run SQL script from the file if the database does not yet exist
            logger.info("Executing sql script from file passed in")
            self.execute_script(self.sql_script, self.sql_script_encoding)

    @property
    def _imported_database(self):
        return isinstance(self._database, sqlite3.Connection)

    def connect(self, database) -> None:
        self.con = sqlite3.connect(
            database, detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES
        )

    def execute(
        self,
        query,
        values=None,
        silent=False,
        column_info=None,
        auto_commit_rollback: bool = False,
    ) -> pd.DataFrame:
        if not silent:
            logger.info(f"Executing query: {query} {values}")

        cursor = self.con.cursor()
        exception = None

        try:
            cur = cursor.execute(query, values) if values else cursor.execute(query)
        except sqlite3.Error as e:
            exception = e
            logger.warning(
                f"Execute exception: {type(e).__name__}: {e}, using query: {query}"
            )
            if auto_commit_rollback:
                self.rollback()
        else:
            if auto_commit_rollback:
                self.commit()

        try:
            rows = cur.fetchall()
        except:  # noqa E722
            rows = []

        lastrowid = cursor.lastrowid if cursor.lastrowid is not None else None
        return Result.set(
            [dict(row) for row in rows], lastrowid, exception, column_info
        )

    def execute_script(self, script, encoding) -> None:
        with open(script, "r", encoding=encoding) as file:
            logger.info(f"Loading script {script} into database.")
            self.con.executescript(file.read())

    def close(self) -> None:
        # Only do cleanup if this is not an imported database
        if not self._imported_database:
            # optimize the database for long-term benefits
            if self._database != ":memory:":
                q = "PRAGMA optimize;"
                self.con.execute(q)
            # Close the connection
            self.con.close()

    def get_tables(self):
        q = (
            "SELECT name FROM sqlite_master "
            'WHERE type="table" AND name NOT like "sqlite%";'
        )
        cur = self.execute(q, silent=True)
        return list(cur["name"])

    def column_info(self, table):
        # Return a list of column names
        q = f"PRAGMA table_xinfo({self.quote_table(table)})"
        rows = self.execute(q, silent=True)
        names = []
        col_info = ColumnInfo(self, table)
        for _, row in rows.iterrows():
            domain, domain_args = self._parse_domain(row["type"])
            col_class = self._get_column_class(domain) or Column
            # TODO: should we exclude hidden columns?
            # if row["hidden"] == 1:
            #    continue
            name = row["name"]
            names.append(name)
            domain = row["type"]
            notnull = row["notnull"]
            default = row["dflt_value"]
            pk = row["pk"]
            generated = row["hidden"] in [2, 3]
            col_info.append(
                col_class(
                    name=name,
                    domain=domain,
                    notnull=notnull,
                    default=default,
                    pk=pk,
                    generated=generated,
                    domain_args=domain_args,
                )
            )

        return col_info

    def pk_column(self, table):
        q = f"PRAGMA table_info({self.quote_table(table)})"
        result = self.execute(q, silent=True)
        return result.loc[result["pk"] == 1, "name"].iloc[0]

    def get_relationships(self):
        # Return a list of dicts {from_table,to_table,from_column,to_column,requery}
        relationships = []
        tables = self.get_tables()
        for from_table in tables:
            rows = self.execute(
                f"PRAGMA foreign_key_list({self.quote_table(from_table)})", silent=True
            )

            for _, row in rows.iterrows():
                dic = {}
                # Add the relationship if it's in the requery list
                if row["on_update"] == "CASCADE":
                    dic["update_cascade"] = True
                else:
                    dic["update_cascade"] = False
                if row["on_delete"] == "CASCADE":
                    dic["delete_cascade"] = True
                else:
                    dic["delete_cascade"] = False
                dic["from_table"] = from_table
                dic["to_table"] = row["table"]
                dic["from_column"] = row["from"]
                dic["to_column"] = row["to"]
                relationships.append(dic)
        return relationships

    def _get_column_class(self, domain) -> Union[ColumnClass, None]:
        if self.COLUMN_CLASS_MAP:
            col_class = super()._get_column_class(domain)
            if col_class is not None:
                return col_class
        if "DATETIME" in domain or "TIMESTAMP" in domain:
            return DateTimeCol
        if "DATE" in domain:
            return DateCol
        if "TIME" in domain:
            return TimeCol
        if any(col_name in domain for col_name in self.DECIMAL_DOMAINS):
            return DecimalCol
        if "BOOL" in domain:
            return BoolCol
        if "INT" in domain:
            return IntCol
        if any(col_name in domain for col_name in ["TEXT", "CHAR", "CLOB"]):
            return StrCol
        if any(col_name in domain for col_name in ["REAL", "FLOA", "DOUB"]):
            return FloatCol
        if "BLOB" in domain or domain in EMPTY:
            return Column
        return None

    def _register_type_callables(self) -> None:
        # Register datetime adapters/converters
        # python 3.12 will depreciate dt.date/dt.datetime default adapters
        sqlite3.register_adapter(dt.date, lambda val: val.isoformat())
        sqlite3.register_adapter(dt.datetime, lambda val: val.isoformat(" "))
        sqlite3.register_adapter(dt.time, lambda val: val.isoformat())

        # Register Decimal adapter/converter
        sqlite3.register_adapter(Decimal, str)
        for domain in self.DECIMAL_DOMAINS:
            sqlite3.register_converter(domain, lambda val: Decimal(val.decode("utf-8")))


# --------------------------------------------------------------------------------------
# FLATFILE DRIVER
# --------------------------------------------------------------------------------------
# The CSV driver uses SQlite3 in the background
# to use pysimplesql directly with CSV files
@dc.dataclass
class Flatfile(Sqlite):

    """The Flatfile driver adds support for flatfile databases such as CSV files to
    pysimplesql.

    The flatfile data is loaded into an internal SQlite database, where it can be used
    and manipulated like any other database file.  Each timem records are saved, the
    contents of the internal SQlite database are written back out to the file. This
    makes working with flatfile data as easy and consistent as any other database.
    """

    def __init__(
        self,
        file_path: str,
        delimiter: str = ",",
        quotechar: str = '"',
        header_row_num: int = 0,
        table: str = None,
        pk_col: str = None,
    ) -> None:
        """Create a new Flatfile driver instance.

        Args:
            file_path: The path to the flatfile
            delimiter: The delimiter for the flatfile. Defaults to ','.  Tabs ('\t') are
                another popular option
            quotechar: The quoting character specified by the flatfile. Defaults to '"'
            header_row_num: The row containing the header column names. Defaults to 0
            table: The name to give this table in pysimplesql. Default is 'Flatfile'
            pk_col: The column name that acts as a primary key for the dataset. See
                 below how to use this parameter:
                - If no pk_col parameter is supplied, then a generic primary key column
                  named 'pk' will be generated with AUTO INCREMENT and PRIMARY KEY set.
                  This is a virtual column and will not be written back out to the
                  flatfile.
                - If the pk_col parameter is supplied, and it exists in the header row,
                  then it will be used as the primary key for the dataset. If this
                  column does not exist in the header row, then a virtual primary key
                  column with this name will be created with AUTO INCREMENT and PRIMARY
                  KEY set. As above, the virtual primary key column that was created
                  will not be written to the flatfile.
        """
        self.file_path = file_path
        self.delimiter = delimiter
        self.quotechar = quotechar
        self.header_row_num = header_row_num
        self.pk_col = pk_col if pk_col is not None else "pk"
        self.pk_col_is_virtual = False
        self.table = table if table is not None else "Flatfile"

        # First up the SQLite driver that we derived from
        super().__init__(":memory:")  # use an in-memory database

        # Change Sqlite SQLDriver init set values to Flatfile-specific
        self.NAME = "Flatfile"
        self.REQUIRES = ["csv,sqlite3"]
        self.placeholder = "?"  # update

    def _init_db(self) -> None:
        self.connect(":memory:")

        self.con.row_factory = sqlite3.Row

        # Store any text up to the header line, so they can be restored
        self.pre_header = []

        # Open the CSV file and read the header row to get column names
        with open(self.file_path, "r") as f:
            reader = csv.reader(f, delimiter=self.delimiter, quotechar=self.quotechar)
            # skip lines as determined by header_row_num
            for _i in range(self.header_row_num):
                self.pre_header.append(next(reader))

            # Grab the header row information
            self.columns = next(reader)

        if self.pk_col not in self.columns:
            # The pk column was not found, we will make it virutal
            self.columns.insert(0, self.pk_col)
            self.pk_col_is_virtual = True

        # Construct the SQL commands to create the table to represent the flatfile data
        q_cols = ""
        for col in self.columns:
            if col == self.pk_col:
                q_cols += f'{col} {"INTEGER PRIMARY KEY AUTOINCREMENT" if self.pk_col_is_virtual else "PRIMARY KEY"}'  # fmt: skip # noqa: E501
            else:
                q_cols += f"{col} TEXT"

            if col != self.columns[-1]:
                q_cols += ", "

        query = f"CREATE TABLE {self.table} ({q_cols})"
        self.execute(query)

        # Load the CSV data into the table
        with open(self.file_path, "r") as f:
            reader = csv.reader(f, delimiter=self.delimiter, quotechar=self.quotechar)
            # advance to past the header column
            for _i in range(self.header_row_num + 1):
                next(reader)

            # We only want to insert the pk_column if it is not virtual. We will remove
            # it now, as it has already served its purpose to create the table
            if self.pk_col_is_virtual:
                self.columns.remove(self.pk_col)

            query = (
                f'INSERT INTO {self.table} ({", ".join(self.columns)}) VALUES '
                f'({", ".join(["?" for _ in self.columns])})'
            )
            for row in reader:
                self.execute(query, row)

        self.commit()  # commit them all at the end

    def _import_required_modules(self) -> None:
        global csv  # noqa PLW0603
        global sqlite3  # noqa PLW0603
        try:
            import csv
            import sqlite3
        except ModuleNotFoundError as e:
            self._import_failed(e)

    def save_record(
        self, dataset: DataSet, changed_row: dict, where_clause: str = None
    ) -> pd.DataFrame:
        # Have SQlite save this record
        result = super().save_record(dataset, changed_row, where_clause)

        if result.attrs["exception"] is None:
            # No it is safe to write our data back out to the CSV file

            # Update the DataSet object's DataFra,e with the changes, so then
            # the entire DataFrame can be written back to file sequentially
            dataset.rows.iloc[dataset.current_index] = pd.Series(changed_row)

            # open the CSV file for writing
            with open(self.file_path, "w", newline="\n") as csvfile:
                # create a csv writer object
                writer = csv.writer(
                    csvfile, delimiter=self.delimiter, quotechar=self.quotechar
                )

                # Skip the number of lines defined by header_row_num.
                # Write out the stored pre_header lines
                for line in self.pre_header:
                    writer.writerow(line)
                # write the header row
                writer.writerow(list(self.columns))

                # write the DataFrame out.
                # Use our columns to exclude the possible virtual pk
                rows = []
                for _, row in dataset.rows.iterrows():
                    rows.append([row[c] for c in self.columns])

                logger.debug(f"Writing the following data to {self.file_path}")
                logger.debug(rows)
                writer.writerows(rows)

        return result


# --------------------------------------------------------------------------------------
# MYSQL DRIVER
# --------------------------------------------------------------------------------------
@dc.dataclass
class Mysql(SQLDriver):
    """The Mysql driver supports MySQL databases."""

    tinyint1_is_boolean: bool = True

    NAME: ClassVar[str] = "MySQL"
    REQUIRES: ClassVar[List[str]] = ["mysql-connector-python"]

    COLUMN_CLASS_MAP: ClassVar[List[str]] = {
        "BIT": BoolCol,
        "BIGINT": IntCol,
        "CHAR": StrCol,
        "DATE": DateCol,
        "DATETIME": DateTimeCol,
        "DECIMAL": DecimalCol,
        "DOUBLE": FloatCol,
        "FLOAT": FloatCol,
        "INT": IntCol,
        "INTEGER": IntCol,
        "LONGTEXT": StrCol,
        "MEDIUMINT": IntCol,
        "MEDIUMTEXT": StrCol,
        "MULTILINESTRING": StrCol,
        "NUMERIC": DecimalCol,
        "REAL": FloatCol,
        "SMALLINT": IntCol,
        "TEXT": StrCol,
        "TIME": TimeCol,
        "TIMESTAMP": DateTimeCol,
        "TINYINT": IntCol,
        "TINYTEXT": StrCol,
        "VARCHAR": StrCol,
        "YEAR": IntCol,
    }

    SQL_CONSTANTS: ClassVar[List[str]] = [
        "CURRENT_DATE",
        "CURRENT_TIME",
        "CURRENT_TIMESTAMP",
    ]

    def _init_db(self) -> None:
        self.con = self.connect()

        self.win_pb.update(lang.SQLDriver_execute, 50)
        if self.sql_commands is not None:
            # run SQL script if the database does not yet exist
            logger.info("Executing sql commands passed in")
            logger.debug(self.sql_commands)
            cursor = self.con.cursor()
            for result in cursor.execute(self.sql_commands, multi=True):
                if result.with_rows:
                    print("Rows produced by statement '{}':".format(result.statement))
                    print(result.fetchall())
                else:
                    print(
                        "Number of rows affected by statement '{}': {}".format(
                            result.statement, result.rowcount
                        )
                    )
            self.con.commit()
            cursor.close()
        if self.sql_script is not None:
            # run SQL script from the file if the database does not yet exist
            logger.info("Executing sql script from file passed in")
            self.execute_script(self.sql_script, self.sql_script_encoding)

    def _import_required_modules(self) -> None:
        global mysql
        try:
            import mysql.connector
        except ModuleNotFoundError as e:
            self._import_failed(e)

    def connect(self, retries=3):
        attempt = 0
        while attempt < retries:
            try:
                return mysql.connector.connect(
                    host=self.host,
                    user=self.user,
                    password=self.password,
                    database=self.database,
                    # connect_timeout=3,
                )
            except mysql.connector.Error as e:
                print(f"Failed to connect to database ({attempt + 1}/{retries})")
                print(e)
                attempt += 1
                sleep(1)
        raise Exception("Failed to connect to database")

    def execute(
        self,
        query,
        values=None,
        silent=False,
        column_info=None,
        auto_commit_rollback: bool = False,
    ):
        if not silent:
            logger.info(f"Executing query: {query} {values}")
        cursor = self.con.cursor(dictionary=True)
        exception = None
        try:
            cursor.execute(query, values) if values else cursor.execute(query)
        except mysql.connector.Error as e:
            exception = e.msg
            logger.warning(
                f"Execute exception: {type(e).__name__}: {e}, using query: {query}"
            )
            if auto_commit_rollback:
                self.rollback()
        else:
            if auto_commit_rollback:
                self.commit()

        try:
            rows = cursor.fetchall()
        except:  # noqa E722
            rows = []

        lastrowid = cursor.lastrowid if cursor.lastrowid else None

        return Result.set(
            [dict(row) for row in rows], lastrowid, exception, column_info
        )

    def execute_script(self, script, encoding) -> None:
        with open(script, "r", encoding=encoding) as file:
            logger.info(f"Loading script {script} into database.")
            cursor = self.con.cursor()
            cursor.execute(file.read(), multi=True)
        self.con.commit()
        cursor.close()

    def get_tables(self):
        query = (
            "SELECT TABLE_NAME FROM information_schema.tables WHERE table_schema = %s"
        )
        rows = self.execute(query, [self.database], silent=True)
        return list(rows["TABLE_NAME"])

    def column_info(self, table):
        # Return a list of column names
        query = f"SELECT * FROM information_schema.columns WHERE table_name = '{table}'"
        rows = self.execute(query, silent=True)
        col_info = ColumnInfo(self, table)
        rows = rows.fillna("")
        for _, row in rows.iterrows():
            name = row["COLUMN_NAME"]
            # Check if the value is a bytes-like object, and decode if necessary
            type_value = (
                row["COLUMN_TYPE"].decode("utf-8")
                if isinstance(row["COLUMN_TYPE"], bytes)
                else row["COLUMN_TYPE"]
            )
            # Capitalize and get rid of the extra information of the row type
            # I.e. varchar(255) becomes VARCHAR
            domain, domain_args = self._parse_domain(type_value)

            # TODO, think about an Enum or SetCol
            # # domain_args for enum/set are actually a list
            # if domain in ["ENUM", "SET"]:
            #     domain_args = [domain_args]

            if (
                self.tinyint1_is_boolean
                and domain == "TINYINT"
                and domain_args == ["1"]
            ):
                col_class = BoolCol

            else:
                col_class = self._get_column_class(domain) or Column
                if col_class == DecimalCol:
                    domain_args = [row["NUMERIC_PRECISION"], row["NUMERIC_SCALE"]]
                elif col_class in [FloatCol, IntCol]:
                    domain_args = [row["NUMERIC_PRECISION"]]
                elif col_class == StrCol:
                    domain_args = [row["CHARACTER_MAXIMUM_LENGTH"]]

            notnull = row["IS_NULLABLE"] == "NO"
            default = row["COLUMN_DEFAULT"]
            pk = row["COLUMN_KEY"] == "PRI"
            generated = row["EXTRA"] in ["VIRTUAL GENERATED", "STORED GENERATED"]
            col_info.append(
                col_class(
                    name=name,
                    domain=domain,
                    notnull=notnull,
                    default=default,
                    pk=pk,
                    generated=generated,
                    domain_args=domain_args,
                )
            )

        return col_info

    def pk_column(self, table):
        query = "SHOW KEYS FROM {} WHERE Key_name = 'PRIMARY'".format(table)
        rows = self.execute(query, silent=True)
        return rows.iloc[0]["Column_name"]

    def get_relationships(self):
        # Return a list of dicts {from_table,to_table,from_column,to_column,requery}
        tables = self.get_tables()
        relationships = []
        for from_table in tables:
            query = (
                "SELECT * FROM information_schema.key_column_usage WHERE "
                "referenced_table_name IS NOT NULL AND table_name = %s"
            )
            rows = self.execute(query, (from_table,), silent=True)

            for _, row in rows.iterrows():
                dic = {}
                # Get the constraint information
                on_update, on_delete = self.constraint(row["CONSTRAINT_NAME"])
                if on_update == "CASCADE":
                    dic["update_cascade"] = True
                else:
                    dic["update_cascade"] = False
                if on_delete == "CASCADE":
                    dic["delete_cascade"] = True
                else:
                    dic["delete_cascade"] = False
                dic["from_table"] = row["TABLE_NAME"]
                dic["to_table"] = row["REFERENCED_TABLE_NAME"]
                dic["from_column"] = row["COLUMN_NAME"]
                dic["to_column"] = row["REFERENCED_COLUMN_NAME"]
                relationships.append(dic)
        return relationships

    # Not required for SQLDriver
    def constraint(self, constraint_name):
        query = (
            "SELECT UPDATE_RULE, DELETE_RULE FROM "
            "INFORMATION_SCHEMA.REFERENTIAL_CONSTRAINTS WHERE CONSTRAINT_NAME = "
            f"'{constraint_name}'"
        )
        update_rule = None
        delete_rule = None
        rows = self.execute(query, silent=True)
        for _, row in rows.iterrows():
            if "UPDATE_RULE" in row:
                update_rule = row["UPDATE_RULE"]
            if "DELETE_RULE" in row:
                delete_rule = row["DELETE_RULE"]
        return update_rule, delete_rule

    def _insert_duplicate_record(
        self, table: str, columns: str, pk_column: str, pk: int
    ) -> pd.DataFrame:
        """Inserts duplicate record, sets attrs["lastrowid"] to new record's pk.

        Used by `SQLDriver.duplicate_record` to handle database-specific differences in
        returning new primary keys.

        Args:
            table: Escaped table name of record to be duplicated
            columns: Escaped and comman (,) seperated list of columns
            pk_column: Non-escaped pk_column
            pk: Primary key of record
        """
        query = (
            f"INSERT INTO {table} ({columns}) "
            f"SELECT {columns} FROM {table} "
            f"WHERE {self.quote_column(pk_column)} = {pk};"
        )
        res = self.execute(query)
        if res.attrs["exception"]:
            return res

        query = "SELECT LAST_INSERT_ID();"

        res = self.execute(query)
        if res.attrs["exception"]:
            return res

        res.attrs["lastrowid"] = res.iloc[0]["LAST_INSERT_ID()"].tolist()
        return res


# --------------------------------------------------------------------------------------
# MARIADB DRIVER
# --------------------------------------------------------------------------------------
# MariaDB is a fork of MySQL and backward compatible.  It technically does not need its
# own driver, but that could change in the future, plus having its own named class makes
# it more clear for the end user.
@dc.dataclass
class Mariadb(Mysql):
    """The Mariadb driver supports MariaDB databases."""

    NAME: ClassVar[str] = "MariaDB"


# --------------------------------------------------------------------------------------
# POSTGRES DRIVER
# --------------------------------------------------------------------------------------
@dc.dataclass
class Postgres(SQLDriver):
    """The Postgres driver supports PostgreSQL databases."""

    sql_char: dc.InitVar[SqlChar] = SqlChar(table_quote='"')  # noqa RUF009
    sync_sequences: bool = False

    NAME: ClassVar[str] = "Postgres"
    REQUIRES: ClassVar[List[str]] = ["psycopg2", "psycopg2.extras"]

    COLUMN_CLASS_MAP: ClassVar[List[str]] = {
        "BIGINT": IntCol,
        "BIGSERIAL": IntCol,
        "BOOLEAN": BoolCol,
        "CHARACTER": StrCol,
        "CHARACTER VARYING": StrCol,
        "DATE": DateCol,
        "DOUBLE PRECISION": FloatCol,
        "INTEGER": IntCol,
        "MONEY": DecimalCol,
        "NUMERIC": DecimalCol,
        "REAL": FloatCol,
        "SMALLINT": IntCol,
        "SMALLSERIAL": IntCol,
        "SERIAL": IntCol,
        "TEXT": StrCol,
        "TIME": TimeCol,
        "TIMETZ": TimeCol,
        "TIMESTAMP": DateTimeCol,
        "TIMESTAMPTZ": DateTimeCol,
    }

    SQL_CONSTANTS: ClassVar[List[str]] = [
        "CURRENT_DATE",
        "CURRENT_TIME",
        "CURRENT_TIMESTAMP",
        "LOCALTIME",
        "LOCALTIMESTAMP",
        "CURRENT_USER",
        "SESSION_USER",
        "USER",
    ]

    def _init_db(self) -> None:
        self.con = self.connect()

        # experiment to see if I can make a nocase collation
        # query ="CREATE COLLATION NOCASE (provider = icu, locale = 'und-u-ks-level2');"
        # self.execute(query)

        if self.sync_sequences:
            # synchronize the sequences with the max pk for each table. This is useful
            # if manual records were inserted without calling nextval() to update the
            # sequencer
            q = "SELECT sequence_name FROM information_schema.sequences;"
            sequences = self.execute(q, silent=True)
            for s in sequences:
                seq = s["sequence_name"]

                # get the max pk for this table
                q = (
                    "SELECT column_name, table_name FROM information_schema.columns "
                    f"WHERE column_default LIKE 'nextval(%{seq}%)'"
                )
                rows = self.execute(q, silent=True, auto_commit_rollback=True)
                row = rows.fetchone()
                table = row["table_name"]
                pk_column = row["column_name"]
                max_pk = self.max_pk(table, pk_column)

                # update the sequence
                # TODO: This needs fixed.  pysimplesql_user does have permissions on the
                # sequence, but this still bombs out
                seq = self.quote_table(seq)
                if max_pk > 0:
                    q = f"SELECT setval('{seq}', {max_pk});"
                else:
                    q = f"SELECT setval('{seq}', 1, false);"
                self.execute(q, silent=True, auto_commit_rollback=True)

        self.win_pb.update(lang.SQLDriver_execute, 50)

        if self.sql_script is not None:
            # run SQL script from the file if the database does not yet exist
            logger.info("Executing sql script from file passed in")
            self.execute_script(self.sql_script, self.sql_script_encoding)

        if self.sql_commands is not None:
            # run SQL script if the database does not yet exist
            logger.info("Executing sql commands passed in")
            logger.debug(self.sql_commands)
            cursor = self.con.cursor()
            cursor.execute(self.sql_commands)
            self.con.commit()
            cursor.close()

    def _import_required_modules(self) -> None:
        global psycopg2  # noqa PLW0603
        try:
            import psycopg2
            import psycopg2.extras
        except ModuleNotFoundError as e:
            self._import_failed(e)

    def connect(self, retries=3):
        attempt = 0
        while attempt < retries:
            try:
                return psycopg2.connect(
                    host=self.host,
                    user=self.user,
                    password=self.password,
                    database=self.database,
                    # connect_timeout=3,
                )
            except psycopg2.Error as e:
                print(f"Failed to connect to database ({attempt + 1}/{retries})")
                print(e)
                attempt += 1
                sleep(1)
        raise Exception("Failed to connect to database")

    def execute(
        self,
        query: str,
        values=None,
        silent=False,
        column_info=None,
        auto_commit_rollback: bool = False,
    ):
        if not silent:
            logger.info(f"Executing query: {query} {values}")
        cursor = self.con.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        exception = None
        try:
            cursor.execute(query, values) if values else cursor.execute(query)
        except psycopg2.Error as e:
            exception = e
            logger.warning(
                f"Execute exception: {type(e).__name__}: {e}, using query: {query}"
            )
            if auto_commit_rollback:
                self.rollback()
        else:
            if auto_commit_rollback:
                self.commit()

        try:
            rows = cursor.fetchall()
        except psycopg2.ProgrammingError:
            rows = []

        # In Postgres, the cursor does not return a lastrowid.  We will not set it here,
        # we will instead set it in save_records() due to the RETURNING stement of the
        # query
        return Result.set(
            [dict(row) for row in rows], exception=exception, column_info=column_info
        )

    def execute_script(self, script, encoding) -> None:
        with open(script, "r", encoding=encoding) as file:
            logger.info(f"Loading script {script} into database.")
            cursor = self.con.cursor()
            cursor.execute(file.read())
        self.con.commit()
        cursor.close()

    def get_tables(self):
        query = (
            "SELECT table_name FROM information_schema.tables WHERE "
            "table_schema='public' AND table_type='BASE TABLE';"
        )
        # query = "SELECT tablename FROM pg_tables WHERE table_schema='public'"
        rows = self.execute(query, silent=True)
        return list(rows["table_name"])

    def column_info(self, table: str) -> ColumnInfo:
        # Return a list of column names
        query = (
            f"SELECT * FROM information_schema.columns WHERE table_name = '{table}' "
            "ORDER BY ordinal_position"
        )
        rows = self.execute(query, silent=True)
        col_info = ColumnInfo(self, table)
        pk_column = self.pk_column(table)
        for _, row in rows.iterrows():
            name = row["column_name"]
            domain = row["data_type"].upper()
            col_class = self._get_column_class(domain) or Column
            domain_args = []
            if col_class == DecimalCol:
                domain_args = [row["numeric_precision"], row["numeric_scale"]]
            elif col_class in [FloatCol, IntCol]:
                domain_args = [row["numeric_precision"]]
            elif col_class == StrCol:
                domain_args = [row["character_maximum_length"]]
            notnull = row["is_nullable"] != "YES"
            default = row["column_default"]
            # Fix the default value by removing the datatype that is appended to the end
            if default is not None and "::" in default:
                default = default[: default.index("::")]
            pk = name == pk_column
            generated = row["is_generated"] == "ALWAYS"
            col_info.append(
                col_class(
                    name=name,
                    domain=domain,
                    notnull=notnull,
                    default=default,
                    pk=pk,
                    generated=generated,
                    domain_args=domain_args,
                )
            )

        return col_info

    def pk_column(self, table):
        query = (
            "SELECT column_name FROM information_schema.table_constraints tc JOIN "
            "information_schema.key_column_usage kcu ON tc.constraint_name = "
            "kcu.constraint_name WHERE tc.constraint_type = 'PRIMARY KEY' AND "
            f"tc.table_name = '{table}';"
        )
        rows = self.execute(query, silent=True)
        return rows.iloc[0]["column_name"]

    def get_relationships(self):
        # Return a list of dicts {from_table,to_table,from_column,to_column,requery}
        tables = self.get_tables()
        relationships = []
        for from_table in tables:
            query = (
                "SELECT conname, conrelid::regclass, confrelid::regclass, "
                "confupdtype, confdeltype, a1.attname AS column_name, a2.attname "
                "AS referenced_column_name "
                "FROM pg_constraint "
                "JOIN pg_attribute AS a1 ON conrelid = a1.attrelid AND "
                "a1.attnum = ANY(conkey) "
                "JOIN pg_attribute AS a2 ON confrelid = a2.attrelid AND "
                "a2.attnum = ANY(confkey) "
                f"WHERE confrelid = '\"{from_table}\"'::regclass AND contype = 'f'"
            )

            rows = self.execute(query, (from_table,), silent=True)

            for _, row in rows.iterrows():
                dic = {}
                # Get the constraint information
                # constraint = self.constraint(row['conname'])
                if row["confupdtype"] == "c":
                    dic["update_cascade"] = True
                else:
                    dic["update_cascade"] = False
                if row["confdeltype"] == "c":
                    dic["delete_cascade"] = True
                else:
                    dic["delete_cascade"] = False
                dic["from_table"] = row["conrelid"].strip('"')
                dic["to_table"] = row["confrelid"].strip('"')
                dic["from_column"] = row["column_name"]
                dic["to_column"] = row["referenced_column_name"]
                relationships.append(dic)
        return relationships

    def min_pk(self, table: str, pk_column: str) -> int:
        table = self.quote_table(table)
        pk_column = self.quote_column(pk_column)
        rows = self.execute(
            f"SELECT COALESCE(MIN({pk_column}), 0) AS min_pk FROM {table};", silent=True
        )
        return rows.iloc[0]["min_pk"].tolist()

    def max_pk(self, table: str, pk_column: str) -> int:
        table = self.quote_table(table)
        pk_column = self.quote_column(pk_column)
        rows = self.execute(
            f"SELECT COALESCE(MAX({pk_column}), 0) AS max_pk FROM {table};", silent=True
        )
        return rows.iloc[0]["max_pk"].tolist()

    def next_pk(self, table: str, pk_column: str) -> int:
        # Working with case-sensitive tables is painful in Postgres.  First, the
        # sequence must be quoted in a manner similar to tables, then the quoted
        # sequence name has to be also surrounded in single quotes to be treated
        # literally and prevent folding of the casing.
        seq = f"{table}_{pk_column}_seq"  # build the default sequence name
        seq = self.quote_table(seq)  # quote it like a table

        # wrap the quoted string in singe quotes.  Phew!
        q = f"SELECT nextval('{seq}') LIMIT 1;"
        rows = self.execute(q, silent=True)
        return rows.iloc[0]["nextval"].tolist()

    def insert_record(self, table: str, pk: int, pk_column: str, row: dict):
        # insert_record() for Postgres is a little different from the rest. Instead of
        # relying on an autoincrement, we first already "reserved" a primary key
        # earlier, so we will use it directly quote appropriately

        # add pk back in if its missing
        row[pk_column] = pk

        # quote
        row = {self.quote_column(k): v for k, v in row.items()}
        table = self.quote_table(table)

        query = (
            f"INSERT INTO {table} ({', '.join(key for key in row)}) VALUES "
            f"({','.join('%s' for _ in range(len(row)))}); "
        )
        values = [value for key, value in row.items()]
        result = self.execute(query, tuple(values))

        result.attrs["lastid"] = pk
        return result


# --------------------------------------------------------------------------------------
# MS SQLSERVER DRIVER
# --------------------------------------------------------------------------------------
@dc.dataclass
class Sqlserver(SQLDriver):
    """The Sqlserver driver supports Microsoft SQL Server databases."""

    sql_char: dc.InitVar[SqlChar] = SqlChar(  # noqa RUF009
        placeholder="?", table_quote="[]"
    )

    NAME: ClassVar[str] = "Sqlserver"
    REQUIRES: ClassVar[List[str]] = ["pyodbc"]

    COLUMN_CLASS_MAP: ClassVar[List[str]] = {
        "BIGINT": IntCol,
        "BIT": BoolCol,
        "CHAR": StrCol,
        "DATE": DateCol,
        "DATETIME": DateTimeCol,
        "DATETIME2": DateTimeCol,
        "DATETIMEOFFSET": DateTimeCol,
        "DECIMAL": DecimalCol,
        "FLOAT": FloatCol,
        "INT": IntCol,
        "MONEY": DecimalCol,
        "NCHAR": StrCol,
        "NTEXT": StrCol,
        "NUMERIC": DecimalCol,
        "NVARCHAR": StrCol,
        "REAL": FloatCol,
        "SMALLDATETIME": DateTimeCol,
        "SMALLINT": IntCol,
        "SMALLMONEY": DecimalCol,
        "TEXT": StrCol,
        "TIME": TimeCol,
        "TIMESTAMP": DateTimeCol,
        "TINYINT": IntCol,
        "VARCHAR": StrCol,
    }

    SQL_CONSTANTS: ClassVar[List[str]] = [
        "CURRENT_USER",
        "HOST_NAME",
        "NULL",
        "SESSION_USER",
        "SYSTEM_USER",
        "USER",
    ]

    def _init_db(self) -> None:
        self.con = self.connect()

        if self.sql_script is not None:
            # run SQL script from the file if the database does not yet exist
            logger.info("Executing sql script from file passed in")
            self.execute_script(self.sql_script, self.sql_script_encoding)

        if self.sql_commands is not None:
            # run SQL script if the database does not yet exist
            logger.info("Executing sql commands passed in")
            logger.debug(self.sql_commands)
            cursor = self.con.cursor()
            cursor.execute(self.sql_commands)
            self.con.commit()
            cursor.close()

    def _import_required_modules(self) -> None:
        global pyodbc  # noqa PLW0603
        try:
            import pyodbc
        except ModuleNotFoundError as e:
            self._import_failed(e)

    def connect(self, retries=3, timeout=3):
        attempt = 0
        while attempt < retries:
            try:
                return pyodbc.connect(
                    f"DRIVER={{ODBC Driver 17 for SQL Server}};"
                    f"SERVER={self.host};"
                    f"DATABASE={self.database};"
                    f"UID={self.user};"
                    f"PWD={self.password}",
                    timeout=timeout,
                )
            except pyodbc.Error as e:
                print(f"Failed to connect to database ({attempt + 1}/{retries})")
                print(e)
                attempt += 1
                sleep(1)
        raise Exception("Failed to connect to database")

    def execute(
        self,
        query,
        values=None,
        silent=False,
        column_info=None,
        auto_commit_rollback: bool = False,
    ):
        if not silent:
            logger.info(f"Executing query: {query} {values}")
        cursor = self.con.cursor()
        exception = None
        try:
            cursor.execute(query, values) if values else cursor.execute(query)
        except pyodbc.Error as e:
            exception = e
            logger.warning(
                f"Execute exception: {type(e).__name__}: {e}, using query: {query}"
            )
            if auto_commit_rollback:
                self.rollback()
        else:
            if auto_commit_rollback:
                self.commit()

        try:
            rows = cursor.fetchall()
        except:  # noqa E722
            rows = []

        lastrowid = cursor.rowcount if cursor.rowcount else None

        return Result.set(
            [
                dict(zip([column[0] for column in cursor.description], row))
                for row in rows
            ],
            lastrowid,
            exception,
            column_info,
        )

    def execute_script(self, script, encoding) -> None:
        with open(script, "r", encoding=encoding) as file:
            logger.info(f"Loading script {script} into database.")
            cursor = self.con.cursor()
            cursor.execute(file.read())
        self.con.commit()
        cursor.close()

    def get_tables(self):
        query = (
            "SELECT table_name FROM information_schema.tables WHERE table_catalog = ?"
        )
        rows = self.execute(query, [self.database], silent=True)
        return list(rows["table_name"])

    def column_info(self, table):
        # Return a list of column names
        query = "SELECT * FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = ?"
        rows = self.execute(query, [table], silent=True)
        col_info = ColumnInfo(self, table)
        # Get the primary key column(s)
        pk_columns = []
        pk_query = """
            SELECT COLUMN_NAME
            FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
            WHERE TABLE_NAME = ?
        """
        pk_rows = self.execute(pk_query, [table], silent=True)
        for _, pk_row in pk_rows.iterrows():
            pk_columns.append(pk_row["COLUMN_NAME"])

        # get the generated columns:
        gen_query = (
            "SELECT name "
            "FROM sys.columns "
            "WHERE object_id = OBJECT_ID(?) "
            "AND is_computed = 1;"
        )
        generated_columns = []
        gen_rows = self.execute(gen_query, [table], silent=True)
        for _, row in gen_rows.iterrows():
            generated_columns.append(row[0])
        rows = rows.fillna("")
        # setup all the variables to be passed to col_info
        for _, row in rows.iterrows():
            name = row["COLUMN_NAME"]
            domain = row["DATA_TYPE"].upper()
            col_class = self._get_column_class(domain) or Column
            domain_args = []
            if col_class == DecimalCol:
                domain_args = [row["NUMERIC_PRECISION"], row["NUMERIC_SCALE"]]
            elif col_class in [FloatCol, IntCol]:
                domain_args = [row["NUMERIC_PRECISION"]]
            elif col_class == StrCol:
                # SqlServer apparently uses -1.0 for None
                domain_args = [row["CHARACTER_MAXIMUM_LENGTH"]] if not -1.0 else None
            notnull = row["IS_NULLABLE"] == "NO"
            if row["COLUMN_DEFAULT"]:
                col_default = row["COLUMN_DEFAULT"]
                if (col_default.startswith("('") and col_default.endswith("')")) or (
                    col_default.startswith('("')
                    and col_default.endswith('")')
                    or (col_default.startswith("((") and col_default.endswith("))"))
                ):
                    default = col_default[2:-2]
                else:
                    default = col_default[1:-1]
            else:
                default = None
            pk = name in pk_columns
            generated = name in generated_columns
            col_info.append(
                col_class(
                    name=name,
                    domain=domain,
                    notnull=notnull,
                    default=default,
                    pk=pk,
                    generated=generated,
                    domain_args=domain_args,
                )
            )

        return col_info

    def get_relationships(self):
        # Return a list of dicts {from_table,to_table,from_column,to_column,requery}
        tables = self.get_tables()
        relationships = []
        for from_table in tables:
            query = (
                "SELECT "
                "   OBJECT_NAME(f.parent_object_id) AS from_table, "
                "   OBJECT_NAME(f.referenced_object_id) AS to_table, "
                "   COL_NAME(fc.parent_object_id, fc.parent_column_id) AS from_column, "
                "   COL_NAME(fc.referenced_object_id, fc.referenced_column_id) AS to_column, "  # noqa: E501
                "   f.update_referential_action_desc AS update_cascade, "
                "   f.delete_referential_action_desc AS delete_cascade "
                "FROM "
                "   sys.foreign_keys AS f "
                "   INNER JOIN sys.foreign_key_columns AS fc "
                "       ON f.object_id = fc.constraint_object_id "
                "WHERE "
                f"   OBJECT_NAME(f.parent_object_id) = '{from_table}'"
            )

            rows = self.execute(query, silent=True)

            for _, row in rows.iterrows():
                dic = {}
                dic["from_table"] = row["from_table"]
                dic["to_table"] = row["to_table"]
                dic["from_column"] = row["from_column"]
                dic["to_column"] = row["to_column"]
                dic["update_cascade"] = row["update_cascade"] == "CASCADE"
                dic["delete_cascade"] = row["delete_cascade"] == "CASCADE"
                relationships.append(dic)
        return relationships

    def pk_column(self, table):
        query = (
            "SELECT "
            "   COLUMN_NAME "
            "FROM "
            "   INFORMATION_SCHEMA.KEY_COLUMN_USAGE "
            "WHERE "
            f"   TABLE_NAME = '{table}' "
            "   AND CONSTRAINT_NAME LIKE 'PK%'"
        )

        rows = self.execute(query, silent=True)

        if not rows.empty:
            return rows.iloc[0]["COLUMN_NAME"]
        return None

    def _insert_duplicate_record(
        self, table: str, columns: str, pk_column: str, pk: int
    ) -> pd.DataFrame:
        query = (
            f"INSERT INTO {table} ({columns}) "
            f"OUTPUT inserted.{self.quote_column(pk_column)} "
            f"SELECT {columns} FROM {table} "
            f"WHERE {self.quote_column(pk_column)} = {pk};"
        )
        res = self.execute(query)
        if res.attrs["exception"]:
            return res
        res.attrs["lastrowid"] = res.iloc[0][pk_column].tolist()
        return res

    def insert_record(self, table: str, pk: int, pk_column: str, row: dict):
        # Remove the pk column
        row = {self.quote_column(k): v for k, v in row.items() if k != pk_column}

        # quote appropriately
        table = self.quote_table(table)

        query = (
            f"INSERT INTO {table} ({', '.join(key for key in row)}) "
            f"OUTPUT inserted.{self.quote_column(pk_column)} "
            f"VALUES "
            f"({','.join(self.placeholder for _ in range(len(row)))}); "
        )
        values = [value for key, value in row.items()]
        res = self.execute(query, tuple(values))
        if res.attrs["exception"]:
            return res
        res.attrs["lastrowid"] = res.iloc[0][pk_column].tolist()
        return res


# --------------------------------------------------------------------------------------
# MS ACCESS DRIVER
# --------------------------------------------------------------------------------------
@dc.dataclass
class MSAccess(SQLDriver):
    """The MSAccess driver supports Microsoft Access databases. Note that only database
    interactions are supported, including stored Queries, but not operations dealing
    with Forms, Reports, etc.

    Note: Jackcess and UCanAccess libraries may not accurately report decimal places
    for "Number" or "Currency" columns. Manual configuration of decimal places may
    be required by replacing the placeholders as follows:
    frm[DATASET KEY].column_info[COLUMN NAME].scale = 2
    """

    sql_char: dc.InitVar[SqlChar] = SqlChar(  # noqa RUF009
        placeholder="?", table_quote="[]"
    )

    NAME: ClassVar[str] = "MSAccess"
    REQUIRES: ClassVar[List[str]] = ["Jype1"]

    COLUMN_CLASS_MAP: ClassVar[List[str]] = {
        "BIG_INT": IntCol,
        "BOOLEAN": BoolCol,
        "DECIMAL": DecimalCol,
        "INTEGER": IntCol,
        "VARCHAR": StrCol,
        "TIMESTAMP": DateTimeCol,
    }

    def __init__(
        self,
        database_file: Union[str, Path],
        *,
        overwrite_file: bool = False,
        sql_script: str = None,
        sql_script_encoding: str = "utf-8",
        sql_commands: str = None,
        update_cascade: bool = True,
        delete_cascade: bool = True,
        sql_char: SqlChar = sql_char,
        infer_datetype_from_default_function: bool = True,
        use_newer_jackcess: bool = False,
    ) -> None:
        """Initialize the MSAccess class.

        Args:
            database_file: The path to the MS Access database file.
            overwrite_file: If True, prompts the user if the file already exists. If the
                user declines to overwrite the file, the provided SQL commands or script
                will not be executed.
            sql_commands: Optional SQL commands to execute after opening the database.
            sql_script: Optional SQL script file to execute after opening the database.
            sql_script_encoding: The encoding of the SQL script file. Defaults to
                'utf-8'.
            update_cascade: (optional) Default:True. Requery and filter child table on
                selected parent primary key. (ON UPDATE CASCADE in SQL)
            delete_cascade: (optional) Default:True. Delete the dependent child records
                if the parent table record is deleted. (ON UPDATE DELETE in SQL)
            infer_datetype_from_default_function: If True, specializes a DateTime column
                by examining the column's default function. A DateTime column with
                '=Date()' will be treated as a 'DateCol', and '=Time()' will be treated
                as a 'TimeCol'. Defaults to True.
            use_newer_jackcess: If True, uses a newer version of the Jackcess library
                for improved compatibility, specifically allowing handling of
                'attachment' columns. Defaults to False.
        """

        self.database_file = str(database_file)
        self.overwrite_file = overwrite_file
        self.sql_script = sql_script
        self.sql_script_encoding = sql_script_encoding
        self.sql_commands = sql_commands
        self.update_cascade = update_cascade
        self.delete_cascade = delete_cascade
        self.infer_datetype_from_default_function = infer_datetype_from_default_function
        self.use_newer_jackcess = use_newer_jackcess

        super().__post_init__(sql_char)

    def _init_db(self) -> None:
        if not self.start_jvm():
            logger.debug("Failed to start jvm")
            exit()

        # handle if file doesn't exist or user wants to overwrite_file
        create_access_file = False
        if not os.path.exists(self.database_file):
            create_access_file = True
        elif os.path.exists(self.database_file) and self.overwrite_file:
            text = sg.popup_get_text(lang.overwrite, title=lang.overwrite_title)
            if text == lang.overwrite_prompt:
                create_access_file = True
            else:
                self.sql_script = None
                self.sql_commands = None

        if create_access_file:
            self._create_access_file()

        # then connect
        self.con = self.connect()

        self.win_pb.update(lang.SQLDriver_execute, 50)

        if self.sql_script is not None:
            # run SQL script from the file if the database does not yet exist
            logger.info("Executing sql script from file passed in")
            self.execute_script(self.sql_script, self.sql_script_encoding)
        if self.sql_commands is not None:
            # run SQL script if the database does not yet exist
            logger.info("Executing sql commands passed in")
            logger.debug(self.sql_commands)
            queries = self.sql_commands.split(
                ";"
            )  # Split the query string by semicolons
            for query in queries:
                self.execute(query)

    import os
    import sys

    def _import_required_modules(self) -> None:
        global jpype  # noqa PLW0603
        try:
            import jpype  # pip install JPype1
            import jpype.imports
        except ModuleNotFoundError as e:
            self._import_failed(e)

    def start_jvm(self) -> bool:
        # Get the path to the 'lib' folder
        current_path = os.path.dirname(os.path.abspath(__file__))
        lib_path = os.path.join(current_path, "lib", "UCanAccess-5.0.1.bin")

        jackcess_file = (
            "jackcess-3.0.1.jar"
            if not self.use_newer_jackcess
            else "jackcess-4.0.5.jar"
        )

        jars = [
            "ucanaccess-5.0.1.jar",
            os.path.join("lib", "commons-lang3-3.8.1.jar"),
            os.path.join("lib", "commons-logging-1.2.jar"),
            os.path.join("lib", "hsqldb-2.5.0.jar"),
            os.path.join("lib", jackcess_file),
            os.path.join("loader", "ucanload.jar"),
        ]
        classpath = os.pathsep.join([os.path.join(lib_path, jar) for jar in jars])

        if not jpype.isJVMStarted():
            jpype.startJVM(
                jpype.getDefaultJVMPath(), "-ea", f"-Djava.class.path={classpath}"
            )
            global java  # noqa PLW0603
            import java

            self._register_default_adapters()
            self._register_default_converters()

            return True
        return True

    def connect(self):
        driver_manager = jpype.JPackage("java").sql.DriverManager
        con_str = f"jdbc:ucanaccess://{self.database_file}"
        return driver_manager.getConnection(con_str)

    def execute(
        self,
        query,
        values=None,
        silent=False,
        column_info=None,
        auto_commit_rollback: bool = False,
    ):
        if not silent:
            logger.info(f"Executing query: {query} {values}")

        exception = None
        has_result_set = False
        try:
            if values:
                stmt = self.con.prepareStatement(query)
                for index, value in enumerate(values, start=1):
                    adapted_value = self.adapt(value)
                    stmt.setObject(index, adapted_value)
                has_result_set = stmt.execute()
            else:
                stmt = self.con.createStatement()
                has_result_set = stmt.execute(query)
        except Exception as e:  # noqa: BLE001
            exception = e
            if not silent:
                logger.warning(
                    f"Execute exception: {type(e).__name__}: {e}, using query: {query}"
                )
            if auto_commit_rollback:
                self.rollback()

        if has_result_set:
            rs = stmt.getResultSet()
            metadata = rs.getMetaData()
            column_count = metadata.getColumnCount()
            rows = []
            lastrowid = None

            while rs.next():
                row = {}
                for i in range(1, column_count + 1):
                    column_name = str(metadata.getColumnName(i))
                    value = rs.getObject(i)
                    value = self.convert(value)
                    row[column_name] = value
                rows.append(row)

                # Set the last row ID
                if "insert" in query.lower():
                    res = self.execute("SELECT @@IDENTITY AS ID")
                    lastrowid = res.iloc[0]["ID"]

            return Result.set(
                [dict(row) for row in rows], lastrowid, exception, column_info
            )

        stmt.getUpdateCount()
        return Result.set([], None, exception, column_info)

    def execute_script(self, script, encoding) -> None:
        with open(script, "r", encoding=encoding) as file:
            logger.info(f"Loading script {script} into the database.")
            script_content = file.read()  # Read the entire script content
            queries = script_content.split(";")  # Split the script by semicolons
            for query in queries:
                q = query.strip()  # Remove leading/trailing whitespace
                if q:
                    self.execute(q)

    def column_info(self, table):
        meta_data = self.con.getMetaData()

        # get column info
        rs = meta_data.getColumns(None, None, table, None)

        col_info = ColumnInfo(self, table)
        pk_columns = [self.pk_column(table)]

        while rs.next():
            # for debugging
            debug = False
            if debug:
                # fmt: off
                columns = ['TABLE_CAT', 'TABLE_SCHEM', 'TABLE_NAME', 'COLUMN_NAME',
                           'DATA_TYPE', 'TYPE_NAME', 'COLUMN_SIZE', 'BUFFER_LENGTH',
                           'DECIMAL_DIGITS', 'NUM_PREC_RADIX', 'NULLABLE', 'REMARKS',
                           'COLUMN_DEF', 'SQL_DATA_TYPE', 'SQL_DATETIME_SUB',
                           'CHAR_OCTET_LENGTH', 'ORDINAL_POSITION', 'IS_NULLABLE',
                           'SCOPE_CATALOG', 'SCOPE_SCHEMA', 'SCOPE_TABLE',
                           'SOURCE_DATA_TYPE', 'IS_AUTOINCREMENT', 'IS_GENERATEDCOLUMN',
                           'ORIGINAL_TYPE']
                # fmt: on
                for col in columns:
                    value = str(rs.getString(col))
                    print(f"{col}: {value}")
            name = str(rs.getString("column_name"))
            domain = str(rs.getString("TYPE_NAME")).upper()
            notnull = str(rs.getString("IS_NULLABLE")) == "NO"
            default = str(rs.getString("COLUMN_DEF")).lstrip("=")
            pk = name in pk_columns
            generated = str(rs.getString("IS_GENERATEDCOLUMN")) == "YES"
            col_class = self._get_column_class(domain) or Column

            domain_args = []
            # handling Date/Time columns, since they are all reported as DateTime
            if self.infer_datetype_from_default_function and col_class == DateTimeCol:
                if default == "DATE()":
                    col_class = DateCol
                elif default == "TIME()":
                    col_class = TimeCol
            if col_class in [DecimalCol, FloatCol, IntCol, StrCol]:
                domain_args = [str(rs.getString("COLUMN_SIZE"))]
            if col_class == DecimalCol:
                domain_args.append(str(rs.getString("DECIMAL_DIGITS")))

            col_info.append(
                col_class(
                    name=name,
                    domain=domain,
                    notnull=notnull,
                    default=default,
                    pk=pk,
                    generated=generated,
                    domain_args=domain_args,
                )
            )

        return col_info

    def pk_column(self, table):
        meta_data = self.con.getMetaData()
        rs = meta_data.getPrimaryKeys(None, None, table)
        if rs.next():
            return str(rs.getString("column_name"))
        return None

    def get_tables(self):
        metadata = self.con.getMetaData()
        rs = metadata.getTables(None, None, "%", ["TABLE"])
        tables = []

        while rs.next():
            tables.append(str(rs.getString("TABLE_NAME")))

        return tables

    def get_relationships(self):
        # Get the mapping of uppercase table and column names to their original case
        table_mapping = {table.upper(): table for table in self.get_tables()}
        column_mappings = {
            table: {col.name.upper(): col.name for col in self.column_info(table)}
            for table in self.get_tables()
        }

        query = (
            "SELECT"
            "  fk.TABLE_NAME AS from_table,"
            "  pk.TABLE_NAME AS to_table,"
            "  fk.COLUMN_NAME AS from_column,"
            "  pk.COLUMN_NAME AS to_column,"
            "  rc.UPDATE_RULE AS on_update,"
            "  rc.DELETE_RULE AS on_delete"
            " FROM"
            "  INFORMATION_SCHEMA.REFERENTIAL_CONSTRAINTS rc"
            " INNER JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE fk"
            " ON rc.CONSTRAINT_NAME = fk.CONSTRAINT_NAME"
            " INNER JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE pk"
            " ON rc.UNIQUE_CONSTRAINT_NAME = pk.CONSTRAINT_NAME"
            " WHERE"
            "  fk.TABLE_SCHEMA = 'PUBLIC'"
            " AND pk.TABLE_SCHEMA = 'PUBLIC'"
        )

        stmt = self.con.createStatement()
        rs = stmt.executeQuery(query)
        relationships = []

        while rs.next():
            from_table_upper = str(rs.getString("from_table"))
            to_table_upper = str(rs.getString("to_table"))
            from_column_upper = str(rs.getString("from_column"))
            to_column_upper = str(rs.getString("to_column"))

            dic = {}
            dic["from_table"] = table_mapping[from_table_upper]
            dic["to_table"] = table_mapping[to_table_upper]
            dic["from_column"] = column_mappings[dic["from_table"]][from_column_upper]
            dic["to_column"] = column_mappings[dic["to_table"]][to_column_upper]
            dic["update_cascade"] = rs.getString("on_update") == "CASCADE"
            dic["delete_cascade"] = rs.getString("on_delete") == "CASCADE"
            relationships.append(dic)

        return relationships

    def max_pk(self, table: str, pk_column: str) -> int:
        rows = self.execute(f"SELECT MAX({pk_column}) as max_pk FROM {table}")
        return rows.iloc[0]["MAX_PK"].tolist()  # returned as upper case

    def _get_column_definitions(self, table_name):
        # Creates a comma separated list of column names and types to be used in a
        # CREATE TABLE statement
        columns = self.column_info(table_name)

        cols = ""
        for c in columns:
            cols += f"{c['name']} {c['domain']}, "
        return cols[:-2]

    def _insert_duplicate_record(
        self, table: str, columns: str, pk_column: str, pk: int
    ) -> pd.DataFrame:
        query = (
            f"INSERT INTO {table} ({columns}) "
            f"SELECT {columns} FROM {table} "
            f"WHERE {pk_column} = {pk};"
        )
        res = self.execute(query)
        if res.attrs["exception"]:
            return res
        res = self.execute("SELECT @@IDENTITY AS ID")
        res.attrs["lastrowid"] = res.iloc[0]["ID"].tolist()
        return res

    def _create_access_file(self) -> bool:
        try:
            db_builder = jpype.JClass(
                "com.healthmarketscience.jackcess.DatabaseBuilder"
            )
            if self.database_file.endswith(".mdb"):
                db_file_format = jpype.JClass(
                    "com.healthmarketscience.jackcess.Database$FileFormat"
                ).V2003
            elif self.database_file.endswith(".accdb"):
                db_file_format = jpype.JClass(
                    "com.healthmarketscience.jackcess.Database$FileFormat"
                ).V2016
            else:
                sg.popup("Access file name must end with .accdb or .mdb")
                return False
            access_db = (
                db_builder(jpype.JClass("java.io.File")(self.database_file))
                .setFileFormat(db_file_format)
                .create()
            )
            access_db.close()
        except Exception as e:  # noqa BLE001
            print("Error creating access file:", e)
            return False
        return True

    def adapt(self, value):
        for py_type, java_type in self.adapters.items():
            if isinstance(value, py_type):
                return java_type @ value
        return value

    def convert(self, value):
        for java_type, converter_fn in self.converters.items():
            if isinstance(value, java_type):
                return converter_fn(value)
        return value

    def _register_default_adapters(self) -> None:
        self.adapters = {
            dt.date: java.sql.Date,
            dt.datetime: java.sql.Timestamp,
            dt.time: java.sql.Time,
        }

    def _register_default_converters(self) -> None:
        self.converters = {
            jpype.JPackage("java").lang.String: lambda value: str(value),
            jpype.JPackage("java").lang.Integer: lambda value: int(value),
            jpype.JPackage("java").math.BigDecimal: lambda value: float(
                value.doubleValue()
            ),
            jpype.JPackage("java").lang.Double: lambda value: float(value),
            jpype.JPackage("java")
            .sql.Timestamp: lambda value: dt.datetime.strptime(
                value.toInstant().toString()[:-1],
                TIMESTAMP_FORMAT_MICROSECOND
                if "." in value.toInstant().toString()[:-1]
                else TIMESTAMP_FORMAT,
            )
            .strftime(DATE_FORMAT),
            jpype.JPackage("java")
            .sql.Date: lambda value: dt.datetime.strptime(value.toString(), DATE_FORMAT)
            .date(),
            jpype.JPackage("java")
            .sql.Time: lambda value: dt.datetime.strptime(value.toString(), TIME_FORMAT)
            .time(),
        }


# --------------------------
# TYPEDDICTS AND TYPEALIASES
# --------------------------
class Driver:
    """The `Driver` class allows for easy driver creation.

    It is a simple wrapper around
    the various `SQLDriver` classes.
    """

    sqlite: callable = Sqlite
    flatfile: callable = Flatfile
    mysql: callable = Mysql
    mariadb: callable = Mariadb
    postgres: callable = Postgres
    sqlserver: callable = Sqlserver
    msaccess: callable = MSAccess


SaveResultsDict = Dict[str, int]
CallbacksDict = Dict[str, Callable[[Form, sg.Window], Union[None, bool]]]
PromptSaveValue = Union[PROMPT_SAVE_PROCEED, PROMPT_SAVE_DISCARDED, PROMPT_SAVE_NONE]


class SimpleTransform(TypedDict):
    decode: Dict[str, Callable[[str, str], None]]
    encode: Dict[str, Callable[[str, str], None]]


ColumnClass = TypeVar("ColumnClass", bound=Column)

SimpleTransformsDict = Dict[str, SimpleTransform]


# ======================================================================================
# ALIASES
# ======================================================================================
languagepack = lang
Database = Form
Table = DataSet
record = field  # for reverse capability
