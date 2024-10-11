import asyncio
import time
import influxdb_client
from influxdb_client import Point
from influxdb_client.client.write_api import SYNCHRONOUS

import ccxt.pro

INFLUXDB_TOKEN = "XDVaHsvV7ZzsGsChrprdaYJWLoozLk2LYPHHL7Cqu-bJxhLDR5qDa9KsjRpXmOOk4w_rRn8kf1UpRXsRGTuuNg=="


token = INFLUXDB_TOKEN
org = "fzu"
url = "http://localhost:8086"

client = influxdb_client.InfluxDBClient(url=url, token=token, org=org)

bucket = "usdt"

write_api = client.write_api(write_options=SYNCHRONOUS)

ticker_dict_spot = {}
ticker_dict_swap = {}


# 观测市场深度数据中的订单变化（数量、价格等）
async def okx_get(symbol_spot, symbol_swap):
    exchange = ccxt.pro.okx(
        {
            "apiKey": "15b54e09-26b7-4777-9cfb-e69f6f5d85b4",
            "secret": "DAEF6B729F87A05C9107EAB4E84D1282",
            "password": "Hde20020104!",
            "options": {
                "watchOrderBook": {
                    "depth": "bbo-tbt",  # tick-by-tick best bidask
                },
            },
        }
    )
    exchange.aiohttp_proxy = "http://127.0.0.1:7890"
    exchange.wsProxy = "http://127.0.0.1:7890"
    await exchange.load_markets()
    try:
        ticker = await exchange.watchTicker(symbol_spot)
        fee = await exchange.fetch_trading_fee(symbol_spot)
        fee_swap = await exchange.fetch_trading_fee(symbol_swap + "-SWAP")
        # print(fee_swap)
        bbo = await exchange.public_get_market_ticker(
            {"instType": "SWAP", "instId": symbol_swap + "-SWAP"}
        )
        swap = bbo["data"][0]
        # print(swap)
        ticker_dict_spot["okx"] = {
            "symbol": symbol_spot,
            "datetime": ticker["datetime"],
            "ask": ticker["ask"],
            "askVolume": ticker["askVolume"],
            "bid": ticker["bid"],
            "bidVolume": ticker["bidVolume"],
            "fee": (-1) * float(fee["taker"]),
        }
        ticker_dict_swap["okx"] = {
            "symbol": symbol_swap,
            "datetime": swap["ts"],
            "ask": float(swap["askPx"]),
            "askVolume": float(swap["askSz"]),
            "bid": float(swap["bidPx"]),
            "bidVolume": float(swap["bidSz"]),
            "fee": (-1) * float(fee_swap["info"]["takerU"]),
        }
        # print(fee['maker'])
        point = (
            Point("okx_spot")
            .tag("exchange", "okx" + symbol_spot)
            .field("ask", ticker["ask"])
            .field("askVolume", ticker["askVolume"])
            .field("bid", ticker["bid"])
            .field("bidVolume", ticker["bidVolume"])
        )  # 写入数据点到InfluxDB
        write_api.write(bucket=bucket, org="fzu", record=point)

        point = (
            Point("okx_swap")
            .tag("exchange", "okx" + symbol_swap)
            .field("ask", float(swap["askPx"]))
            .field("askVolume", float(swap["askSz"]))
            .field("bid", float(swap["bidPx"]))
            .field("bidVolume", float(swap["bidSz"]))
        )  # 写入数据点到InfluxDB
        write_api.write(bucket=bucket, org="fzu", record=point)
    except Exception as e:
        print(type(e).__name__, str(e))
    await exchange.close()


async def huobi_get(symbol_spot, symbol_swap):
    exchange = ccxt.pro.huobi(
        {
            "apiKey": "e50d5558-ez2xc4vb6n-4a8e27d8-ffe6d",
            "secret": "55539711-0cee963f-3f10919e-4e6ea",
            "options": {
                "watchOrderBook": {
                    "depth": "bbo-tbt",  # tick-by-tick best bidask
                },
            },
        }
    )
    exchange.aiohttp_proxy = "http://127.0.0.1:7890"
    exchange.wsProxy = "http://127.0.0.1:7890"
    await exchange.load_markets()
    try:
        ticker = await exchange.fetchTicker(symbol_spot)
        await exchange.fetch_trading_fee(symbol_spot)
        fee_swap = (
            await exchange.contract_public_get_linear_swap_api_v1_swap_funding_rate(
                {"contract_code": symbol_swap}
            )
        )
        # print(fee_swap)
        bbo = await exchange.contract_public_get_linear_swap_ex_market_bbo(
            {"contract_code": symbol_swap}
        )
        # print(bbo)
        swap = bbo["ticks"][0]
        ticker_dict_spot["huobi"] = {
            "symbol": symbol_spot,
            "datetime": ticker["datetime"],
            "ask": ticker["ask"],
            "askVolume": ticker["askVolume"],
            "bid": ticker["bid"],
            "bidVolume": ticker["bidVolume"],
            "fee": 0.002,
        }
        ticker_dict_swap["huobi"] = {
            "symbol": symbol_swap,
            "datetime": swap["ts"],
            "ask": float(swap["ask"][0]),
            "askVolume": float(swap["ask"][1]),
            "bid": float(swap["bid"][0]),
            "bidVolume": float(swap["bid"][1]),
            "fee": float(fee_swap["data"]["funding_rate"]),
        }
        point = (
            Point("huobi_spot")
            .tag("exchange", "huobi" + symbol_spot)
            .field("ask", ticker["ask"])
            .field("askVolume", ticker["askVolume"])
            .field("bid", ticker["bid"])
            .field("bidVolume", ticker["bidVolume"])
        )  # 写入数据点到InfluxDB
        write_api.write(bucket=bucket, org="fzu", record=point)

        point = (
            Point("huobi_swap")
            .tag("exchange", "huobi" + symbol_swap)
            .field("ask", float(swap["ask"][0]))
            .field("askVolume", float(swap["ask"][1]))
            .field("bid", float(swap["bid"][0]))
            .field("bidVolume", float(swap["bid"][1]))
        )  # 写入数据点到InfluxDB
        write_api.write(bucket=bucket, org="fzu", record=point)
        # print(bbo)
        # print(fee)
    except Exception as e:
        print(type(e).__name__, str(e))
    await exchange.close()


def cal_price_difference(exchange_A, exchange_B):
    print(exchange_A["symbol"])
    print("-------------------------------------------")
    min_volume = -1
    if exchange_A and exchange_B:
        # 计算价格差
        B_buy_A_sell = exchange_A["ask"] * (1 - exchange_A["fee"]) - exchange_B[
            "bid"
        ] * (1 + exchange_B["fee"])
        if B_buy_A_sell > 0:
            min_volume = min(exchange_A["askVolume"], exchange_B["bidVolume"])
            total_price = min_volume * B_buy_A_sell
            print(
                "huobi购买价格：",
                exchange_B["bid"],
                "okx卖出价格：",
                exchange_A["ask"],
                "扣除手续费后的差价：",
                B_buy_A_sell,
                "成交数量：",
                min_volume,
                "总利润；",
                total_price,
            )

        # 计算价格差
        A_buy_B_sell = exchange_B["ask"] * (1 - exchange_B["fee"]) - exchange_A[
            "bid"
        ] * (1 + exchange_A["fee"])
        if A_buy_B_sell > 0:
            min_volume = min(exchange_B["askVolume"], exchange_A["bidVolume"])
            total_price = min_volume * A_buy_B_sell
            print(
                "okx购买价格：",
                exchange_A["bid"],
                "huobi卖出价格：",
                exchange_B["ask"],
                "扣除手续费后的差价：",
                A_buy_B_sell,
                "成交数量：",
                min_volume,
                "总利润；",
                total_price,
            )

        if min_volume < 0:
            print("okx原始购买价格：", exchange_A["bid"])
            print("okx购买价格：", exchange_A["bid"] * (1 + exchange_A["fee"]))
            print("huobi原始卖出价格：", exchange_B["ask"])
            print("huobi卖出价格：", exchange_B["ask"] * (1 - exchange_B["fee"]))
            print("*********************************************************")
            print("huobi原始购买价格：", exchange_B["bid"])
            print("huobi购买价格：", exchange_B["bid"] * (1 + exchange_B["fee"]))
            print("okx原始卖出价格：", exchange_A["ask"] * (1 - exchange_A["fee"]))
            print("okx卖出价格：", exchange_A["ask"] * (1 - exchange_A["fee"]))
            print("当前无法盈利")
    else:
        print("data is missing")


if __name__ == "__main__":
    # 1、获取交易所的接口（买入卖出、获取指定订单簿的价格）
    # coinbase需要 身份
    symbols = ["BTC/USDT", "ETH/USDT", "DOGE/USDT", "DAI/USDT", "BCH/USDT"]
    symbols_swap = ["BTC-USDT", "ETH-USDT", "DOGE-USDT", "DAI-USDT", "BCH-USDT"]
    while True:
        for i in range(len(symbols)):
            ticker_dict_spot = {}
            ticker_dict_swap = {}
            asyncio.run(okx_get(symbols[i], symbols_swap[i]))
            asyncio.run(huobi_get(symbols[i], symbols_swap[i]))
            if ticker_dict_spot and ticker_dict_swap:
                # 2、计算差价（后续计算多个交易所之间的差价并排序）
                cal_price_difference(
                    ticker_dict_spot.get("okx"), ticker_dict_spot.get("huobi")
                )
                cal_price_difference(
                    ticker_dict_swap.get("okx"), ticker_dict_swap.get("huobi")
                )
        time.sleep(60)
    # coinbase、币安、mex
    # 加狗狗币和eth

    # 3、策略：
    # 当前剩余的资产
    # 价差大小（价差太小就只均衡货币数量，价差够大才最大化交易数量）
    # 盘口挂单数量

    # 4、下单
