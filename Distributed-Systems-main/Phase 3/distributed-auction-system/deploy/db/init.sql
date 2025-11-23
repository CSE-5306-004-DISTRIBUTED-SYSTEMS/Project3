CREATE EXTENSION IF NOT EXISTS pgcrypto;
-- auctions
CREATE TABLE IF NOT EXISTS auctions (
  id UUID PRIMARY KEY,
  title TEXT NOT NULL,
  description TEXT NOT NULL,
  start_price DOUBLE PRECISION NOT NULL CHECK (start_price > 0),
  end_at_unix BIGINT NOT NULL CHECK (end_at_unix > 0),
  seller_id TEXT NOT NULL,
  created_at_unix BIGINT NOT NULL,
  status TEXT NOT NULL DEFAULT 'OPEN',  -- OPEN|CLOSED
  winner_id TEXT,                        -- nullable until closed
  winning_amount DOUBLE PRECISION        -- nullable until closed
);

-- bids
CREATE TABLE IF NOT EXISTS bids (
  auction_id UUID NOT NULL,
  bidder_id TEXT NOT NULL,
  amount DOUBLE PRECISION NOT NULL CHECK (amount > 0),
  placed_at_unix BIGINT NOT NULL,
  PRIMARY KEY (auction_id, bidder_id, placed_at_unix),
  FOREIGN KEY (auction_id) REFERENCES auctions(id) ON DELETE CASCADE
);

-- helpful index
CREATE INDEX IF NOT EXISTS bids_auction_amount_idx
  ON bids (auction_id, amount DESC, placed_at_unix DESC);

-- find expirations quickly
CREATE INDEX IF NOT EXISTS auctions_end_open_idx
  ON auctions (end_at_unix, status);

