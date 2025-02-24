import uuid
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
    id = AutoField()
    email = TextField(null=True)
    username = TextField()
    password = TextField()
    active = BooleanField(default=True)
    fs_uniquifier = TextField(default=lambda: str(uuid.uuid4()))
    #confirmed_at = DateTimeField(null=True)

    @staticmethod
    def all() -> list['User']:
        return list(User.select())
    
    @staticmethod
    def get_by_uid(u: str) -> 'User':
        sel = User.select().where(User.fs_uniquifier == u)
        return sel.first()
    
    @staticmethod
    def get_by_username(uid: str) -> 'User':
        sel = User.select().where(User.username == uid)
        return sel.first()
        
    
    @staticmethod
    def add_user(username: str, hashed_password: str):
        user = User.get_or_create(
             username = username,
             password = hashed_password
        )
        return user

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