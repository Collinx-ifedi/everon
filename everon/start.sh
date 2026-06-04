#!/bin/bash
# 1. Start the autonomous background data collector loop in the background
python main.py &

# 2. Start the Streamlit frontend UI on Render's assigned dynamic port
streamlit run app.py --server.port $PORT --server.address 0.0.0.0