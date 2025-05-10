import pandas as pd
import numpy as np


HEVY_DATA = "data/hevy/20250426_HevyExport.csv"

def _read_hevy_data():
    return pd.read_csv(HEVY_DATA, sep=",", encoding="utf-8")


def get_hevy_data():
    df = _read_hevy_data()
    df[["start_time", "end_time"]] = df[["start_time", "end_time"]].apply(pd.to_datetime, format="%d %b %Y, %H:%M")
    df["date"] = df["start_time"].dt.date
    df["id_workout"] = df.groupby(["date", "title"]).ngroup()  # Group by workout date and title
    df["id_workout"] = df["id_workout"].astype(str).str.pad(width=3, side="left", fillchar="0")  # Convert to string for unique ID creation

    # Group by workout ID
    dfs = []  # Create an empty list to store processed DataFrames

    df_workouts = []
    for id_workout, workout in df.groupby("id_workout"):
        df_exercises = []
        # Group exercises within each workout and create a unique ID
        ids = workout.groupby("exercise_title").ngroup()  # Group by exercise title
        workout["id_exercise"] = id_workout + "_" + ids.astype(str).str.pad(width=2, side="left", fillchar="0")  # Create unique exercise ID
        def one_rep_max(weight, reps):
            return weight * (1 + reps / 30) 
        for id_exercise, exercise in workout.groupby("id_exercise"):
            exercise["one_rep_max"] = max(one_rep_max(exercise["weight_kg"], exercise["reps"]))
            exercise["max_weight"] = exercise["weight_kg"].max()
            df_exercises.append(exercise)
        workout = pd.concat(df_exercises).reset_index(drop=True)  # Concatenate exercises within the workout
        dfs.append(workout)

    df_processed = pd.concat(dfs).reset_index(drop=True)  # Concatenate and reset index

    df_processed["set_index"] += 1  # Increment set_index to start from 1
    df_processed = df_processed[df_processed["reps"].notna()].copy()
    df_processed["reps"] = df_processed["reps"].astype(int)  # Convert reps to integer
    return df_processed

def _read_runkeeper_data():
    return pd.read_csv("data/runkeeper/cardioActivities.csv", sep=",", encoding="utf-8")

def normalize_duration_column(series):
    series = series.astype(str).str.strip()
    
    # Count the number of colons
    colon_counts = series.str.count(":")

    # Prepend "00:" to durations with only MM:SS
    series = np.where(colon_counts == 1, "00:" + series, series)

    return pd.to_timedelta(series)

def get_runkeeper_data():
    df = _read_runkeeper_data()
    cols = {
        'Activity Id': 'id_activity', 
        'Date': 'start_time', 
        'Type': 'type', 
        'Route Name': 'route_name', 
        'Distance (km)': 'distance_km',
        'Duration': 'duration', 
        'Average Pace': 'average_pace', 
        'Average Speed (km/h)': 'average_speed_kmh', 
        'Calories Burned': 'calories',
        'Climb (m)': 'climb_m', 
        'Average Heart Rate (bpm)': 'average_heart_rate_bpm', 
        r"Friend's Tagged": 'friends_tagged', 
        'Notes': 'notes',
        'GPX File': 'gpx_file',
    }
    df.rename(columns=cols, inplace=True)
    df["start_time"] = pd.to_datetime(df["start_time"], format="%Y-%m-%d %H:%M:%S")
    df["duration"] = normalize_duration_column(df["duration"])
    df["end_time"] = df["start_time"] + df["duration"]
    return df

get_runkeeper_data()
