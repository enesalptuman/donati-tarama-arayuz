"""ilk şema — taramalar tablosu

Revision ID: 0001_ilk_sema
Revises:
Create Date: 2026-07-21

Bu ilk migration, app/db_models.py'deki TaramaKaydi tablosunu oluşturur.
Sonraki şema değişiklikleri `alembic revision --autogenerate` ile üretilecek.
"""

import sqlalchemy as sa

from alembic import op

# Alembic tarafından kullanılan revizyon kimlikleri
revision = "0001_ilk_sema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "taramalar",
        sa.Column("tarama_id", sa.String(64), primary_key=True),
        sa.Column("operator", sa.String(200), nullable=False),
        sa.Column("konum_etiketi", sa.String(300), nullable=False),
        sa.Column("eleman_tipi", sa.String(20), nullable=False),
        sa.Column("gerekli_pas_payi_mm", sa.Float, nullable=False),
        sa.Column("durum", sa.String(20), nullable=False),
        sa.Column("ilerleme", sa.Integer, nullable=False),
        sa.Column("hata_mesaji", sa.Text, nullable=True),
        sa.Column("tarih", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sonuc_json", sa.Text, nullable=True),
        sa.Column("olusturma_zamani", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("taramalar")
