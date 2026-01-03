import pandas as pd
import json
import numpy as np
import os

MAX_POINTS_ON_GLOBE = 10000

def clean_data(df):
    """Cleans the UFO sightings dataframe."""
    # Convert datetime column to datetime objects, coercing errors
    df['datetime'] = pd.to_datetime(df['datetime'], errors='coerce')

    # Drop rows where datetime conversion failed
    df.dropna(subset=['datetime'], inplace=True)

    # Extract year, month, hour
    df['year'] = df['datetime'].dt.year
    df['month'] = df['datetime'].dt.month
    df['hour'] = df['datetime'].dt.hour

    # Clean numeric columns: duration (seconds), latitude, longitude
    df['duration_seconds'] = pd.to_numeric(df['duration_seconds'], errors='coerce')
    
    # --- Added: Filter out extremely long or zero durations for more meaningful stats ---
    # Cap at 1 week (604800s) for sanity, ensure positive duration
    df = df[(df['duration_seconds'] > 0) & (df['duration_seconds'] < 604800)] 


    df['latitude'] = pd.to_numeric(df['latitude'], errors='coerce')
    df['longitude'] = pd.to_numeric(df['longitude'], errors='coerce')

    # Handle missing or problematic geographic data
    # Also ensure duration_seconds is not NaN after its cleaning, as it's now more critical
    df.dropna(subset=['latitude', 'longitude', 'duration_seconds'], inplace=True)
    df = df[(df['latitude'] >= -90) & (df['latitude'] <= 90)]
    df = df[(df['longitude'] >= -180) & (df['longitude'] <= 180)]

    if 'shape' in df.columns:
        df['shape'] = df['shape'].astype(str).str.lower().str.strip()
        # Consolidate various forms of unknown/other
        df['shape'].replace(['unknown', 'other', 'nan', '', 'na', 'unspecified'], 'various', inplace=True)
        df['shape'] = df['shape'].fillna('various') # Ensure no NaNs in shape after cleaning

    if 'country' in df.columns:
        df['country'] = df['country'].astype(str).str.lower().str.strip()
        df.loc[df['country'] == 'gb', 'country'] = 'uk'
        df.loc[df['country'] == '', 'country'] = 'unknown' # Handle empty strings
        df['country'] = df['country'].fillna('unknown')


    if 'state' in df.columns:
        df['state'] = df['state'].astype(str).str.upper().str.strip()
        df.loc[df['state'] == '', 'state'] = 'UNKNOWN' # Handle empty strings
        df['state'] = df['state'].fillna('UNKNOWN')


    return df

def perform_eda(df):
    """Performs basic and advanced EDA and prepares summary."""
    print("--- UFO Sightings EDA Insights ---")
    print(f"\nTotal cleaned sightings suitable for analysis: {len(df)}")

    # --- Basic EDA ---
    median_duration_overall = df['duration_seconds'].median() if 'duration_seconds' in df and not df['duration_seconds'].empty else None
    if median_duration_overall is not None:
        print(f"Overall median sighting duration: {median_duration_overall:.2f} seconds")
    else:
        print("Overall median sighting duration: Not available")

    sightings_by_year = df['year'].value_counts().sort_index()
    # Using pandas to generate month names for robustness
    month_map = {i: pd.Timestamp(f'2000-{i}-01').strftime('%b') for i in range(1, 13)}
    sightings_by_month_named = df['month'].value_counts().sort_index().rename(index=month_map)
    
    peak_month_name = sightings_by_month_named.idxmax() if not sightings_by_month_named.empty else "N/A"
    print(f"Peak sighting month: {peak_month_name}")

    sightings_by_hour = df['hour'].value_counts().sort_index()
    peak_hour_numeric = sightings_by_hour.idxmax() if not sightings_by_hour.empty else None
    peak_hour_readable = f"{int(peak_hour_numeric)}:00 - {int(peak_hour_numeric)+1}:00" if peak_hour_numeric is not None else "N/A"
    print(f"Peak sighting hour (24h format): {peak_hour_readable}")

    valid_countries = df[(df['country'].notna()) & (df['country'] != 'unknown')]['country']
    top_countries = valid_countries.value_counts().nlargest(5) if not valid_countries.empty else pd.Series(dtype='int')

    us_sightings = df[(df['country'] == 'us') & (df['state'].notna()) & (df['state'] != 'UNKNOWN')]
    top_states_us = us_sightings['state'].value_counts().nlargest(5) if not us_sightings.empty else pd.Series(dtype='int')

    valid_shapes_df = df[(df['shape'].notna()) & (df['shape'] != 'various')]
    top_shapes_series = valid_shapes_df['shape'].value_counts().nlargest(10) if not valid_shapes_df.empty else pd.Series(dtype='int')
    most_common_shape = top_shapes_series.index[0] if len(top_shapes_series) > 0 else "N/A"
    second_most_common_shape = top_shapes_series.index[1] if len(top_shapes_series) > 1 else "N/A"
    print(f"Most common reported shape (excluding 'various'): {most_common_shape}")

    peak_year_report = str(sightings_by_year.idxmax()) if not sightings_by_year.empty else "N/A"
    print(f"Year with most reports: {peak_year_report}")

    # --- Advanced Statistical Insights ---

    # 1. Sighting Duration by UFO Shape (Top 5 shapes)
    durations_by_shape = {}
    if not top_shapes_series.empty and 'duration_seconds' in valid_shapes_df.columns:
        print("\nMedian Sighting Duration (seconds) by Top UFO Shapes:")
        # Iterate over the top N shapes if available, ensuring the shape exists in valid_shapes_df
        for shape in top_shapes_series.head(5).index: # Focus on top 5 for summary
            shape_data = valid_shapes_df[valid_shapes_df['shape'] == shape]
            if not shape_data.empty and not shape_data['duration_seconds'].dropna().empty:
                median_dur = shape_data['duration_seconds'].median()
                durations_by_shape[shape] = round(median_dur, 2) if pd.notna(median_dur) else None
                print(f"  - {shape.capitalize()}: {durations_by_shape[shape] if durations_by_shape[shape] is not None else 'N/A'}")
            else:
                durations_by_shape[shape] = None # Store None if no valid duration data for this shape
                print(f"  - {shape.capitalize()}: N/A (no duration data)")


    # 2. Shape Distribution During Peak Sighting Hour
    top_shapes_in_peak_hour_summary = "N/A"
    peak_hour_dominant_shape = "N/A"
    if peak_hour_numeric is not None and not df[df['hour'] == peak_hour_numeric].empty:
        peak_hour_sightings = df[(df['hour'] == peak_hour_numeric) & (df['shape'] != 'various') & (df['shape'].notna())]
        if not peak_hour_sightings.empty:
            peak_hour_shapes_dist = peak_hour_sightings['shape'].value_counts(normalize=True).nlargest(3) # Top 3
            if not peak_hour_shapes_dist.empty:
                peak_hour_dominant_shape = peak_hour_shapes_dist.index[0]
                top_shapes_in_peak_hour_summary = ", ".join([f"{s.capitalize()} ({p*100:.1f}%)" for s, p in peak_hour_shapes_dist.items()])
                print(f"\nDuring peak hour ({peak_hour_readable}), top shapes: {top_shapes_in_peak_hour_summary}")
            else:
                 print(f"\nNo dominant shapes found during peak hour ({peak_hour_readable}) after excluding 'various'.")
        else:
            print(f"\nNo non-'various' shape data available for the peak hour ({peak_hour_readable}).")
    else:
        print("\nPeak hour not determinable or no sightings in peak hour for shape distribution analysis.")


    # 3. Sighting Duration: Night vs. Day
    df_copy = df.copy()
    df_copy['time_of_day'] = df_copy['hour'].apply(lambda h: 'Night (18:00-05:59)' if (18 <= h <= 23 or 0 <= h <= 5) else 'Day (06:00-17:59)')
    
    night_durations = df_copy[df_copy['time_of_day'] == 'Night (18:00-05:59)']['duration_seconds'].dropna()
    day_durations = df_copy[df_copy['time_of_day'] == 'Day (06:00-17:59)']['duration_seconds'].dropna()

    median_duration_night = night_durations.median() if not night_durations.empty else None
    median_duration_day = day_durations.median() if not day_durations.empty else None
    
    print("\nMedian Sighting Duration by Time of Day:")
    print(f"  - Night: {median_duration_night:.2f}s" if pd.notna(median_duration_night) else "  - Night: N/A")
    print(f"  - Day: {median_duration_day:.2f}s" if pd.notna(median_duration_day) else "  - Day: N/A")

    # 4. Proportion of Long-Duration Sightings
    long_duration_threshold_sec = 300 # 5 minutes
    long_duration_threshold_sec_2 = 3600 # 1 hour
    
    count_long_duration = len(df[df['duration_seconds'] > long_duration_threshold_sec])
    proportion_long_duration = (count_long_duration / len(df)) * 100 if len(df) > 0 else 0
    count_very_long_duration = len(df[df['duration_seconds'] > long_duration_threshold_sec_2])
    proportion_very_long_duration = (count_very_long_duration / len(df)) * 100 if len(df) > 0 else 0

    print(f"\nProportion of sightings lasting over 5 minutes ({long_duration_threshold_sec}s): {proportion_long_duration:.2f}%")
    print(f"Proportion of sightings lasting over 1 hour ({long_duration_threshold_sec_2}s): {proportion_very_long_duration:.2f}%")


    print("\n--- End of EDA Insights ---")

    return {
        "total_sightings": len(df),
        "median_duration_seconds_overall": float(median_duration_overall) if pd.notna(median_duration_overall) else None,
        "peak_month": peak_month_name,
        "peak_hour_readable": peak_hour_readable,
        "peak_hour_numeric": int(peak_hour_numeric) if pd.notna(peak_hour_numeric) else None, # ensure int if not None
        "most_common_shape": most_common_shape,
        "second_most_common_shape": second_most_common_shape,
        "peak_year_of_reports": peak_year_report,
        
        "median_durations_by_top_shapes": durations_by_shape, #This is a dict
        "top_shapes_in_peak_hour_summary": top_shapes_in_peak_hour_summary, #This is a string
        "peak_hour_dominant_shape": peak_hour_dominant_shape, #This is a string
        "median_duration_night_seconds": float(median_duration_night) if pd.notna(median_duration_night) else None,
        "median_duration_day_seconds": float(median_duration_day) if pd.notna(median_duration_day) else None,
        "proportion_over_5_min_percent": round(proportion_long_duration, 2),
        "proportion_over_1_hour_percent": round(proportion_very_long_duration, 2),

        "sightings_by_year": {int(k):int(v) for k,v in sightings_by_year.to_dict().items()}, # Ensure keys are int
        "sightings_by_month": sightings_by_month_named.to_dict(),
        "sightings_by_hour": {int(k):int(v) for k,v in sightings_by_hour.to_dict().items()}, # Ensure keys are int
        "top_countries": top_countries.to_dict(),
        "top_states_us": top_states_us.to_dict(),
        "top_shapes": top_shapes_series.to_dict()
    }

def export_globe_data(df, filename="data/sightings_for_globe.json"):
    """Exports necessary data for the 3D globe visualization, with sampling."""
    if df.empty:
        print("DataFrame is empty, cannot export globe data.")
        # Create an empty file or a file with an empty list
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        with open(filename, 'w') as f:
            json.dump([], f)
        print(f"Empty globe data file created at {filename}")
        return

    if len(df) > MAX_POINTS_ON_GLOBE:
        print(f"Sampling down to {MAX_POINTS_ON_GLOBE} points from {len(df)} for globe visualization.")
        globe_df = df.sample(n=MAX_POINTS_ON_GLOBE, random_state=42).copy()
    else:
        globe_df = df.copy()

    if 'duration_seconds' in globe_df.columns and not globe_df['duration_seconds'].dropna().empty:
        min_duration, max_duration_cap = 1.0, 3600.0 * 24 # Cap at 1 day for visualization scaling
        globe_df.loc[:, 'positive_duration'] = globe_df['duration_seconds'].clip(lower=1e-6) # Should be positive from clean_data
        globe_df.loc[:, 'normalized_duration'] = globe_df['positive_duration'].clip(min_duration, max_duration_cap)
        
        log_min_duration = np.log(min_duration)
        log_max_duration_cap = np.log(max_duration_cap) # Max for normalization, not necessarily data max
        
        if log_max_duration_cap > log_min_duration:
            # Normalize against the capped max duration for consistent scaling
            log_norm_duration = (np.log(globe_df['normalized_duration']) - log_min_duration) / \
                                (log_max_duration_cap - log_min_duration)
        else: 
            log_norm_duration = 0.1 
            
        globe_df.loc[:, 'magnitude'] = 0.03 + (log_norm_duration * 0.25) # Adjusted magnitude range slightly
        globe_df['magnitude'] = globe_df['magnitude'].fillna(0.03) # Default to min magnitude
    else:
        globe_df['magnitude'] = 0.03 

    output_data = []
    for _, row in globe_df.iterrows():
        output_data.append({
            "lat": row['latitude'],
            "lng": row['longitude'],
            "alt": 0.005, 
            "radius": max(0.01, row.get('magnitude', 0.03)), # Ensure a minimum visible radius
            "color": "rgba(255, 255, 0, 0.7)" 
        })
    
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    with open(filename, 'w') as f:
        json.dump(output_data, f)
    print(f"\nGlobe data exported to {filename} with {len(output_data)} points.")


if __name__ == "__main__":
    raw_df = pd.DataFrame() # Initialize raw_df
    try:
        script_dir = os.path.dirname(os.path.realpath(__file__))
        # Try loading the full dataset first
        # Adjusted paths for 'docs' directory structure (data is in ../docs/data)
        csv_path_full = os.path.join(script_dir, '../docs/data/ufo_sightings_scrubbed.csv')
        csv_path_sample = os.path.join(script_dir, '../docs/data/dataset_sample.csv')
        
        csv_to_load = None
        if os.path.exists(csv_path_full):
            csv_to_load = csv_path_full
            print(f"Attempting to load full dataset: '{os.path.basename(csv_to_load)}'")
        elif os.path.exists(csv_path_sample):
            csv_to_load = csv_path_sample
            print(f"Full dataset not found. Attempting to load sample dataset: '{os.path.basename(csv_to_load)}'")
        else:
            print(f"Error: Neither '{os.path.basename(csv_path_full)}' nor '{os.path.basename(csv_path_sample)}' found. Place one in the 'docs/data' directory.")
            exit()
        
        raw_df = pd.read_csv(csv_to_load, low_memory=False, on_bad_lines='skip')
        print(f"Successfully loaded {len(raw_df)} rows from {os.path.basename(csv_to_load)}")
        
        # Standardize column names (idempotent)
        raw_df.columns = raw_df.columns.str.lower().str.strip().str.replace('[^A-Za-z0-9_]+', '', regex=True)
        
        # Specific renames - check if target doesn't already exist to prevent errors on re-runs
        rename_map = {
            'durationseconds': 'duration_seconds',
            'durationhoursmin': 'duration_hours_min',
            'durationseconds_1': 'duration_seconds' # example for a problematic column name if it occurs
        }
        # Ensure 'duration(seconds)' from sample is handled
        if 'durationseconds' not in raw_df.columns and 'durationseconds_1' in raw_df.columns: # Specific for NUFORC data variation
             raw_df.rename(columns={'durationseconds_1': 'duration_seconds'}, inplace=True)
        elif 'durationseconds' in raw_df.columns: # common nuforc name
             raw_df.rename(columns={'durationseconds': 'duration_seconds'}, inplace=True)


        # Apply general renames carefully
        for old_name, new_name in rename_map.items():
            if old_name in raw_df.columns and new_name not in raw_df.columns:
                raw_df.rename(columns={old_name: new_name}, inplace=True)
            # If new_name already exists but old_name also does (and isn't new_name), it's ambiguous
            # but we prioritize keeping new_name if it's already correct.

    except FileNotFoundError: # Should be caught by the explicit checks above
        print("Error: CSV file not found despite checks. Ensure a UFO sightings CSV is in the script's directory.")
        exit()
    except Exception as e:
        print(f"Error loading or performing initial rename on CSV: {e}")
        print(f"Columns in raw_df before error (if loaded): {raw_df.columns.tolist() if not raw_df.empty else 'Not loaded'}")
        exit()

    required_cols_check = ['datetime', 'latitude', 'longitude']
    if 'duration_seconds' not in raw_df.columns:
         print(f"CRITICAL: 'duration_seconds' column is missing after attempts to standardize. This column is vital. Available columns: {raw_df.columns.tolist()}")
         print("Please ensure your CSV contains a clear column for sighting duration in seconds (e.g., 'duration (seconds)', 'duration_seconds', 'durationseconds').")
         exit()


    missing_cols_after_load = [col for col in required_cols_check if col not in raw_df.columns]
    if missing_cols_after_load:
        print(f"Error: Missing essential columns after loading and initial rename: {missing_cols_after_load}. Available columns: {raw_df.columns.tolist()}")
        exit()

    df = raw_df.copy()
    print(f"Proceeding with cleaning {len(df)} rows...")
    df = clean_data(df)
    print(f"Data cleaning complete. {len(df)} rows remaining for analysis.")


    if df.empty:
        print("DataFrame is empty after cleaning. This could be due to strict cleaning rules removing all data, or issues with the raw data not meeting criteria (e.g., all records miss critical data like valid datetime, lat/lng, or positive durations).")
        if not raw_df.empty and 'duration_seconds' in raw_df.columns:
            print("Stats for 'duration_seconds' in raw_df BEFORE aggressive cleaning:")
            print(f"  Min: {pd.to_numeric(raw_df['duration_seconds'], errors='coerce').min()}, Max: {pd.to_numeric(raw_df['duration_seconds'], errors='coerce').max()}, Median: {pd.to_numeric(raw_df['duration_seconds'], errors='coerce').median()}")
            print(f"  Count of positive durations: {len(raw_df[pd.to_numeric(raw_df['duration_seconds'], errors='coerce') > 0])}")
        else:
            print("Raw data was empty or 'duration_seconds' column was not found in raw_df for pre-cleaning stats.")
        # Exit if no data to process
        # Create empty JSONs to prevent JS errors if frontend expects them
        data_dir = os.path.join(script_dir, '../docs/data')
        os.makedirs(data_dir, exist_ok=True)
        with open(os.path.join(data_dir, 'eda_summary.json'), 'w') as f: json.dump({}, f)
        export_globe_data(df, filename=os.path.join(data_dir, "sightings_for_globe.json")) # Will create empty globe data
        print("Exiting due to empty DataFrame after cleaning.")
        exit()


    eda_summary = perform_eda(df)
    
    data_dir = os.path.join(script_dir, '../docs/data')
    os.makedirs(data_dir, exist_ok=True) # Ensure data directory exists
    
    # Export data for globe
    export_globe_data(df.copy(), filename=os.path.join(data_dir, "sightings_for_globe.json")) # Pass a copy to be safe

    # Export EDA summary
    summary_path = os.path.join(data_dir, 'eda_summary.json')
    with open(summary_path, 'w') as f:
        class NpEncoder(json.JSONEncoder):
            def default(self, obj):
                if isinstance(obj, (np.integer, np.int64)): return int(obj)
                if isinstance(obj, (np.floating, np.float64)): return float(obj) # Handle numpy floats
                if isinstance(obj, np.ndarray): return obj.tolist()
                if isinstance(obj, pd.Timestamp): return obj.isoformat()
                if pd.isna(obj): return None # Handle pandas NaT or NaN directly for numeric fields
                return super(NpEncoder, self).default(obj)
        json.dump(eda_summary, f, indent=4, cls=NpEncoder, allow_nan=True) # Allow NaN for graceful nulls
    print(f"\nEDA summary exported to {summary_path}")
    print("\nPython script finished. Open index.html in your browser (preferably via a local server).")