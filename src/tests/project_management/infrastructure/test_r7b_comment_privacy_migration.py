from datetime import datetime

import sqlalchemy as sa
from alembic import command
from alembic.config import Config


def test_comment_privacy_upgrade_downgrade_preserves_redaction(tmp_path):
    config = Config("src/infra/persistence/migrations/alembic.ini")
    config.set_main_option(
        "sqlalchemy.url", f"sqlite:///{(tmp_path / 'privacy.db').as_posix()}"
    )
    command.upgrade(config, "d1e8c4a3f976")
    engine = sa.create_engine(config.get_main_option("sqlalchemy.url"))
    with engine.begin() as connection:
        connection.execute(
            sa.text(
                "INSERT INTO notifications (id, recipient_user_id, category, title, body, created_at, metadata_json) "
                "VALUES ('old-mention', 'user', 'pm.comment.mentioned.v1', 'Mention', 'Private deleted text', :now, :metadata)"
            ),
            {
                "now": datetime.now().isoformat(" "),
                "metadata": '{"task_id":"private-task"}',
            },
        )
    command.upgrade(config, "a7b19c32d405")
    inspector = sa.inspect(engine)
    assert any(
        fk["constrained_columns"] == ["parent_comment_id", "task_id"]
        for fk in inspector.get_foreign_keys("task_comments")
    )
    with engine.connect() as connection:
        body, metadata = connection.execute(
            sa.text(
                "SELECT body, metadata_json FROM notifications WHERE id='old-mention'"
            )
        ).one()
        assert "Private deleted text" not in body and metadata == "{}"
    command.downgrade(config, "d1e8c4a3f976")
    assert any(
        fk["constrained_columns"] == ["parent_comment_id"]
        for fk in sa.inspect(engine).get_foreign_keys("task_comments")
    )
    command.upgrade(config, "a7b19c32d405")
    with engine.connect() as connection:
        assert (
            connection.scalar(
                sa.text(
                    "SELECT metadata_json FROM notifications WHERE id='old-mention'"
                )
            )
            == "{}"
        )
    engine.dispose()
