from __future__ import annotations

from tortoise import fields
from tortoise.models import Model


class Tag(Model):
    id = fields.IntField(pk=True, generated=True)
    name = fields.CharField(max_length=50, unique=True)

    class Meta:
        table = "tags"
