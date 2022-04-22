from peewee import *
dbName = "data.db"
db = SqliteDatabase(dbName,pragmas={
    'journal_mode': 'wal',
    'cache_size': -1 * 64000,  # 64MB
    'foreign_keys': 1,
    'ignore_check_constraints': 0,
    'synchronous': 0
})
db.connect()
class BaseModel(Model):
    class Meta:
        database =db
class Sensor(BaseModel):
    so2= FloatField(null=False)
    no2= FloatField(null=False)
    co= FloatField(null=False)
    time = IntegerField(null=False)

def creat_table():
    if db.table_exists(table_name='sensor')!=True:
        db.create_tables([Sensor])
def db_close():
    db.close()
