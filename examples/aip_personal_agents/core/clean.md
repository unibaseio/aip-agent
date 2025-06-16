# tweet用户个性化报告生成

+ 根据用户的推文得到用户画像，查询kol相关的推文，生成个性化报告
+ 代码中的注释使用英文
+ 功能未全部完成前不要测试

## tweet标签

+ 推文范围：Web3 / Blockchain / Crypto / AI / Meme Coin / 各类代币

+ 多维度标签：主题，主体，意图，语气，受众

+ 标签设计：多级标签，例如

```
分类使用二级方式，例如web3
├── DeFi
│   ├── yield_farming
│   ├── stablecoins
│   └── staking
├── NFT
│   ├── gaming
│   ├── music
│   └── PFP
├── DAO
│   ├── governance
│   └── treasury

blockchain
├── layer1
│   ├── Ethereum
│   ├── Solana
│   └── Avalanche
├── layer2
│   ├── Arbitrum
│   ├── zkSync
│   └── Base

crypto
├── tokenomics
├── meme_coin
│   ├── DOGE
│   ├── PEPE
│   └── WIF
├── regulation
├── security

AI
├── LLM
│   ├── GPT-4
│   ├── Claude
│   └── open-source
├── agent
├── prompt_engineering

```

## 使用用户的推文进行用户画像

使用用户历史推文，对用户进行画像，得到用户的话题/关注偏好，用于后续为用户生成个性化报告

## 为推文打标

对所有推文进行标记，保存在向量/KV数据库（具体保存可以先空着，先将保存的数据结构设计好）

## 推文筛选

根据用户画像，结合最近的相关推文，筛选出符合用户画像的推文


## 个性化报告

使用筛选后的推文，为用户生成个性化报告

