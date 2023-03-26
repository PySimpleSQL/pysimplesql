# To keep examples concise, avoid Black formatting. Remove # fmt: off to use Black formatting.
# fmt: off

import PySimpleGUI as sg
import pysimplesql as ss            # <=== PySimpleSQL lines will be marked like this.  There's only a few!
from io import BytesIO
import logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)
try:
    from PIL import Image               # note: must pip3 install Pillow
except ModuleNotFoundError:
    sg.popup(" The Pillow library is not in stalled.  Please install with `pip3 install Pillow`")
    exit(0)


# ---------------
# IMAGE THUMBNAIL
# ---------------
# This function will limit the size of the image.  This example will
# work without it, but images will not be limited in size and can then overwhelm the GUI.
# Note in the code later in this file, that you can choose to either:
# 1) thumbnail the image prior to saving, so that you never store a large image in the database
# 2) thumbnail the image only for display purposes, storing the full resolution image in the database
def thumbnail(image_data, size=(320, 240)):
    img = Image.open(BytesIO(image_data))
    img.thumbnail(size)
    with BytesIO() as output:
        img.save(output, format=img.format)
        data = output.getvalue()
    return data


# -------------------------------------
# CREATE A SIMPLE DATABASE TO WORK WITH
# -------------------------------------
sql = """
CREATE TABLE Image(
    "pkImage"   INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    "name"      TEXT DEFAULT "New Image",
    "imageData"      BLOB
);
"""

# ------------------------
# Build a simple interface
# ------------------------
layout = [
    [sg.Image(key='preview', size=(300, 300))],
    [sg.HSep()],
    [ss.field('Image.name')],
    # Display some text if there are no records.  We will start with it being hidden
    [sg.T("*** No records available.  Use the insert button below to get started. ***", key='no_records',
          text_color='black', visible=False)],
    [ss.field('Image.imageData', no_label=True, visible=False)],  # Hide this record - it is only here to receive data
                                                                  # to insert into the database
    [sg.Input(key='image_path'), sg.FileBrowse(target='image_path', file_types=(('PNG Images', '*.png'),),
                                               key='file_browse')],
    [sg.HSep()],
    [ss.actions('Image', edit_protect=False)]
]

win = sg.Window('Image storage/retrieval demo', layout=layout, finalize=True)
driver = ss.Sqlite('Image.db', sql_commands=sql)
frm = ss.Database(driver, win)


# ------------------
# Callback functions
# ------------------
# We will need two callback functions.
# One callback to load the file in and encode it before saving to the database.
# Another callback to update the sg.Image element when the elements update

# first callback for encoding before saving to the database
def encode_image():
    if not win['image_path'].get():
        return False
    with open(win['image_path'].get(), 'rb') as file:
        blobdata = file.read()
        blobdata = thumbnail(blobdata)  # <==uncomment for thumbnail sizing during the saving process
        win['Image.imageData'].update(blobdata)
    # clear the file input
    win['image_path'].update('')
    return True


# Set the callback
frm['Image'].set_callback('before_save', encode_image)


# Second callback updates the sg.Image element with the image data
def update_display(frm: ss.Form, win: sg.Window):
    # Handle case where there are no records
    if len(frm['Image'].rows) == 0:
        visible = True
    else:
        visible = False
    win['no_records'].update(visible=visible)
    win['Image.name'].update(visible=not visible)
    win['Image.name:label'].update(visible=not visible)
    win['image_path'].update(visible=not visible)
    win['file_browse'].update(visible=not visible)

    blob = frm['Image']['imageData']
    if blob:
        blob = bytes(eval(blob))  # <==Secret Sauce
        blob = thumbnail(blob)    # <==comment/uncomment for thumbnail sizing during the display process
        win['preview'].update(data=blob, size=(320, 240))
    else:
        # clear the image (there is no image data present)
        win['preview'].update('', size=(320, 240))


# set a callback to display the image
frm.set_callback('update_elements', update_display)

# Update for our first run.  The update_elements callback will take care of this the rest of the time
update_display(frm, win)

while True:
    event, values = win.read()
    if event == sg.WINDOW_CLOSED or event == 'Exit':
        break
    frm.process_events(event, values)
win.close()
