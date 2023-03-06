import pysimplesql as ss
import PySimpleGUI as sg
import logging
logger=logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Create a simple layout for working with our flatfile data.
# Note that you can set a specific table name to use, but here I am just using the defaul 'Flatfile'
# Lets also use some sortable headers so that we can rearrange the flatfile data when saving
headings=ss.TableHeadings(sort_enable=True)
headings.add_column('name', 'Name', width=12)
headings.add_column('address', 'Address', width=25)
headings.add_column('phone', 'Phone #', width=10)
headings.add_column('email', 'EMail', width=25)

layout = [
    [ss.selector('Flatfile', sg.Table, num_rows=10, headings=headings)],
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
driver = ss.Flatfile('test.csv', header_row_num=10)

# Use a pysimplesql Form to bind the window to the driver
frm= ss.Form(driver, bind=win)

# This is optional. Forces the saving of unchanged records.  This will allow us to use our sortable headers to arrange
# the data to our liking, then hit save without making any actual changes to the data and have the newly sorted
# data saved back to the flatfile.
frm.set_force_save(True)

# As you can see, using a Flatfile is just like using any database with pysimplesql!
while True:
    event,values = win.read()

    if ss.process_events(event, values):  # <=== let PySimpleSQL process its own events! Simple!
        logger.info(f'PySimpleDB event handler handled the event {event}!')
    elif event == sg.WIN_CLOSED or event == 'Exit':
        frm.close()  # <= ensures proper closing of the sqlite database and runs a database optimization
        break
    else:
        logger.info(f'This event ({event}) is not yet handled.')
