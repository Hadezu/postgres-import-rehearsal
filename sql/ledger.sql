-- Our additions. Original Chinook tables remain structurally unchanged.
CREATE SCHEMA rehearsal;
CREATE TABLE rehearsal.identity (id boolean PRIMARY KEY CHECK (id), target_id uuid NOT NULL);
CREATE TABLE rehearsal.revisions (customer_id integer PRIMARY KEY, revision bigint NOT NULL);
CREATE SEQUENCE rehearsal.revision_seq;
CREATE FUNCTION rehearsal.track_customer() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF TG_OP = 'UPDATE' AND NEW.customer_id <> OLD.customer_id THEN
    RAISE EXCEPTION 'customer primary key is immutable in this adapter';
  END IF;
  INSERT INTO rehearsal.revisions VALUES
    (CASE WHEN TG_OP = 'DELETE' THEN OLD.customer_id ELSE NEW.customer_id END,
     nextval('rehearsal.revision_seq'))
  ON CONFLICT (customer_id) DO UPDATE SET revision = EXCLUDED.revision;
  RETURN NULL;
END $$;
CREATE TRIGGER rehearsal_customer_revision AFTER INSERT OR UPDATE OR DELETE ON public.customer
FOR EACH ROW EXECUTE FUNCTION rehearsal.track_customer();
CREATE TABLE rehearsal.plans (
  id uuid PRIMARY KEY,
  digest text NOT NULL,
  payload jsonb NOT NULL,
  status text NOT NULL DEFAULT 'PLANNED' CHECK (status IN ('PLANNED','APPLIED','UNDONE')),
  receipt jsonb,
  created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE FUNCTION rehearsal.protect_plan() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF TG_OP = 'DELETE' THEN RAISE EXCEPTION 'plans are retained'; END IF;
  IF NEW.id <> OLD.id OR NEW.digest <> OLD.digest OR NEW.payload <> OLD.payload
     OR NEW.created_at <> OLD.created_at THEN RAISE EXCEPTION 'plan is immutable'; END IF;
  IF NOT ((OLD.status='PLANNED' AND NEW.status='APPLIED') OR
          (OLD.status='APPLIED' AND NEW.status='UNDONE')) THEN
    RAISE EXCEPTION 'invalid plan transition';
  END IF;
  IF OLD.status='APPLIED' AND NEW.receipt IS DISTINCT FROM OLD.receipt THEN
    RAISE EXCEPTION 'applied receipt is immutable';
  END IF;
  RETURN NEW;
END $$;
CREATE TRIGGER immutable_plan BEFORE UPDATE OR DELETE ON rehearsal.plans
FOR EACH ROW EXECUTE FUNCTION rehearsal.protect_plan();
CREATE TABLE rehearsal.events (
  id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  plan_id uuid NOT NULL REFERENCES rehearsal.plans(id),
  action text NOT NULL CHECK (action IN ('APPLY','UNDO')),
  at timestamptz NOT NULL DEFAULT clock_timestamp(),
  UNIQUE (plan_id, action)
);
CREATE FUNCTION rehearsal.no_mutation() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'events are append-only'; END $$;
CREATE TRIGGER immutable_event BEFORE UPDATE OR DELETE ON rehearsal.events
FOR EACH ROW EXECUTE FUNCTION rehearsal.no_mutation();

