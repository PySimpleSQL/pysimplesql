import PySimpleGUI as sg
import pysimplesql as ss            # <=== PySimpleSQL lines will be marked like this.  There's only a few!
from io import BytesIO
from PIL import Image               # note: must pip3 install Pillow

# ---------------
# IMAGE THUMBNAIL
# ---------------
# This function will limit the size of the image.  This example will
# work without it, but images will not be limited in size and can then overwhelm the GUI.
# Note in the code below, that you can choose to either:
# 1) thumbnail the image prior to saving, so that you never store a large image in the database
# 2) thumbnail the image only for display purposes, storing the full resolution image in the database
def thumbnail(image_data, size=(320, 240)):
    img=Image.open(BytesIO(image_data))
    img.thumbnail(size)
    with BytesIO() as output:
        img.save(output, format=img.format)
        data=output.getvalue()
    return data


# -------------------------------------
# CREATE A SIMPLE DATABASE TO WORK WITH
# -------------------------------------
sql="""
CREATE TABLE Image(
    "pkImage"   INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    "name"      TEXT DEFAULT "New Image",
    "data"      BLOB
);
"""

# ------------------------
# Build a simple interface
#-------------------------
layout=[
    [sg.Image(key='preview',size=(300,300))],
    [ss.record('Image.name')],
    [ss.record('Image.data', no_label=True, visible=False)], # Hide this record - it is only here to recieve data to insert into the database
    [sg.Input(key='image_path'), sg.FileBrowse(target='image_path',file_types=(('PNG Images','*.png'),))],
    [ss.actions('actImage', 'Image', edit_protect=False)]
]

win=sg.Window('Image storage/retreival demo',layout=layout,finalize=True)
driver=ss.Sqlite('Image.db', sql_commands=sql)
db=ss.Database(driver,win)

# ------------------
# Callback functions
# ------------------
# We will need two callback functions.
# One callback to load the file in and encode it before saving to the database.
# Another callback to update the sg.Image element when the elements update

# first callback for encoding before saving to the database
def encode_image():
    if not win['image_path'].get(): return False
    with open(win['image_path'].get(), 'rb') as file:
        blobdata=file.read()
        blobdata=thumbnail(blobdata) # <==uncomment for thumbnail sizing during the saving process
        win['Image.data'].update(blobdata)
    # clear the file input
    win['image_path'].update('')
    return True

# Set the callback
db['Image'].set_callback('before_save',encode_image)


# Second callback updates the sg.Image element with the image data
def display_image(db,win):
    blob=db['Image']['data']
    if blob:
        blob=bytes(eval(blob)) # <==Secret Sauce
        #blob=thumbnail(blob) # <==uncomment for thumbnail sizing during the display process
        win['preview'].update(data=blob, size=(320, 240))
    else:
        # clear the image (there is no image data present)
        win['preview'].update('', size=(320, 240))

#set a callback to display the image
db.set_callback('update_elements',display_image)

# Update the image right off the bat for our first run.  The update_elements callback will take care of this the rest of the time
display_image(db,win)
while True:
    event,values=win.read()
    if event==sg.WINDOW_CLOSED or event == 'Exit':
        break
    db.process_events(event,values)
win.close()

