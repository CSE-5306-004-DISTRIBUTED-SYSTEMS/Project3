import pandas as pd
import matplotlib.pyplot as plt
import os
import time

# --- Configuration ---
# The Locust load-tester service saves files with this prefix in the /mnt/results/ directory
CSV_PREFIX = "test_run_1"
INPUT_DIR = "test_results"
OUTPUT_DIR = "test_results/analysis"

def load_data(file_name):
    """Loads a CSV file into a pandas DataFrame, normalizing column names."""
    file_path = os.path.join(INPUT_DIR, file_name)
    print(f"Loading data from: {file_path}")
    if not os.path.exists(file_path):
        # NOTE: We specifically check for the history file, as it is the only required file.
        raise FileNotFoundError(f"Required file not found: {file_path}. Did the load test run correctly?")
    
    df = pd.read_csv(file_path)
    
    # Normalize column names (strip whitespace, convert to lowercase)
    df.columns = df.columns.str.strip().str.lower()
    
    # Process history file: Convert timestamp and calculate run time
    if 'stats_history' in file_name:
        if 'timestamp' not in df.columns:
             raise ValueError("The 'stats_history' file is missing the 'timestamp' column after normalization.")
             
        start_time = df['timestamp'].min()
        df['Run Time (s)'] = (df['timestamp'] - start_time) / 1000.0

    return df

def generate_graphs(history_df):
    """Generates and saves the two required performance graphs using only the history data."""
    
    # 1. Prepare for Graphing
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Standardize plot style
    plt.style.use('seaborn-v0_8-darkgrid')
    
    # Filter for aggregated stats (try different possible names)
    possible_names = ['aggregated', 'total', 'aggregate', 'all']
    throughput_df = history_df[history_df['name'].str.lower().isin(possible_names)]
    
    # Check if we found aggregated data
    if throughput_df.empty:
        print("[WARNING] No aggregated data found. Available names:")
        print(history_df['name'].unique())
        # Try using the first unique name as a fallback
        throughput_df = history_df.groupby('name').first().reset_index()
        if throughput_df.empty:
            print("[ERROR] No data available for analysis")
            return
    
    # --- GRAPH 1: Throughput (RPS) vs. Time ---
    
    # Calculate Total RPS using the correct column names from your CSV
    throughput_df['Total RPS'] = throughput_df['requests/s'] + throughput_df['failures/s']
    
    plt.figure(figsize=(12, 6))
    
    # Plot Total RPS (Success + Failure)
    plt.plot(throughput_df['Run Time (s)'], throughput_df['Total RPS'], 
             label='Total Throughput (RPS)', color='#3366cc', linewidth=2)
             
    # Plot Success RPS
    plt.plot(throughput_df['Run Time (s)'], throughput_df['requests/s'], 
             label='Successful RPS', color='#4CAF50', linewidth=1.5, linestyle='--')
    
    # Highlight the point where the number of users is maximum (using normalized lowercase)
    max_users = throughput_df['user count'].max()
    
    # Add a point for saturation, usually where failures spike or RPS drops
    saturation_point = throughput_df[throughput_df['failures/s'] > 0.01].iloc[0] if not throughput_df[throughput_df['failures/s'] > 0.01].empty else None
    
    if saturation_point is not None:
        plt.axvline(saturation_point['Run Time (s)'], color='red', linestyle=':', label='Saturation Point')
    
    plt.title(f'Application Throughput Over Time (Max Users: {max_users})', fontsize=16)
    plt.xlabel('Run Time (seconds)', fontsize=14)
    plt.ylabel('Requests Per Second (RPS)', fontsize=14)
    plt.legend()
    plt.grid(True, alpha=0.6)
    
    throughput_path = os.path.join(OUTPUT_DIR, f"{CSV_PREFIX}_throughput_vs_time.png")
    plt.savefig(throughput_path)
    plt.close()
    print(f"Generated Throughput vs. Time graph: {throughput_path}")
    
    
    # --- GRAPH 2: Latency (P95) vs. Concurrent Users ---
    
    # The '95%' column is provided by Locust
    p95_col = '95%'
    
    plt.figure(figsize=(12, 6))
    
    # Aggregate data by user count to get cleaner plot points for the ramp-up stages
    latency_summary = throughput_df.groupby('user count')['95%'].mean().reset_index()
    
    plt.plot(latency_summary['user count'], latency_summary['95%'], 
             label='95th Percentile Latency (Avg)', color='#ff6600', marker='o', markersize=6)

    plt.title(f'P95 Latency vs. Concurrent Users', fontsize=16)
    plt.xlabel('Concurrent User Count', fontsize=14)
    plt.ylabel('95th Percentile Response Time (ms)', fontsize=14)
    
    # Add a horizontal line to indicate a common acceptable SLA (e.g., 500ms)
    plt.axhline(y=500, color='r', linestyle='-', linewidth=1, alpha=0.7, label='500ms SLA Target')
    
    plt.legend()
    plt.grid(True, alpha=0.6)
    
    latency_path = os.path.join(OUTPUT_DIR, f"{CSV_PREFIX}_latency_vs_users.png")
    plt.savefig(latency_path)
    plt.close()
    print(f"Generated P95 Latency vs. Users graph: {latency_path}")


def main():
    """Main function to run the analysis."""
    print(f"Starting analysis of load test data...")
    
    # The only file we now explicitly require is the stats history file
    history_file = f"{CSV_PREFIX}_stats_history.csv"

    try:
        # Load the only required file
        history_df = load_data(history_file)
        
        # Generate the required graphs (requests_df is no longer needed)
        generate_graphs(history_df)
        
        print("\nAnalysis Complete! Graphs are saved in the 'test_results/analysis' directory.")
        # 

    except FileNotFoundError as e:
        print(f"\n[ERROR] Analysis failed: {e}")
        print("Please ensure the file 'test_results/test_run_1_stats_history.csv' exists.")
    except Exception as e:
        print(f"\n[ERROR] An unexpected error occurred during analysis: {e}")
        # Provide debug column info if possible
        if 'history_df' in locals():
            print(f"History DF Columns: {history_df.columns.tolist()}")

if __name__ == "__main__":
    # Wait briefly for filesystems to sync after the load test container exits
    time.sleep(5)
    main()
