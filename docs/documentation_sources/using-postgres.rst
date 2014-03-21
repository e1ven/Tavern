Using Postgresql
================

# Tavern works with either MongoDB or Postgres.
# The support for postgres is not as well tested as other parts of Tavern-
# It works reasonably well, but there's more work to do.

# You'll likely want to use  http://postgresapp.com/ instead of compiling postgres yourself.
# I'd suggest version > 9.2.4.3 (https://s3-eu-west-1.amazonaws.com/eggerapps.at/postgresapp/PostgresApp-9.2.4.3-Beta2.zip)

PATH="/Applications/Postgres.app/Contents/MacOS/bin:$PATH"


# Create Tavern DB
createdb -O`whoami` -Eutf8 Tavern
psql -d Tavern -c "CREATE EXTENSION plv8"

cd /opt/Tavern/libs
git clone https://github.com/JerrySievert/mongolike.git
cd mongolike

psql Tavern < create_collection.sql
psql Tavern < drop_collection.sql
psql Tavern < find.sql
psql Tavern < mapreduce.sql
psql Tavern < save.sql
psql Tavern < whereclause.sql



#
# select save('test','"{\"f\": 1}"');
# select find('test','"{}"');
