# To keep examples concise, avoid Black formatting. Remove # fmt: off to use Black formatting.
# fmt: off

import PySimpleGUI as sg
import pysimplesql as ss                              # <=== PySimpleSQL lines will be marked like this.  There's only a few!
import logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)    # <=== Set the logging level here (NOTSET,DEBUG,INFO,WARNING,ERROR,CRITICAL)

# MYSQL EXAMPLE
# ----------------------------------
# CREATE A DATABASE SELECTION WINDOW
# ----------------------------------
layout_selection = [
    [sg.B('SQLite', key='sqlite'), sg.B('MySQL', key='mysql'), sg.B('PostgreSQL', key='postgres')]
]
win = sg.Window('SELECT A DATABASE TO USE', layout=layout_selection, finalize=True)
selected_driver = None
while True:
    event, values = win.read()

    if event == sg.WIN_CLOSED or event == 'Exit':
        selected_driver='sqlite'  # default to the SQLite driver
    else:
        selected_driver = event
    break
win.close()

# -------------------------
# CREATE PYSIMPLEGUI LAYOUT
# -------------------------
# Define the columns for the table selector using the TableHeading convenience class.  This will also allow sorting!
headings = ss.TableHeadings(sort_enable=True)
headings.add_column('title', 'Title', width=40)
headings.add_column('entry_date', 'Date', width=10)
headings.add_column('mood_id', 'Mood', width=20)

layout = [
    [sg.Text('Selected driver: '), sg.Text('', key='driver')],
    [ss.selector('Journal', sg.Table, num_rows=10, headings=headings)],
    [ss.actions('Journal')],
    [ss.field('Journal.entry_date'), sg.CalendarButton("Select Date", close_when_date_chosen=True,
                                                       target="Journal.entry_date",  # <- target matches field() name
                                                       format="%Y-%m-%d", size=(10, 1), key='datepicker')],
    [ss.field('Journal.mood_id', sg.Combo, size=(30, 10), label='My mood:', auto_size_text=False)],
    [ss.field('Journal.title')],
    [ss.field('Journal.entry', sg.MLine, size=(71, 20))]
]
# Create the Window, Driver and Form
win = sg.Window('Journal example: Multiple Databases', layout, finalize=True)

# Load the database with the selected driver.  This should show that the same PySimpleGUI/pysimplesql code is completely
# portable across all supported databases
if selected_driver == 'mysql':
    driver = ss.Mysql(**ss.mysql_examples)  # Use the mysql examples database credentials
elif selected_driver == 'postgres':
    driver = ss.Postgres(**ss.postgres_examples)
else:
    driver = ss.Sqlite('./SQLite_examples/Journal.db')
# Update the driver display in the GUI
win['driver'].update(driver.name)

frm = ss.Form(driver, bind_window=win)  # <=== Here is the magic!

# Reverse the default sort order so new journal entries appear at the top
frm['Journal'].set_order_clause('ORDER BY entry_date ASC')
# Set the column order for search operations.  By default, only the designated description column is searched
frm['Journal'].set_search_order(['entry_date', 'title', 'entry'])
# Requery the data since we made changes to the sort order
frm['Journal'].requery()

# ------------------------------------------
# How to Edit Protect your sg.CalendarButton
# ------------------------------------------
# By default, action() includes an edit_protect() call, that disables edits in the window.
# You can toggle it off with:
frm.edit_protect()  # Comment this out to edit protect elements when the window is created.
# Set initial CalendarButton state to the same as pysimplesql elements
win['datepicker'].update(disabled=frm.get_edit_protect())
# Then watch for the 'edit_protect' event in your Main Loop

# ---------
# MAIN LOOP
# ---------
while True:
    event, values = win.read()


    if event == sg.WIN_CLOSED or event == 'Exit':
        frm.close()              # <= ensures proper closing of the sqlite database and runs a database optimization
        win.close()
        break
    elif ss.process_events(event, values):                  # <=== let PySimpleSQL process its own events! Simple!
        logger.info(f'PySimpleDB event handler handled the event {event}!')
        if "edit_protect" in event:
            win['datepicker'].update(disabled=frm.get_edit_protect())
    else:
        logger.info(f'This event ({event}) is not yet handled.')


"""
Learnings from this example:
- Writing database-agnostic code with pysimplesql is easy.  The complexities of dealing with different types of 
  databases are completely hidden from the user
- Using DataSet.set_search_order() to set the search order of the query for search operations.
- How to edit protect PySimpleGUI elements
- using Form.field() and Form.selector() functions for easy GUI element creation
- using the label keyword argument to Form.record() to define a custom label
- using Tables as Form.selector() element types
- Using the TableHeadings() function to define sortable table headings
"""

