import logging
import platform
import re
import PySimpleGUI as sg
import pysimplesql as ss

# PySimpleGUI options
# -----------------------------
sg.change_look_and_feel("SystemDefaultForReal")
sg.set_options(font=("Arial", 11), dpi_awareness=True)

# Setup Logger
# -----------------------------
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)
# Set up the appropriate theme depending on the OS
# -----------------------------
if platform.system() == "Windows":
    # Use the xpnative theme, and the `crystal_remix` iconset
    os_ttktheme = "xpnative"
    os_tp = ss.tp_crystal_remix
else:
    # Use the defaults for the OS
    os_ttktheme = "default"
    os_tp = ss.ThemePack.default

# Generate the custom themepack
# -----------------------------
custom = {
    "ttk_theme": os_ttktheme,
    "marker_sort_asc": " ⬇ ",
    "marker_sort_desc": " ⬆ ",
}
custom = custom | os_tp
ss.themepack(custom)


# create your own validator to be passed to a
# frm[DATA_KEY].column_info[COLUMN_NAME].custom_validate_fn
# used below in the quick_editor arguments
def is_valid_email(email: str):
    valid_email = re.match(r"^[\w\.-]+@[\w\.-]+\.\w+$", email) is not None
    if not valid_email:
        return ss.ValidateResponse(
            ss.ValidateRule.CUSTOM, email, " is not a valid email"
        )
    return ss.ValidateResponse()


quick_editor_kwargs = {
    "column_attributes": {
        "email": {"custom_validate_fn": lambda value: is_valid_email(value)}
    }
}


# SQL Statement
# ======================================================================================

sql = """
CREATE TABLE customers (
    customer_id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT
);

CREATE TABLE orders (
    order_id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER NOT NULL,
    date DATE NOT NULL DEFAULT (date('now')),
    total DECTEXT(10,2),
    completed BOOLEAN NOT NULL,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
);

CREATE TABLE products (
    product_id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL DEFAULT 'New Product',
    price DECTEXT(10,2) NOT NULL,
    inventory INTEGER DEFAULT 0
);

CREATE TABLE order_details (
    order_detail_id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER,
    product_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL,
    price DECTEXT(10,2),
    subtotal DECTEXT(10,2) GENERATED ALWAYS AS (price * quantity) STORED,
    FOREIGN KEY (order_id) REFERENCES orders(order_id) ON UPDATE CASCADE ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(product_id)
);

INSERT INTO customers (name, email) VALUES
    ('Alice Rodriguez', 'rodriguez.alice@example.com'),
    ('Bryan Patel', 'patel.bryan@example.com'),
    ('Cassandra Kim', 'kim.cassandra@example.com'),
    ('David Nguyen', 'nguyen.david@example.com'),
    ('Ella Singh', 'singh.ella@example.com'),
    ('Franklin Gomez', 'gomez.franklin@example.com'),
    ('Gabriela Ortiz', 'ortiz.gabriela@example.com'),
    ('Henry Chen', 'chen.henry@example.com'),
    ('Isabella Kumar', 'kumar.isabella@example.com'),
    ('Jonathan Lee', 'lee.jonathan@example.com'),
    ('Katherine Wright', 'wright.katherine@example.com'),
    ('Liam Davis', 'davis.liam@example.com'),
    ('Mia Ali', 'ali.mia@example.com'),
    ('Nathan Kim', 'kim.nathan@example.com'),
    ('Oliver Brown', 'brown.oliver@example.com'),
    ('Penelope Martinez', 'martinez.penelope@example.com'),
    ('Quentin Carter', 'carter.quentin@example.com'),
    ('Rosa Hernandez', 'hernandez.rosa@example.com'),
    ('Samantha Jones', 'jones.samantha@example.com'),
    ('Thomas Smith', 'smith.thomas@example.com'),
    ('Uma Garcia', 'garcia.uma@example.com'),
    ('Valentina Lopez', 'lopez.valentina@example.com'),
    ('William Park', 'park.william@example.com'),
    ('Xander Williams', 'williams.xander@example.com'),
    ('Yara Hassan', 'hassan.yara@example.com'),
    ('Zoe Perez', 'perez.zoe@example.com');

INSERT INTO products (name, price, inventory) VALUES
    ('Thingamabob', 5.00, 200),
    ('Doohickey', 15.00, 75),
    ('Whatchamacallit', 25.00, 50),
    ('Gizmo', 10.00, 100),
    ('Widget', 20.00, 60),
    ('Doodad', 30.00, 40),
    ('Sprocket', 7.50, 150),
    ('Flibbertigibbet', 12.50, 90),
    ('Thingamajig', 22.50, 30),
    ('Dooberry', 17.50, 50),
    ('Whirligig', 27.50, 25),
    ('Gadget', 8.00, 120),
    ('Contraption', 18.00, 65),
    ('Thingummy', 28.00, 35),
    ('Dinglehopper', 9.50, 100),
    ('Doodlywhatsit', 19.50, 55),
    ('Whatnot', 29.50, 20),
    ('Squiggly', 6.50, 175),
    ('Fluffernutter', 11.50, 80),
    ('Goober', 21.50, 40),
    ('Doozie', 16.50, 60),
    ('Whammy', 26.50, 30),
    ('Thingy', 7.00, 130),
    ('Doodadery', 17.00, 70);

INSERT INTO orders (customer_id, date, completed)
SELECT customer_id, DATE('now', '-' || (ABS(RANDOM()) % 30) || ' days'), 0
FROM customers
ORDER BY RANDOM() LIMIT 100;

INSERT INTO order_details (order_id, product_id, quantity)
SELECT O.order_id, P.product_id, (ABS(RANDOM()) % 10) + 1
FROM orders O
JOIN (SELECT product_id FROM products ORDER BY RANDOM() LIMIT 25) P
ON 1=1
ORDER BY 1;

UPDATE order_details
    SET price = (
        SELECT products.price FROM products WHERE products.product_id = order_details.product_id
);

UPDATE orders
    SET total = (
        SELECT SUM(subtotal) FROM order_details WHERE order_details.order_id = orders.order_id
);
"""

# -------------------------
# CREATE PYSIMPLEGUI LAYOUT
# -------------------------

# fmt: off
# Create a basic menu
menu_def = [
    ["&File",["&Save","&Requery All",],],
    ["&Edit", ["&Edit Products", "&Edit Customers"]],
]
# fmt: on
layout = [[sg.Menu(menu_def, key="-MENUBAR-", font="_ 12")]]

# Set our universal table options
table_style = ss.TableStyler(
    row_height=25,
    expand_x=True,
    expand_y=True,
    frame_pack_kwargs={"expand": True, "fill": "both"},
)

# Define the columns for the table selector using the Tabletable class.
order_table = ss.TableBuilder(
    num_rows=5,
    sort_enable=True,  # Click a table to sort
    allow_cell_edits=True,  # Double-click a cell to make edits.
    # Exempted: Primary Key columns, Generated columns, and columns set as readonly
    apply_search_filter=True,  # Filter rows as you type in the search input
    lazy_loading=True,  # For larger DataSets, inserts slice of rows. See `LazyTable`
    add_save_heading_button=True,  # Click 💾 in sg.Table Heading to trigger DataSet.save_record()
    style=table_style,
)

# Add columns
order_table.add_column(column="order_id", heading="ID", width=5)
order_table.add_column("customer_id", "Customer", 30)
order_table.add_column("date", "Date", 20)
order_table.add_column(
    column="total",
    heading="Total",
    width=10,
    readonly=True,  # set to True to disable editing for individual columns!
    col_justify="right",  # default, "left". Available: "left", "right", "center"
)
order_table.add_column("completed", "✔", 8)

# Layout
layout.append(
    [
        [sg.Text("Orders", font="_16")],
        [
            ss.selector(
                "orders",
                order_table,
            )
        ],
        [ss.actions("orders")],
        [sg.Sizer(h_pixels=0, v_pixels=20)],
    ]
)

# order_details TableBuilder:
details_table = ss.TableBuilder(
    num_rows=10,
    sort_enable=True,
    allow_cell_edits=True,
    add_save_heading_button=True,
    style=table_style,
)
details_table.add_column("product_id", "Product", 30)
details_table.add_column("quantity", "Quantity", 10, col_justify="right")
details_table.add_column("price", "Price/Ea", 10, readonly=True, col_justify="right")
details_table.add_column("subtotal", "Subtotal", 10, readonly=True, col_justify="right")

orderdetails_layout = [
    [sg.Sizer(h_pixels=0, v_pixels=10)],
    [
        ss.field(
            "orders.customer_id",
            sg.Combo,
            label="Customer",
            quick_editor_kwargs=quick_editor_kwargs,
        )
    ],
    [
        ss.field("orders.date", label="Date"),
    ],
    [ss.field("orders.completed", sg.Checkbox, default=False)],
    [
        ss.selector(
            "order_details",
            details_table,
        )
    ],
    [ss.actions("order_details", default=False, save=True, insert=True, delete=True)],
    [ss.field("order_details.product_id", sg.Combo)],
    [ss.field("order_details.quantity")],
    [ss.field("order_details.price", sg.Text)],
    [ss.field("order_details.subtotal", sg.Text)],
    [sg.Sizer(h_pixels=0, v_pixels=10)],
    [sg.StatusBar(" " * 100, key="info_msg", metadata={"type": ss.ElementType.INFO})],
]

layout.append([sg.Frame("Order Details", orderdetails_layout, expand_x=True)])

win = sg.Window(
    "Order Example",
    layout,
    finalize=True,
    # Below is Important! pysimplesql progressbars/popups/quick_editors use
    # ttk_theme and icon as defined in themepack.
    ttk_theme=os_ttktheme,
    icon=ss.themepack.icon,
)

# Init pysimplesql Driver and Form
# --------------------------------

# Create sqlite driver, keeping the database in memory
driver = ss.Driver.sqlite(":memory:", sql_commands=sql)
frm = ss.Form(
    driver,
    bind_window=win,
    live_update=True,  # this updates the `Selector`, sg.Table as we type in fields.
)
# Few more settings
# -----------------

frm.edit_protect()  # Comment this out to edit protect when the window is created.
# Reverse the default sort order so orders are sorted by date
frm["orders"].set_order_clause("ORDER BY date ASC")
# Requery the data since we made changes to the sort order
frm["orders"].requery()
# Set the column order for search operations.
frm["orders"].set_search_order(["customer_id", "order_id"])


# Application-side code to update orders `total`
# when saving/deleting order_details line item
# ----------------------------------------------
def update_orders(frm_reference, window, data_key) -> bool:
    if data_key == "order_details":
        order_id = frm["order_details"]["order_id"]
        driver.execute(
            f"UPDATE orders "
            f"SET total = ("
            f"    SELECT SUM(subtotal)"
            f"    FROM order_details"
            f"    WHERE order_details.order_id = {order_id}) "
            f"WHERE orders.order_id = {order_id};"
        )
        # do our own subtotal/total summing to avoid requerying
        frm["order_details"]["subtotal"] = (
            frm["order_details"]["price"] * frm["order_details"]["quantity"]
        )
        frm["orders"]["total"] = frm["order_details"].rows["subtotal"].sum()
        frm["orders"].save_record(display_message=False)
        frm.update_selectors("orders")
        frm.update_selectors("ordersDetails")
    return True


# set this to be called after a save or delete of order_details
frm["order_details"].set_callback("after_save", update_orders)
frm["order_details"].set_callback("after_delete", update_orders)

# ---------
# MAIN LOOP
# ---------
while True:
    event, values = win.read()
    if event == sg.WIN_CLOSED or event == "Exit":
        frm.close()  # <= ensures proper closing of the sqlite database
        win.close()
        break
    # <=== let PySimpleSQL process its own events! Simple!
    elif ss.process_events(event, values):
        logger.info(f"PySimpleDB event handler handled the event {event}!")
    # Code to automatically save and refresh order_details:
    # ----------------------------------------------------
    elif (
        "after_record_edit" in event
        and values["after_record_edit"]["data_key"] == "order_details"
    ):
        dataset = frm["order_details"]
        current_row = dataset.current.get()
        # after a product and quantity is entered, grab price & save
        if (
            dataset.row_count
            and current_row["product_id"] not in [None, ss.PK_PLACEHOLDER]
            and current_row["quantity"] not in ss.EMPTY
        ):
            # get product_id
            product_id = current_row["product_id"]
            # get products rows df reference
            product_df = frm["products"].rows
            # set current rows 'price' to match price as matching product_id
            dataset["price"] = product_df.loc[
                product_df["product_id"] == product_id, "price"
            ].to_numpy()[0]
            # save the record
            dataset.save_record(display_message=False)

    # ----------------------------------------------------

    # Display the quick_editor for products and customers
    elif "Edit Products" in event:
        frm["products"].quick_editor()
    elif "Edit Customers" in event:
        frm["customers"].quick_editor(**quick_editor_kwargs)
    # call a Form-level save
    elif "Save" in event:
        frm.save_records()
    # call a Form-level requery
    elif "Requery All" in event:
        frm.requery_all()
    else:
        logger.info(f"This event ({event}) is not yet handled.")
