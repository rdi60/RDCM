from django.contrib.postgres.operations import BtreeGistExtension
from django.db import migrations

# This is the load-bearing migration in the whole system: it's what makes
# double-booking a chair or a doctor impossible at the database level,
# independent of application code (see docs/ARCHITECTURE.md §4). The SQL
# below is copied verbatim from db/schema.sql, which was hand-validated
# against a real Postgres 16 instance — including proving both exclusion
# constraints actually reject overlapping inserts and that a cancelled
# appointment doesn't block rebooking. Do not "simplify" this into an ORM
# ExclusionConstraint without re-running those checks.

SET_BLOCKED_UNTIL_TRIGGER_SQL = """
CREATE OR REPLACE FUNCTION set_appointment_blocked_until() RETURNS trigger AS $$
BEGIN
    NEW.blocked_until := NEW.end_time + (NEW.buffer_minutes * interval '1 minute');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_set_blocked_until
    BEFORE INSERT OR UPDATE OF end_time, buffer_minutes ON appointments
    FOR EACH ROW EXECUTE FUNCTION set_appointment_blocked_until();
"""

DROP_TRIGGER_SQL = """
DROP TRIGGER IF EXISTS trg_set_blocked_until ON appointments;
DROP FUNCTION IF EXISTS set_appointment_blocked_until();
"""

ADD_EXCLUSION_CONSTRAINTS_SQL = """
ALTER TABLE appointments
    ADD CONSTRAINT appointments_chair_excl EXCLUDE USING gist (
        chair_id WITH =,
        tstzrange(start_time, blocked_until) WITH &&
    ) WHERE (status NOT IN ('cancelled', 'no_show'));

ALTER TABLE appointments
    ADD CONSTRAINT appointments_doctor_excl EXCLUDE USING gist (
        doctor_id WITH =,
        tstzrange(start_time, end_time) WITH &&
    ) WHERE (status NOT IN ('cancelled', 'no_show'));
"""

DROP_EXCLUSION_CONSTRAINTS_SQL = """
ALTER TABLE appointments DROP CONSTRAINT IF EXISTS appointments_chair_excl;
ALTER TABLE appointments DROP CONSTRAINT IF EXISTS appointments_doctor_excl;
"""


class Migration(migrations.Migration):

    dependencies = [
        ("scheduling", "0001_initial"),
    ]

    operations = [
        BtreeGistExtension(),
        migrations.RunSQL(SET_BLOCKED_UNTIL_TRIGGER_SQL, reverse_sql=DROP_TRIGGER_SQL),
        migrations.RunSQL(ADD_EXCLUSION_CONSTRAINTS_SQL, reverse_sql=DROP_EXCLUSION_CONSTRAINTS_SQL),
    ]
