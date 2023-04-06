# To keep examples concise, avoid Black formatting. Remove # fmt: off to use Black formatting.
# fmt: off

import PySimpleGUI as sg
import pysimplesql as ss  # <=== PySimpleSQL lines will be marked like this.  There's only a few!
import logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)  # <=== set the logging level here (NOTSET,DEBUG,INFO,WARNING,ERROR,CRITICAL)


# -------------------------
# CREATE PYSIMPLEGUI LAYOUT
# -------------------------
# Define the columns for the table selector
headings = ss.TableHeadings(sort_enable=True)
headings.add_column("title", "Title", width=40)
headings.add_column("entry_date", "Date", width=10)
headings.add_column("mood_id", "Mood", width=20)

layout = [
    [ss.selector('Journal', sg.Table, key='sel_journal', num_rows=10, headings=headings)],
    [ss.actions('Journal', 'act_journal', edit_protect=False)],
    [ss.field('Journal.entry_date')],
    [ss.field('Journal.mood_id', sg.Combo, size=(30, 10), label='My mood:', auto_size_text=False)],
    [ss.field('Journal.title')],
    [ss.field('Journal.entry', sg.MLine, size=(71, 20))]
]

win = sg.Window('Journal (external)  example', layout, finalize=True)
driver = ss.Driver.sqlite('./SQLite_examples/Journal.db', sql_script='journal.sql')
frm = ss.Form(driver, bind_window=win)  # <=== Here is the magic!
# Note:  sql_script is only run if Journal.db does not exist!  This has the effect of creating a new blank
# database as defined by the sql_script file if the database does not yet exist, otherwise it will use the database!

# Reverse the default sort order so new journal entries appear at the top
frm['Journal'].set_order_clause('ORDER BY entry_date ASC')
# Set the column order for search operations.  Normally only the column designated as the description column is searched
frm['Journal'].set_search_order(['entry_date', 'title', 'entry'])
# Requery the data since we made changes to the sort order
frm['Journal'].requery()

# ---------
# MAIN LOOP
# ---------
while True:
    event, values = win.read()

    if event == sg.WIN_CLOSED or event == 'Exit':
        frm.close()  # <= ensures proper closing of the sqlite database and runs a database optimization
        win.close()
        break
    elif ss.process_events(event, values):  # <=== let PySimpleSQL process its own events! Simple!
        logger.info(f'PySimpleDB event handler handled the event {event}!')
    else:
        logger.info(f'This event ({event}) is not yet handled.')
