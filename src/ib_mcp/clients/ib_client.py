"""Interactive Brokers API Client using ib_async."""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any

from ib_async import IB, Stock, Contract, Order, Execution, ExecutionFilter

from ..config import IBConfig

logger = logging.getLogger(__name__)


class IBConnectionError(Exception):
    """Raised when IB connection fails."""

    def __init__(self, message: str, suggestion: str | None = None):
        super().__init__(message)
        self.suggestion = suggestion or (
            "Ensure IB Gateway or TWS is running and API connections are enabled. "
            "Download IB Gateway: https://www.interactivebrokers.com/en/trading/ibgateway-stable.php"
        )


class IBClient:
    """Client for Interactive Brokers API operations."""

    def __init__(self, config: IBConfig):
        self.config = config
        self.ib = IB()
        self._connected = False
        self._lock = asyncio.Lock()

    async def ensure_connected(self) -> None:
        """Ensure connection to IB Gateway/TWS."""
        async with self._lock:
            if self._connected and self.ib.isConnected():
                return

            try:
                logger.info(
                    f"Connecting to IB at {self.config.host}:{self.config.port} "
                    f"(clientId={self.config.client_id})"
                )
                await self.ib.connectAsync(
                    host=self.config.host,
                    port=self.config.port,
                    clientId=self.config.client_id,
                    timeout=self.config.timeout,
                    readonly=self.config.readonly,
                )
                self._connected = True
                logger.info("Connected to IB Gateway/TWS successfully")
            except Exception as e:
                self._connected = False
                raise IBConnectionError(
                    f"Failed to connect to IB Gateway/TWS at {self.config.host}:{self.config.port}: {e}"
                )

    async def disconnect(self) -> None:
        """Disconnect from IB."""
        if self.ib.isConnected():
            self.ib.disconnect()
            self._connected = False
            logger.info("Disconnected from IB")

    async def check_connection(self) -> dict[str, Any]:
        """Check IB connection status."""
        try:
            await self.ensure_connected()
            accounts = self.ib.managedAccounts()
            return {
                "connected": True,
                "host": self.config.host,
                "port": self.config.port,
                "accounts": accounts,
                "server_version": self.ib.client.serverVersion() if self.ib.client else None,
            }
        except IBConnectionError as e:
            return {
                "connected": False,
                "error": str(e),
                "suggestion": e.suggestion,
                "host": self.config.host,
                "port": self.config.port,
            }

    # =========================================================================
    # Portfolio Methods
    # =========================================================================

    async def get_account_summary(self, account_id: str | None = None) -> dict[str, Any]:
        """Get account summary including net liquidation, buying power, etc."""
        await self.ensure_connected()

        # Get all accounts if none specified
        accounts = self.ib.managedAccounts()
        if not accounts:
            return {"error": "No accounts found"}

        target_account = account_id or accounts[0]

        # Request account summary
        summary = await self.ib.accountSummaryAsync(target_account)

        # Organize by tag
        result = {
            "account_id": target_account,
            "summary": {},
            "timestamp": datetime.now().isoformat(),
        }

        for item in summary:
            result["summary"][item.tag] = {
                "value": item.value,
                "currency": item.currency,
            }

        # Extract key metrics
        key_metrics = {}
        important_tags = [
            "NetLiquidation",
            "TotalCashValue",
            "BuyingPower",
            "AvailableFunds",
            "ExcessLiquidity",
            "GrossPositionValue",
            "MaintMarginReq",
            "InitMarginReq",
        ]

        for tag in important_tags:
            if tag in result["summary"]:
                key_metrics[tag] = result["summary"][tag]

        result["key_metrics"] = key_metrics

        return result

    async def get_positions(
        self, account_id: str | None = None, include_zero: bool = False
    ) -> dict[str, Any]:
        """Get all current positions."""
        await self.ensure_connected()

        positions = self.ib.positions()

        # Filter by account if specified
        if account_id:
            positions = [p for p in positions if p.account == account_id]

        # Filter zero positions
        if not include_zero:
            positions = [p for p in positions if p.position != 0]

        result = {
            "positions": [],
            "total_count": len(positions),
            "timestamp": datetime.now().isoformat(),
        }

        for pos in positions:
            position_data = {
                "symbol": pos.contract.symbol,
                "security_type": pos.contract.secType,
                "exchange": pos.contract.exchange or "SMART",
                "currency": pos.contract.currency,
                "quantity": float(pos.position),
                "avg_cost": float(pos.avgCost),
                "account": pos.account,
            }

            # Calculate market value if we have avg cost
            if pos.avgCost and pos.position:
                position_data["cost_basis"] = float(pos.position) * float(pos.avgCost)

            result["positions"].append(position_data)

        return result

    async def get_portfolio_pnl(self, account_id: str | None = None) -> dict[str, Any]:
        """Get portfolio P&L breakdown."""
        await self.ensure_connected()

        accounts = self.ib.managedAccounts()
        target_account = account_id or (accounts[0] if accounts else None)

        if not target_account:
            return {"error": "No account found"}

        # Get account values for P&L
        account_values = await self.ib.accountValuesAsync(target_account)

        pnl_data = {
            "account_id": target_account,
            "timestamp": datetime.now().isoformat(),
        }

        # Extract P&L related values
        pnl_tags = [
            "UnrealizedPnL",
            "RealizedPnL",
            "DailyPnL",
            "NetLiquidation",
            "TotalCashValue",
            "GrossPositionValue",
        ]

        for value in account_values:
            if value.tag in pnl_tags:
                if value.tag not in pnl_data:
                    pnl_data[value.tag] = {}
                pnl_data[value.tag][value.currency] = value.value

        return pnl_data

    async def get_position_details(
        self, symbol: str, account_id: str | None = None
    ) -> dict[str, Any]:
        """Get detailed information for a specific position."""
        await self.ensure_connected()

        # Find the position
        positions = self.ib.positions()

        if account_id:
            positions = [p for p in positions if p.account == account_id]

        position = next(
            (p for p in positions if p.contract.symbol.upper() == symbol.upper()),
            None
        )

        if not position:
            return {
                "error": f"Position not found for symbol: {symbol}",
                "symbol": symbol,
            }

        result = {
            "symbol": position.contract.symbol,
            "security_type": position.contract.secType,
            "exchange": position.contract.exchange or "SMART",
            "currency": position.contract.currency,
            "quantity": float(position.position),
            "avg_cost": float(position.avgCost),
            "account": position.account,
            "cost_basis": float(position.position) * float(position.avgCost),
            "timestamp": datetime.now().isoformat(),
        }

        # Try to get current market price
        try:
            contract = Stock(symbol, "SMART", position.contract.currency)
            self.ib.qualifyContracts(contract)
            ticker = self.ib.reqMktData(contract, snapshot=True)
            await asyncio.sleep(2)  # Wait for data

            if ticker.last and ticker.last > 0:
                result["current_price"] = ticker.last
                result["market_value"] = float(position.position) * ticker.last
                result["unrealized_pnl"] = result["market_value"] - result["cost_basis"]
                result["unrealized_pnl_pct"] = (
                    (result["unrealized_pnl"] / result["cost_basis"]) * 100
                    if result["cost_basis"] != 0
                    else 0
                )

            self.ib.cancelMktData(contract)
        except Exception as e:
            logger.warning(f"Could not get market data for {symbol}: {e}")

        return result

    async def get_open_orders(self, account_id: str | None = None) -> dict[str, Any]:
        """Get all open/pending orders."""
        await self.ensure_connected()

        orders = self.ib.openOrders()

        if account_id:
            orders = [o for o in orders if o.account == account_id]

        result = {
            "orders": [],
            "total_count": len(orders),
            "timestamp": datetime.now().isoformat(),
        }

        for order in orders:
            order_data = {
                "order_id": order.orderId,
                "client_id": order.clientId,
                "symbol": order.contract.symbol if order.contract else None,
                "action": order.action,
                "order_type": order.orderType,
                "quantity": float(order.totalQuantity),
                "limit_price": order.lmtPrice if order.lmtPrice else None,
                "stop_price": order.auxPrice if order.auxPrice else None,
                "status": order.status if hasattr(order, "status") else "Unknown",
                "account": order.account,
            }
            result["orders"].append(order_data)

        return result

    async def get_executions(
        self, days_back: int = 1, symbol: str | None = None
    ) -> dict[str, Any]:
        """Get recent trade executions."""
        await self.ensure_connected()

        # Create execution filter
        exec_filter = ExecutionFilter()
        if symbol:
            exec_filter.symbol = symbol.upper()

        # Get executions
        executions = await self.ib.reqExecutionsAsync(exec_filter)

        result = {
            "executions": [],
            "total_count": len(executions),
            "timestamp": datetime.now().isoformat(),
        }

        for fill in executions:
            exec_data = {
                "exec_id": fill.execution.execId,
                "symbol": fill.contract.symbol,
                "side": fill.execution.side,
                "quantity": float(fill.execution.shares),
                "price": float(fill.execution.price),
                "time": fill.execution.time,
                "exchange": fill.execution.exchange,
                "account": fill.execution.acctNumber,
                "commission": float(fill.commissionReport.commission)
                if fill.commissionReport
                else None,
            }
            result["executions"].append(exec_data)

        return result

    # =========================================================================
    # Market Data Methods
    # =========================================================================

    async def get_quote(
        self, symbol: str, include_extended: bool = False
    ) -> dict[str, Any]:
        """Get real-time quote for a symbol."""
        await self.ensure_connected()

        contract = Stock(symbol.upper(), "SMART", "USD")
        qualified = await self.ib.qualifyContractsAsync(contract)

        if not qualified:
            return {"error": f"Could not find contract for symbol: {symbol}"}

        contract = qualified[0]

        # Request market data
        ticker = self.ib.reqMktData(contract, snapshot=True)
        await asyncio.sleep(2)  # Wait for snapshot

        result = {
            "symbol": symbol.upper(),
            "timestamp": datetime.now().isoformat(),
            "bid": ticker.bid if ticker.bid and ticker.bid > 0 else None,
            "ask": ticker.ask if ticker.ask and ticker.ask > 0 else None,
            "last": ticker.last if ticker.last and ticker.last > 0 else None,
            "close": ticker.close if ticker.close and ticker.close > 0 else None,
            "high": ticker.high if ticker.high and ticker.high > 0 else None,
            "low": ticker.low if ticker.low and ticker.low > 0 else None,
            "volume": ticker.volume if ticker.volume else None,
            "bid_size": ticker.bidSize if ticker.bidSize else None,
            "ask_size": ticker.askSize if ticker.askSize else None,
        }

        # Calculate spread
        if result["bid"] and result["ask"]:
            result["spread"] = result["ask"] - result["bid"]
            result["spread_pct"] = (result["spread"] / result["ask"]) * 100

        # Calculate change
        if result["last"] and result["close"]:
            result["change"] = result["last"] - result["close"]
            result["change_pct"] = (result["change"] / result["close"]) * 100

        self.ib.cancelMktData(contract)

        return result

    async def get_historical_data(
        self,
        symbol: str,
        duration: str = "1 M",
        bar_size: str = "1 day",
    ) -> dict[str, Any]:
        """Get historical OHLCV data."""
        await self.ensure_connected()

        contract = Stock(symbol.upper(), "SMART", "USD")
        qualified = await self.ib.qualifyContractsAsync(contract)

        if not qualified:
            return {"error": f"Could not find contract for symbol: {symbol}"}

        contract = qualified[0]

        # Request historical data
        bars = await self.ib.reqHistoricalDataAsync(
            contract,
            endDateTime="",
            durationStr=duration,
            barSizeSetting=bar_size,
            whatToShow="TRADES",
            useRTH=True,
        )

        result = {
            "symbol": symbol.upper(),
            "duration": duration,
            "bar_size": bar_size,
            "bars": [],
            "count": len(bars),
        }

        for bar in bars:
            result["bars"].append({
                "date": bar.date.isoformat() if hasattr(bar.date, "isoformat") else str(bar.date),
                "open": float(bar.open),
                "high": float(bar.high),
                "low": float(bar.low),
                "close": float(bar.close),
                "volume": int(bar.volume),
                "average": float(bar.average) if bar.average else None,
            })

        return result

    async def get_contract_details(self, symbol: str) -> dict[str, Any]:
        """Get detailed contract information."""
        await self.ensure_connected()

        contract = Stock(symbol.upper(), "SMART", "USD")

        details = await self.ib.reqContractDetailsAsync(contract)

        if not details:
            return {"error": f"No contract details found for: {symbol}"}

        detail = details[0]

        return {
            "symbol": detail.contract.symbol,
            "security_type": detail.contract.secType,
            "exchange": detail.contract.exchange,
            "primary_exchange": detail.contract.primaryExchange,
            "currency": detail.contract.currency,
            "local_symbol": detail.contract.localSymbol,
            "long_name": detail.longName,
            "industry": detail.industry,
            "category": detail.category,
            "subcategory": detail.subcategory,
            "market_name": detail.marketName,
            "min_tick": detail.minTick,
            "trading_hours": detail.tradingHours,
            "liquid_hours": detail.liquidHours,
            "timezone": detail.timeZoneId,
        }

    async def search_symbols(
        self, query: str, security_type: str = "STK", limit: int = 10
    ) -> dict[str, Any]:
        """Search for symbols by name."""
        await self.ensure_connected()

        # Use matching symbols
        matches = await self.ib.reqMatchingSymbolsAsync(query)

        if not matches:
            return {
                "query": query,
                "results": [],
                "count": 0,
            }

        results = []
        for match in matches[:limit]:
            contract = match.contract
            results.append({
                "symbol": contract.symbol,
                "security_type": contract.secType,
                "exchange": contract.primaryExchange or contract.exchange,
                "currency": contract.currency,
                "description": match.derivativeSecTypes if hasattr(match, "derivativeSecTypes") else None,
            })

        return {
            "query": query,
            "results": results,
            "count": len(results),
        }
