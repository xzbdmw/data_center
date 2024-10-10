import ccxt.pro
import asyncio

ticker_dict = {}

# export INFLUXDB_TOKEN=M-f5Eha2b4Egx-73BjOkqkhwyZsel4PG3AqF9r-MzQp7QEozDgYL771hCAZ4dZJ_YezUVnblVDCkPuBFcGzwTA==

# 观测市场深度数据中的订单变化（数量、价格等）
async def okx_get(symbol):
    exchange = ccxt.pro.okx({
        'apiKey': '81977931-d319-42af-8306-be750d4531b5',
        'secret': '24342D8C1CA4505D66F6A35D3C09E52D',
        'password': 'Hde20020104!',
        'options': {
            'watchOrderBook': {
                'depth': 'bbo-tbt',  # tick-by-tick best bidask
            },
        },
    })
    exchange.aiohttp_proxy = 'http://127.0.0.1:7890'
    exchange.wsProxy = 'http://127.0.0.1:7890'
    markets = await exchange.load_markets()
    try:
        ticker = await exchange.watchTicker(symbol)
        fee = await exchange.fetch_trading_fee(symbol)
        ticker_dict['okx'] = {
            'datetime': ticker['datetime'],
            'ask': ticker['ask'],
            'askVolume': ticker['askVolume'],
            'bid': ticker['bid'],
            'bidVolume': ticker['bidVolume'],
            'fee': fee['maker']
        }
    except Exception as e:
        print(type(e).__name__, str(e))
    await exchange.close()

async def huobi_get(symbol):
    exchange = ccxt.pro.huobi({
        'apiKey': 'e50d5558-ez2xc4vb6n-4a8e27d8-ffe6d',
        'secret': '55539711-0cee963f-3f10919e-4e6ea',
        'options': {
            'watchOrderBook': {
                'depth': 'bbo-tbt',  # tick-by-tick best bidask
            },
        },
    })
    exchange.aiohttp_proxy = 'http://127.0.0.1:7890'
    exchange.wsProxy = 'http://127.0.0.1:7890'
    markets = await exchange.load_markets()
    try:
        ticker = await exchange.fetchTicker(symbol)
        fee = await exchange.fetch_trading_fee(symbol)
        ticker_dict['huobi'] = {
            'datetime': ticker['datetime'],
            'ask': ticker['ask'],
            'askVolume': ticker['askVolume'],
            'bid': ticker['bid'],
            'bidVolume': ticker['bidVolume'],
            'fee': fee['maker']
        }
    except Exception as e:
        print(type(e).__name__, str(e))
    await exchange.close()

def cal_price_difference(exchange_A, exchange_B):
    min_volume = -1
    if exchange_A and exchange_B:
        # 计算价格差
        B_buy_A_sell = exchange_A['ask'] * (1 - exchange_A['fee']) - exchange_B['bid'] * (1 + exchange_B['fee'])
        if B_buy_A_sell > 0:
            min_volume = min(exchange_A['askVolume'], exchange_B['bidVolume'])
            total_price = min_volume * B_buy_A_sell
            print("huobi购买价格：", exchange_B['bid'], "okx卖出价格：", exchange_A['ask'], "扣除手续费后的差价：",
                  B_buy_A_sell,
                  "成交数量：", min_volume, "总利润；", total_price)

        # 计算价格差
        A_buy_B_sell = exchange_B['ask'] * (1 - exchange_B['fee']) - exchange_A['bid'] * (1 + exchange_A['fee'])
        if A_buy_B_sell > 0:
            min_volume = min(exchange_B['askVolume'], exchange_A['bidVolume'])
            total_price = min_volume * A_buy_B_sell
            print("okx购买价格：", exchange_A['bid'], "huobi卖出价格：", exchange_B['ask'], "扣除手续费后的差价：",
                  A_buy_B_sell,
                  "成交数量：", min_volume, "总利润；", total_price)

        if min_volume < 0:
            print("okx原始购买价格：", exchange_A['bid'])
            print("okx购买价格：", exchange_A['bid'] * (1 + exchange_A['fee']))
            print("huobi原始卖出价格：", exchange_B['ask'])
            print("huobi卖出价格：", exchange_B['ask'] * (1 - exchange_B['fee']))
            print("-------------------------------------------------------------")
            print("huobi原始购买价格：", exchange_B['bid'])
            print("huobi购买价格：", exchange_B['bid'] * (1 + exchange_B['fee']))
            print("okx原始卖出价格：", exchange_A['ask'] * (1 - exchange_A['fee']))
            print("okx卖出价格：", exchange_A['ask'] * (1 - exchange_A['fee']))
            print("当前无法盈利")
    else:
        print("data is missing")

if __name__ == '__main__':
    # 1、获取交易所的接口（买入卖出、获取指定订单簿的价格）
    # coinbase需要身份
    symbols = ['BTC/USDT', 'ETH/USDT', 'DOGE/USDT']
    for symbol in symbols:
        asyncio.run(okx_get(symbol = 'BTC/USDT'))
        asyncio.run(huobi_get(symbol = 'BTC/USDT'))
        # 2、计算差价（后续计算多个交易所之间的差价并排序）
        print("-------------------------------------------------------------")
        print("当前货币：", symbol)
        cal_price_difference(ticker_dict.get('okx'), ticker_dict.get('huobi'))

    # 火币0.002
    # okx0.0008
    # 交易费率文档

    # coinbase、币安、mex
    # coinbase中国身份证不能认证，费率高
    # 币安需要充值后才能创建api
    # mex中国手机号无法认证

    # 加狗狗币和eth（已完成）

    # 3、策略：
    # 当前剩余的资产
    # 价差大小（价差太小就只均衡货币数量，价差够大才最大化交易数量）
    # 盘口挂单数量

    # 4、下单
