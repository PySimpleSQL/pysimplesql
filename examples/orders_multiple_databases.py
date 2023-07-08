import logging
import platform
import re

import numpy as np
import pandas as pd
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
# fmt: off
icons = {   'msaccess': b'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',
    'mysql': b'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',
    'postgres': b'iVBORw0KGgoAAAANSUhEUgAAAC8AAAAsCAYAAAD1s+ECAAAAAXNSR0IArs4c6QAAAARnQU1BAACxjwv8YQUAAAAJcEhZcwAADsMAAA7DAcdvqGQAAAASdEVYdFNvZnR3YXJlAEdyZWVuc2hvdF5VCAUAAAnvSURBVGhD7VgJUNTnFY9tczRH06bJpEemaVptp+1MayomZmxs4hjTek11LCbqKFBpTAE5NCCH7nItLsdyX8uxB+wue8ICC7ggyyVgFKyoQFGjUevteI63/vq9z910hf8KHqnTGX8zb2B3v93/773vvd973/cE/o/xmPyjwmPyjwpjIn/z5k2cPn0ajY2NSE5ORnh4ODepVAqDwYD+/n5cunQJ58+fR0dHBxITE7FixQr4+PggICAAkZGR8PPzw/Tp0zF58mR4eXlh0qRJ/P8FCxYgPz8fBw4cwPXr151PHBtGJX/kyBGo1Wr+cLFYDI1Gg9raWtTU1ECn0yEjIwNhYWFYunQplixZgtDQUL6+qakJDoeDr9NqtbDV1aOxvQumTZ0orWtFWUMbbK1daGxqRmpaGnfU5cRYcVfy+/fvh1KphDguHnKdCWuKzFiUYcCc1ArMSanAX9P1WJFrgFhpQVmVDZa6jZCUWbEky4iZyXq8L2Xr2NpP5FYoHT1wDHyJXEcf5mRX4+0kA6almDFbZkKw3IICrRmi2Dikp6dj+/btuHXrlpOFZ3gkf+HCBZ4S4vhESBV6+BbXY2J8BV5ZXYLnggrwPLOXw4rxi3VlCNG3wbh1CNL6rZzQD9aU4ql/5OEbK3P52p+sVWJqsgnLFY1Yb+1GKFs/gX1v3Cc5eCYgH78SabC40IZEpQkxcQnIzc3F0NCQk4lneCS/e/dunhIxqdkILGvE90KK8AR72HB7LUKBAI0D0ZWd+LVYI7jGZS+FFeFPmVbE1mxBmLEdP2bfdX32/KpCLMyvhaiwnO10AioqKnDjxg0nG2F4JG82myHLyERUkR6/T6i4g4TLKHKzs2sQbenErKxq/lponbt9O7AAU6UmpG7shb96E55lOzNu5e3PXgyRI1TdgERZFlJTU3Hx4kUnG2EIkiePMzMzkZAiQ5iilqfHcBJk9OA1xg4EV7Thh5+VCq4RMory+2mV0HYP8sBQirk+8yvdiPisQqSkpODkyZNORsIQJH/58mXk5OQgNj0HvvIanrvuD3fZhJgyiKu78XFRA19DkR9L9CnS5GykuRMS21a8FPrflPRTbERcVgGX5OPHjzsZCUOQPGk2FY0kVw7fkro7HuxuVMAiRn5+vo2Tpwi6R9GTPROYj1+ygl1abMem/oP8/299mst/w6+I5X3a7bQ5d+6ck5EwPJKnyMdn5sOX/ZgrJ4fbH1MsyLD3wtq7F7YdX6B18BBs//wCqw3tjMxIJ0hZPkivgnJzP6q274N2y7/Q/+9TeC/VgmdZLbyyupinqTgpmUf+2rVrTkbCECRPnU4mk0EsTUNgSTVeDJaPIEL2l5xa5Dt2YH1VFxYV1mMd+2vfdYA7Qrvy5LBdeG2tAn7KJpR3DqCkbRc+LXfAypx4S6LnuzGepWFkqQUpaTIoFIpRtV6QPH2puLgYssxsRKtr8Xqk8g4SLpvDFGYN0+wZskoetd/F6eCn2gRJ7efcGVIW9/XUE/yY1gcyaX1bYsA7SUZetBNi1Hyn/sx+b3VqPpI2bEBzc7OTjWcIkifU1dUhm6VOeJ6Gk3In4bLpTDH8ShvxZryO5yupz0+jVPBmxDfUbcV3hu3Yz6LVWMGco4hTCr3Jdse4bQ/vFU8F5PF+EiqScKXZt2+fk4lneCRPLZpadUhSJuax9HAn4bIPZFXwZeQnujn3QnAhZjHtN/fsvUNFyEhyl7H1CWxnaKfIaeO2IU7+R+EKiHUNiBTFQi6X8w4/GjySP3ToEO+w4QnJCNE5BOXSu6AOy0vsLB3Kv3qPyM/OqeG5TB3Vff2TLDVmsIIleXyXjQvjo1XQdA/gDbZb1OTEeSrEJySivr7+wWYb0noqmqg4CaJ1drzAGos7EbJATQt8WQG+Hqn66r3vsi65sLAOWU3becd0X0/GZ6GKVkRaNrNol0Ld2Y+3EvWQ1nQhMDyKq9xYJ0uP5Mlzo9GI+EQJknW1+I3A3BKkbeEt/o0o9VfvUXGn1G/DXJY6lNfu68moiGdmsCmzYzf+wKJfxpTHp9SOUqsdQcEhsFgso0qkCx7JE/r6+pCdnY3QhFQ2NI1sVu+lmrHWvJlrN72mBuXFZI/0myIspPXUgWmnPjN1oLJnD9d7/ZZBhEbGcHkeGBhwPn103JX8iRMn+MEiNFqM2KoO3gXdibzKWjxpOzlASvIyK0JveQNymndwRzyNChR9akzd+45g2/5jqG/ZjL/5/x02m42fxkabJl24K3naPjo1hUdGI6fSjp8zPXYnQU1oLivO0vZdKOsagLRhG8qZbkcwZ4igJ/LjWPGTwiSxwj1x9gLWRkVhypQp8Pb2RlBQEKLY68rKSl53d8NdyRN27twJGZPMGGk612d3EiR9ASo70hVaRMclIltRjt69h1DQ0sdm/BZe5EIOPO3UeBUbExp27kdRhRkZBUWQFRSjWFWO9SIR4uPjcfjwYScLYYxK/syZMzwKK4OCUdxwOz2+ydLnOUZsUUEt0sorEb42Ev7+/sgoLIGydQc/KdG8M55J4PBUI6PmRTvWuPtL+Jc1c+ksZzvXPngQbZ/3QsrmGolEgqNHjzpZCGNU8nRzQIUrYtGQZrCOq2/BJDaDz8+rQUH1Jig1OmzIzEVCoRqiCjsfj6nDbh46DC+2jqI8nPz32Y59LK9HTXcflmXp4ZOpQ3CuFlJ5GeIkG/hBn9L1vgaz4aAistvt8PH1hcZsxTqVFSWV9fxBOr0B1vatEJlasTC7EstyLVDYHOjbc4CR1wmSp266ko3aer0eeXl53OLi4vh1CeV7a2srrly54ny6Z4yJPIHSh646ZsyYgVWrVvH7FrqHoesOOnXRnQ4NU0VFRVj00UdQmaz47XoVIz9SLklGY8psWL58OS9QmmXIkcHBQT6OjxVjJk8gCaM8pKGtp6cHp06d4lGKiYnhzsybNw+LFy/G7DlzoTZYMHGdEk8LHE5oXC60tXHipOv3etnkwj2RJ5ADJGFXr17l9UDbe/bsWX7epL5At2exsXHQmqvgJVaxLjuSPJ1bFfVtCAwMxMGDB8es68Nxz+RHAzlAqWOptmFqopbp/Z05TwOeV7wGhSYbz3FynIJwP3jo5IkMKUWDvREz00z8psCdPF1CfZisR5HWyHN+LIXpCQ+dPCkT3VFarVbMz64acSB5dU0JluSYoSrX8kZ0vylDeOjkqR7oIEND1nqDg0+ZrrMAnbTeTTZCpLbyrk3qNJa53RMeOnnKX8r7iIgIlFfVYVlhDb8he0dqxOwMCyIUVcgrVfHrcVKrB8FDJ08graZrbZJQQ3UdNBvbYWruQo29GbmsIVG69Pb2OlffP74W8gTKZZWKHe9mzeIT47Rp03hDo9PZsWPHnKseDF8b+f8FHpN/VHhM/tEA+A862AXOTURcVwAAAABJRU5ErkJggg==',
    'sqlite': b'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',
    'sqlserver': b'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'}
# fmt: on
layout_selection = [
    [
        [sg.Text("Pick a database to use:", font="_16")],
        [sg.Image(icons["sqlite"]), sg.B("SQLite", key="sqlite")],
        [sg.Image(icons["mysql"]), sg.B("MySQL", key="mysql")],
        [sg.Image(icons["postgres"]), sg.B("PostgreSQL", key="postgres")],
        [sg.Image(icons["sqlserver"]), sg.B("SQLServer", key="sqlserver")],
        [sg.Image(icons["msaccess"]), sg.B("MsAccess", key="msaccess")],
    ]
]
win = sg.Window("Databases", layout=layout_selection, finalize=True)
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

if database not in ["sqlite", "msaccess"]:
    docker_image = f"pysimplesql/examples:{database}"
    docker_image_pull(docker_image)
    docker_container = docker_container_start(
        image=docker_image,
        container_name=f"pysimplesql-examples-{database}",
        ports={f"{port[database]}/tcp": ("127.0.0.1", port[database])},
    )


class SqlFormat(dict):
    def __missing__(self, key):
        return ""


class Template:
    def __init__(self, template_string):
        self.template_string = template_string

    def render(self, context):
        lang_format = SqlFormat(context)
        return self.template_string.format_map(lang_format)


# create your own validator to be passed to a
# frm[DATA_KEY].column_info[COLUMN_NAME].custom_validate_fn
# used below in the quick_editor arguments
def is_valid_email(email):
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
{disable_constraints}
DROP TABLE IF EXISTS customers {cascade};
CREATE TABLE customers (
    customer_id {pk_type} NOT NULL PRIMARY KEY {autoincrement},
    name {text_type} NOT NULL,
    email {text_type}
);

DROP TABLE IF EXISTS orders {cascade};
CREATE TABLE orders (
    order_id {pk_type} NOT NULL PRIMARY KEY {autoincrement},
    customer_id {integer_type} NOT NULL,
    date {date_type} NOT NULL DEFAULT {date_default},
    total {numeric_type},
    completed {boolean_type} NOT NULL,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
);

DROP TABLE IF EXISTS products {cascade};
CREATE TABLE products (
    product_id {pk_type} NOT NULL PRIMARY KEY {autoincrement},
    name {text_type} NOT NULL DEFAULT {default_string},
    price {numeric_type} NOT NULL,
    inventory {integer_type} DEFAULT 0
);

DROP TABLE IF EXISTS order_details {cascade};
CREATE TABLE order_details (
    order_detail_id {pk_type} NOT NULL PRIMARY KEY {autoincrement},
    order_id {integer_type},
    product_id {integer_type} NOT NULL,
    quantity {integer_type} NOT NULL,
    price {numeric_type},
    subtotal {generated_column},
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
"""

# Generate random orders using pandas DataFrame
num_orders = 100
rng = np.random.default_rng()
orders_df = pd.DataFrame(
    {
        "order_id": np.arange(1, num_orders + 1),
        "customer_id": rng.integers(1, 25, size=num_orders),
        "date": pd.date_range(
            start=pd.Timestamp.now().strftime("%Y-%m-%d"), periods=num_orders
        ).date.tolist(),
        "completed": rng.choice(["{true_bool}", "{false_bool}"], size=num_orders),
    }
)

# Generate random order details using pandas DataFrame
num_order_details = num_orders * 5
order_details_df = pd.DataFrame(
    {
        "order_id": rng.choice(
            orders_df["order_id"], size=num_order_details, replace=True
        ),
        "product_id": rng.integers(1, 25, size=num_order_details),
        "quantity": rng.integers(1, 10, size=num_order_details),
    }
)

# Generate the insert statements
sql += "INSERT INTO orders (customer_id, date, completed) VALUES\n"
sql_values = [
    f"({row['customer_id']}, '{row['date']}', {row['completed']})"
    for _, row in orders_df.iterrows()
]
sql_values_str = ", ".join(sql_values)
sql += sql_values_str + ";\n"
sql += "INSERT INTO order_details (order_id, product_id, quantity) VALUES\n"
sql_values = [
    f"({row['order_id']}, {row['product_id']}, {row['quantity']})"
    for _, row in order_details_df.iterrows()
]
sql_values_str = ", ".join(sql_values)
sql += sql_values_str + ";\n"

sql += """
UPDATE order_details
    SET price = (
        SELECT products.price FROM products WHERE products.product_id = order_details.product_id
);

{msaccess_update_subtotal}

UPDATE orders
    SET total = (
        SELECT SUM(subtotal) FROM order_details WHERE order_details.order_id = orders.order_id
);
{enable_constraints}
"""  # noqa E501

sqlserver_disable_constraints = """
DECLARE @sql nvarchar(MAX)
SET @sql = N''

SELECT @sql = @sql + N'ALTER TABLE ' + QUOTENAME(KCU1.TABLE_SCHEMA)
    + N'.' + QUOTENAME(KCU1.TABLE_NAME)
    + N' DROP CONSTRAINT ' -- + QUOTENAME(rc.CONSTRAINT_SCHEMA)  + N'.'  -- not in MS-SQL
    + QUOTENAME(rc.CONSTRAINT_NAME) + N'; ' + CHAR(13) + CHAR(10)
FROM INFORMATION_SCHEMA.REFERENTIAL_CONSTRAINTS AS RC

INNER JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE AS KCU1
    ON KCU1.CONSTRAINT_CATALOG = RC.CONSTRAINT_CATALOG
    AND KCU1.CONSTRAINT_SCHEMA = RC.CONSTRAINT_SCHEMA
    AND KCU1.CONSTRAINT_NAME = RC.CONSTRAINT_NAME

EXECUTE(@sql)
"""

compatibility = {
    "sqlite": {
        "pk_type": "INTEGER",
        "text_type": "TEXT",
        "integer_type": "INTEGER",
        "date_type": "DATE",
        "numeric_type": "DECTEXT(10,2)",
        "date_default": "(date('now'))",
        "boolean_type": "BOOLEAN",
        "default_string": "'New Product'",
        "default_boolean": "0",
        "generated_column": "NUMERIC(10,2) GENERATED ALWAYS AS (price * quantity) STORED",
        "autoincrement": "AUTOINCREMENT",
        "false_bool": 0,
        "true_bool": 1,
    },
    "mysql": {
        "pk_type": "INTEGER",
        "text_type": "VARCHAR(255)",
        "integer_type": "INTEGER",
        "numeric_type": "DECIMAL(10,2)",
        "date_type": "DATE",
        "date_default": "(CURRENT_DATE())",
        "boolean_type": "BIT",
        "default_string": "'New Product'",
        "default_boolean": "FALSE",
        "generated_column": "DECIMAL(10,2) GENERATED ALWAYS AS (`price` * `quantity`) STORED",  # noqa E501
        "autoincrement": "AUTO_INCREMENT",
        "false_bool": 0,
        "true_bool": 1,
        "disable_constraints": "SET FOREIGN_KEY_CHECKS=0;",
        "enable_constraints": "SET FOREIGN_KEY_CHECKS=1;",
    },
    "postgres": {
        "pk_type": "SERIAL",
        "text_type": "VARCHAR(255)",
        "integer_type": "INTEGER",
        "numeric_type": "NUMERIC(10,2)",
        "date_type": "DATE",
        "date_default": "(CURRENT_DATE)",
        "boolean_type": "BOOLEAN",
        "default_string": "'New Product'",
        "default_boolean": "FALSE",
        "generated_column": "NUMERIC(10,2) GENERATED ALWAYS AS (price * quantity) STORED",  # noqa E501
        "autoincrement": "",
        "false_bool": False,
        "true_bool": True,
        "cascade": "CASCADE",
    },
    "sqlserver": {
        "pk_type": "INT",
        "text_type": "VARCHAR(255)",
        "integer_type": "INT",
        "numeric_type": "DECIMAL(10,2)",
        "date_type": "DATE",
        "date_default": "(CAST(GETDATE() as DATE))",
        "boolean_type": "BIT",
        "default_string": "'New Product'",
        "default_boolean": "0",
        "generated_column": "AS ([price] * [quantity]) PERSISTED",
        "autoincrement": "IDENTITY(1,1)",
        "false_bool": 0,
        "true_bool": 1,
        "disable_constraints": sqlserver_disable_constraints,
    },
    "msaccess": {
        "pk_type": "COUNTER",
        "text_type": "TEXT(255)",
        "integer_type": "LONG",
        "numeric_type": "NUMERIC(10,2)",
        "date_type": "DATETIME",
        "date_default": "'=DATE()'",
        "boolean_type": "BOOLEAN",
        "default_string": "'New Product'",
        "default_boolean": "0",
        "generated_column": "NUMERIC(10,2)",
        "autoincrement": "",
        "false_bool": 0,
        "true_bool": 1,
        "msaccess_update_subtotal": "UPDATE order_details SET subtotal = price * quantity;",
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
    ["&Edit", ["&Edit Products", "&Edit Customers"]],
]
# fmt: on
layout = [[sg.Menu(menu_def, key="-MENUBAR-", font="_ 12")]]

# Define the columns for the table selector using the TableHeading class.
order_heading = ss.TableHeadings(
    sort_enable=True,  # Click a heading to sort
    allow_cell_edits=True,  # Double-click a cell to make edits.
    # Exempted: Primary Key columns, Generated columns, and columns set as readonly
    add_save_heading_button=True,  # Click 💾 in sg.Table Heading to trigger DataSet.save_record()
    apply_search_filter=True,  # Filter rows as you type in the search input
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
details_heading = ss.TableHeadings(
    sort_enable=True, allow_cell_edits=True, add_save_heading_button=True
)
details_heading.add_column("product_id", "Product", 30)
details_heading.add_column("quantity", "quantity", 10)
details_heading.add_column("price", "price/Ea", 10, readonly=True)
details_heading.add_column("subtotal", "subtotal", 10, readonly=True)

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
    [sg.StatusBar(" " * 100, key="info_msg", metadata={"type": ss.TYPE_INFO})],
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
elif database == "msaccess":
    # Import java_helper for msaccess
    import os
    import pathlib
    import sys

    current_dir = pathlib.Path(os.path.dirname(os.path.abspath(__file__)))
    java_install_dir = str(pathlib.Path(current_dir / "MSAccess_examples"))
    sys.path.append(str(java_install_dir))
    from install_java import java_check_install

    # Ensure that Java is installed
    if not java_check_install():
        exit(0)
    driver = ss.Driver.msaccess("orders.accdb", sql_commands=sql, overwrite_file=True)
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
        current_row = dataset.get_current_row()
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
