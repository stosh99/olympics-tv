-- Add token tracking to commentary table
ALTER TABLE commentary
ADD COLUMN input_tokens INTEGER DEFAULT 0,
ADD COLUMN output_tokens INTEGER DEFAULT 0,
ADD COLUMN estimated_cost NUMERIC(10, 6) DEFAULT 0;

-- Create index on estimated_cost for cost analysis
CREATE INDEX idx_commentary_cost ON commentary(estimated_cost DESC);

-- Log the migration
SELECT 'Token tracking columns added to commentary table' as status;
