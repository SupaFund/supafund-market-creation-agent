-- Create prediction_markets table to track created markets and prevent duplicates
-- Migration: 001_create_prediction_markets_table.sql

CREATE TABLE public.prediction_markets (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  application_id uuid NOT NULL,
  market_id text NOT NULL,  -- Omen platform market ID
  market_title text NOT NULL,
  market_url text,
  market_question text,
  closing_time timestamp with time zone,
  initial_funds_usd numeric,
  omen_creation_output text,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  updated_at timestamp with time zone NOT NULL DEFAULT now(),
  status text NOT NULL DEFAULT 'created' CHECK (status = ANY (ARRAY['created'::text, 'active'::text, 'closed'::text, 'resolved'::text, 'failed'::text])),
  metadata jsonb DEFAULT '{}'::jsonb,
  
  CONSTRAINT prediction_markets_pkey PRIMARY KEY (id),
  CONSTRAINT prediction_markets_application_id_unique UNIQUE (application_id),
  CONSTRAINT prediction_markets_market_id_unique UNIQUE (market_id),
  CONSTRAINT prediction_markets_application_id_fkey FOREIGN KEY (application_id) REFERENCES public.program_applications(id)
);

-- Add indexes for better performance
CREATE INDEX idx_prediction_markets_application_id ON public.prediction_markets (application_id);
CREATE INDEX idx_prediction_markets_market_id ON public.prediction_markets (market_id);
CREATE INDEX idx_prediction_markets_status ON public.prediction_markets (status);
CREATE INDEX idx_prediction_markets_created_at ON public.prediction_markets (created_at);

-- Add audit trigger for updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_prediction_markets_updated_at 
    BEFORE UPDATE ON public.prediction_markets 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();