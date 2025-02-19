from peewee import *
from flask_security import UserMixin, RoleMixin
import ast

user_db = SqliteDatabase('users.db')

class Role(RoleMixin, user_db.Model):
    name = CharField(unique=True)
    description = TextField(null=True)
    permissions = TextField(default="[]")

    #NOTE: the default method flask-security uses is broken
    #so this shim is here instead
    def get_permissions(self): 
        return ast.literal_eval(self.permissions)



# N.B. order is important since db.Model also contains a get_id() -
# we need the one from UserMixin.
class User(UserMixin, user_db.Model):
    email = TextField()
    username = TextField()
    password = TextField()
    active = BooleanField(default=True)
    fs_uniquifier = TextField(null=False)
    confirmed_at = DateTimeField(null=True)

    @staticmethod
    def all() -> list['User']:
        return list(User.select())

class UserRoles(user_db.Model):
    # Because peewee does not come with built-in many-to-many
    # relationships, we need this intermediary class to link
    # user to roles.
    user = ForeignKeyField(User, related_name='roles')
    role = ForeignKeyField(Role, related_name='users')
    name = property(lambda self: self.role.name)
    description = property(lambda self: self.role.description)

    def get_permissions(self):
        return self.role.get_permissions()


    class Meta:
        database = user_db