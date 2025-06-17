# 📘 Web3 Token Signal Aggregator – LLM-Powered Design Document for Cursor

## 1. Overview

This system is a modular Web3 token data aggregator with OpenAI-powered chat-based interaction. It allows users to ask questions like "Should I buy \$PEPE?" and get real-time trading signals based on technical indicators and market data.

**Target**: Medium-short term retail traders
**Built for**: Rapid prototyping and modular implementation inside [Cursor](https://www.cursor.sh)

---

## 2. Data Structure (Three-Tier Architecture)

### 2.1 Architecture Overview

```
Token (Base Info)
├── Pools (Token Pairs on Different DEXs)
│   ├── Pool Metrics (Real-time Pool Data)
│   └── Pool Historical Data
└── Token Metrics (Aggregated from All Pools)
```

### 2.2 Data Flow

1. **Token Level**: Basic token information (contract, name, symbol)
2. **Pool Level**: Each token-pair combination on specific DEX (e.g., PEPE/WETH on Uniswap V3)
3. **Pool Metrics Level**: Real-time data for each pool (price, volume, liquidity)
4. **Token Metrics Level**: Real-time data for each token (price, volume, liquidity)

### 2.3 Entity Relationships

**Token (1) → Pools (N) → Pool Metrics (N) → Token Metrics (1)**

- One token can have multiple pools (different pairs, different DEXs)
- Each pool has its own metrics and historical data
- Token metrics are calculated using token analystic and holder stat
- This supports multi-DEX arbitrage analysis and comprehensive token evaluation

---

## 3. Modules Breakdown

### 🔌 Module 1: Token Data Aggregator

Fetch periodically:

* **BirdEye**: token list
* **DEX Screener**: token pools, price, volume, liquidity
* **Moralis**: holder count and change

Store in `PostgreSQL`.

#### BirdEye API

```
import requests

url = "https://public-api.birdeye.so/defi/tokenlist?sort_by=v24hUSD&sort_type=desc&offset=0&limit=50&min_liquidity=100"

headers = {
    "accept": "application/json",
    "x-chain": "bsc",
    "X-API-KEY": "3079160b0c4b47cdb972014a615efb47"
}

response = requests.get(url, headers=headers)

print(response.text)
```

+ response

```
{
  "success": true,
  "data": {
    "updateUnixTime": 1750129091,
    "updateTime": "2025-06-17T02:58:11",
    "tokens": [
      {
        "address": "0x55d398326f99059fF775485246999027B3197955",
        "decimals": 18,
        "lastTradeUnixTime": 1750128527,
        "liquidity": 674627993.9950634,
        "logoURI": "https://assets.coingecko.com/coins/images/325/small/Tether.png?1668148663",
        "mc": 6284993799.505675,
        "name": "Tether",
        "symbol": "USDT",
        "v24hChangePercent": 81.81183801273328,
        "v24hUSD": 9517344717.06078,
        "price": 1
      },
      {
        "address": "0x95034f653D5D161890836Ad2B6b8cc49D14e029a",
        "decimals": 18,
        "lastTradeUnixTime": 1750127573,
        "liquidity": 1965444.0342806377,
        "logoURI": null,
        "mc": 1558230528.0980895,
        "name": "AB",
        "symbol": "AB",
        "v24hChangePercent": 464.46875704563075,
        "v24hUSD": 4238224070.95335,
        "price": 0.015654957822456916
      }
    ]
  }
}
```

#### DEX SCREENER API

baseurl: https://api.dexscreener.com

+ /tokens/v1/{chainId}/{tokenAddresses}

```json
[
  {
    "chainId": "bsc",
    "dexId": "pancakeswap",
    "url": "https://dexscreener.com/bsc/0x4ba556e9754a9dedc0f108960283f0535f4c5ff4",
    "pairAddress": "0x4Ba556E9754a9dedC0F108960283f0535f4c5FF4",
    "labels": [
      "v3"
    ],
    "baseToken": {
      "address": "0x238950013FA29A3575EB7a3D99C00304047a77b5",
      "name": "Beeper Coin",
      "symbol": "BEEPER"
    },
    "quoteToken": {
      "address": "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c",
      "name": "Wrapped BNB",
      "symbol": "WBNB"
    },
    "priceNative": "0.0000003488",
    "priceUsd": "0.0002283",
    "txns": {
      "m5": {
        "buys": 0,
        "sells": 1
      },
      "h1": {
        "buys": 0,
        "sells": 1
      },
      "h6": {
        "buys": 4,
        "sells": 11
      },
      "h24": {
        "buys": 28,
        "sells": 38
      }
    },
    "volume": {
      "h24": 435.3,
      "h6": 117.69,
      "h1": 3.68,
      "m5": 3.68
    },
    "priceChange": {
      "m5": 0.52,
      "h1": 0.52,
      "h6": 1.03,
      "h24": 0.44
    },
    "liquidity": {
      "usd": 170298.58,
      "base": 379990799,
      "quote": 127.5722
    },
    "fdv": 2283867,
    "marketCap": 2283867,
    "pairCreatedAt": 1735779663000,
    "info": {
      "imageUrl": "https://dd.dexscreener.com/ds-data/tokens/bsc/0x238950013fa29a3575eb7a3d99c00304047a77b5.png?key=43bae0",
      "header": "https://dd.dexscreener.com/ds-data/tokens/bsc/0x238950013fa29a3575eb7a3d99c00304047a77b5/header.png?key=43bae0",
      "openGraph": "https://cdn.dexscreener.com/token-images/og/bsc/0x238950013fa29a3575eb7a3d99c00304047a77b5?timestamp=1750054500000",
      "websites": [
        {
          "label": "Website",
          "url": "https://beeper.fun/"
        }
      ],
      "socials": [
        {
          "type": "twitter",
          "url": "https://x.com/BeeperBoss"
        },
        {
          "type": "telegram",
          "url": "https://t.me/beeper_ai"
        }
      ]
    }
  }
]

```

+ /latest/dex/search

params: q string required

```
{
  "schemaVersion": "1.0.0",
  "pairs": [
    {
      "chainId": "bsc",
      "dexId": "pancakeswap",
      "url": "https://dexscreener.com/bsc/0x4ba556e9754a9dedc0f108960283f0535f4c5ff4",
      "pairAddress": "0x4Ba556E9754a9dedC0F108960283f0535f4c5FF4",
      "labels": [
        "v3"
      ],
      "baseToken": {
        "address": "0x238950013FA29A3575EB7a3D99C00304047a77b5",
        "name": "Beeper Coin",
        "symbol": "BEEPER"
      },
      "quoteToken": {
        "address": "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c",
        "name": "Wrapped BNB",
        "symbol": "WBNB"
      },
      "priceNative": "0.0000003488",
      "priceUsd": "0.0002289",
      "txns": {
        "m5": {
          "buys": 0,
          "sells": 0
        },
        "h1": {
          "buys": 0,
          "sells": 3
        },
        "h6": {
          "buys": 4,
          "sells": 7
        },
        "h24": {
          "buys": 24,
          "sells": 37
        }
      },
      "volume": {
        "h24": 387.41,
        "h6": 111.51,
        "h1": 23.17,
        "m5": 0
      },
      "priceChange": {
        "h1": 0.16,
        "h6": 1.17,
        "h24": 0.95
      },
      "liquidity": {
        "usd": 170694.48,
        "base": 380020600,
        "quote": 127.5626
      },
      "fdv": 2289000,
      "marketCap": 2289000,
      "pairCreatedAt": 1735779663000,
      "info": {
        "imageUrl": "https://dd.dexscreener.com/ds-data/tokens/bsc/0x238950013fa29a3575eb7a3d99c00304047a77b5.png?key=43bae0",
        "header": "https://dd.dexscreener.com/ds-data/tokens/bsc/0x238950013fa29a3575eb7a3d99c00304047a77b5/header.png?key=43bae0",
        "openGraph": "https://cdn.dexscreener.com/token-images/og/bsc/0x238950013fa29a3575eb7a3d99c00304047a77b5?timestamp=1750062600000",
        "websites": [
          {
            "label": "Website",
            "url": "https://beeper.fun/"
          }
        ],
        "socials": [
          {
            "type": "twitter",
            "url": "https://x.com/BeeperBoss"
          },
          {
            "type": "telegram",
            "url": "https://t.me/beeper_ai"
          }
        ]
      }
    }
  ]
}
```

#### MORALIS

+ token analytics

```
# Dependencies to install:

# $ python -m pip install requests

import requests

url = "https://deep-index.moralis.io/api/v2.2/tokens/0x238950013FA29A3575EB7a3D99C00304047a77b5/analytics?chain=bsc"

headers = {
  "Accept": "application/json",
  "X-API-Key": "YOUR_API_KEY"
}

response = requests.request("GET", url, headers=headers)

print(response.text)
```

response
```json
{
  "tokenAddress": "0x238950013fa29a3575eb7a3d99c00304047a77b5",
  "totalBuyVolume": {
    "5m": 0,
    "1h": 0,
    "6h": 36.08441127519937,
    "24h": 145.31766518635527
  },
  "totalSellVolume": {
    "5m": 0,
    "1h": 0,
    "6h": 23.61049011135401,
    "24h": 151.1848144618685
  },
  "totalBuyers": {
    "5m": 0,
    "1h": 0,
    "6h": 5,
    "24h": 19
  },
  "totalSellers": {
    "5m": 0,
    "1h": 0,
    "6h": 4,
    "24h": 21
  },
  "totalBuys": {
    "5m": 0,
    "1h": 0,
    "6h": 5,
    "24h": 21
  },
  "totalSells": {
    "5m": 0,
    "1h": 0,
    "6h": 4,
    "24h": 26
  },
  "uniqueWallets": {
    "5m": 0,
    "1h": 0,
    "6h": 8,
    "24h": 25
  },
  "pricePercentChange": {
    "5m": 0,
    "1h": 0,
    "6h": 0.20572543374533,
    "24h": 0.14180992701153
  },
  "usdPrice": "0.000228710596262586",
  "totalLiquidityUsd": "170546.99",
  "totalFullyDilutedValuation": "2287469.14578223"
}
```

+ holder stats

```
import requests

url = "https://deep-index.moralis.io/api/v2.2/erc20/0x6982508145454ce325ddbe47a25d4ec3d2311933/holders?chain=eth"

headers = {
  "Accept": "application/json",
  "X-API-Key": "YOUR_API_KEY"
}

response = requests.request("GET", url, headers=headers)

print(response.text)
```

+ holder stats

```
# Dependencies to install:

# $ python -m pip install requests

import requests

url = "https://deep-index.moralis.io/api/v2.2/erc20/0x238950013FA29A3575EB7a3D99C00304047a77b5/holders?chain=bsc"

headers = {
  "Accept": "application/json",
  "X-API-Key": "YOUR_API_KEY"
}

response = requests.request("GET", url, headers=headers)

print(response.text)
```

response
```
{
  "totalHolders": 6541,
  "holdersByAcquisition": {
    "swap": 1044,
    "transfer": 5496,
    "airdrop": 1
  },
  "holderChange": {
    "5min": {
      "change": 0,
      "changePercent": 0
    },
    "1h": {
      "change": 0,
      "changePercent": 0
    },
    "6h": {
      "change": 2,
      "changePercent": 0.031
    },
    "24h": {
      "change": -1,
      "changePercent": -0.015
    },
    "3d": {
      "change": -6,
      "changePercent": -0.092
    },
    "7d": {
      "change": 1,
      "changePercent": 0.015
    },
    "30d": {
      "change": 20,
      "changePercent": 0.31
    }
  },
  "holderSupply": {
    "top10": {
      "supply": "1261255524.56",
      "supplyPercent": 13
    },
    "top25": {
      "supply": "2182504702.61",
      "supplyPercent": 22
    },
    "top50": {
      "supply": "3281626279.9",
      "supplyPercent": 33
    },
    "top100": {
      "supply": "4988793598.04",
      "supplyPercent": 50
    },
    "top250": {
      "supply": "8244242362.99",
      "supplyPercent": 82
    },
    "top500": {
      "supply": "9964805670.42",
      "supplyPercent": 100
    }
  },
  "holderDistribution": {
    "whales": 324,
    "sharks": 80,
    "dolphins": 112,
    "fish": 37,
    "octopus": 309,
    "crabs": 206,
    "shrimps": 5473
  }
}
```


---

### 🧠 Module 2: Indicator Engine

* RSI (14-day)
* Moving Averages (MA7, MA30)
* Volume delta
* Holder delta
* Breakout detection

---

### 💬 Module 3: LLM Chat Layer

* **LLM**: OpenAI GPT-4.1-mini
* Responsibilities:

  * Intent recognition
  * Ticker → token resolution
  * API call orchestration
  * Signal level + explanation

---

### 🌐 Module 4: REST API (FastAPI)

```ts
GET  /tokens
POST /tokens { ticker, contract_address, chain }
GET  /tokens/:id/signal
POST /chat { message: string }
```

---

## 3. Token & Metrics Schema (PostgreSQL) - Three-Tier Architecture

```sql
-- Tier 1: Token Base Information
CREATE TABLE tokens (
  id UUID PRIMARY KEY,
  name TEXT NOT NULL,
  symbol TEXT NOT NULL,
  symbol_lower TEXT NOT NULL, -- for case-insensitive queries
  contract_address TEXT NOT NULL,
  chain TEXT NOT NULL,
  decimals INTEGER DEFAULT 18,
  image_url TEXT,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW(),
  UNIQUE(contract_address, chain)
);

-- Tier 2: Token Pools (Token Pairs on Different DEXs)
CREATE TABLE token_pools (
  id UUID PRIMARY KEY,
  base_token_id UUID REFERENCES tokens(id),
  quote_token_id UUID REFERENCES tokens(id),
  dex TEXT NOT NULL, -- e.g., 'uniswap-v3', 'pancakeswap'
  chain TEXT NOT NULL,
  pair_address TEXT NOT NULL,
  fee_tier INTEGER, -- e.g., 3000 for 0.3%
  pool_version TEXT, -- e.g., 'v2', 'v3'
  created_at TIMESTAMP DEFAULT NOW(),
  is_active BOOLEAN DEFAULT TRUE,
  UNIQUE(pair_address, chain, dex)
);

-- Tier 3: Pool Metrics (Real-time Pool Data)
CREATE TABLE pool_metrics (
  id UUID PRIMARY KEY,
  pool_id UUID REFERENCES token_pools(id),
  price_usd DECIMAL(20, 10),
  price_native DECIMAL(30, 18),
  volume_1h DECIMAL(20, 2),
  volume_24h DECIMAL(20, 2),
  liquidity_usd DECIMAL(20, 2),
  liquidity_base DECIMAL(30, 18),
  liquidity_quote DECIMAL(30, 18),
  price_change_1h DECIMAL(10, 4),
  price_change_24h DECIMAL(10, 4),
  txns_1h_buys INTEGER DEFAULT 0,
  txns_1h_sells INTEGER DEFAULT 0,
  txns_24h_buys INTEGER DEFAULT 0,
  txns_24h_sells INTEGER DEFAULT 0,
  market_cap DECIMAL(20, 2),
  fdv DECIMAL(20, 2), -- Fully Diluted Valuation
  data_source TEXT, -- 'dexscreener', 'moralis', 'birdeye'
  updated_at TIMESTAMP DEFAULT NOW()
);

-- Tier 4: Token Metrics (Aggregated from All Pools)
CREATE TABLE token_metrics (
  id UUID PRIMARY KEY,
  token_id UUID REFERENCES tokens(id),
  -- Aggregated Price Data
  avg_price_usd DECIMAL(20, 10),
  weighted_price_usd DECIMAL(20, 10), -- Volume weighted
  total_volume_24h DECIMAL(20, 2),
  total_liquidity_usd DECIMAL(20, 2),
  market_cap DECIMAL(20, 2),
  -- Technical Indicators
  rsi_14d FLOAT,
  ma_7d FLOAT,
  ma_30d FLOAT,
  volatility_24h FLOAT,
  -- On-chain Metrics
  holder_count INTEGER,
  unique_traders_24h INTEGER,
  -- Signals
  breakout_signal BOOLEAN DEFAULT FALSE,
  trend_direction TEXT CHECK (trend_direction IN ('bullish', 'bearish', 'sideways')),
  signal_strength FLOAT CHECK (signal_strength >= 0 AND signal_strength <= 1),
  -- Meta
  pools_count INTEGER DEFAULT 0,
  last_calculation_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- Historical Data for Time Series Analysis
CREATE TABLE pool_metrics_history (
  id UUID PRIMARY KEY,
  pool_id UUID REFERENCES token_pools(id),
  price_usd DECIMAL(20, 10),
  volume_24h DECIMAL(20, 2),
  liquidity_usd DECIMAL(20, 2),
  recorded_at TIMESTAMP NOT NULL
);

-- Indexes for Performance
CREATE INDEX idx_tokens_symbol_lower ON tokens(symbol_lower);
CREATE INDEX idx_tokens_contract_chain ON tokens(contract_address, chain);
CREATE INDEX idx_pool_metrics_pool_updated ON pool_metrics(pool_id, updated_at);
CREATE INDEX idx_pool_metrics_history_recorded ON pool_metrics_history(pool_id, recorded_at);
CREATE INDEX idx_token_metrics_updated ON token_metrics(token_id, updated_at);
```

---

## 4. Signal Levels with Reasoning

| Signal Level    | Description               | Example Reason                                                 |
| --------------- | ------------------------- | -------------------------------------------------------------- |
| **Strong Buy**  | Bullish breakout, low RSI | "RSI is 45, breakout confirmed, and volume surged 3x average." |
| **Buy**         | Uptrend, low-mid RSI      | "MA7 > MA30, RSI 55 — healthy uptrend forming."                |
| **Watch**       | Mixed signals             | "RSI above 70, strong price momentum — possible continuation." |
| **Hold**        | Sideways market           | "MA7 ≈ MA30, RSI neutral — no clear direction."                |
| **Sell**        | Overbought, start of drop | "Price down 12%, RSI > 75 — likely cooling off."               |
| **Strong Sell** | Confirmed bearish trend   | "MA30 > MA7, RSI < 30 — strong downward pressure."             |

LLM is used to convert raw metrics into human-readable decisions + justifications.

---

## 5. Example: `/chat` Request and Response

**User input**:

```json
{ "message": "What's the outlook on $DOGE?" }
```

**Parsed intent**:

```json
{
  "intent": "token_analysis",
  "token": { "ticker": "DOGE" }
}
```

**Backend response**:

```json
{
  "token": "DOGE",
  "signal": "Watch",
  "reason": "RSI is 68, approaching overbought. MA7 > MA30, but volume is flat. Momentum slowing.",
  "metrics": {
    "price": 0.091,
    "rsi": 68,
    "ma_7d": 0.089,
    "ma_30d": 0.084,
    "volume_24h": 32000000
  }
}
```

---

## 6. OpenAI Prompt Template (used in `/chat`)

```txt
You are a Web3 trading assistant. Given the following token metrics, output a trading signal and explain why.

Token: ${{token}}
Price: ${{price}}
24H Volume: ${{volume_24h}}
RSI: {{rsi}}
MA7: {{ma7}}
MA30: {{ma30}}

Return:
- Signal (Strong Buy, Buy, Watch, Hold, Sell, Strong Sell)
- Reason (based on above metrics)
```

---

## 7. Suggested Stack

* **FastAPI** – lightweight backend
* **PostgreSQL** – relational data store
* **OpenAI SDK** – LLM chat and signal generation

---

## 8. MVP Checklist for Cursor

* [ ] Data fetcher: CoinGecko, DEX Screener, Moralis
* [ ] Signal calculator (RSI, MA, etc.)
* [ ] OpenAI LLM signal generation function
* [ ] FastAPI endpoints: `/tokens`, `/signal`, `/chat`
* [ ] Local DB + testing scripts

---

## 9. Optional Enhancements

* Telegram/Discord bots
* Sentiment analysis (Twitter API)
* Wallet analytics (Moralis + address tracking)
* Portfolio simulation/backtest

--- 

## 10. Notice

+ no unit test 
