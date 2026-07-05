import dspy
import os
import yfinance as yf

# --------------------------------
# CONFIGURE OLLAMA ENDPOINT
# --------------------------------
os.environ["OLLAMA_HOST"] = "http://localhost:11434"

lm = dspy.LM(
    model="ollama/gpt-oss:latest",
    api_base="http://localhost:11434",
)
dspy.configure(lm=lm)

# --------------------------------
# FETCH STOCK DATA WITH REAL LABEL
# --------------------------------
def get_stock_data_with_label(symbol):
    """
    Fetch stock data and calculate REAL direction based on actual price movement
    Compares last close with previous close to determine 'up' or 'down'
    """
    stock = yf.Ticker(symbol)
    hist = stock.history(period="5d")  # last 5 trading days
    
    if len(hist) < 2:
        print(f"Warning: Not enough data for {symbol}")
        return None
    
    # Get last two days
    latest_close = float(hist["Close"].iloc[-1])
    previous_close = float(hist["Close"].iloc[-2])
    latest_volume = int(hist["Volume"].iloc[-1])
    
    # Calculate REAL direction based on actual price change
    actual_direction = "up" if latest_close > previous_close else "down"
    
    # Calculate percentage change for reference
    pct_change = ((latest_close - previous_close) / previous_close) * 100
    
    return {
        "last_close": latest_close,
        "previous_close": previous_close,
        "volume": latest_volume,
        "direction": actual_direction,
        "pct_change": pct_change
    }

# --------------------------------
# DSPy SIGNATURE + MODULE WITH ADDITIONAL FIELDS
# --------------------------------
class StockPredict(dspy.Signature):
    symbol = dspy.InputField()
    last_close = dspy.InputField()
    volume = dspy.InputField()
    direction = dspy.OutputField(desc="Predict 'up' or 'down'")

class StockPredictModule(dspy.Module):
    def __init__(self):
        super().__init__()
        self.predict = dspy.Predict(StockPredict)

    def forward(self, symbol, last_close=None, volume=None):
        # Forward pass using all features
        return self.predict(symbol=symbol, last_close=last_close, volume=volume)

# Custom metric
def exact_match_metric(example, pred, trace=None):
    return pred.direction.lower() == example.direction.lower()

predictor = StockPredictModule()

# --------------------------------
# TRAINING EXAMPLES WITH REAL LABELS
# --------------------------------
train_symbols = ["AAPL", "GOOGL", "TSLA", "MSFT", "META", "NVDA", "AMD", "INTC"]
train_examples = []


print("\n=== Fetching Real Training Data ===")
print(f"{'Symbol':<10}{'Previous':<12}{'Latest':<12}{'Change %':<10}{'Direction':<10}")
print("-" * 54)

for sym in train_symbols:
    data = get_stock_data_with_label(sym)
    if data:  # Only add if we got valid data
        print(f"{sym:<10}${data['previous_close']:<11.2f}${data['last_close']:<11.2f}"
              f"{data['pct_change']:<9.2f}%{data['direction']:<10}")
        
        example = dspy.Example(
            symbol=sym,
            last_close=data["last_close"],
            volume=data["volume"],
            direction=data["direction"]
        ).with_inputs("symbol", "last_close", "volume")
        train_examples.append(example)

# --------------------------------
# OPTIMIZATION USING BOOTSTRAP FEW-SHOT
# --------------------------------
print(f"\n=== Optimizing with {len(train_examples)} training examples ===")
optimizer = dspy.BootstrapFewShot(
    metric=exact_match_metric,
    max_bootstrapped_demos=3,
    max_labeled_demos=4,
    max_rounds=1
)

optimized_predictor = optimizer.compile(predictor, trainset=train_examples)

# --------------------------------
# OPTIMIZATION SUMMARY
# --------------------------------
print("\n=== Optimization Summary (Training Set Performance) ===")
print(f"{'Symbol':<10}{'Predicted':<12}{'Actual':<12}{'Match':<6}")
print("-" * 40)

correct = 0
for ex in train_examples:
    pred_obj = optimized_predictor(
        ex.symbol, last_close=ex.last_close, volume=ex.volume
    )
    match = pred_obj.direction.lower() == ex.direction.lower()
    if match:
        correct += 1
    print(f"{ex.symbol:<10}{pred_obj.direction:<12}{ex.direction:<12}{str(match):<6}")

accuracy = (correct / len(train_examples)) * 100 if train_examples else 0
print(f"\nTraining Accuracy: {accuracy:.1f}% ({correct}/{len(train_examples)})")

# --------------------------------
# TEST NEW STOCKS WITH REAL VALIDATION
# --------------------------------
new_symbols = ["INFY", "AMZN", "NFLX"]
print("\n=== Predictions for New Stocks (with Actual Direction) ===")
print(f"{'Symbol':<10}{'Predicted':<12}{'Actual':<12}{'Match':<8}{'Last Close':<12}{'Volume':<12}")
print("-" * 68)

correct_test = 0
valid_tests = 0

for sym in new_symbols:
    data = get_stock_data_with_label(sym)
    if data:
        pred_obj = optimized_predictor(
            sym, last_close=data["last_close"], volume=data["volume"]
        )
        match = pred_obj.direction.lower() == data["direction"].lower()
        if match:
            correct_test += 1
        valid_tests += 1
        
        print(f"{sym:<10}{pred_obj.direction:<12}{data['direction']:<12}{str(match):<8}"
              f"${data['last_close']:<11.2f}{data['volume']:<12}")

if valid_tests > 0:
    test_accuracy = (correct_test / valid_tests) * 100
    print(f"\nTest Accuracy: {test_accuracy:.1f}% ({correct_test}/{valid_tests})")