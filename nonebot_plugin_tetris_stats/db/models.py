from tortoise.fields import (
    BinaryField,
    # BooleanField,
    CharField,
    DatetimeField,
    IntField,
    JSONField,
    TextField,
)
from tortoise.models import Model


class Bind(Model):
    id = IntField(pk=True, generated=True)
    qq = CharField(max_length=16, null=True, index=True)
    IO = CharField(max_length=32, null=True)
    # IO_verify = BooleanField(null=True)
    TOP = CharField(max_length=16, null=True)
    # TOP_verify = BooleanField(null=True)


class Historical_Data(Model):
    id = IntField(pk=True, generated=True)
    receive_time = DatetimeField(null=True)
    game_type = CharField(max_length=16, null=True)
    bot_id = CharField(max_length=16, null=True)
    source_type = CharField(max_length=16, null=True)
    source_id = TextField(null=True)
    message_id = IntField(null=True, index=True)
    message = TextField(null=True)
    call_time = DatetimeField(null=True)
    command_type = CharField(max_length=16, null=True)
    command_args = TextField(null=True)
    user = JSONField(null=True)
    response = JSONField(null=True)
    processed_data = JSONField(null=True)
    return_message = BinaryField(null=True)
    send_time = DatetimeField(null=True)


class Version(Model):
    version = CharField(max_length=16)
