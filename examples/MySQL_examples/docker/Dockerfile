# dump build stage
FROM mysql as builder

#RUN ["sed", "-i", "s/exec \"$@\"/echo \"skipping...\"/", "/usr/local/bin/docker-entrypoint.sh"]
ENV MYSQL_USER=pysimplesql_user
ENV MYSQL_PASSWORD=pysimplesql
ENV MYSQL_ROOT_PASSWORD=pysimplesq
ENV MYSQL_DATABASE=pysimplesql_examples

COPY Journal.sql /docker-entrypoint-initdb.d/Journal.sql

