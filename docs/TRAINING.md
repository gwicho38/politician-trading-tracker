# ML Model Training

## Training Code Locations

```
python-etl-service/app/services/
├── feature_pipeline.py
│   ├── class FeaturePipeline       (line 35)   - Feature extraction
│   ├── prepare_training_data()     (line 82)   - Fetch disclosures, build features, label data
│   ├── class TrainingJob           (line 444)  - Training job wrapper
│   └── TrainingJob.run()           (line 481)  - ORCHESTRATES THE FULL TRAINING FLOW:
│                                                 1. Create model record in DB
│                                                 2. Prepare training data
│                                                 3. Train model
│                                                 4. Save model artifact
│                                                 5. Update DB with metrics
│
└── ml_signal_model.py
    ├── class CongressSignalModel   (line 56)   - XGBoost model wrapper
    ├── train()                     (line 129)  - ACTUAL XGBOOST TRAINING:
    │                                             - Train/val split
    │                                             - Feature scaling
    │                                             - XGBClassifier.fit()
    │                                             - Compute accuracy, F1, feature importance
    └── predict()                   (line 205)  - Make predictions
```

## Training a Model

```bash
mcli run ml train-watch
```

This command:
1. Triggers training via the ETL service API
2. Streams real-time logs from Fly.io
3. Shows training progress and final metrics

### Options

```bash
mcli run ml train-watch --lookback 180    # Use 6 months of data (default: 365)
mcli run ml train-watch --model lightgbm  # Use LightGBM instead of XGBoost
mcli run ml train-watch -v                # Verbose: show all logs
mcli run ml train-watch --job <job_id>    # Watch existing job
```

## Checking Model Status

```bash
mcli run ml active    # Show active model info with metrics & features
mcli run ml status    # List all trained models
mcli run ml health    # Check ML service health
mcli run ml list      # List all models with details
```

## Testing & Predictions

```bash
mcli run ml predict AAPL                  # Get prediction for a ticker
mcli run ml predict NVDA -p 5 -r 3.0 -b   # Custom features
mcli run ml test                          # Test on default tickers
mcli run ml test --scenarios              # Run multiple test scenarios
```

## Model Management

```bash
mcli run ml features            # Show feature importance for active model
mcli run ml features <model_id> # Show features for specific model
mcli run ml activate <model_id> # Activate a specific model
```
