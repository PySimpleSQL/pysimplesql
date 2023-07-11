# To keep examples concise, avoid Black formatting. Remove # fmt: off to use Black formatting.
# fmt: off

import pysimplesql as ss
import PySimpleGUI as sg
import logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)

# Let's use a fun language pack
ss.languagepack(ss.lp_90s)

# Create a simple layout for working with our flatfile data.
# Note that you can set a specific table name to use, but here I am just using the defaul 'Flatfile'
# Lets also use some sortable headers so that we can rearrange the flatfile data when saving
table_builder = ss.TableBuilder(num_rows=10)
table_builder.add_column('name', 'Name', width=12)
table_builder.add_column('address', 'Address', width=25)
table_builder.add_column('phone', 'Phone #', width=10)
table_builder.add_column('email', 'EMail', width=25)

layout = [
    [ss.selector('Flatfile', table_builder)],
    [ss.field('Flatfile.name')],
    [ss.field('Flatfile.address')],
    [ss.field('Flatfile.phone')],
    [ss.field('Flatfile.email')],
    [ss.actions('Flatfile', edit_protect=False)]
]

# Create our PySimpleGUI Window
win = sg.Window('Test', layout=layout, finalize=True)

# Create a Flatfile driver.  Notice the header_row_num parameter.
# If you open up test.csv, you will see why this is needed
driver = ss.Driver.flatfile('test.csv', header_row_num=10)

# Use a pysimplesql Form to bind the window to the driver
frm = ss.Form(driver, bind_window=win)

# This is optional. Forces the saving of unchanged records.  This will allow us to use our sortable headers to arrange
# the data to our liking, then hit save without making any actual changes to the data and have the newly sorted
# data saved back to the flatfile.
frm.set_force_save(True)

# Make it so that the name, address and email can be part of the search
frm['Flatfile'].set_search_order(['name', 'address', 'email'])

# As you can see, using a Flatfile is just like using any database with pysimplesql!
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
