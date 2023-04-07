from install_java import java_check_install
import logging
import PySimpleGUI as sg
import pysimplesql as ss  # <=== PySimpleSQL lines will be marked like this.  There's only a few!

# Set the logging level here (NOTSET,DEBUG,INFO,WARNING,ERROR,CRITICAL)
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

if __name__ == "__main__":  # Must use for ss.ProgressAnimation on Windows.
    # Ensure that Java is installed
    if not java_check_install():
        exit(0)

    # -------------------------
    # CREATE PYSIMPLEGUI LAYOUT
    # -------------------------
    # Define the columns for the table selector using the TableHeading convenience class.
    # This will also allow sorting!
    headings = ss.TableHeadings(sort_enable=True)
    headings.add_column("title", "Title", width=40)
    headings.add_column("entry_date", "Date", width=10)
    headings.add_column("mood_id", "Mood", width=20)

    layout = [
        [ss.selector("Journal", sg.Table, num_rows=10, headings=headings)],
        [ss.actions("Journal")],
        [
            ss.field("Journal.entry_date"),
            sg.CalendarButton(
                "Select Date",
                close_when_date_chosen=True,
                target="Journal.entry_date",  # <- target matches field() name
                format="%Y-%m-%d",
                size=(10, 1),
                key="datepicker",
            ),
        ],
        [
            ss.field(
                "Journal.mood_id",
                sg.Combo,
                size=(30, 10),
                label="My mood:",
                auto_size_text=False,
            )
        ],
        [ss.field("Journal.title")],
        [ss.field("Journal.entry", sg.MLine, size=(71, 20))],
    ]

    # Create the Window, Driver and Form
    win = sg.Window("Journal example: MS Access", layout, finalize=True)
    driver = ss.Driver.msaccess("Journal.accdb")
    frm = ss.Form(driver, bind_window=win)  # <=== Here is the magic!

    # Reverse the default sort order so new journal entries appear at the top
    frm["Journal"].set_order_clause("ORDER BY entry_date ASC")
    # Set the column order for search operations.  By default, only the designated
    # description column is searched
    frm["Journal"].set_search_order(["entry_date", "title", "entry"])
    # Requery the data since we made changes to the sort order
    frm["Journal"].requery()

    # ------------------------------------------
    # How to Edit Protect your sg.CalendarButton
    # ------------------------------------------
    # By default, action() includes an edit_protect() call, that disables edits in the
    # window. You can toggle it off with:
    frm.edit_protect()  # Comment this out to edit protect elements on Window creation.
    # Set initial CalendarButton state to the same as pysimplesql elements
    win["datepicker"].update(disabled=frm.get_edit_protect())
    # Then watch for the 'edit_protect' event in your Main Loop

    # ---------
    # MAIN LOOP
    # ---------
    while True:
        event, values = win.read()

        if event == sg.WIN_CLOSED or event == "Exit":
            # Ensure proper closing of our resources
            driver.close()
            frm.close()
            win.close()
            break
        elif ss.process_events(
            event, values
        ):  # <=== let PySimpleSQL process its own events! Simple!
            logger.info(f"PySimpleDB event handler handled the event {event}!")
            if "edit_protect" in event:
                win["datepicker"].update(disabled=frm.get_edit_protect())
        else:
            logger.info(f"This event ({event}) is not yet handled.")
