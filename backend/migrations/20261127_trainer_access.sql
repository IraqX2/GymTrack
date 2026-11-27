-- GymTrack trainer-account linking and progress history.
-- Apply this once to the Supabase PostgreSQL database before deploying this branch.
-- Existing trainer rows remain unlinked until an admin adds them again through the app.
ALTER TABLE public.trainer
    ADD COLUMN IF NOT EXISTS user_id BIGINT NULL REFERENCES public."user"(id);

CREATE UNIQUE INDEX IF NOT EXISTS uq_trainer_user_id
    ON public.trainer (user_id)
    WHERE user_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS public.trainer_progress (
    id SERIAL PRIMARY KEY,
    assignment_id INTEGER NOT NULL REFERENCES public.workout_assignment(id) ON DELETE CASCADE,
    member_id INTEGER NOT NULL REFERENCES public.member(id) ON DELETE CASCADE,
    trainer_id INTEGER NOT NULL REFERENCES public.trainer(id) ON DELETE CASCADE,
    completion_percent INTEGER NOT NULL CHECK (completion_percent >= 0 AND completion_percent <= 100),
    notes VARCHAR(1000) NOT NULL DEFAULT '',
    progress_date DATE NOT NULL DEFAULT CURRENT_DATE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_trainer_progress_assignment_id
    ON public.trainer_progress (assignment_id);
CREATE INDEX IF NOT EXISTS ix_trainer_progress_member_id
    ON public.trainer_progress (member_id);
CREATE INDEX IF NOT EXISTS ix_trainer_progress_trainer_id
    ON public.trainer_progress (trainer_id);
