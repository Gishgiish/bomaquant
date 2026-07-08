# Centralized, validated list of supported NSE symbols
NSE_SYMBOLS = {
    "SCOM": "Safaricom PLC",
    "EQTY": "Equity Group Holdings",
    "KCB": "KCB Group",
    "NCBA": "NCBA Group",
    "COOP": "Co-operative Bank",
    "BRIT": "Britam Holdings",
    "CNTM": "Centum Investment",
    "EABL": "East African Breweries",
    "NSE20": "NSE 20 Share Index"  # Special case for index
}

def is_valid_nse_symbol(symbol: str) -> bool:
    """Check if symbol is in our supported list"""
    return symbol.upper() in NSE_SYMBOLS

def get_symbol_name(symbol: str) -> str:
    """Get full company name for symbol"""
    return NSE_SYMBOLS.get(symbol.upper(), "Unknown")