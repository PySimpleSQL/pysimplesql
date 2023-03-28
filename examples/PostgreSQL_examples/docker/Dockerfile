FROM postgres

ENV POSTGRES_USER=pysimplesql_user
ENV POSTGRES_PASSWORD=pysimplesql
ENV POSTGRES_DB=pysimplesql_examples
ENV PGDATA=/data/pysimplesql_examples

COPY ./Journal.sql /docker-entrypoint-initdb.d/Journal.sql
RUN chown postgres:postgres /docker-entrypoint-initdb.d/Journal.sql

EXPOSE 5432