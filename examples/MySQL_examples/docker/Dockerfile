FROM mysql:latest

# Set the environment variables for MySQL
ENV MYSQL_DATABASE pysimplesql_examples
ENV MYSQL_USER pysimplesql_user
ENV MYSQL_PASSWORD pysimplesql
ENV MYSQL_ROOT_PASSWORD pysimplesql

# Copy the SQL script to initialize the database
COPY Journal.sql /docker-entrypoint-initdb.d/

