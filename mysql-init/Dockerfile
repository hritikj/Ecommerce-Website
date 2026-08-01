FROM mysql:8.0

ENV MYSQL_ROOT_PASSWORD=root

COPY mysql-init/ /docker-entrypoint-initdb.d/

EXPOSE 3306

HEALTHCHECK --interval=5s --timeout=5s --retries=10 \
  CMD mysqladmin ping -h localhost -proot || exit 1
