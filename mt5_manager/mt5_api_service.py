"""
MT5 API Service - Connects to MT5 instances via REST API (port 8001)
Provides account info, positions, and trade history.
"""
import requests
from typing import Dict, List, Optional
from datetime import datetime, timedelta


class MT5ApiService:
    """Service to connect to MT5 containers via their REST API."""
    
    def __init__(self, default_timeout: int = 10):
        self.default_timeout = default_timeout
    
    def _make_request(self, host: str, port: str, endpoint: str, method: str = "GET", data: dict = None) -> Dict:
        """Makes a request to the MT5 API."""
        try:
            url = f"http://{host}:{port}/{endpoint}"
            
            if method == "GET":
                response = requests.get(url, timeout=self.default_timeout)
            else:
                response = requests.post(url, json=data, timeout=self.default_timeout)
            
            if response.status_code == 200:
                return {"success": True, "data": response.json()}
            else:
                return {"success": False, "error": f"HTTP {response.status_code}: {response.text}"}
                
        except requests.exceptions.ConnectionError:
            return {"success": False, "error": "Connection refused - MT5 API may not be running"}
        except requests.exceptions.Timeout:
            return {"success": False, "error": "Request timed out"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_account_info(self, host: str = "localhost", port: str = "8001") -> Dict:
        """
        Gets account information from MT5.
        Returns: balance, equity, profit, margin, free_margin, leverage
        """
        result = self._make_request(host, port, "account_info")
        
        if result["success"]:
            data = result["data"]
            return {
                "success": True,
                "balance": data.get("balance", 0),
                "equity": data.get("equity", 0),
                "profit": data.get("profit", 0),
                "margin": data.get("margin", 0),
                "free_margin": data.get("free_margin", 0),
                "leverage": data.get("leverage", 1),
                "currency": data.get("currency", "USD"),
                "name": data.get("name", "Unknown"),
                "server": data.get("server", "Unknown"),
                "company": data.get("company", "Unknown")
            }
        return result
    
    def get_positions(self, host: str = "localhost", port: str = "8001") -> Dict:
        """
        Gets open positions from MT5.
        Returns: list of positions with symbol, type, volume, profit, etc.
        """
        result = self._make_request(host, port, "positions")
        
        if result["success"]:
            positions = result["data"] if isinstance(result["data"], list) else result["data"].get("positions", [])
            
            formatted = []
            for pos in positions:
                formatted.append({
                    "ticket": pos.get("ticket", 0),
                    "symbol": pos.get("symbol", ""),
                    "type": "BUY" if pos.get("type", 0) == 0 else "SELL",
                    "volume": pos.get("volume", 0),
                    "price_open": pos.get("price_open", 0),
                    "price_current": pos.get("price_current", 0),
                    "profit": pos.get("profit", 0),
                    "swap": pos.get("swap", 0),
                    "sl": pos.get("sl", 0),
                    "tp": pos.get("tp", 0),
                    "time": pos.get("time", "")
                })
            
            return {
                "success": True,
                "positions": formatted,
                "total_profit": sum(p["profit"] for p in formatted),
                "count": len(formatted)
            }
        return result
    
    def get_orders(self, host: str = "localhost", port: str = "8001") -> Dict:
        """Gets pending orders from MT5."""
        result = self._make_request(host, port, "orders")
        
        if result["success"]:
            orders = result["data"] if isinstance(result["data"], list) else result["data"].get("orders", [])
            return {
                "success": True,
                "orders": orders,
                "count": len(orders)
            }
        return result
    
    def get_history(self, host: str = "localhost", port: str = "8001", days: int = 7) -> Dict:
        """
        Gets trade history from MT5.
        Returns: list of closed deals with profit/loss.
        """
        result = self._make_request(host, port, f"history?days={days}")
        
        if result["success"]:
            deals = result["data"] if isinstance(result["data"], list) else result["data"].get("deals", [])
            
            # Calculate summary
            total_profit = 0
            total_trades = 0
            wins = 0
            losses = 0
            
            for deal in deals:
                profit = deal.get("profit", 0)
                if deal.get("entry", 0) == 1:  # Exit deal
                    total_profit += profit
                    total_trades += 1
                    if profit > 0:
                        wins += 1
                    elif profit < 0:
                        losses += 1
            
            win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
            
            return {
                "success": True,
                "deals": deals,
                "summary": {
                    "total_profit": round(total_profit, 2),
                    "total_trades": total_trades,
                    "wins": wins,
                    "losses": losses,
                    "win_rate": round(win_rate, 1)
                }
            }
        return result
    
    def check_connection(self, host: str = "localhost", port: str = "8001") -> bool:
        """Checks if MT5 API is accessible."""
        result = self._make_request(host, port, "ping")
        return result.get("success", False)


# Singleton instance
mt5_api = MT5ApiService()
