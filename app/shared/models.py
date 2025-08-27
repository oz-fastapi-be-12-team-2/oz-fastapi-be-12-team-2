from tortoise.models import Model
from tortoise import fields

class TimestampMixin(Model):
    """타임스탬프 필드를 제공하는 믹스인"""
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        abstract = True # 실제 테이블 생성안됨