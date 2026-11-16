# Base price is KES 899. 
CURRENCY_RATES = {
    'Kenya': {'currency': 'KES', 'symbol': 'KSh', 'rate': 1.0},
    'Uganda': {'currency': 'UGX', 'symbol': 'USh', 'rate': 28.0},
    'Tanzania': {'currency': 'TZS', 'symbol': 'TSh', 'rate': 17.5}, 
    'Nigeria': {'currency': 'NGN', 'symbol': '₦', 'rate': 10.5},
    'Zambia': {'currency': 'ZMW', 'symbol': 'ZK', 'rate': 0.18},
    'Ghana': {'currency': 'GHS', 'symbol': 'GH₵', 'rate': 0.10},
    'South Africa': {'currency': 'ZAR', 'symbol': 'R', 'rate': 0.14},
}

def get_local_amount(country):
    # Normalize country name to match dictionary keys
    country_key = country.strip().title() 
    data = CURRENCY_RATES.get(country_key, {'currency': 'KES', 'symbol': 'KSh', 'rate': 1.0})
    local_amount = round(899 * data['rate'], 2)
    return data['currency'], data['symbol'], local_amount