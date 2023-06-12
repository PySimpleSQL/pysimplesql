import logging
import platform

import PySimpleGUI as sg
import pysimplesql as ss
from pysimplesql.docker_utils import *

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
    "marker_sort_asc": " ⬇",
    "marker_sort_desc": " ⬆",
}
custom = custom | os_tp
ss.themepack(custom)

# ----------------------------------
# CREATE A DATABASE SELECTION WINDOW
# ----------------------------------
layout_selection = [
    [
        sg.B("SQLite", key="sqlite"),
        sg.B("MySQL", key="mysql"),
        sg.B("PostgreSQL", key="postgres"),
        sg.B("SQLServer", key="sqlserver"),
    ]
]
win = sg.Window("SELECT A DATABASE TO USE", layout=layout_selection, finalize=True)
selected_driver = None
while True:
    event, values = win.read()
    # Set SQLite as default if popup closed without selection
    selected_driver = "sqlite" if (event == sg.WIN_CLOSED or event == "Exit") else event
    break
win.close()

database = selected_driver

port = {
    "mysql": 3306,
    "postgres": 5432,
    "sqlserver": 1433,
}

if database != "sqlite":
    docker_image = f"pysimplesql/examples:{database}"
    docker_image_pull(docker_image)
    docker_container = docker_container_start(
        image=docker_image,
        container_name=f"pysimplesql-examples-{database}",
        ports={f"{port[database]}/tcp": ("127.0.0.1", port[database])},
    )


class Template:
    def __init__(self, template_string):
        self.template_string = template_string

    def render(self, context):
        output = self.template_string

        for key, value in context.items():
            placeholder = "{{" + key + "}}"
            output = output.replace(placeholder, str(value))

        return output


# SQL Statement
# ======================================================================================
sql = """
CREATE TABLE customers (
    customer_id {{pk_type}} NOT NULL PRIMARY KEY {{autoincrement}},
    name {{text_type}} NOT NULL,
    email {{text_type}}
);

CREATE TABLE orders (
    order_id {{pk_type}} NOT NULL PRIMARY KEY {{autoincrement}},
    customer_id {{integer_type}} NOT NULL,
    date DATE NOT NULL DEFAULT ({{date_default}}),
    total {{real_type}},
    completed {{boolean_type}} NOT NULL,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
);

CREATE TABLE products (
    product_id {{pk_type}} NOT NULL PRIMARY KEY {{autoincrement}},
    name {{text_type}} NOT NULL DEFAULT {{default_string}},
    price {{real_type}} NOT NULL,
    inventory {{integer_type}} DEFAULT 0
);

CREATE TABLE order_details (
    order_detail_id {{pk_type}} NOT NULL PRIMARY KEY {{autoincrement}},
    order_id {{integer_type}},
    product_id {{integer_type}} NOT NULL,
    quantity {{integer_type}},
    price {{real_type}},
    subtotal {{generated_column}},
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
SELECT customer_id, {{orders_select}}, {{false_int}}
FROM customers
ORDER BY {{random_function}} {{limit_100}};

INSERT INTO order_details (order_id, product_id, quantity)
SELECT O.order_id, P.product_id, {{details_select}}
FROM orders O
JOIN (SELECT product_id FROM products ORDER BY {{random_function}} {{limit_25}}) P
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
"""  # noqa E501

compatibility = {
    "sqlite": {
        "pk_type": "INTEGER",
        "text_type": "TEXT",
        "integer_type": "INTEGER",
        "date_type": "DATE",
        "real_type": "REAL",
        "date_default": "date('now')",
        "boolean_type": "BOOLEAN",
        "default_string": "'New Product'",
        "default_boolean": "0",
        "generated_column": "REAL GENERATED ALWAYS AS (price * quantity) STORED",
        "autoincrement": "AUTOINCREMENT",
        "random_function": "RANDOM()",
        "details_select": "(ABS(RANDOM()) % 10) + 1",
        "orders_select": "DATE('now', '-' || (ABS(RANDOM()) % 30) || ' days')",
        "limit_100": "LIMIT 100",
        "limit_25": "LIMIT 25",
        "false_int": 0,
    },
    "mysql": {
        "pk_type": "INTEGER",
        "text_type": "VARCHAR(255)",
        "integer_type": "INTEGER",
        "real_type": "DECIMAL(10,2)",
        "date_type": "DATE",
        "date_default": "CURRENT_DATE()",
        "boolean_type": "BOOLEAN",
        "default_string": "'New Product'",
        "default_boolean": "FALSE",
        "generated_column": "DECIMAL(10,2) GENERATED ALWAYS AS (`price` * `quantity`) STORED",  # noqa E501
        "autoincrement": "AUTO_INCREMENT",
        "random_function": "RAND()",
        "details_select": "(CAST(ABS(RAND()) % 10 AS UNSIGNED) + 1)",
        "orders_select": "DATE_SUB(CURDATE(), INTERVAL (ABS(RAND()) % 30) DAY)",
        "limit_100": "LIMIT 100",
        "limit_25": "LIMIT 25",
        "false_int": 0,
    },
    "postgres": {
        "pk_type": "SERIAL",
        "text_type": "VARCHAR(255)",
        "integer_type": "INTEGER",
        "real_type": "NUMERIC(10,2)",
        "date_type": "DATE",
        "date_default": "CURRENT_DATE",
        "boolean_type": "BOOLEAN",
        "default_string": "'New Product'",
        "default_boolean": "FALSE",
        "generated_column": "NUMERIC(10,2) GENERATED ALWAYS AS (price * quantity) STORED",  # noqa E501
        "autoincrement": "",
        "random_function": "RANDOM()",
        "details_select": "((CAST((TRUNC(ABS(RANDOM()) * 1000000)) AS INTEGER) % 10) + 1)",
        "orders_select": "CURRENT_DATE - INTERVAL '1' * (CAST(FLOOR(ABS(RANDOM()) * 30) AS INTEGER))",
        "limit_100": "LIMIT 100",
        "limit_25": "LIMIT 25",
        "false_int": False,
    },
    "sqlserver": {
        "pk_type": "INT IDENTITY(1,1)",
        "text_type": "VARCHAR(255)",
        "integer_type": "INT",
        "real_type": "DECIMAL(10,2)",
        "date_type": "DATE",
        "date_default": "GETDATE()",
        "boolean_type": "BIT",
        "default_string": "'New Product'",
        "default_boolean": "0",
        "generated_column": "AS ([price] * [quantity]) PERSISTED",
        "autoincrement": "",
        "random_function": "ABS(CHECKSUM(NEWID()))",
        "details_select": "(CAST(FLOOR(ABS(CHECKSUM(NEWID())) % 10) + 1 AS INT))",
        "orders_select": "DATEADD(DAY, -ABS(CHECKSUM(NEWID())) % 30, GETDATE())",
        "limit_100": "OFFSET 0 ROWS FETCH NEXT 100 ROWS ONLY",
        "limit_25": "OFFSET 0 ROWS FETCH NEXT 25 ROWS ONLY",
        "false_int": 0,
    },
}
# Perform the template replacement based on the target database
template = Template(sql)
sql = template.render(compatibility[database])
print(sql)
# -------------------------
# CREATE PYSIMPLEGUI LAYOUT
# -------------------------

# fmt: off
# Create a basic menu
menu_def = [
    ["&File",["&Save","&Requery All",],],
    ["&Edit", ["&Edit products", "&Edit customers"]],
]
# fmt: on
layout = [[sg.Menu(menu_def, key="-MENUBAR-", font="_ 12")]]

# Define the columns for the table selector using the TableHeading class.
order_heading = ss.TableHeadings(
    # Click a heading to sort
    sort_enable=True,
    # Double-click a cell to make edits.
    # Exempted: Primary Key columns, Generated columns, and columns set as readonly
    edit_enable=True,
    # Click 💾 in sg.Table Heading to trigger DataSet.save_record()
    save_enable=True,
    # Filter rows as you type in the search input
    apply_search_filter=True,
)

# Add columns
order_heading.add_column(column="order_id", heading_column="ID", width=5)
order_heading.add_column("customer_id", "Customer", 30)
order_heading.add_column("date", "Date", 20)
order_heading.add_column(
    "total", "total", width=10, readonly=True
)  # set to True to disable editing for individual columns!)
order_heading.add_column("completed", "✔", 8)

# Layout
layout.append(
    [
        [sg.Text("Orders", font="_16")],
        [
            ss.selector(
                "orders",
                sg.Table,
                num_rows=5,
                headings=order_heading,
                row_height=25,
            )
        ],
        [ss.actions("orders")],
        [sg.Sizer(h_pixels=0, v_pixels=20)],
    ]
)

# order_details TableHeadings:
details_heading = ss.TableHeadings(sort_enable=True, edit_enable=True, save_enable=True)
details_heading.add_column("product_id", "Product", 30)
details_heading.add_column("quantity", "quantity", 10)
details_heading.add_column("price", "price/Ea", 10, readonly=True)
details_heading.add_column("subtotal", "subtotal", 10)

orderdetails_layout = [
    [sg.Sizer(h_pixels=0, v_pixels=10)],
    [ss.field("orders.customer_id", sg.Combo, label="Customer")],
    [
        ss.field("orders.date", label="Date"),
    ],
    [ss.field("orders.completed", sg.Checkbox, default=False)],
    [
        ss.selector(
            "order_details",
            sg.Table,
            num_rows=10,
            headings=details_heading,
            row_height=25,
        )
    ],
    [ss.actions("order_details", default=False, save=True, insert=True, delete=True)],
    [ss.field("order_details.product_id", sg.Combo)],
    [ss.field("order_details.quantity")],
    [ss.field("order_details.price", sg.Text)],
    [ss.field("order_details.subtotal", sg.Text)],
    [sg.Sizer(h_pixels=0, v_pixels=10)],
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

# Expand our sg.Tables so they fill the screen
win["orders:selector"].expand(True, True)
win["orders:selector"].table_frame.pack(expand=True, fill="both")
win["order_details:selector"].expand(True, True)
win["order_details:selector"].table_frame.pack(expand=True, fill="both")

# Init pysimplesql Driver and Form
# --------------------------------
if database == "sqlite":
    # Create sqlite driver, keeping the database in memory
    driver = ss.Driver.sqlite(":memory:", sql_commands=sql)
elif database == "mysql":
    mysql_docker = {
        "user": "pysimplesql_user",
        "password": "pysimplesql",
        "host": "127.0.0.1",
        "database": "pysimplesql_examples",
    }
    driver = ss.Driver.mysql(**mysql_docker, sql_commands=sql)
elif database == "postgres":
    postgres_docker = {
        "host": "localhost",
        "user": "pysimplesql_user",
        "password": "pysimplesql",
        "database": "pysimplesql_examples",
    }
    driver = ss.Driver.postgres(**postgres_docker, sql_commands=sql)
elif database == "sqlserver":
    sqlserver_docker = {
        "host": "127.0.0.1",
        "user": "pysimplesql_user",
        "password": "Pysimplesql!",
        "database": "pysimplesql_examples",
    }
    driver = ss.Driver.sqlserver(**sqlserver_docker, sql_commands=sql)
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
def update_orders(frm_reference, window, data_key):
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

print(frm["orders"].set_by_pk(1))
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
        "current_row_updated" in event
        and values["current_row_updated"]["data_key"] == "order_details"
    ):
        dataset = frm["order_details"]
        current_row = dataset.get_current_row()
        # after a product and quantity is entered, grab price & save
        if (
            dataset.row_count
            and current_row["product_id"] not in [None, ss.PK_PLACEHOLDER]
            and current_row["quantity"]
        ):
            # get product_id
            product_id = current_row["product_id"]
            # get products rows df reference
            product_df = frm["products"].rows
            # set current rows 'price' to match price as matching product_id
            dataset["price"] = product_df.loc[
                product_df["product_id"] == product_id, "price"
            ].values[0]
            # save the record
            dataset.save_record(display_message=False)

    # ----------------------------------------------------

    # Display the quick_editor for products and customers
    elif "Edit products" in event:
        frm["products"].quick_editor()
    elif "Edit customers" in event:
        frm["customers"].quick_editor()
    # call a Form-level save
    elif "Save" in event:
        frm.save_records()
    # call a Form-level requery
    elif "Requery All" in event:
        frm.requery_all()
    else:
        logger.info(f"This event ({event}) is not yet handled.")
